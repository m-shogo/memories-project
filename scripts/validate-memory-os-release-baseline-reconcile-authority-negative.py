#!/usr/bin/env python3
"""Prove release baseline reconcile rejects authority substitution and no-op validator bypass."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-release-baseline-registry.py"
CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location(
        "release_baseline_reconciler_authority_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load release reconciler")
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
            raise NegativeFailure(f"release reconciler accepted authority substitution: {label}")
        require(
            CONTRACT_PATH.read_bytes() == original_contract,
            f"release contract mutated after authority substitution: {label}",
        )
        require(
            STATUS_PATH.read_bytes() == original_status,
            f"production status mutated after authority substitution: {label}",
        )
    finally:
        setattr(reconciler, attribute, original_attribute)
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def prove_noop_runs_canonical_validators(reconciler: Any) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    original_contract_reconcile = reconciler.reconcile_contract_readiness
    original_status_reconcile = reconciler.reconcile_status
    original_runner = reconciler.run_canonical_validators
    calls = 0

    def unchanged_contract(*_: Any, **__: Any) -> bool:
        return False

    def unchanged_status(*_: Any, **__: Any) -> bool:
        return False

    def rejected_validator_chain() -> None:
        nonlocal calls
        calls += 1
        raise subprocess.CalledProcessError(1, ["synthetic-release-validator"])

    reconciler.reconcile_contract_readiness = unchanged_contract
    reconciler.reconcile_status = unchanged_status
    reconciler.run_canonical_validators = rejected_validator_chain
    try:
        try:
            reconciler.main()
        except subprocess.CalledProcessError:
            pass
        else:
            raise NegativeFailure("release reconciler accepted no-op authority without canonical validators")
        require(calls == 1, "no-op release reconciliation did not invoke canonical validator chain exactly once")
        require(CONTRACT_PATH.read_bytes() == original_contract, "no-op validator rejection mutated release contract")
        require(STATUS_PATH.read_bytes() == original_status, "no-op validator rejection mutated production status")
    finally:
        reconciler.reconcile_contract_readiness = original_contract_reconcile
        reconciler.reconcile_status = original_status_reconcile
        reconciler.run_canonical_validators = original_runner
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_reconciler()
    reconciler.enforce_runtime_authorities()
    cases = (
        ("WRITER_PATH", reconciler.VALIDATOR_PATH, "writer executable"),
        ("VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "release validator executable"),
        ("EVIDENCE_BINDING_VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "evidence validator executable"),
        ("VERSION_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "version validator executable"),
        ("OPERABILITY_VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "operability validator executable"),
        ("CONTRACT_PATH", reconciler.STATUS_PATH, "release contract path"),
        ("STATUS_PATH", reconciler.CONTRACT_PATH, "production status path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)
    prove_noop_runs_canonical_validators(reconciler)
    print("PASS: release reconcile rejects authority substitutions and validates canonical authority on no-op")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"RELEASE RECONCILE AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
