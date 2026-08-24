#!/usr/bin/env python3
"""Fail closed if generation-evidence executable or data authority is substituted."""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-evidence.yml"
EXPECTED_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
EXPECTED_NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
EXPECTED_SEMANTIC_NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-semantic-generation-negative.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GENERATION_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
EXPECTED_DRILL_REQUEST_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EXPECTED_DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
EXPECTED_GENERATION_BINDING = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
EXPECTED_NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_NON_RESURRECTION_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_NON_RESURRECTION_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
EXPECTED_INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
EXPECTED_INDEPENDENT_REVIEW_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-negative.py"
EXPECTED_MATERIAL_DELTA_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"
EXPECTED_MATERIAL_DELTA_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, module_name: str, label: str) -> Any:
    require(path.is_file(), f"canonical {label} missing")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> Any:
    return load_module(WRITER, "memory_os_generation_evidence_writer_authority", "generation-evidence writer")


def load_generation_validator() -> Any:
    return load_module(EXPECTED_VALIDATOR, "memory_os_generation_evidence_validator_authority", "generation-evidence validator")


def load_contract() -> dict[str, Any]:
    try:
        value = json.loads(EXPECTED_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"generation-evidence contract unreadable or invalid: {exc}") from exc
    require(isinstance(value, dict), "generation-evidence contract root must be object")
    return value


def require_contract_ref(contract: dict[str, Any], field: str, expected: Path, label: str) -> None:
    expected_ref = expected.relative_to(ROOT).as_posix()
    require(contract.get(field) == expected_ref, f"generation-evidence contract {label} ref drift")
    require(expected.is_file(), f"canonical {label} missing")


def require_canonical_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"generation-evidence validator {label} authority drift")
    require(expected.is_file(), f"canonical generation-evidence {label} missing")
    require(not expected.is_symlink(), f"canonical generation-evidence {label} must not be symlink")
    try:
        require(expected.resolve(strict=True) == expected, f"canonical generation-evidence {label} resolved path drift")
    except OSError as exc:
        raise Fail(f"canonical generation-evidence {label} cannot resolve: {exc}") from exc


def require_authority(writer: Any, name: str, expected: Path, label: str) -> None:
    actual = getattr(writer, name, None)
    require(actual == expected, f"generation-evidence {label} authority drift")
    canonical_repo_file = getattr(writer, "canonical_repo_file", None)
    require(callable(canonical_repo_file), "canonical repository authority guard missing")
    canonical_repo_file(actual, label)


def require_generation_validator_authorities(validator: Any) -> None:
    for name, expected, label in (
        ("CONTRACT", EXPECTED_CONTRACT, "contract"),
        ("REGISTRY", EXPECTED_REGISTRY, "registry"),
        ("GEN_REGISTRY", EXPECTED_GENERATION_REGISTRY, "environment generation registry"),
        ("OBJECTIVES_REGISTRY", EXPECTED_OBJECTIVES_REGISTRY, "recovery objectives registry"),
        ("DRILL_CONTRACT", EXPECTED_DRILL_REQUEST_CONTRACT, "drill request contract"),
        ("DRILL_REGISTRY", EXPECTED_DRILL_REQUEST_REGISTRY, "drill request registry"),
        ("GEN_BINDING", EXPECTED_GENERATION_BINDING, "generation binding contract"),
        ("WRITER", WRITER, "writer"),
        ("NEGATIVE_VALIDATOR", EXPECTED_NEGATIVE_VALIDATOR, "negative admission validator"),
        ("SEMANTIC_NEGATIVE_VALIDATOR", EXPECTED_SEMANTIC_NEGATIVE_VALIDATOR, "semantic generation negative validator"),
    ):
        actual = getattr(validator, name, None)
        require_canonical_file(actual, expected, label)


def require_cli_guard(writer: Any) -> None:
    guard = getattr(writer, "require_cli_authorities", None)
    require(callable(guard), "generation-evidence writer CLI canonical authority guard missing")
    main_source = inspect.getsource(writer.main)
    guard_index = main_source.find("require_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser")
    require(guard_index >= 0, "generation-evidence writer CLI does not invoke canonical authority guard")
    require(
        parser_index >= 0 and guard_index < parser_index,
        "generation-evidence writer CLI authority guard must run before argument parsing",
    )
    try:
        guard()
    except writer.Fail as exc:
        raise Fail(f"canonical generation-evidence writer CLI authority rejected: {exc}") from exc


def require_atomic_diagnostic_publication() -> None:
    require(WORKFLOW.is_file(), "generation-evidence workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"generation-evidence diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "generation-evidence diagnostic publication regressed to direct write_text",
    )


def run_review_validator(path: Path, module_name: str, label: str) -> None:
    module = load_module(path, module_name, label)
    if hasattr(module, "REGISTRY"):
        require(getattr(module, "REGISTRY") == EXPECTED_REGISTRY, f"{label} registry authority drift")
    try:
        result = module.main()
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            raise Fail(f"{label} invalid: {exc}") from exc
        raise
    require(result == 0, f"{label} did not complete successfully")


def main() -> int:
    writer = load_writer()
    validator = load_generation_validator()
    contract = load_contract()
    require_cli_guard(writer)
    require_generation_validator_authorities(validator)

    for name, expected, label in (
        ("CONTRACT", EXPECTED_CONTRACT, "contract"),
        ("REGISTRY", EXPECTED_REGISTRY, "registry"),
        ("GEN_REGISTRY", EXPECTED_GENERATION_REGISTRY, "environment-generation registry"),
        ("GEN_WRITER", EXPECTED_GENERATION_WRITER, "environment-generation writer"),
        ("OBJECTIVES_REGISTRY", EXPECTED_OBJECTIVES_REGISTRY, "recovery-objectives registry"),
        ("OBJECTIVES_WRITER", EXPECTED_OBJECTIVES_WRITER, "recovery-objectives writer"),
        ("DRILL_REQUEST_CONTRACT", EXPECTED_DRILL_REQUEST_CONTRACT, "drill-request contract"),
        ("DRILL_REQUEST_REGISTRY", EXPECTED_DRILL_REQUEST_REGISTRY, "drill-request registry"),
        ("DRILL_REQUEST_WRITER", EXPECTED_DRILL_REQUEST_WRITER, "drill-request writer"),
        ("NON_RESURRECTION_CONTRACT", EXPECTED_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract"),
        ("NON_RESURRECTION_REGISTRY", EXPECTED_NON_RESURRECTION_REGISTRY, "typed non-resurrection registry"),
        ("NON_RESURRECTION_WRITER", EXPECTED_NON_RESURRECTION_WRITER, "typed non-resurrection writer"),
        ("INDEPENDENT_REVIEW_VALIDATOR", EXPECTED_INDEPENDENT_REVIEW_VALIDATOR, "independent-review validator"),
    ):
        require_authority(writer, name, expected, label)

    require_contract_ref(contract, "independentReviewValidator", EXPECTED_INDEPENDENT_REVIEW_VALIDATOR, "independent-review validator")
    require_contract_ref(contract, "independentReviewNegativeValidator", EXPECTED_INDEPENDENT_REVIEW_NEGATIVE, "independent-review negative validator")
    require_contract_ref(contract, "materialDeltaReviewValidator", EXPECTED_MATERIAL_DELTA_VALIDATOR, "material-delta review validator")
    require_contract_ref(contract, "materialDeltaReviewNegativeValidator", EXPECTED_MATERIAL_DELTA_NEGATIVE, "material-delta review negative validator")

    lock = getattr(writer, "LOCK", None)
    require(lock == EXPECTED_LOCK, "generation-evidence append lock authority drift")
    require(lock.parent == EXPECTED_REGISTRY.parent, "generation-evidence append lock must share registry authority directory")

    independent_reviews_satisfied = getattr(writer, "independent_reviews_satisfied", None)
    require(callable(independent_reviews_satisfied), "candidate independent-review delegation missing")
    require(
        independent_reviews_satisfied(
            {
                "securityReviewRef": "README.md",
                "operabilityReviewRef": "SECURITY.md",
            }
        )
        is False,
        "generic repository review refs bypass strict candidate review authority",
    )

    run_review_validator(
        EXPECTED_INDEPENDENT_REVIEW_VALIDATOR,
        "memory_os_generation_independent_review_authority",
        "generation independent-review validator",
    )
    run_review_validator(
        EXPECTED_INDEPENDENT_REVIEW_NEGATIVE,
        "memory_os_generation_independent_review_negative_authority",
        "generation independent-review negative validator",
    )
    run_review_validator(
        EXPECTED_MATERIAL_DELTA_VALIDATOR,
        "memory_os_generation_material_delta_review_authority",
        "generation material-delta review validator",
    )
    run_review_validator(
        EXPECTED_MATERIAL_DELTA_NEGATIVE,
        "memory_os_generation_material_delta_review_negative_authority",
        "generation material-delta review negative validator",
    )
    require_atomic_diagnostic_publication()

    print("Memory OS generation-evidence executable/data authority validation PASS")
    print("generation-evidence CLI authority guard required: true")
    print("generation-evidence validator data/writer authority substitution accepted: false")
    print("generation-evidence negative validator authority substitution accepted: false")
    print("generation-evidence semantic negative validator authority substitution accepted: false")
    print("environment-generation authority substitution accepted: false")
    print("recovery-objectives authority substitution accepted: false")
    print("drill-request authority substitution accepted: false")
    print("typed non-resurrection authority substitution accepted: false")
    print("independent review authority substitution accepted: false")
    print("generic repository review refs create candidate eligibility: false")
    print("material-delta review authority substitution accepted: false")
    print("append lock authority substitution accepted: false")
    print("crash-safe generation-evidence failure diagnostic required: true")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE WRITER AUTHORITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
