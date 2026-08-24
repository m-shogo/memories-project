#!/usr/bin/env python3
"""Focused negative for final-candidate independent-review execution authority."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical independent-review validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == Path("scripts/validate-memory-os-backup-restore-generation-independent-review.py"), "canonical independent-review validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_execution_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent-review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_candidate_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail:
            return
        raise Fail(f"candidate execution substitution unexpectedly passed: {field}")
    finally:
        setattr(module, field, original)


def expect_candidate_mutation_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str) -> None:
    mutate()
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail as exc:
            require("semantic authority drift" in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"candidate semantic authority substitution unexpectedly passed: {label}")
    finally:
        restore()


def expect_main_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str, expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"main execution substitution unexpectedly passed: {label}")
    finally:
        restore()


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
        ("validate_contract_authority", lambda: None),
        ("canonical_ref", lambda *_args: ("docs/evidence/backup-restore/fake.json", Path("/tmp/fake-review.json"))),
        ("git_history", lambda *_args: ["a" * 40]),
        ("require_append_only_review", lambda *_args: None),
        ("require_utc_rfc3339", lambda value, _field: value),
        ("validate_review", lambda *_args: ("docs/evidence/backup-restore/fake.json", "reviewer-fake")),
        ("load_material_delta_validator", lambda: object()),
    ):
        expect_candidate_rejected(module, field, replacement)

    original_contract = module.CONTRACT
    original_contract_rel = module.CONTRACT_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "CONTRACT", module.REGISTRY), setattr(module, "CONTRACT_REL", module.REGISTRY_REL)),
        lambda: (setattr(module, "CONTRACT", original_contract), setattr(module, "CONTRACT_REL", original_contract_rel)),
        "paired contract path authority substitution",
    )

    original_registry = module.REGISTRY
    original_registry_rel = module.REGISTRY_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "REGISTRY", module.CONTRACT), setattr(module, "REGISTRY_REL", module.CONTRACT_REL)),
        lambda: (setattr(module, "REGISTRY", original_registry), setattr(module, "REGISTRY_REL", original_registry_rel)),
        "paired registry path authority substitution",
    )

    original_material = module.MATERIAL_DELTA_VALIDATOR
    original_material_rel = module.MATERIAL_DELTA_VALIDATOR_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "MATERIAL_DELTA_VALIDATOR", module.VALIDATOR), setattr(module, "MATERIAL_DELTA_VALIDATOR_REL", module.VALIDATOR_REL)),
        lambda: (setattr(module, "MATERIAL_DELTA_VALIDATOR", original_material), setattr(module, "MATERIAL_DELTA_VALIDATOR_REL", original_material_rel)),
        "paired material-delta validator authority substitution",
    )

    original_evidence_root = module.EVIDENCE_ROOT
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "EVIDENCE_ROOT", Path("docs/evidence")),
        lambda: setattr(module, "EVIDENCE_ROOT", original_evidence_root),
        "review evidence root widening",
    )

    original_schema = module.REVIEW_SCHEMA
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEW_SCHEMA", "memory-os-backup-restore-generation-review-evidence.v0"),
        lambda: setattr(module, "REVIEW_SCHEMA", original_schema),
        "review schema substitution",
    )

    original_fields = module.REQUIRED_FIELDS
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REQUIRED_FIELDS", set(original_fields) - {"drillRequestId"}),
        lambda: setattr(module, "REQUIRED_FIELDS", original_fields),
        "required review field removal",
    )

    original_roles = module.ROLE_BY_REF
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "ROLE_BY_REF", {"securityReviewRef": "OPERABILITY", "operabilityReviewRef": "SECURITY"}),
        lambda: setattr(module, "ROLE_BY_REF", original_roles),
        "review role map substitution",
    )

    original_reviewer = module.REVIEWER_ID
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEWER_ID", re.compile(r"^.*$")),
        lambda: setattr(module, "REVIEWER_ID", original_reviewer),
        "reviewer identity rule widening",
    )

    original_guard = module.enforce_execution_authority
    expect_main_rejected(
        module,
        lambda: setattr(module, "enforce_execution_authority", lambda: None),
        lambda: setattr(module, "enforce_execution_authority", original_guard),
        "main execution guard substitution",
        "main execution guard drift",
    )

    original_candidate = module.candidate_reviews_approved
    expect_main_rejected(
        module,
        lambda: setattr(module, "candidate_reviews_approved", lambda _row: True),
        lambda: setattr(module, "candidate_reviews_approved", original_candidate),
        "main candidate helper substitution",
        "candidate authority drift",
    )

    original_guard = module.enforce_execution_authority
    original_candidate = module.candidate_reviews_approved
    def mutate_both() -> None:
        module.enforce_execution_authority = lambda: None
        module.candidate_reviews_approved = lambda _row: True
    def restore_both() -> None:
        module.enforce_execution_authority = original_guard
        module.candidate_reviews_approved = original_candidate
    expect_main_rejected(
        module,
        mutate_both,
        restore_both,
        "main guard and candidate double substitution",
        "main execution guard drift",
    )

    require(module.CONTRACT.read_bytes() == canonical_contract, "execution substitution mutated canonical generation evidence contract")
    require(module.REGISTRY.read_bytes() == canonical_registry, "execution substitution mutated canonical generation evidence registry")
    print("Memory OS generation independent-review execution authority negative PASS")
    print("candidate execution helper substitution accepted: false")
    print("paired semantic authority substitution accepted: false")
    print("main execution guard substitution accepted: false")
    print("main candidate helper substitution accepted: false")
    print("main double substitution accepted: false")
    print("canonical authority mutation: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION INDEPENDENT REVIEW EXECUTION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
