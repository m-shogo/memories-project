#!/usr/bin/env python3
"""Fail-closed validation for generation recovery candidate independent reviews.

Security and Operability review payloads must be typed, distinct, repository-contained,
append-only in Git history after their first committed version, and bound to the exact
recovery authority they approve. Cross-generation candidates must also satisfy the
canonical typed material-delta review authority. All candidate reviews must satisfy the
canonical source-commit chronology authority before candidate admission. This validator
never creates review evidence or production authority.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
MATERIAL_DELTA_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-material-delta-review.py")
REVIEW_SOURCE_ORDER_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-review-source-order.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-independent-review.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
REVIEW_SCHEMA = "memory-os-backup-restore-generation-review-evidence.v1"
MATERIAL_DELTA_VALIDATOR = ROOT / MATERIAL_DELTA_VALIDATOR_REL
REVIEW_SOURCE_ORDER_VALIDATOR = ROOT / REVIEW_SOURCE_ORDER_VALIDATOR_REL
VALIDATOR = ROOT / VALIDATOR_REL
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
REQUIRED_FIELDS = {
    "schemaVersion", "evidenceId", "drillRequestId", "recoveryObjectivesId",
    "sourceEnvironmentGenerationId", "restoreTargetGenerationId", "reviewRole",
    "reviewResult", "reviewedAt", "reviewerPseudonym", "productionTrafficChanged",
    "productionCredentialsUsed", "automaticPromotion",
}
BOUND_FIELDS = (
    "evidenceId", "drillRequestId", "recoveryObjectivesId",
    "sourceEnvironmentGenerationId", "restoreTargetGenerationId",
)
ROLE_BY_REF = {"securityReviewRef": "SECURITY", "operabilityReviewRef": "OPERABILITY"}
BOUND_RULE_BY_FIELD = {
    "evidenceId": "independentReviewMustBindEvidenceId",
    "drillRequestId": "independentReviewMustBindDrillRequestId",
    "recoveryObjectivesId": "independentReviewMustBindRecoveryObjectivesId",
    "sourceEnvironmentGenerationId": "independentReviewMustBindSourceEnvironmentGenerationId",
    "restoreTargetGenerationId": "independentReviewMustBindRestoreTargetGenerationId",
}


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
        (MATERIAL_DELTA_VALIDATOR, MATERIAL_DELTA_VALIDATOR_REL, "candidate material-delta review validator"),
        (REVIEW_SOURCE_ORDER_VALIDATOR, REVIEW_SOURCE_ORDER_VALIDATOR_REL, "candidate review source-order validator"),
        (VALIDATOR, VALIDATOR_REL, "generation independent-review validator"),
    ):
        require_exact_repo_file(path, expected, field)


MAX_JSON_BYTES = 1024 * 1024


def load_json(path: Path, field: str) -> dict[str, Any]:
    """Reject ambiguous independent-review JSON before candidate admission."""
    require(isinstance(path, Path) and path.is_absolute(), "independent review JSON path invalid")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail("independent review JSON path missing or unsafe") from None
    require(
        resolved == path and path.is_file() and not path.is_symlink(),
        "independent review JSON path missing or unsafe",
    )

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "independent review JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("independent review JSON nonfinite number refused")

    def parse_finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "independent review JSON nonfinite number refused")
        return number

    def parse_bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "independent review JSON integer too large")
        return int(value)

    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "independent review JSON size limit exceeded")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite,
            parse_float=parse_finite_float,
            parse_int=parse_bounded_int,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("independent review JSON unreadable or invalid") from None
    require(isinstance(value, dict), "independent review JSON root must be object")
    return value

def validate_contract_authority() -> None:
    require_exact_repo_file(CONTRACT, CONTRACT_REL, "generation evidence contract")
    contract = load_json(CONTRACT, "generation evidence contract")
    require(contract.get("independentReviewEvidenceSchemaVersion") == REVIEW_SCHEMA, "independent review evidence schema authority drift")
    require(contract.get("independentReviewEvidenceRoot") == EVIDENCE_ROOT.as_posix(), "independent review evidence root authority drift")
    require(contract.get("materialDeltaReviewValidator") == MATERIAL_DELTA_VALIDATOR_REL.as_posix(), "candidate material-delta review validator authority drift")
    require(contract.get("reviewSourceOrderValidator") == REVIEW_SOURCE_ORDER_VALIDATOR_REL.as_posix(), "candidate review source-order validator authority drift")
    fields = contract.get("requiredIndependentReviewEvidenceFields")
    require(isinstance(fields, list) and all(isinstance(field, str) and field for field in fields) and len(fields) == len(set(fields)) and set(fields) == REQUIRED_FIELDS, "independent review required field authority drift")
    require(contract.get("independentReviewRoles") == ROLE_BY_REF, "independent review role authority drift")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict), "generation evidence recordRules missing")
    for rule in (
        "independentSecurityAndOperabilityReviewsRequired",
        "typedIndependentReviewEvidenceRequired",
        "candidateDerivationMustUseTypedIndependentReviewAuthority",
        "independentReviewEvidenceMustRemainInsideMonitoredNamespace",
        "independentReviewRoleMustMatchReference",
        "independentReviewMustBeApproved",
        "independentReviewReviewerPseudonymsMustBeDistinct",
        "independentReviewPayloadMustRemainAppendOnlyAfterFirstCommit",
        "independentReviewMustBeCreatedStrictlyAfterSourceCommit",
        "crossGenerationMaterialDeltaReviewMustBeCreatedStrictlyAfterSourceCommit",
        "independentReviewCannotAuthorizeAutomaticPromotion",
    ):
        require(rules.get(rule) is True, f"independent review contract rule drift: {rule}")
    for field, rule in BOUND_RULE_BY_FIELD.items():
        require(rules.get(rule) is True, f"independent review binding rule drift: {field}")
    promotion = contract.get("promotionBoundary")
    require(isinstance(promotion, dict), "generation evidence promotionBoundary missing")
    require(promotion.get("completeReviewedRecordAlsoRequiresTypedAppendOnlyIndependentReviews") is True, "independent review promotion boundary drift")


def canonical_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be canonical repository-relative path")
    require(relative.parts[:3] == EVIDENCE_ROOT.parts, f"{field} must remain inside docs/evidence/backup-restore")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to canonical repository file")
    return value, path


def git_history(ref: str, field: str) -> list[str]:
    # Only the two most recent changes are needed to reject rewritten review evidence.
    # Do not let Git stderr, a stalled subprocess or an unbounded history enter CI diagnostics.
    try:
        completed = subprocess.run(
            ["git", "log", "--format=%H", "--max-count=2", "--follow", "--", ref],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field} Git history") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"cannot inspect {field} Git history")
    require(isinstance(completed.stdout, str), f"{field} Git history output invalid")
    commits = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(commits, f"{field} must be committed review evidence")
    require(len(commits) <= 2 and all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in commits),
            f"{field} Git history output invalid")
    return commits


def require_append_only_review(ref: str, path: Path, field: str) -> None:
    commits = git_history(ref, field)
    require(len(commits) == 1, f"{field} must remain append-only after its first committed version")
    object_ref = f"{commits[0]}:{ref}"
    try:
        size_result = subprocess.run(
            ["git", "cat-file", "-s", object_ref], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect initial committed bytes for {field}") from None
    require(
        type(size_result.returncode) is int and size_result.returncode == 0
        and isinstance(size_result.stdout, str)
        and re.fullmatch(r"[0-9]+\n", size_result.stdout) is not None,
        f"cannot inspect initial committed bytes for {field}",
    )
    size = int(size_result.stdout[:-1])
    require(0 < size <= MAX_JSON_BYTES, f"{field} initial committed bytes size limit exceeded")
    require(path.is_file() and not path.is_symlink(), f"{field} current review path unsafe")
    try:
        with path.open("rb") as source:
            current = source.read(MAX_JSON_BYTES + 1)
    except OSError:
        raise Fail(f"cannot read current review bytes for {field}") from None
    require(len(current) <= MAX_JSON_BYTES, f"{field} current review bytes size limit exceeded")
    try:
        completed = subprocess.run(
            ["git", "show", object_ref], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot read initial committed bytes for {field}") from None
    require(
        type(completed.returncode) is int and completed.returncode == 0
        and isinstance(completed.stdout, bytes),
        f"cannot read initial committed bytes for {field}",
    )
    require(len(completed.stdout) == size, f"{field} initial committed bytes size mismatch")
    require(current == completed.stdout, f"{field} bytes drift from initial committed review evidence")


def require_utc_rfc3339(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} required")
    require(len(value) == 20 and value.endswith("Z"), f"{field} must be canonical UTC RFC3339 seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise Fail(f"{field} must be canonical UTC RFC3339 seconds") from exc
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, f"{field} must be canonical UTC RFC3339 seconds")
    return value


def validate_review(row: dict[str, Any], ref_field: str, expected_role: str) -> tuple[str, str]:
    ref, path = canonical_ref(row.get(ref_field), ref_field)
    require_append_only_review(ref, path, ref_field)
    payload = load_json(path, ref_field)
    require(set(payload) == REQUIRED_FIELDS, f"{ref_field} typed review fields drift")
    require(payload.get("schemaVersion") == REVIEW_SCHEMA, f"{ref_field} schemaVersion drift")
    for field in BOUND_FIELDS:
        require(payload.get(field) == row.get(field), f"{ref_field} {field} mismatch")
    require(payload.get("reviewRole") == expected_role, f"{ref_field} reviewRole mismatch")
    require(payload.get("reviewResult") == "APPROVED", f"{ref_field} review must be APPROVED")
    reviewer = payload.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and REVIEWER_ID.fullmatch(reviewer), f"{ref_field} reviewerPseudonym invalid")
    require_utc_rfc3339(payload.get("reviewedAt"), f"{ref_field} reviewedAt")
    require(payload.get("productionTrafficChanged") is False, f"{ref_field} cannot change production traffic")
    require(payload.get("productionCredentialsUsed") is False, f"{ref_field} cannot use production credentials")
    require(payload.get("automaticPromotion") is False, f"{ref_field} cannot authorize automatic promotion")
    return ref, reviewer


def load_material_delta_validator():
    require_exact_repo_file(MATERIAL_DELTA_VALIDATOR, MATERIAL_DELTA_VALIDATOR_REL, "candidate material-delta review validator")
    spec = importlib.util.spec_from_file_location("memory_os_generation_material_delta_review_for_candidate_reviews", MATERIAL_DELTA_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load candidate material-delta review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT, "candidate material-delta review contract authority drift")
    require(getattr(module, "REGISTRY", None) == REGISTRY, "candidate material-delta review registry authority drift")
    require(callable(getattr(module, "material_delta_review_approved", None)), "candidate material-delta review authority missing")
    require(callable(getattr(module, "enforce_execution_authority", None)), "candidate material-delta execution authority missing")
    require(callable(getattr(module, "enforce_runtime_authorities", None)), "candidate material-delta runtime authority missing")
    require(callable(getattr(module, "validate_contract_authority", None)), "candidate material-delta contract authority missing")
    return module


def load_review_source_order_validator():
    require_exact_repo_file(REVIEW_SOURCE_ORDER_VALIDATOR, REVIEW_SOURCE_ORDER_VALIDATOR_REL, "candidate review source-order validator")
    spec = importlib.util.spec_from_file_location("memory_os_review_source_order_for_candidate_reviews", REVIEW_SOURCE_ORDER_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load candidate review source-order validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT, "candidate review source-order contract authority drift")
    require(getattr(module, "REGISTRY", None) == REGISTRY, "candidate review source-order registry authority drift")
    require(callable(getattr(module, "validate_row", None)), "candidate review source-order authority missing")
    return module


CANONICAL_REQUIRE = require
CANONICAL_EXECUTION_HELPERS = (
    enforce_runtime_authorities,
    require_exact_repo_file,
    load_json,
    validate_contract_authority,
    canonical_ref,
    git_history,
    require_append_only_review,
    require_utc_rfc3339,
    validate_review,
    load_material_delta_validator,
    load_review_source_order_validator,
)
CANONICAL_EXECUTION_TRANSPORT = (
    subprocess.run,
    importlib.util.spec_from_file_location,
    importlib.util.module_from_spec,
)
CANONICAL_AUTHORITY_CONFIG = (
    CONTRACT_REL.as_posix(),
    REGISTRY_REL.as_posix(),
    MATERIAL_DELTA_VALIDATOR_REL.as_posix(),
    REVIEW_SOURCE_ORDER_VALIDATOR_REL.as_posix(),
    VALIDATOR_REL.as_posix(),
    EVIDENCE_ROOT.as_posix(),
    REVIEW_SCHEMA,
    tuple(sorted(REQUIRED_FIELDS)),
    BOUND_FIELDS,
    tuple(sorted(ROLE_BY_REF.items())),
    tuple(sorted(BOUND_RULE_BY_FIELD.items())),
    REVIEWER_ID.pattern,
)


def enforce_execution_authority(
    canonical_require=CANONICAL_REQUIRE,
    canonical_helpers: tuple[Any, ...] = CANONICAL_EXECUTION_HELPERS,
    canonical_transport: tuple[Any, ...] = CANONICAL_EXECUTION_TRANSPORT,
    canonical_config: tuple[Any, ...] = CANONICAL_AUTHORITY_CONFIG,
) -> None:
    expected_root = Path(enforce_execution_authority.__code__.co_filename).resolve().parents[1]
    try:
        actual_root = ROOT.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise Fail("generation independent-review repository root missing") from exc
    if actual_root != expected_root:
        raise Fail("generation independent-review repository root drift")
    if require is not canonical_require:
        raise Fail("generation independent-review require helper drift")
    current_helpers = (
        enforce_runtime_authorities,
        require_exact_repo_file,
        load_json,
        validate_contract_authority,
        canonical_ref,
        git_history,
        require_append_only_review,
        require_utc_rfc3339,
        validate_review,
        load_material_delta_validator,
        load_review_source_order_validator,
    )
    if current_helpers != canonical_helpers:
        raise Fail("generation independent-review execution helper drift")
    current_transport = (
        subprocess.run,
        importlib.util.spec_from_file_location,
        importlib.util.module_from_spec,
    )
    if current_transport != canonical_transport:
        raise Fail("generation independent-review execution transport drift")
    current_config = (
        CONTRACT_REL.as_posix(),
        REGISTRY_REL.as_posix(),
        MATERIAL_DELTA_VALIDATOR_REL.as_posix(),
        REVIEW_SOURCE_ORDER_VALIDATOR_REL.as_posix(),
        VALIDATOR_REL.as_posix(),
        EVIDENCE_ROOT.as_posix(),
        REVIEW_SCHEMA,
        tuple(sorted(REQUIRED_FIELDS)),
        BOUND_FIELDS,
        tuple(sorted(ROLE_BY_REF.items())),
        tuple(sorted(BOUND_RULE_BY_FIELD.items())),
        REVIEWER_ID.pattern,
    )
    if current_config != canonical_config:
        raise Fail("generation independent-review semantic authority drift")


CANONICAL_EXECUTION_GUARD = enforce_execution_authority


def candidate_reviews_approved(
    row: dict[str, Any],
    canonical_execution_guard=CANONICAL_EXECUTION_GUARD,
) -> bool:
    if enforce_execution_authority is not canonical_execution_guard:
        raise Fail("generation independent-review execution guard drift")
    enforce_execution_authority()
    enforce_runtime_authorities()
    validate_contract_authority()
    try:
        load_review_source_order_validator().validate_row(row, -1)
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            raise Fail(f"review source-order authority invalid: {exc}") from exc
        raise
    try:
        material_delta_ok = load_material_delta_validator().material_delta_review_approved(row)
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            raise Fail(f"material-delta review authority invalid: {exc}") from exc
        raise
    require(material_delta_ok is True, "material-delta review authority did not approve candidate")
    security_ref, security_reviewer = validate_review(row, "securityReviewRef", ROLE_BY_REF["securityReviewRef"])
    operability_ref, operability_reviewer = validate_review(row, "operabilityReviewRef", ROLE_BY_REF["operabilityReviewRef"])
    require(security_ref != operability_ref, "Security and Operability review refs must remain distinct")
    require(security_reviewer != operability_reviewer, "Security and Operability reviewers must remain distinct")
    return True


CANONICAL_CANDIDATE_REVIEW = candidate_reviews_approved
CANONICAL_MAIN_EXECUTION_GUARD = enforce_execution_authority


def main(
    canonical_candidate_review=CANONICAL_CANDIDATE_REVIEW,
    canonical_execution_guard=CANONICAL_MAIN_EXECUTION_GUARD,
) -> int:
    if enforce_execution_authority is not canonical_execution_guard:
        raise Fail("generation independent-review main execution guard drift")
    if candidate_reviews_approved is not canonical_candidate_review:
        raise Fail("generation independent-review candidate authority drift")
    enforce_execution_authority()
    enforce_runtime_authorities()
    validate_contract_authority()
    try:
        material_delta_validator = load_material_delta_validator()
        material_delta_validator.enforce_execution_authority()
        material_delta_validator.enforce_runtime_authorities()
        material_delta_validator.validate_contract_authority()
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            raise Fail(f"material-delta review authority invalid: {exc}") from exc
        raise
    registry = load_json(REGISTRY, "generation evidence registry")
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    reviewed_records = 0
    for index, row in enumerate(rows):
        security_ref = row.get("securityReviewRef")
        operability_ref = row.get("operabilityReviewRef")
        if security_ref is None and operability_ref is None:
            continue
        require(
            isinstance(security_ref, str) and security_ref and isinstance(operability_ref, str) and operability_ref,
            f"records[{index}] must provide Security and Operability reviews together",
        )
        try:
            candidate_reviews_approved(row)
        except Fail as exc:
            raise Fail(f"records[{index}] independent review authority invalid: {exc}") from exc
        reviewed_records += 1
    candidate_count = registry.get("productionEquivalentRecoveryCandidateCount")
    require(
        isinstance(candidate_count, int) and not isinstance(candidate_count, bool) and 0 <= candidate_count <= reviewed_records,
        "productionEquivalentRecoveryCandidateCount cannot exceed independently reviewed records",
    )
    print(f"PASS: generation independent-review authority records={len(rows)} reviewedRecords={reviewed_records} productionEvidence=false productionReady=false")
    print("canonical generation evidence contract/registry authority substitution accepted: false")
    print("generation independent-review execution helper substitution accepted: false")
    print("generation independent-review execution transport substitution accepted: false")
    print("paired semantic authority substitution accepted: false")
    print("material-delta semantic authority validated even without reviewed records: true")
    print("unreviewed generation evidence may remain non-candidate: true")
    print("partial independent review pairs accepted: false")
    print("review source-order authority required before candidate admission: true")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
