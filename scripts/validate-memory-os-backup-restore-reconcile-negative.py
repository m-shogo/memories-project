#!/usr/bin/env python3
"""Negative checks for backup/restore policy reconciliation authority."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action) -> None:
    try:
        action()
    except Exception as exc:
        if exc.__class__.__name__ == "ReconcileFailure":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def authority_identity_negative(module) -> None:
    original = module.OPERABILITY_VALIDATOR_PATH
    module.OPERABILITY_VALIDATOR_PATH = module.BACKUP_VALIDATOR_PATH
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR_PATH = original


def rollback_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    real_load = module.load
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def stale_status_load(path: Path):
        value = real_load(path)
        if path != module.STATUS_PATH:
            return value
        candidate = copy.deepcopy(value)
        gate = next(
            row for row in candidate.get("areas", [])
            if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
        )
        existing = gate.get("existingEvidence")
        require(isinstance(existing, list), "OPS-P0-007 existing evidence missing")
        require(module.NEW_EXISTING[0] in existing,
                "canonical backup policy evidence missing from rollback fixture")
        existing.remove(module.NEW_EXISTING[0])
        return candidate

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        # Deterministic projection must be repairable first. Reject only after
        # the candidate status exists, at aggregate Operability validation.
        if len(calls) == 4 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.ReconcileFailure("synthetic aggregate operability rejection")

    module.load = stale_status_load
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "post-write operability rejection rolls back backup policy status",
            module.main,
        )
        expected = [
            module.BACKUP_VALIDATOR_PATH,
            module.LOCAL_LOGICAL_VALIDATOR_PATH,
            module.LOCAL_OBJECT_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
        ]
        require(calls == expected, "backup policy validator transaction order drift")
        require(module.STATUS_PATH.read_bytes() == original_status,
                "production status was not rolled back byte-for-byte")
    finally:
        module.load = real_load
        module.run_validator = real_run_validator
        if module.STATUS_PATH.read_bytes() != original_status:
            module.STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_backup_restore_reconcile_negative_target")
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    rollback_negative(reconciler)
    print("Memory OS backup/restore policy reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("deterministic drift repair before full validation: enforced")
    print("post-write aggregate rollback: enforced")
    print("canonical production blockers: unchanged")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
