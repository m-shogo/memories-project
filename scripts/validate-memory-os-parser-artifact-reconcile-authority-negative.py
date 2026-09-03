#!/usr/bin/env python3
"""Prove parser artifact reconcile rejects authority substitution and no-op validator bypass."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-parser-artifact-registry.py"
CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location(
        "parser_artifact_reconciler_authority_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load parser reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Path, label: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            message = str(exc)
            require(
                "authority drift" in message or "missing or escapes repository" in message,
                f"{label} rejected for unrelated reason: {message}",
            )
        else:
            raise NegativeFailure(f"parser reconciler accepted authority substitution: {label}")
        require(
            CONTRACT_PATH.read_bytes() == original_contract,
            f"parser contract mutated after authority substitution: {label}",
        )
        require(
            STATUS_PATH.read_bytes() == original_status,
            f"production status mutated after authority substitution: {label}",
        )
    finally:
        setattr(reconciler, attribute, original_attribute)
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def expect_noop_validator_rejection(reconciler: Any) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    original_runner = reconciler.run_canonical_validators

    class SyntheticAggregateFailure(RuntimeError):
        pass

    try:
        # Converge only inside this negative harness, then prove an already-current
        # direct reconcile still invokes the complete canonical validator chain.
        reconciler.main()
        converged_contract = CONTRACT_PATH.read_bytes()
        converged_status = STATUS_PATH.read_bytes()

        def reject_noop_validation() -> None:
            raise SyntheticAggregateFailure("synthetic no-op aggregate rejection")

        reconciler.run_canonical_validators = reject_noop_validation
        try:
            reconciler.main()
        except SyntheticAggregateFailure:
            pass
        else:
            raise NegativeFailure(
                "parser reconciler skipped canonical validators on already-current authority"
            )
        require(
            CONTRACT_PATH.read_bytes() == converged_contract,
            "parser contract mutated after no-op aggregate rejection",
        )
        require(
            STATUS_PATH.read_bytes() == converged_status,
            "production status mutated after no-op aggregate rejection",
        )
    finally:
        reconciler.run_canonical_validators = original_runner
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def expect_atomic_transport_binding(reconciler: Any) -> None:
    original_replace = reconciler.os.replace

    def reject_mutable_replace(*_args: Any, **_kwargs: Any) -> None:
        raise NegativeFailure("mutable os.replace transport was invoked")

    with tempfile.TemporaryDirectory(prefix="parser-artifact-atomic-negative-") as temp_dir:
        target = Path(temp_dir) / "authority.json"
        target.write_bytes(b"before\n")
        os.chmod(target, 0o640)
        before_mode = target.stat().st_mode & 0o7777
        reconciler.os.replace = reject_mutable_replace
        try:
            reconciler.atomic_write_bytes(target, b"after\n")
        finally:
            reconciler.os.replace = original_replace

        require(target.read_bytes() == b"after\n", "bound atomic writer did not replace payload")
        require(
            target.stat().st_mode & 0o7777 == before_mode,
            "bound atomic writer did not preserve target mode",
        )
        require(
            not list(target.parent.glob(f".{target.name}.*.tmp")),
            "bound atomic writer left temporary residue",
        )


def expect_transaction_transport_binding(reconciler: Any) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    original_write = reconciler.write
    original_atomic = reconciler.atomic_write_bytes
    original_runner = reconciler.run_canonical_validators

    class SyntheticPostWriteFailure(RuntimeError):
        pass

    def reject_mutable_helper(*_args: Any, **_kwargs: Any) -> None:
        raise NegativeFailure("mutable transaction helper was invoked")

    def fail_post_write() -> None:
        raise SyntheticPostWriteFailure("synthetic post-write validator failure")

    contract = json.loads(original_contract.decode("utf-8"))
    status = json.loads(original_status.decode("utf-8"))
    contract["_syntheticAtomicTransportNegative"] = True
    status["_syntheticAtomicTransportNegative"] = True

    contract_mode = CONTRACT_PATH.stat().st_mode & 0o7777
    status_mode = STATUS_PATH.stat().st_mode & 0o7777
    reconciler.write = reject_mutable_helper
    reconciler.atomic_write_bytes = reject_mutable_helper
    reconciler.run_canonical_validators = reject_mutable_helper
    try:
        try:
            reconciler.commit_authority_transaction(
                contract,
                status,
                validator_runner=fail_post_write,
            )
        except SyntheticPostWriteFailure:
            pass
        else:
            raise NegativeFailure("synthetic post-write failure was not propagated")

        require(
            CONTRACT_PATH.read_bytes() == original_contract,
            "parser contract was not byte-for-byte rolled back by bound transport",
        )
        require(
            STATUS_PATH.read_bytes() == original_status,
            "production status was not byte-for-byte rolled back by bound transport",
        )
        require(
            CONTRACT_PATH.stat().st_mode & 0o7777 == contract_mode,
            "parser contract mode changed after bound rollback",
        )
        require(
            STATUS_PATH.stat().st_mode & 0o7777 == status_mode,
            "production status mode changed after bound rollback",
        )
        for target in (CONTRACT_PATH, STATUS_PATH):
            require(
                not list(target.parent.glob(f".{target.name}.*.tmp")),
                f"temporary residue remained after bound rollback: {target.name}",
            )
    finally:
        reconciler.write = original_write
        reconciler.atomic_write_bytes = original_atomic
        reconciler.run_canonical_validators = original_runner
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_reconciler()
    reconciler.enforce_runtime_authorities()
    cases = (
        ("WRITER_PATH", reconciler.VALIDATOR_PATH, "writer executable"),
        ("VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "parser validator executable"),
        ("VERSION_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "version validator executable"),
        ("OPERABILITY_VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "operability validator executable"),
        ("CONTRACT_PATH", reconciler.STATUS_PATH, "parser contract path"),
        ("STATUS_PATH", reconciler.CONTRACT_PATH, "production status path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)
    expect_atomic_transport_binding(reconciler)
    expect_transaction_transport_binding(reconciler)
    expect_noop_validator_rejection(reconciler)
    print(
        "PASS: parser reconcile rejects authority substitutions and pins atomic transport/rollback"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"PARSER RECONCILE AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
