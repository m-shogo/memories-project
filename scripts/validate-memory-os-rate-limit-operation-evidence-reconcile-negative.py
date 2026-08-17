#!/usr/bin/env python3
"""Prove rate-limit operation-ledger reconcile rolls back both authority files on post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operation-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_operation_evidence_reconcile_negative", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rate-limit operation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    reconciler = load_module()
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
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("transactional write accepted synthetic post-write validation failure")

        for path, original in originals.items():
            if path.read_bytes() != original:
                raise RuntimeError(f"rollback failed for {path.relative_to(ROOT)}")
    finally:
        reconciler.validate_written_authority = original_validator
        for path, original in originals.items():
            path.write_bytes(original)

    print("PASS: rate-limit operation evidence post-write failure restores operations contract and production status byte-for-byte")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
