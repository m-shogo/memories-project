#!/usr/bin/env python3
"""Focused negative for cross-generation material-delta review execution authority."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical material-delta validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == Path("scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"), "canonical material-delta validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_material_delta_execution_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load material-delta validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same_generation_row() -> dict[str, Any]:
    return {
        "sourceEnvironmentGenerationId": "pegen_same_execution_negative",
        "restoreTargetGenerationId": "pegen_same_execution_negative",
        "materialDeltaReviewRef": None,
    }


def expect_candidate_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        try:
            module.material_delta_review_approved(same_generation_row())
        except module.Fail:
            return
        raise Fail(f"material-delta candidate execution substitution unexpectedly passed: {field}")
    finally:
        setattr(module, field, original)


def expect_main_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str, expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"material-delta main execution substitution unexpectedly passed: {label}")
    finally:
        restore()


def expect_row_rejected(module: Any, row: dict[str, Any], label: str) -> None:
    required_fields = module.validate_contract_authority()["requiredMaterialDeltaReviewEvidenceFields"]
    try:
        module.validate_row(row, 0, required_fields)
    except module.Fail:
        return
    raise Fail(f"material-delta row semantic negative unexpectedly passed: {label}")


def main() -> int:
    module = load_validator()
    canonical_contract = module.CONTRACT.read_bytes()
    canonical_registry = module.REGISTRY.read_bytes()

    for field, replacement in (
        ("enforce_execution_authority", lambda: None),
        ("enforce_runtime_authorities", lambda: None),
        ("require", lambda *_args: None),
        ("require_exact_repo_file", lambda path, *_args: path),
        ("load_json", lambda *_args: {}),
        ("validate_contract_authority", lambda: {"requiredMaterialDeltaReviewEvidenceFields": []}),
        ("canonical_material_delta_ref", lambda *_args: ("docs/evidence/backup-restore/material-delta/fake.json", Path("/tmp/fake-material-delta.json"))),
        ("git_history", lambda *_args: ["a" * 40]),
        ("require_append_only_review", lambda *_args: None),
        ("require_utc_rfc3339", lambda value, _field: value),
        ("validate_material_delta_payload", lambda *_args: None),
        ("validate_row", lambda *_args: None),
    ):
        expect_candidate_rejected(module, field, replacement)

    original_guard = module.enforce_execution_authority
    expect_main_rejected(
        module,
        lambda: setattr(module, "enforce_execution_authority", lambda: None),
        lambda: setattr(module, "enforce_execution_authority", original_guard),
        "main execution guard substitution",
        "main execution guard drift",
    )

    original_candidate = module.material_delta_review_approved
    expect_main_rejected(
        module,
        lambda: setattr(module, "material_delta_review_approved", lambda _row: True),
        lambda: setattr(module, "material_delta_review_approved", original_candidate),
        "main material-delta candidate substitution",
        "candidate authority drift",
    )

    original_guard = module.enforce_execution_authority
    original_candidate = module.material_delta_review_approved
    def mutate_both() -> None:
        module.enforce_execution_authority = lambda: None
        module.material_delta_review_approved = lambda _row: True
    def restore_both() -> None:
        module.enforce_execution_authority = original_guard
        module.material_delta_review_approved = original_candidate
    expect_main_rejected(
        module,
        mutate_both,
        restore_both,
        "main guard and candidate double substitution",
        "main execution guard drift",
    )

    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_execution_negative",
            "restoreTargetGenerationId": "pegen_target_execution_negative",
            "materialDeltaReviewRef": "SECURITY.md",
        },
        "generic repository review ref",
    )
    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_same_execution_negative",
            "restoreTargetGenerationId": "pegen_same_execution_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/should-be-null.json",
        },
        "same-generation non-null review ref",
    )
    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_execution_negative",
            "restoreTargetGenerationId": "pegen_target_execution_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/../escape.json",
        },
        "material-delta path traversal",
    )

    require(module.CONTRACT.read_bytes() == canonical_contract, "execution substitution mutated canonical generation evidence contract")
    require(module.REGISTRY.read_bytes() == canonical_registry, "execution substitution mutated canonical generation evidence registry")
    print("Memory OS generation material-delta execution authority negative PASS")
    print("candidate execution helper substitution accepted: false")
    print("main execution guard substitution accepted: false")
    print("main candidate helper substitution accepted: false")
    print("main double substitution accepted: false")
    print("generic repository material-delta ref accepted: false")
    print("same-generation non-null material-delta ref accepted: false")
    print("material-delta path traversal accepted: false")
    print("canonical authority mutation: false")
    print("automatic production promotion authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION MATERIAL DELTA EXECUTION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
