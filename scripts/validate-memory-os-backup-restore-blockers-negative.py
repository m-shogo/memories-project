#!/usr/bin/env python3
"""Negative suite for canonical OPS-P0-007 production blocker ownership."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore.py"
CANONICAL_NORMALIZER = ROOT / "scripts/reconcile-memory-os-backup-authority.py"
SEMANTIC_AUTHORITY = ROOT / "scripts/reconcile-memory-os-backup-semantic-overlay.py"
COHERENT_AUTHORITY = ROOT / "scripts/reconcile-memory-os-backup-coherent-authority.py"


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


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        result = action()
    except Exception as exc:
        exc_module = exc.__class__.__module__
        controlled = (
            exc_module.startswith("memory_os_backup_restore_")
            and exc.__class__.__name__ in {"ValidationFailure", "ReconcileFailure", "Fail"}
        )
        if not controlled:
            raise Fail(
                f"negative case raised unexpected {exc.__class__.__name__}: {name}: {exc}"
            ) from exc
        print(f"PASS reject: {name}")
        return

    if type(result) is int and result == 1:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def status_with_mutation(module, mutate: Callable[[list[str]], None]) -> dict[str, Any]:
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    area = next(
        row for row in status["areas"]
        if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
    )
    missing = area.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence missing in baseline")
    mutate(missing)
    return status


def run_with_status(module, status: dict[str, Any]) -> int:
    real_load = module.load

    def fake_load(path: Path) -> dict[str, Any]:
        if path == module.STATUS_PATH:
            return copy.deepcopy(status)
        return real_load(path)

    module.load = fake_load
    try:
        return module.main()
    finally:
        module.load = real_load


def validate_normalizer_status(module, status: dict[str, Any]) -> None:
    module.normalize(copy.deepcopy(status))


def validate_semantic_status(module, status: dict[str, Any]) -> None:
    module.validate(copy.deepcopy(status))


def validate_coherent_status(module, status: dict[str, Any]) -> None:
    module.normalized(copy.deepcopy(status))


def append_transaction_sentinel(candidate: dict[str, Any], label: str) -> dict[str, Any]:
    area = next(
        row for row in candidate["areas"]
        if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
    )
    existing = area.get("existingEvidence")
    require(isinstance(existing, list), f"OPS-P0-007 existingEvidence missing in {label} fixture")
    existing.append(f"synthetic local-only {label} rollback sentinel")
    return candidate


def validate_normalizer_transaction(module) -> None:
    original_bytes = module.STATUS_PATH.read_bytes()
    real_normalize = module.normalize
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def fake_normalize(status: dict[str, Any]) -> dict[str, Any]:
        return append_transaction_sentinel(copy.deepcopy(status), "normalizer")

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise module.ReconcileFailure("synthetic post-write operability rejection")

    module.normalize = fake_normalize
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "canonical normalizer rolls back after post-write operability rejection",
            module.main,
        )
        require(
            calls == [module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            "canonical normalizer validator transaction order drift",
        )
        require(
            module.STATUS_PATH.read_bytes() == original_bytes,
            "canonical normalizer did not roll back production status byte-for-byte",
        )
    finally:
        module.normalize = real_normalize
        module.run_validator = real_run_validator
        if module.STATUS_PATH.read_bytes() != original_bytes:
            module.STATUS_PATH.write_bytes(original_bytes)


def validate_coherent_transaction(module) -> None:
    original_bytes = module.STATUS.read_bytes()
    real_normalized = module.normalized
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def fake_normalized(status: dict[str, Any]) -> dict[str, Any]:
        return append_transaction_sentinel(copy.deepcopy(status), "coherent")

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise module.Fail("synthetic post-write operability rejection")

    module.normalized = fake_normalized
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "coherent restore authority rolls back after post-write operability rejection",
            module.main,
        )
        require(
            calls == [module.VALIDATOR, module.BACKUP_VALIDATOR, module.OPERABILITY_VALIDATOR],
            "coherent restore validator transaction order drift",
        )
        require(
            module.STATUS.read_bytes() == original_bytes,
            "coherent restore authority did not roll back production status byte-for-byte",
        )
    finally:
        module.normalized = real_normalized
        module.run_validator = real_run_validator
        if module.STATUS.read_bytes() != original_bytes:
            module.STATUS.write_bytes(original_bytes)


def main() -> int:
    module = load_module(
        VALIDATOR,
        "memory_os_backup_restore_blocker_negative_target",
    )
    normalizer = load_module(
        CANONICAL_NORMALIZER,
        "memory_os_backup_restore_normalizer_negative_target",
    )
    semantic = load_module(
        SEMANTIC_AUTHORITY,
        "memory_os_backup_restore_semantic_negative_target",
    )
    coherent = load_module(
        COHERENT_AUTHORITY,
        "memory_os_backup_restore_coherent_negative_target",
    )

    baseline = copy.deepcopy(module.load(module.STATUS_PATH))
    require(run_with_status(module, baseline) == 0,
            "canonical six-blocker baseline must validate")
    validate_normalizer_status(normalizer, baseline)
    validate_semantic_status(semantic, baseline)
    validate_coherent_status(coherent, baseline)
    validate_normalizer_transaction(normalizer)
    validate_coherent_transaction(coherent)
    print("PASS baseline: canonical six OPS-P0-007 production blockers")

    extra = status_with_mutation(
        module,
        lambda missing: missing.append(
            "production object backup with independently owned retention, deletion protection and lifecycle verification"
        ),
    )
    expect_rejected(
        "extra legacy production blocker cannot coexist with canonical six",
        lambda: run_with_status(module, extra),
    )
    expect_rejected(
        "canonical normalizer cannot repair an extra legacy blocker",
        lambda: validate_normalizer_status(normalizer, extra),
    )
    expect_rejected(
        "semantic authority cannot repair an extra legacy blocker",
        lambda: validate_semantic_status(semantic, extra),
    )
    expect_rejected(
        "coherent restore authority cannot repair an extra legacy blocker",
        lambda: validate_coherent_status(coherent, extra),
    )

    removed = status_with_mutation(module, lambda missing: missing.pop())
    expect_rejected(
        "canonical production blocker cannot disappear",
        lambda: run_with_status(module, removed),
    )
    expect_rejected(
        "canonical normalizer cannot repair a missing canonical blocker",
        lambda: validate_normalizer_status(normalizer, removed),
    )
    expect_rejected(
        "semantic authority cannot repair a missing canonical blocker",
        lambda: validate_semantic_status(semantic, removed),
    )
    expect_rejected(
        "coherent restore authority cannot repair a missing canonical blocker",
        lambda: validate_coherent_status(coherent, removed),
    )

    def replace_with_legacy(missing: list[str]) -> None:
        missing[0] = "production PostgreSQL backup schedule, independent retention and PITR configuration"

    substituted = status_with_mutation(module, replace_with_legacy)
    expect_rejected(
        "legacy blocker wording cannot substitute for canonical semantic authority",
        lambda: run_with_status(module, substituted),
    )
    expect_rejected(
        "canonical normalizer cannot rewrite legacy blocker wording",
        lambda: validate_normalizer_status(normalizer, substituted),
    )
    expect_rejected(
        "semantic authority cannot rewrite legacy blocker wording",
        lambda: validate_semantic_status(semantic, substituted),
    )
    expect_rejected(
        "coherent restore authority cannot rewrite legacy blocker wording",
        lambda: validate_coherent_status(coherent, substituted),
    )

    reordered = status_with_mutation(
        module,
        lambda missing: missing.__setitem__(slice(None), list(reversed(missing))),
    )
    expect_rejected(
        "canonical production blockers cannot be reordered",
        lambda: run_with_status(module, reordered),
    )
    expect_rejected(
        "canonical normalizer cannot reorder canonical blockers",
        lambda: validate_normalizer_status(normalizer, reordered),
    )
    expect_rejected(
        "semantic authority cannot reorder canonical blockers",
        lambda: validate_semantic_status(semantic, reordered),
    )
    expect_rejected(
        "coherent restore authority cannot reorder canonical blockers",
        lambda: validate_coherent_status(coherent, reordered),
    )

    def cross_domain_duplicate(missing: list[str]) -> None:
        missing[-1] = (
            "independent review of generation-bound recovery evidence after production PostgreSQL backup and PITR schedule validation"
        )

    duplicated = status_with_mutation(module, cross_domain_duplicate)
    expect_rejected(
        "one blocker row cannot duplicate another canonical blocker domain",
        lambda: run_with_status(module, duplicated),
    )
    expect_rejected(
        "canonical normalizer cannot accept cross-domain blocker duplication",
        lambda: validate_normalizer_status(normalizer, duplicated),
    )
    expect_rejected(
        "semantic authority cannot accept cross-domain blocker duplication",
        lambda: validate_semantic_status(semantic, duplicated),
    )
    expect_rejected(
        "coherent restore authority cannot accept cross-domain blocker duplication",
        lambda: validate_coherent_status(coherent, duplicated),
    )

    print("Memory OS backup/restore canonical blocker negative suite PASS")
    print("canonical blocker count: 6")
    print("canonical normalizer repair behavior: disabled")
    print("canonical normalizer post-write rollback: enforced")
    print("semantic authority repair behavior: disabled")
    print("coherent restore blocker repair behavior: disabled")
    print("coherent restore post-write rollback: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE BLOCKER NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
