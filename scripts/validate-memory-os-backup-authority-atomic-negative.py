#!/usr/bin/env python3
"""Focused fail-closed checks for local backup authority reconciliation."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / "scripts/reconcile-memory-os-backup-authority.py"
COHERENT = ROOT / "scripts/reconcile-memory-os-backup-coherent-authority.py"
SEMANTIC = ROOT / "scripts/reconcile-memory-os-backup-semantic-overlay.py"


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
        if exc.__class__.__name__ in {"ReconcileFailure", "Fail"}:
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def changed_candidate(status, label: str):
    candidate = copy.deepcopy(status)
    gate = next(
        row for row in candidate.get("areas", [])
        if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
    )
    existing = gate.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-007 existing evidence missing")
    existing.append(f"synthetic local-only atomic {label} sentinel")
    return candidate


def semantic_authority_identity(module) -> None:
    original = module.STATUS_PATH
    module.STATUS_PATH = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
    try:
        expect_rejected(
            "semantic overlay rejects repository-contained production status substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.STATUS_PATH = original
    module.validate_runtime_authority()


def coherent_authority_identity(module) -> None:
    original_root = module.ROOT
    original_status = module.STATUS
    original_index = module.INDEX
    original_result = module.RESULT
    original_validator = module.VALIDATOR
    original_blocker = module.require_canonical_gaps
    original_subprocess_run = module.subprocess.run
    original_guard = module.validate_runtime_authority
    try:
        module.STATUS = original_index
        module.INDEX = original_status
        expect_rejected(
            "coherent paired status/index substitution",
            module.validate_runtime_authority,
        )
        module.STATUS = original_status
        module.INDEX = original_index

        module.RESULT = original_index
        expect_rejected(
            "coherent result authority substitution",
            module.validate_runtime_authority,
        )
        module.RESULT = original_result

        module.VALIDATOR = module.BACKUP_VALIDATOR
        expect_rejected(
            "coherent validator authority substitution",
            module.validate_runtime_authority,
        )
        module.VALIDATOR = original_validator

        module.ROOT = ROOT / "scripts"
        expect_rejected(
            "coherent repository root substitution",
            module.validate_runtime_authority,
        )
        module.ROOT = original_root

        module.require_canonical_gaps = lambda *args, **kwargs: args[0] if args else None
        expect_rejected(
            "coherent blocker validator substitution",
            module.validate_runtime_authority,
        )
        module.require_canonical_gaps = original_blocker

        module.subprocess.run = lambda *args, **kwargs: type("Completed", (), {"returncode": 0})()
        expect_rejected(
            "coherent subprocess execution transport substitution",
            module.validate_runtime_authority,
        )
        module.subprocess.run = original_subprocess_run

        module.validate_runtime_authority = lambda: None
        expect_rejected(
            "coherent runtime authority guard substitution",
            module.main,
        )
    finally:
        module.ROOT = original_root
        module.STATUS = original_status
        module.INDEX = original_index
        module.RESULT = original_result
        module.VALIDATOR = original_validator
        module.require_canonical_gaps = original_blocker
        module.subprocess.run = original_subprocess_run
        module.validate_runtime_authority = original_guard
    module.validate_runtime_authority()


def normalizer_noop_validation(module) -> None:
    original = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def unchanged(status):
        return copy.deepcopy(status)

    def track(path: Path) -> None:
        calls.append(path)

    module.normalize = unchanged
    module.run_validator = track
    try:
        require(module.main() == 0, "normalizer no-op path failed unexpectedly")
        require(
            calls == [module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            f"normalizer no-op validator order drift: {calls}",
        )
        require(module.STATUS_PATH.read_bytes() == original,
                "normalizer no-op path mutated production status")
    finally:
        module.normalize = real_normalize
        module.run_validator = real_run_validator
        if module.STATUS_PATH.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS_PATH, original)


def normalizer_atomic_replace_failure(module) -> None:
    original = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_replace = module.os.replace
    replace_calls = 0

    def fake_normalize(status):
        return changed_candidate(status, "backup authority")

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
            "normalizer initial atomic replacement failure preserves production status",
            module.main,
        )
        require(replace_calls == 1, f"unexpected normalizer initial replace count: {replace_calls}")
        require(module.STATUS_PATH.read_bytes() == original,
                "normalizer atomic replacement failure mutated production status")
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "normalizer atomic replacement failure left a temporary authority file",
        )
    finally:
        module.normalize = real_normalize
        module.os.replace = real_replace
        if module.STATUS_PATH.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS_PATH, original)


def normalizer_atomic_rollback(module) -> None:
    original = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_run_validator = module.run_validator
    real_replace = module.os.replace
    validator_calls: list[Path] = []
    replace_calls = 0

    def fake_normalize(status):
        return changed_candidate(status, "backup authority rollback")

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
            "normalizer post-write rejection atomically rolls back production status",
            module.main,
        )
        require(
            validator_calls == [module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            "backup authority validator transaction order drift",
        )
        require(replace_calls == 2,
                f"normalizer publication and rollback must each use atomic replacement: {replace_calls}")
        require(module.STATUS_PATH.read_bytes() == original,
                "normalizer atomic rollback did not restore production status byte-for-byte")
        require(
            not list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp")),
            "normalizer atomic rollback left a temporary authority file",
        )
    finally:
        module.normalize = real_normalize
        module.run_validator = real_run_validator
        module.os.replace = real_replace
        if module.STATUS_PATH.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS_PATH, original)


def coherent_noop_validation(module) -> None:
    original = module.STATUS.read_bytes()
    real_normalized = module.normalized
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def unchanged(status):
        return copy.deepcopy(status)

    def track(path: Path) -> None:
        calls.append(path)

    module.normalized = unchanged
    module.run_validator = track
    try:
        require(module.main() == 0, "coherent no-op path failed unexpectedly")
        require(
            calls == [module.VALIDATOR, module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            f"coherent no-op validator order drift: {calls}",
        )
        require(module.STATUS.read_bytes() == original,
                "coherent no-op path mutated production status")
    finally:
        module.normalized = real_normalized
        module.run_validator = real_run_validator
        if module.STATUS.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS, original)


def coherent_atomic_replace_failure(module) -> None:
    original = module.STATUS.read_bytes()
    real_normalized = module.normalized
    real_initial_validator = module.run_validator
    real_replace = module.os.replace
    replace_calls = 0

    def fake_normalized(status):
        return changed_candidate(status, "coherent authority")

    def fake_initial_validator(path: Path) -> None:
        if path == module.VALIDATOR:
            return
        real_initial_validator(path)

    def fail_first_replace(source, destination) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError("synthetic coherent atomic replacement failure")
        real_replace(source, destination)

    module.normalized = fake_normalized
    module.run_validator = fake_initial_validator
    module.os.replace = fail_first_replace
    try:
        expect_rejected(
            "coherent initial atomic replacement failure preserves production status",
            module.main,
        )
        require(replace_calls == 1, f"unexpected coherent initial replace count: {replace_calls}")
        require(module.STATUS.read_bytes() == original,
                "coherent atomic replacement failure mutated production status")
        require(
            not list(module.STATUS.parent.glob(f".{module.STATUS.name}.*.tmp")),
            "coherent atomic replacement failure left a temporary authority file",
        )
    finally:
        module.normalized = real_normalized
        module.run_validator = real_initial_validator
        module.os.replace = real_replace
        if module.STATUS.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS, original)


def coherent_atomic_rollback(module) -> None:
    original = module.STATUS.read_bytes()
    real_normalized = module.normalized
    real_run_validator = module.run_validator
    real_replace = module.os.replace
    validator_calls: list[Path] = []
    replace_calls = 0

    def fake_normalized(status):
        return changed_candidate(status, "coherent authority rollback")

    def fake_run_validator(path: Path) -> None:
        validator_calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise module.Fail("synthetic coherent post-write operability rejection")

    def tracked_replace(source, destination) -> None:
        nonlocal replace_calls
        replace_calls += 1
        real_replace(source, destination)

    module.normalized = fake_normalized
    module.run_validator = fake_run_validator
    module.os.replace = tracked_replace
    try:
        expect_rejected(
            "coherent post-write rejection atomically rolls back production status",
            module.main,
        )
        require(
            validator_calls == [module.VALIDATOR, module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            "coherent authority validator transaction order drift",
        )
        require(replace_calls == 2,
                f"coherent publication and rollback must each use atomic replacement: {replace_calls}")
        require(module.STATUS.read_bytes() == original,
                "coherent atomic rollback did not restore production status byte-for-byte")
        require(
            not list(module.STATUS.parent.glob(f".{module.STATUS.name}.*.tmp")),
            "coherent atomic rollback left a temporary authority file",
        )
    finally:
        module.normalized = real_normalized
        module.run_validator = real_run_validator
        module.os.replace = real_replace
        if module.STATUS.read_bytes() != original:
            module.atomic_write_bytes(module.STATUS, original)


def main() -> int:
    normalizer = load_module(NORMALIZER, "memory_os_backup_authority_atomic_negative_target")
    coherent = load_module(COHERENT, "memory_os_coherent_backup_authority_atomic_negative_target")
    semantic = load_module(SEMANTIC, "memory_os_backup_semantic_authority_negative_target")
    normalizer.validate_runtime_authority()
    coherent.validate_runtime_authority()
    semantic.validate_runtime_authority()
    semantic_authority_identity(semantic)
    coherent_authority_identity(coherent)
    normalizer_noop_validation(normalizer)
    normalizer_atomic_replace_failure(normalizer)
    normalizer_atomic_rollback(normalizer)
    coherent_noop_validation(coherent)
    coherent_atomic_replace_failure(coherent)
    coherent_atomic_rollback(coherent)
    print("Memory OS backup authority atomic negative suite PASS")
    print("semantic production status identity: enforced")
    print("coherent data/executable authority identity: enforced")
    print("coherent blocker validator identity: enforced")
    print("coherent subprocess execution transport: enforced")
    print("coherent runtime authority guard identity: enforced")
    print("normalizer no-op aggregate validation: enforced")
    print("normalizer atomic replacement/rollback: enforced")
    print("coherent no-op aggregate validation: enforced")
    print("coherent atomic replacement/rollback: enforced")
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
