#!/usr/bin/env python3
"""Prove rate-limit operation reconcile rejects authority substitution and rolls back aggregate failures."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operation-evidence.py"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location(
        "rate_limit_operation_reconciler_authority_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load rate-limit operation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Path, label: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_operations = OPERATIONS_PATH.read_bytes()
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
            raise NegativeFailure(f"rate-limit operation reconciler accepted authority substitution: {label}")
        require(OPERATIONS_PATH.read_bytes() == original_operations,
                f"operations contract mutated after authority substitution: {label}")
        require(STATUS_PATH.read_bytes() == original_status,
                f"production status mutated after authority substitution: {label}")
    finally:
        setattr(reconciler, attribute, original_attribute)
        OPERATIONS_PATH.write_bytes(original_operations)
        STATUS_PATH.write_bytes(original_status)


def restore_file(path: Path, payload: bytes, mode: int) -> None:
    path.write_bytes(payload)
    os.chmod(path, mode)


def prove_aggregate_validator_chain(reconciler: Any) -> None:
    validators = (
        (reconciler.EVIDENCE_VALIDATOR, "evidence"),
        (reconciler.OPERATIONS_VALIDATOR, "operations"),
        (reconciler.RATE_LIMIT_VALIDATOR, "rate-limit"),
        (reconciler.OPERABILITY_VALIDATOR, "operability"),
        (reconciler.ENTRY_DOCS_VALIDATOR, "entry-docs"),
    )
    originals = {
        path: (path.read_bytes(), path.stat().st_mode & 0o777)
        for path, _label in validators
    }
    previous_log = os.environ.get("MEMORY_OS_RATE_LIMIT_VALIDATOR_ORDER")
    try:
        with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-validator-order-") as temp_dir:
            log = Path(temp_dir) / "order.log"
            os.environ["MEMORY_OS_RATE_LIMIT_VALIDATOR_ORDER"] = str(log)
            for path, label in validators:
                path.write_text(
                    "import os\n"
                    "from pathlib import Path\n"
                    f"Path(os.environ['MEMORY_OS_RATE_LIMIT_VALIDATOR_ORDER']).open('a', encoding='utf-8').write('{label}\\n')\n",
                    encoding="utf-8",
                )
            reconciler.validate_written_authority()
            observed = log.read_text(encoding="utf-8").splitlines()
            expected = [label for _path, label in validators]
            require(observed == expected,
                    f"rate-limit operation aggregate validator chain drift: {observed!r} != {expected!r}")
    finally:
        if previous_log is None:
            os.environ.pop("MEMORY_OS_RATE_LIMIT_VALIDATOR_ORDER", None)
        else:
            os.environ["MEMORY_OS_RATE_LIMIT_VALIDATOR_ORDER"] = previous_log
        for path, (payload, mode) in originals.items():
            restore_file(path, payload, mode)


def prove_atomic_transport_and_mode(reconciler: Any) -> None:
    original_operations = OPERATIONS_PATH.read_bytes()
    original_mode = OPERATIONS_PATH.stat().st_mode & 0o777
    original_replace = reconciler.os.replace
    temp_pattern = f".{OPERATIONS_PATH.name}.*.tmp"
    before_temps = {path.name for path in OPERATIONS_PATH.parent.glob(temp_pattern)}

    try:
        reconciler.os.replace = lambda _source, _destination: None
        try:
            reconciler.atomic_write_bytes(OPERATIONS_PATH, b"synthetic replacement payload\n")
        except reconciler.ReconcileFailure as exc:
            require("atomic replace transport drift" in str(exc),
                    "atomic replace substitution rejected for unrelated reason")
        else:
            raise NegativeFailure("atomic writer accepted replacement transport substitution")
        require(OPERATIONS_PATH.read_bytes() == original_operations,
                "operations contract changed after rejected replace transport substitution")
        after_temps = {path.name for path in OPERATIONS_PATH.parent.glob(temp_pattern)}
        require(after_temps == before_temps,
                f"atomic writer left temporary residue: {sorted(after_temps - before_temps)}")
    finally:
        reconciler.os.replace = original_replace

    reconciler.atomic_write_bytes(OPERATIONS_PATH, original_operations)
    require(OPERATIONS_PATH.read_bytes() == original_operations,
            "atomic writer changed canonical bytes during mode-preservation proof")
    require((OPERATIONS_PATH.stat().st_mode & 0o777) == original_mode,
            "atomic writer changed canonical file mode")
    after_temps = {path.name for path in OPERATIONS_PATH.parent.glob(temp_pattern)}
    require(after_temps == before_temps,
            f"atomic writer left temporary residue after successful replacement: {sorted(after_temps - before_temps)}")


def prove_direct_transaction_helper_rejection(reconciler: Any) -> None:
    original_operations = OPERATIONS_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    operations = copy.deepcopy(json.loads(original_operations.decode("utf-8")))
    status = copy.deepcopy(json.loads(original_status.decode("utf-8")))
    status["asOf"] = "2099-12-31"
    cases = (
        ("atomic_write_json", lambda *_args, **_kwargs: None, "atomic JSON writer execution authority drift"),
        ("atomic_write_bytes", lambda *_args, **_kwargs: None, "atomic byte writer execution authority drift"),
        ("validate_written_authority", lambda: None, "post-write validator execution authority drift"),
        ("run_validator", lambda *_args, **_kwargs: None, "validator runner execution authority drift"),
    )
    for attribute, substitute, expected in cases:
        original = getattr(reconciler, attribute)
        try:
            setattr(reconciler, attribute, substitute)
            try:
                reconciler.transactional_write(operations, status)
            except reconciler.ReconcileFailure as exc:
                require(expected in str(exc),
                        f"direct transaction {attribute} substitution rejected for unrelated reason: {exc}")
            else:
                raise NegativeFailure(f"direct transaction accepted {attribute} substitution")
            require(OPERATIONS_PATH.read_bytes() == original_operations,
                    f"operations contract mutated after direct {attribute} substitution")
            require(STATUS_PATH.read_bytes() == original_status,
                    f"production status mutated after direct {attribute} substitution")
        finally:
            setattr(reconciler, attribute, original)


def prove_transaction_rollback(reconciler: Any) -> None:
    original_operations = OPERATIONS_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    original_operations_mode = OPERATIONS_PATH.stat().st_mode & 0o777
    original_status_mode = STATUS_PATH.stat().st_mode & 0o777
    operations = copy.deepcopy(json.loads(original_operations.decode("utf-8")))
    status = copy.deepcopy(json.loads(original_status.decode("utf-8")))
    status["asOf"] = "2099-12-31"

    validator_paths = (
        reconciler.EVIDENCE_VALIDATOR,
        reconciler.OPERATIONS_VALIDATOR,
        reconciler.RATE_LIMIT_VALIDATOR,
        reconciler.OPERABILITY_VALIDATOR,
    )
    originals = {
        path: (path.read_bytes(), path.stat().st_mode & 0o777)
        for path in validator_paths
    }
    try:
        for path in validator_paths[:-1]:
            path.write_text("raise SystemExit(0)\n", encoding="utf-8")
        reconciler.OPERABILITY_VALIDATOR.write_text("raise SystemExit(9)\n", encoding="utf-8")
        try:
            reconciler.transactional_write(operations, status)
        except reconciler.ReconcileFailure as exc:
            require("operability aggregate post-write validation failed" in str(exc),
                    f"rate-limit operation rollback failed for unrelated reason: {exc}")
        else:
            raise NegativeFailure("rate-limit operation transaction accepted canonical operability rejection")
        require(OPERATIONS_PATH.read_bytes() == original_operations,
                "rate-limit operations contract was not rolled back byte-for-byte")
        require(STATUS_PATH.read_bytes() == original_status,
                "rate-limit production status was not rolled back byte-for-byte")
        require((OPERATIONS_PATH.stat().st_mode & 0o777) == original_operations_mode,
                "rate-limit operations contract mode drifted during rollback")
        require((STATUS_PATH.stat().st_mode & 0o777) == original_status_mode,
                "rate-limit production status mode drifted during rollback")
    finally:
        for path, (payload, mode) in originals.items():
            restore_file(path, payload, mode)
        if OPERATIONS_PATH.read_bytes() != original_operations:
            reconciler.atomic_write_bytes(OPERATIONS_PATH, original_operations)
        if STATUS_PATH.read_bytes() != original_status:
            reconciler.atomic_write_bytes(STATUS_PATH, original_status)


def main() -> int:
    reconciler = load_reconciler()
    reconciler.enforce_runtime_authorities()
    cases = (
        ("WRITER_PATH", reconciler.EVIDENCE_VALIDATOR, "operation writer executable"),
        ("EVIDENCE_VALIDATOR", reconciler.OPERATIONS_VALIDATOR, "evidence validator executable"),
        ("OPERATIONS_VALIDATOR", reconciler.RATE_LIMIT_VALIDATOR, "operations validator executable"),
        ("RATE_LIMIT_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "rate-limit validator executable"),
        ("OPERABILITY_VALIDATOR", reconciler.ENTRY_DOCS_VALIDATOR, "operability validator executable"),
        ("ENTRY_DOCS_VALIDATOR", reconciler.RATE_LIMIT_VALIDATOR, "entry docs validator executable"),
        ("EVIDENCE_PATH", reconciler.OPERATIONS_PATH, "evidence contract path"),
        ("OPERATIONS_PATH", reconciler.STATUS_PATH, "operations contract path"),
        ("STATUS_PATH", reconciler.OPERATIONS_PATH, "production status path"),
        ("WORKFLOW_PATH", reconciler.EVIDENCE_PATH, "workflow authority path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)
    prove_aggregate_validator_chain(reconciler)
    prove_atomic_transport_and_mode(reconciler)
    prove_direct_transaction_helper_rejection(reconciler)
    prove_transaction_rollback(reconciler)
    print("PASS: rate-limit operation reconcile pins full canonical authority chain, direct transaction helpers, mode-preserving atomic publication, and aggregate rollback")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print("RATE-LIMIT OPERATION RECONCILE AUTHORITY NEGATIVE FAILED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
