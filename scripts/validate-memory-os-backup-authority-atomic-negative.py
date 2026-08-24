#!/usr/bin/env python3
"""Focused crash-safety checks for local backup authority normalization."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-authority.py"


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


def changed_candidate(module, status):
    candidate = copy.deepcopy(status)
    gate = next(
        row for row in candidate.get("areas", [])
        if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
    )
    existing = gate.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-007 existing evidence missing")
    existing.append("synthetic local-only atomic backup authority sentinel")
    return candidate


def atomic_replace_failure(module) -> None:
    original = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_replace = module.os.replace
    replace_calls = 0

    def fake_normalize(status):
        return changed_candidate(module, status)

    def fail_first_replace(source, destination) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError("synthetic atomic replacement failure")
        real_replace(source, destination)

    module.normalize = fake_normalize
    module.os.replace = fail_first_replace
    try:
        expect_rejected(
            "initial atomic replacement failure preserves production status",
            module.main,
        )
        require(replace_calls == 1, f"unexpected initial replace count: {replace_calls}")
        require(module.STATUS_PATH.read_bytes() == original,
                "initial atomic replacement failure mutated production status")
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "initial atomic replacement failure left a temporary authority file",
        )
    finally:
        module.normalize = real_normalize
        module.os.replace = real_replace
        if module.STATUS_PATH.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS_PATH, original)


def atomic_rollback(module) -> None:
    original = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_run_validator = module.run_validator
    real_replace = module.os.replace
    validator_calls: list[Path] = []
    replace_calls = 0

    def fake_normalize(status):
        return changed_candidate(module, status)

    def fake_run_validator(path: Path) -> None:
        validator_calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise module.ReconcileFailure("synthetic post-write operability rejection")

    def tracked_replace(source, destination) -> None:
        nonlocal replace_calls
        replace_calls += 1
        real_replace(source, destination)

    module.normalize = fake_normalize
    module.run_validator = fake_run_validator
    module.os.replace = tracked_replace
    try:
        expect_rejected(
            "post-write rejection atomically rolls back production status",
            module.main,
        )
        require(
            validator_calls == [module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            "backup authority validator transaction order drift",
        )
        require(replace_calls == 2,
                f"candidate publication and rollback must each use atomic replacement: {replace_calls}")
        require(module.STATUS_PATH.read_bytes() == original,
                "atomic rollback did not restore production status byte-for-byte")
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "atomic rollback left a temporary authority file",
        )
    finally:
        module.normalize = real_normalize
        module.run_validator = real_run_validator
        module.os.replace = real_replace
        if module.STATUS_PATH.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS_PATH, original)


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_backup_authority_atomic_negative_target")
    reconciler.validate_runtime_authority()
    atomic_replace_failure(reconciler)
    atomic_rollback(reconciler)
    print("Memory OS backup authority atomic negative suite PASS")
    print("initial atomic replacement non-mutation: enforced")
    print("atomic rollback after aggregate rejection: enforced")
    print("temporary authority cleanup: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP AUTHORITY ATOMIC NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
