#!/usr/bin/env python3
"""Prove emergency drill reconcile rolls back both authorities on post-write failure."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-emergency-drill.py"


def load_reconciler():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_emergency_reconciler", RECONCILER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load emergency drill reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    reconciler = load_reconciler()
    contract_before = reconciler.CONTRACT_PATH.read_bytes()
    status_before = reconciler.STATUS_PATH.read_bytes()
    contract = json.loads(contract_before)
    status = json.loads(status_before)

    contract["description"] = str(contract.get("description", "")) + " synthetic-rollback-probe"
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority

    def reject_after_write(source_sha: str) -> None:
        if reconciler.CONTRACT_PATH.read_bytes() == contract_before:
            raise AssertionError("contract candidate was not written before post-write validation")
        if reconciler.STATUS_PATH.read_bytes() == status_before:
            raise AssertionError("status candidate was not written before post-write validation")
        raise reconciler.ReconcileFailure("synthetic post-write validation failure")

    reconciler.validate_written_authority = reject_after_write
    try:
        try:
            reconciler.transactional_write(contract, status, "0" * 40)
        except reconciler.ReconcileFailure as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise AssertionError(f"unexpected rollback rejection: {exc}") from exc
        else:
            raise AssertionError("post-write failure was incorrectly accepted")
    finally:
        reconciler.validate_written_authority = original_validator

    if reconciler.CONTRACT_PATH.read_bytes() != contract_before:
        raise AssertionError("emergency drill contract was not rolled back byte-for-byte")
    if reconciler.STATUS_PATH.read_bytes() != status_before:
        raise AssertionError("production status was not rolled back byte-for-byte")

    print("PASS: emergency drill reconcile rolls back contract and status on post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
