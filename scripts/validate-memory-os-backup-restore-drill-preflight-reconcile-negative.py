#!/usr/bin/env python3
"""Prove restore drill preflight reconciliation rolls back partial publication."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_backup_restore_drill_preflight_reconcile_negative",
        RECONCILER,
    )
    require(spec is not None and spec.loader is not None, "cannot load restore drill preflight reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_second_replace_rollback(module) -> None:
    contract_before = module.CONTRACT.read_bytes()
    status_before = module.STATUS.read_bytes()
    contract_mode_before = mode(module.CONTRACT)
    status_mode_before = mode(module.STATUS)
    real_replace = module.os.replace
    replace_calls = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("synthetic preflight second atomic replacement failure")
        real_replace(source, destination)

    module.os.replace = fail_second_replace
    try:
        try:
            module._reconcile()
        except module.Fail as exc:
            require(
                "cannot atomically write" in str(exc),
                f"preflight second replace rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("preflight second atomic replacement failure unexpectedly accepted")
    finally:
        module.os.replace = real_replace

    require(replace_calls == 4, f"unexpected preflight replace/rollback call count: {replace_calls}")
    require(module.CONTRACT.read_bytes() == contract_before, "preflight contract partial publication was not rolled back byte-for-byte")
    require(module.STATUS.read_bytes() == status_before, "production status changed after preflight partial publication failure")
    require(mode(module.CONTRACT) == contract_mode_before, "preflight contract mode changed after partial publication rollback")
    require(mode(module.STATUS) == status_mode_before, "production status mode changed after partial publication rollback")
    require(
        not list(module.CONTRACT.parent.glob(f".{module.CONTRACT.name}.*.tmp")),
        "preflight contract partial publication failure left a temporary authority file",
    )
    require(
        not list(module.STATUS.parent.glob(f".{module.STATUS.name}.*.tmp")),
        "production status partial publication failure left a temporary authority file",
    )
    print("PASS rollback: preflight second replace failure restores contract/status bytes and modes")
    print("PASS boundary: preflight second replace failure leaves no temporary authority files")


def main() -> int:
    require(RECONCILER.is_file(), "restore drill preflight reconciler missing")
    module = load_module()
    module.enforce_execution_identity()
    module.enforce_runtime_authorities()
    prove_second_replace_rollback(module)
    print("Restore drill preflight reconcile negative suite PASS")
    print("partial preflight/status publication accepted: false")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
