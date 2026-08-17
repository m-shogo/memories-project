#!/usr/bin/env python3
"""Prove rate-limit operations reconcile rolls back both authority files on post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operations.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_operations_reconcile_negative", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rate-limit operations reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    reconciler = load_module()
    originals = {
        reconciler.POLICY_PATH: reconciler.POLICY_PATH.read_bytes(),
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.read_bytes(),
    }
    policy = copy.deepcopy(load_json(reconciler.POLICY_PATH))
    status = copy.deepcopy(load_json(reconciler.STATUS_PATH))
    policy["operations"]["drillCompleted"] = False
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic post-write validation failure")
    )
    try:
        try:
            reconciler.transactional_write(policy, status)
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

    print("PASS: rate-limit operations post-write failure restores policy and production status byte-for-byte")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
