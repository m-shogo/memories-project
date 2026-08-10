#!/usr/bin/env python3
"""Prove drill-request reconciliation rolls back every authority on post-validation failure."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load drill request reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failed_post_validator(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args[0] if args else [], returncode=23, stdout="synthetic post-validator failure\n", stderr="")


def main() -> int:
    require(RECONCILER.is_file(), "drill request reconciler missing")
    for path in (CONTRACT, REGISTRY, STATUS):
        require(path.is_file(), f"canonical authority missing: {path.name}")

    reconciler = load_reconciler()
    require(issubclass(reconciler.Fail, RuntimeError), "reconciler Fail must remain a runtime validation error")

    with tempfile.TemporaryDirectory(prefix=".memory-os-drill-request-rollback-", dir=ROOT) as tmp:
        tmp_path = Path(tmp)
        contract = tmp_path / CONTRACT.name
        registry = tmp_path / REGISTRY.name
        status = tmp_path / STATUS.name
        shutil.copy2(CONTRACT, contract)
        shutil.copy2(REGISTRY, registry)
        shutil.copy2(STATUS, status)

        original_contract = contract.read_bytes()
        original_registry = registry.read_bytes()
        original_status = status.read_bytes()

        reconciler.CONTRACT = contract
        reconciler.REGISTRY = registry
        reconciler.STATUS = status
        real_run = reconciler.subprocess.run
        reconciler.subprocess.run = failed_post_validator
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("post-reconcile drill request validator failed" in str(exc), "synthetic post-validator failure was not the rollback trigger")
            else:
                raise Fail("reconciler unexpectedly accepted a failed post-validator")
        finally:
            reconciler.subprocess.run = real_run

        require(contract.read_bytes() == original_contract, "contract mutation survived failed post-validation")
        require(registry.read_bytes() == original_registry, "registry mutation survived failed post-validation")
        require(status.read_bytes() == original_status, "production status mutation survived failed post-validation")

    print("Memory OS backup/restore drill request reconcile rollback negative suite PASS")
    print("forced post-validator failure observed: true")
    print("contract byte-for-byte rollback: true")
    print("registry byte-for-byte rollback: true")
    print("production status byte-for-byte rollback: true")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST RECONCILE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
