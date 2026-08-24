#!/usr/bin/env python3
"""Fail closed on mutable, generic, or semantically unbound material-delta review references.

Cross-generation recovery evidence must reference one committed, append-only typed review
under `docs/evidence/backup-restore/material-delta/`. The review must bind the exact
recovery evidence, drill request, recovery objective, source generation, and target
generation. Same-generation evidence must keep the reference null. This validator does
not create review evidence or production authority.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-material-delta-review.py")
NEGATIVE_REL = Path("scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
VALIDATOR = ROOT / VALIDATOR_REL
NEGATIVE = ROOT / NEGATIVE_REL
MATERIAL_DELTA_ROOT = Path("docs/evidence/backup-restore/material-delta")
EXPECTED_SCHEMA = "memory-os-backup-restore-material-delta-review.v1"
EXPECTED_VALIDATOR = VALIDATOR_REL.as_posix()
EXPECTED_NEGATIVE = NEGATIVE_REL.as_posix()
REVIEW_RESULT = "APPROVED"
REVIEWER = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "generation evidence contract"),
        (REGISTRY, REGISTRY_REL, "generation evidence registry"),
        (VALIDATOR, VALIDATOR_REL, "material-delta review validator"),
        (NEGATIVE, NEGATIVE_REL, "material-delta review negative validator"),
    ):
        require_exact_repo_file(path, expected, field)


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{field} unreadable or invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{field} root must be object")
    return value


def validate_contract_authority() -> dict[str, Any]:
    require_exact_repo_file(CONTRACT, CONTRACT_REL, "generation evidence contract")
    contract = load_json(CONTRACT, "generation evidence contract")
    require(contract.get("materialDeltaReviewEvidenceRoot") == MATERIAL_DELTA_ROOT.as_posix(), "material-delta review evidence root authority drift")
    require(contract.get("materialDeltaReviewEvidenceSchemaVersion") == EXPECTED_SCHEMA, "material-delta review evidence schema authority drift")
    require(contract.get("materialDeltaReviewValidator") == EXPECTED_VALIDATOR, "material-delta review validator authority drift")
    require(contract.get("materialDeltaReviewNegativeValidator") == EXPECTED_NEGATIVE, "material-delta review negative validator authority drift")
    required_fields = contract.get("requiredMaterialDeltaReviewEvidenceFields")
    require(required_fields == [
        "schemaVersion", "evidenceId", "drillRequestId", "recoveryObjectivesId",
        "sourceEnvironmentGenerationId", "restoreTargetGenerationId", "reviewResult",
        "reviewedAt", "reviewerPseudonym", "productionTrafficChanged",
        "productionCredentialsUsed", "automaticPromotion",
    ], "material-delta review required fields authority drift")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict), "generation evidence recordRules missing")
    for rule in (
        "crossGenerationRestoreRequiresMaterialDeltaReview",
        "sameGenerationRestoreMayUseNullMaterialDeltaReview",
        "crossGenerationMaterialDeltaReviewMustRemainInsideMonitoredNamespace",
        "crossGenerationMaterialDeltaReviewMustRemainAppendOnlyAfterFirstCommit",
        "crossGenerationMaterialDeltaReviewMustBeTyped",
        "crossGenerationMaterialDeltaReviewMustBindEvidenceId",
        "crossGenerationMaterialDeltaReviewMustBindDrillRequestId",
        "crossGenerationMaterialDeltaReviewMustBindRecoveryObjectivesId",
        "crossGenerationMaterialDeltaReviewMustBindSourceGenerationId",
        "crossGenerationMaterialDeltaReviewMustBindRestoreTargetGenerationId",
        "crossGenerationMaterialDeltaReviewMustBeApproved",
        "crossGenerationMaterialDeltaReviewCannotAuthorizeAutomaticPromotion",
        "candidateDerivationMustUseTypedMaterialDeltaReviewAuthority",
    ):
        require(rules.get(rule) is True, f"material-delta review contract rule drift: {rule}")
    promotion = contract.get("promotionBoundary")
    require(isinstance(promotion, dict), "generation evidence promotionBoundary missing")
    require(promotion.get("completeReviewedRecordAlsoRequiresTypedAppendOnlyMaterialDeltaReviewForCrossGenerationRestore") is True, "material-delta promotion boundary drift")
    return contract


def canonical_material_delta_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be canonical repository-relative path")
    require(relative.parts[: len(MATERIAL_DELTA_ROOT.parts)] == MATERIAL_DELTA_ROOT.parts and len(relative.parts) > len(MATERIAL_DELTA_ROOT.parts), f"{field} must remain inside {MATERIAL_DELTA_ROOT.as_posix()}/")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to canonical repository file")
    return value, path


def git_history(ref: str, field: str) -> list[str]:
    completed = subprocess.run(["git", "log", "--format=%H", "--follow", "--", ref], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"cannot inspect {field} Git history")
    commits = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(commits, f"{field} must be committed material-delta review evidence")
    return commits


def require_append_only_review(ref: str, path: Path, field: str) -> None:
    commits = git_history(ref, field)
    require(len(commits) == 1, f"{field} must remain append-only after its first committed version")
    completed = subprocess.run(["git", "show", f"{commits[0]}:{ref}"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"cannot read initial committed bytes for {field}")
    require(path.read_bytes() == completed.stdout, f"{field} bytes drift from initial committed material-delta review evidence")


def require_utc_rfc3339(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} required")
    require(len(value) == 20 and value.endswith("Z"), f"{field} must be canonical UTC RFC3339 seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise Fail(f"{field} must be canonical UTC RFC3339 seconds") from exc
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, f"{field} must be canonical UTC RFC3339 seconds")
    return value


def validate_material_delta_payload(row: dict[str, Any], payload: dict[str, Any], index: int, required_fields: list[str]) -> None:
    field = f"records[{index}].materialDeltaReviewRef"
    require(set(payload) == set(required_fields), f"{field} typed review fields drift")
    require(payload.get("schemaVersion") == EXPECTED_SCHEMA, f"{field} schemaVersion drift")
    require(payload.get("evidenceId") == row.get("evidenceId"), f"{field} evidenceId mismatch")
    require(payload.get("drillRequestId") == row.get("drillRequestId"), f"{field} drillRequestId mismatch")
    require(payload.get("recoveryObjectivesId") == row.get("recoveryObjectivesId"), f"{field} recoveryObjectivesId mismatch")
    require(payload.get("sourceEnvironmentGenerationId") == row.get("sourceEnvironmentGenerationId"), f"{field} sourceEnvironmentGenerationId mismatch")
    require(payload.get("restoreTargetGenerationId") == row.get("restoreTargetGenerationId"), f"{field} restoreTargetGenerationId mismatch")
    require(payload.get("reviewResult") == REVIEW_RESULT, f"{field} reviewResult must be APPROVED")
    require_utc_rfc3339(payload.get("reviewedAt"), f"{field} reviewedAt")
    reviewer = payload.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and REVIEWER.fullmatch(reviewer), f"{field} reviewerPseudonym invalid")
    require(payload.get("productionTrafficChanged") is False, f"{field} productionTrafficChanged must remain false")
    require(payload.get("productionCredentialsUsed") is False, f"{field} productionCredentialsUsed must remain false")
    require(payload.get("automaticPromotion") is False, f"{field} automaticPromotion must remain false")


def validate_row(row: dict[str, Any], index: int, required_fields: list[str]) -> None:
    source = row.get("sourceEnvironmentGenerationId")
    target = row.get("restoreTargetGenerationId")
    require(isinstance(source, str) and source, f"records[{index}] sourceEnvironmentGenerationId required")
    require(isinstance(target, str) and target, f"records[{index}] restoreTargetGenerationId required")
    value = row.get("materialDeltaReviewRef")
    if source == target:
        require(value is None, f"records[{index}] same-generation restore must not declare materialDeltaReviewRef")
        return
    ref, path = canonical_material_delta_ref(value, f"records[{index}].materialDeltaReviewRef")
    require_append_only_review(ref, path, f"records[{index}].materialDeltaReviewRef")
    payload = load_json(path, f"records[{index}].materialDeltaReviewRef")
    validate_material_delta_payload(row, payload, index, required_fields)


CANONICAL_REQUIRE = require
CANONICAL_EXECUTION_HELPERS = (
    enforce_runtime_authorities,
    require_exact_repo_file,
    load_json,
    validate_contract_authority,
    canonical_material_delta_ref,
    git_history,
    require_append_only_review,
    require_utc_rfc3339,
    validate_material_delta_payload,
    validate_row,
)
CANONICAL_AUTHORITY_CONFIG = (
    CONTRACT_REL.as_posix(),
    REGISTRY_REL.as_posix(),
    VALIDATOR_REL.as_posix(),
    NEGATIVE_REL.as_posix(),
    MATERIAL_DELTA_ROOT.as_posix(),
    EXPECTED_SCHEMA,
    EXPECTED_VALIDATOR,
    EXPECTED_NEGATIVE,
    REVIEW_RESULT,
    REVIEWER.pattern,
)


def enforce_execution_authority(
    canonical_require=CANONICAL_REQUIRE,
    canonical_helpers: tuple[Any, ...] = CANONICAL_EXECUTION_HELPERS,
    canonical_config: tuple[Any, ...] = CANONICAL_AUTHORITY_CONFIG,
) -> None:
    expected_root = Path(enforce_execution_authority.__code__.co_filename).resolve().parents[1]
    try:
        actual_root = ROOT.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise Fail("material-delta review repository root missing") from exc
    if actual_root != expected_root:
        raise Fail("material-delta review repository root drift")
    if require is not canonical_require:
        raise Fail("material-delta review require helper drift")
    current_helpers = (
        enforce_runtime_authorities,
        require_exact_repo_file,
        load_json,
        validate_contract_authority,
        canonical_material_delta_ref,
        git_history,
        require_append_only_review,
        require_utc_rfc3339,
        validate_material_delta_payload,
        validate_row,
    )
    if current_helpers != canonical_helpers:
        raise Fail("material-delta review execution helper drift")
    current_config = (
        CONTRACT_REL.as_posix(),
        REGISTRY_REL.as_posix(),
        VALIDATOR_REL.as_posix(),
        NEGATIVE_REL.as_posix(),
        MATERIAL_DELTA_ROOT.as_posix(),
        EXPECTED_SCHEMA,
        EXPECTED_VALIDATOR,
        EXPECTED_NEGATIVE,
        REVIEW_RESULT,
        REVIEWER.pattern,
    )
    if current_config != canonical_config:
        raise Fail("material-delta review semantic authority drift")


CANONICAL_EXECUTION_GUARD = enforce_execution_authority


def material_delta_review_approved(
    row: dict[str, Any],
    canonical_execution_guard=CANONICAL_EXECUTION_GUARD,
) -> bool:
    if enforce_execution_authority is not canonical_execution_guard:
        raise Fail("material-delta review execution guard drift")
    enforce_execution_authority()
    enforce_runtime_authorities()
    contract = validate_contract_authority()
    validate_row(row, 0, contract["requiredMaterialDeltaReviewEvidenceFields"])
    return True


CANONICAL_MATERIAL_DELTA_REVIEW = material_delta_review_approved
CANONICAL_MAIN_EXECUTION_GUARD = enforce_execution_authority


def main(
    canonical_material_delta_review=CANONICAL_MATERIAL_DELTA_REVIEW,
    canonical_execution_guard=CANONICAL_MAIN_EXECUTION_GUARD,
) -> int:
    if enforce_execution_authority is not canonical_execution_guard:
        raise Fail("material-delta review main execution guard drift")
    if material_delta_review_approved is not canonical_material_delta_review:
        raise Fail("material-delta review candidate authority drift")
    enforce_execution_authority()
    enforce_runtime_authorities()
    contract = validate_contract_authority()
    required_fields = contract["requiredMaterialDeltaReviewEvidenceFields"]
    registry = load_json(REGISTRY, "generation evidence registry")
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    for index, row in enumerate(rows):
        validate_row(row, index, required_fields)
    print(f"PASS: typed generation material-delta review authority records={len(rows)} productionEvidence=false productionReady=false")
    print("canonical generation evidence contract/registry authority substitution accepted: false")
    print("material-delta review execution helper substitution accepted: false")
    print("paired semantic authority substitution accepted: false")
    print("automatic promotion authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
