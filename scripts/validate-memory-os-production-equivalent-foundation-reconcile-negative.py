#!/usr/bin/env python3
"""Prove production-equivalent foundation reconciliation rolls back derived authority."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-foundation.py"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("production_foundation_reconcile", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load production-equivalent foundation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-production-foundation-rollback-") as tmp:
        tmp_root = Path(tmp)
        load_path = tmp_root / "load.json"
        status_path = tmp_root / "status.json"
        load_path.write_bytes(LOAD.read_bytes())
        status_path.write_bytes(STATUS.read_bytes())

        load_contract = json.loads(load_path.read_text(encoding="utf-8"))
        status = json.loads(status_path.read_text(encoding="utf-8"))
        load_contract["_rollbackNegativeMarker"] = True
        status["_rollbackNegativeMarker"] = True

        module.LOAD_PATH = load_path
        module.STATUS_PATH = status_path
        original_validator = module.validate_current_authority

        def controlled_validator() -> None:
            raise module.Fail("controlled post-write production foundation validation failure")

        module.validate_current_authority = controlled_validator
        before_load = load_path.read_bytes()
        before_status = status_path.read_bytes()
        try:
            try:
                module.write_and_validate_transactionally(load_contract, status)
            except module.Fail as exc:
                require(
                    "controlled post-write production foundation validation failure" in str(exc),
                    f"unexpected rollback failure: {exc}",
                )
            else:
                raise Fail("controlled production foundation post-write failure was accepted")
        finally:
            module.validate_current_authority = original_validator

        require(load_path.read_bytes() == before_load, "load authority was not rolled back byte-for-byte")
        require(status_path.read_bytes() == before_status, "production status was not rolled back byte-for-byte")

    print("PASS: production-equivalent foundation reconcile rolls back derived authority on post-write failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"PRODUCTION FOUNDATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
