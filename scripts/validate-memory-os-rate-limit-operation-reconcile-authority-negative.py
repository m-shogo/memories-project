#!/usr/bin/env python3
"""Prove rate-limit operation reconcile rejects authority substitution and rolls back aggregate failures."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
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


def prove_aggregate_validator_chain(reconciler: Any) -> None:
    expected = [
        reconciler.OPERATIONS_VALIDATOR.resolve(),
        reconciler.RATE_LIMIT_VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
        reconciler.ENTRY_DOCS_VALIDATOR.resolve(),
    ]
    observed: list[Path] = []
    original_validate_evidence = reconciler.validate_evidence_authority
    original_run_validator = reconciler.run_validator

    def capture_run(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.validate_evidence_authority = lambda _evidence: None
        reconciler.run_validator = capture_run
        reconciler.validate_written_authority()
    finally:
        reconciler.validate_evidence_authority = original_validate_evidence
        reconciler.run_validator = original_run_validator

    require(observed == expected,
            f"rate-limit operation aggregate validator chain drift: {observed!r} != {expected!r}")


def prove_transaction_rollback(reconciler: Any) -> None:
    original_operations = OPERATIONS_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    operations = json.loads(original_operations.decode("utf-8"))
    status = json.loads(original_status.decode("utf-8"))
    operations = copy.deepcopy(operations)
    status = copy.deepcopy(status)
    operations["readiness"]["evidenceLedgerImplemented"] = True
    status["asOf"] = "2099-12-31"
    original_validate_written = reconciler.validate_written_authority

    def fail_after_write() -> None:
        raise reconciler.ReconcileFailure("synthetic aggregate operability rejection")

    try:
        reconciler.validate_written_authority = fail_after_write
        try:
            reconciler.transactional_write(operations, status)
        except reconciler.ReconcileFailure as exc:
            require("synthetic aggregate operability rejection" in str(exc),
                    "rate-limit operation rollback failed for unrelated reason")
        else:
            raise NegativeFailure("rate-limit operation transaction accepted aggregate rejection")
        require(OPERATIONS_PATH.read_bytes() == original_operations,
                "rate-limit operations contract was not rolled back byte-for-byte")
        require(STATUS_PATH.read_bytes() == original_status,
                "rate-limit production status was not rolled back byte-for-byte")
    finally:
        reconciler.validate_written_authority = original_validate_written
        OPERATIONS_PATH.write_bytes(original_operations)
        STATUS_PATH.write_bytes(original_status)


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
    prove_transaction_rollback(reconciler)
    print("PASS: rate-limit operation reconcile pins full canonical authority chain and rolls back aggregate rejection")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print("RATE-LIMIT OPERATION RECONCILE AUTHORITY NEGATIVE FAILED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
