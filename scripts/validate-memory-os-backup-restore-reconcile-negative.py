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


def data_authority_identity_negative(module) -> None:
    original_contract = module.CONTRACT_PATH
    original_status = module.STATUS_PATH
    try:
        module.CONTRACT_PATH = original_status
        expect_rejected(
            "repository-contained backup contract substitution",
            module.validate_runtime_authority,
        )
        module.CONTRACT_PATH = original_contract
        module.STATUS_PATH = original_contract
        expect_rejected(
            "repository-contained production status substitution",
            module.validate_runtime_authority,
        )
        module.CONTRACT_PATH = original_status
        module.STATUS_PATH = original_contract
        expect_rejected(
            "paired repository-contained contract/status substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.CONTRACT_PATH = original_contract
        module.STATUS_PATH = original_status


def blocker_authority_identity_negative(module) -> None:
    original_root = module.ROOT
    original_helper = module.require_canonical_gaps
    original_guard = module.validate_runtime_authority
    try:
        module.ROOT = ROOT / "scripts"
        expect_rejected(
            "repository root substitution",
            module.validate_runtime_authority,
        )
        module.ROOT = original_root

        module.require_canonical_gaps = lambda *args, **kwargs: args[0] if args else None
        expect_rejected(
            "canonical blocker validator substitution",
            module.validate_runtime_authority,
        )
        module.require_canonical_gaps = original_helper

        module.validate_runtime_authority = lambda: None
        expect_rejected(
            "runtime authority guard substitution",
            module.main,
        )
    finally:
        module.ROOT = original_root
        module.require_canonical_gaps = original_helper
        module.validate_runtime_authority = original_guard


def make_stale_status_load(module, real_load):
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

    return stale_status_load


def atomic_replace_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    real_load = module.load
    real_os_replace = module.os.replace
    replace_calls = 0

    def fail_first_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError("synthetic atomic replacement failure")
        real_os_replace(source, destination)

    module.load = make_stale_status_load(module, real_load)
    module.os.replace = fail_first_replace
    try:
        expect_rejected(
            "atomic production status replacement failure preserves canonical authority",
            module.main,
        )
        require(replace_calls == 1, f"unexpected atomic replace call count: {replace_calls}")
        require(module.STATUS_PATH.read_bytes() == original_status,
                "failed atomic replacement mutated production status")
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "failed atomic replacement left temporary production status authority behind",
        )
    finally:
        module.load = real_load
        module.os.replace = real_os_replace
        if module.STATUS_PATH.read_bytes() != original_status:
            module.atomic_write_bytes(module.STATUS_PATH, original_status)


def rollback_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    real_load = module.load
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        # Deterministic projection must be repairable first. Reject only after
        # the candidate status exists, at aggregate Operability validation.
        if len(calls) == 4 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.ReconcileFailure("synthetic aggregate operability rejection")

    module.load = make_stale_status_load(module, real_load)
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
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "post-write rollback left temporary production status authority behind",
        )
    finally:
        module.load = real_load
        module.run_validator = real_run_validator
        if module.STATUS_PATH.read_bytes() != original_status:
            module.atomic_write_bytes(module.STATUS_PATH, original_status)


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_backup_restore_reconcile_negative_target")
    original_status = reconciler.STATUS_PATH.read_bytes()
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    data_authority_identity_negative(reconciler)
    blocker_authority_identity_negative(reconciler)
    atomic_replace_negative(reconciler)
    rollback_negative(reconciler)
    require(reconciler.STATUS_PATH.read_bytes() == original_status,
            "authority negatives mutated canonical Production Status")
    print("Memory OS backup/restore policy reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("canonical contract/status identity: enforced")
    print("paired contract/status substitution accepted: false")
    print("canonical repository root identity: enforced")
    print("canonical blocker validator substitution accepted: false")
    print("runtime authority guard substitution accepted: false")
    print("deterministic drift repair before full validation: enforced")
    print("atomic production status replacement: enforced")
    print("atomic replacement temp cleanup: enforced")
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
