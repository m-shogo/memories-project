#!/usr/bin/env python3
"""Prove rate-limit operation-ledger reconcile authority and rollback boundaries fail closed."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operation-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_evidence_reconcile_negative", RECONCILER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rate-limit operation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def expect_authority_identity(reconciler) -> None:
    reconciler.enforce_runtime_authorities()
    original_operations = reconciler.OPERATIONS_PATH.read_bytes()
    original_status = reconciler.STATUS_PATH.read_bytes()
    substitutions = (
        ("EVIDENCE_PATH", reconciler.OPERATIONS_PATH, "operation evidence contract"),
        ("OPERATIONS_PATH", reconciler.EVIDENCE_PATH, "operations contract"),
        ("STATUS_PATH", reconciler.OPERATIONS_PATH, "production operability status"),
        ("WRITER_PATH", reconciler.EVIDENCE_VALIDATOR, "operation writer"),
        ("EVIDENCE_VALIDATOR", reconciler.OPERATIONS_VALIDATOR, "operation evidence validator"),
        ("OPERATIONS_VALIDATOR", reconciler.RATE_LIMIT_VALIDATOR, "operations validator"),
        ("RATE_LIMIT_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "rate-limit validator"),
        ("OPERABILITY_VALIDATOR", reconciler.ENTRY_DOCS_VALIDATOR, "operability validator"),
        ("ENTRY_DOCS_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "entry docs validator"),
        (
            "WORKFLOW_PATH",
            ROOT / ".github/workflows/reconcile-rate-limit-operations.yml",
            "operation workflow",
        ),
    )
    for attribute, substitute, label in substitutions:
        original = getattr(reconciler, attribute)
        try:
            setattr(reconciler, attribute, substitute)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.ReconcileFailure as exc:
                message = str(exc)
                if "authority drift" not in message and "missing or escapes repository" not in message:
                    raise RuntimeError(f"{label} rejected for unrelated reason: {message}") from exc
            else:
                raise RuntimeError(f"reconciler accepted authority substitution: {label}")
        finally:
            setattr(reconciler, attribute, original)
    if reconciler.OPERATIONS_PATH.read_bytes() != original_operations:
        raise RuntimeError("operations contract changed after authority substitution rejection")
    if reconciler.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after authority substitution rejection")
    reconciler.enforce_runtime_authorities()


def prove_validator_chain(reconciler) -> None:
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator
    original_validate_evidence = reconciler.validate_evidence_authority

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        reconciler.validate_evidence_authority = lambda _evidence: None
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run_validator
        reconciler.validate_evidence_authority = original_validate_evidence

    expected = [
        reconciler.OPERATIONS_VALIDATOR.resolve(),
        reconciler.RATE_LIMIT_VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
        reconciler.ENTRY_DOCS_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"post-write validator chain drift: {observed!r} != {expected!r}")


def prove_transaction_rollback(reconciler) -> None:
    originals = {
        reconciler.OPERATIONS_PATH: reconciler.OPERATIONS_PATH.read_bytes(),
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.read_bytes(),
    }
    operations = copy.deepcopy(load_json(reconciler.OPERATIONS_PATH))
    status = copy.deepcopy(load_json(reconciler.STATUS_PATH))
    operations["readiness"]["evidenceLedgerImplemented"] = True
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic post-write validation failure")
    )
    try:
        try:
            reconciler.transactional_write(operations, status)
        except reconciler.ReconcileFailure as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise RuntimeError(f"transaction rollback failed for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("transactional write accepted synthetic post-write validation failure")

        for path, original in originals.items():
            if path.read_bytes() != original:
                raise RuntimeError(f"rollback failed for {path.relative_to(ROOT)}")
    finally:
        reconciler.validate_written_authority = original_validator
        for path, original in originals.items():
            path.write_bytes(original)


def main() -> int:
    reconciler = load_module()
    expect_authority_identity(reconciler)
    prove_validator_chain(reconciler)
    prove_transaction_rollback(reconciler)

    print("PASS: rate-limit operation evidence exact data/executable authorities reject substitution")
    print("PASS: post-write validation includes operations, aggregate rate-limit, operability and entry-doc authorities")
    print("PASS: post-write failure restores operations contract and production status byte-for-byte")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
