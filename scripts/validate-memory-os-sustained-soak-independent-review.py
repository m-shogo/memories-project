#!/usr/bin/env python3
"""Fail closed around sustained-soak independent review and leak-proof promotion."""

from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
LOCAL_CONTRACT = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
TREND_REVIEW = ROOT / "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
LOCK_PATH = ROOT / "contracts/operations/.sustained-soak-independent-review.lock"
CANONICAL_LOCK_REF = "contracts/operations/.sustained-soak-independent-review.lock"
CRITERIA_ID = re.compile(r"^soakcrit_[a-z0-9][a-z0-9_-]{7,63}$")
REVIEW_ID = re.compile(r"^soakrev_[a-z0-9][a-z0-9_-]{7,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PSEUDONYM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
EXPECTED_REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "registeredCriteriaCount",
    "registeredReviewCount",
    "approvedLeakStabilityCriteriaCount",
    "passingIndependentReviewCount",
    "leakProof",
    "capacityBoundaryEstablished",
    "operationalThresholdApproved",
    "productionSustainedSoakEvidence",
    "productionReady",
    "criteria",
    "reviews",
    "limitations",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_count(value: Any, expected: int, field: str) -> None:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer, not boolean")
    require(value == expected, f"{field} drift")


def validate_registry_aggregates(registry: dict[str, Any]) -> None:
    require(set(registry) == EXPECTED_REGISTRY_FIELDS, "registry field drift")
    require(registry.get("schemaVersion") == "memory-os-sustained-soak-independent-review-registry.v1", "registry schema drift")
    require(registry.get("registryClass") == "SUSTAINED_SOAK_INDEPENDENT_REVIEW", "registry class drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False, "registry cannot claim production evidence")

    criteria_rows = registry.get("criteria")
    review_rows = registry.get("reviews")
    limitations = registry.get("limitations")
    require(isinstance(criteria_rows, list), "criteria registry must be list")
    require(isinstance(review_rows, list), "review registry must be list")
    require(isinstance(limitations, list) and all(isinstance(item, str) and item for item in limitations), "registry limitations invalid")

    current_criteria_id: str | None = None
    if criteria_rows:
        current = criteria_rows[-1]
        require(isinstance(current, dict), "current criteria row must be object")
        current_criteria_id = current.get("criteriaId")
        require(isinstance(current_criteria_id, str) and current_criteria_id, "current criteria row requires criteriaId")
    passing_reviews = sum(
        1
        for review in review_rows
        if isinstance(review, dict)
        and review.get("outcome") == "PASS"
        and review.get("criteriaId") == current_criteria_id
    )

    require_count(registry.get("registeredCriteriaCount"), len(criteria_rows), "registeredCriteriaCount")
    require_count(registry.get("approvedLeakStabilityCriteriaCount"), len(criteria_rows), "approvedLeakStabilityCriteriaCount")
    require_count(registry.get("registeredReviewCount"), len(review_rows), "registeredReviewCount")
    require_count(registry.get("passingIndependentReviewCount"), passing_reviews, "passingIndependentReviewCount")
    for field in ("leakProof", "capacityBoundaryEstablished", "operationalThresholdApproved", "productionSustainedSoakEvidence", "productionReady"):
        require(registry.get(field) is False, f"independent review registry cannot automatically enable {field}")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise Fail(f"missing file: {label}") from exc
    except json.JSONDecodeError as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise Fail(f"invalid JSON: {label}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def canonical_record_sha256(record: dict[str, Any]) -> str:
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} must be UTC RFC3339") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field} must be UTC")
    return parsed


def bounded_text(value: Any, field: str, maximum: int = 500) -> str:
    require(isinstance(value, str), f"{field} must be string")
    normalized = " ".join(value.strip().split())
    require(1 <= len(normalized) <= maximum, f"{field} invalid length")
    lowered = normalized.casefold()
    for forbidden in ("http://", "https://", "password", "private_key", "access_key", "authorization: bearer", "@"):
        require(forbidden not in lowered, f"{field} contains forbidden material: {forbidden}")
    return normalized


def git_head_blob(relative: Path, field: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(result.returncode == 0, f"{field} must be tracked at HEAD")
    return result.stdout


def dedicated_ref(value: Any, directory: str, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{field} unsafe")
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"{field} must be symlink-free")
    full = (ROOT / relative).resolve()
    base = (ROOT / directory).resolve()
    require(full.is_relative_to(base), f"{field} must use dedicated authority directory")
    require(full.is_file(), f"{field} missing: {value}")
    require(full.read_bytes() == git_head_blob(relative, field), f"{field} must match tracked HEAD bytes")
    return value, full


def load_result_validator() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_sustained_soak_result_validator", RESULT_VALIDATOR)
    require(spec is not None and spec.loader is not None, "unable to import LOCAL_LONG_SOAK result validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_run_bindings(value: Any, record_authority: dict[str, Any], result_validator: Any, field: str) -> list[dict[str, str]]:
    minimum = record_authority.get("minimumBoundRuns")
    require(isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= 2, "minimumBoundRuns invalid")
    require(isinstance(value, list) and len(value) >= minimum, f"{field} must bind at least {minimum} runs")
    required_fields = set(record_authority.get("runBindingRequiredFields", []))
    require(required_fields == {"runId", "evidenceRef", "sha256"}, "run binding field authority drift")
    canonical_dir = record_authority.get("canonicalRunEvidenceDirectory")
    canonical_glob = record_authority.get("canonicalRunEvidenceGlob")
    require(isinstance(canonical_dir, str) and canonical_dir, "canonicalRunEvidenceDirectory invalid")
    require(isinstance(canonical_glob, str) and canonical_glob, "canonicalRunEvidenceGlob invalid")
    normalized: list[dict[str, str]] = []
    run_ids: set[str] = set()
    refs: set[str] = set()
    for index, binding in enumerate(value):
        require(isinstance(binding, dict) and set(binding) == required_fields, f"{field}[{index}] field drift")
        run_id = binding.get("runId")
        evidence_ref = binding.get("evidenceRef")
        digest = binding.get("sha256")
        require(isinstance(run_id, str) and run_id and len(run_id) <= 160, f"{field}[{index}].runId invalid")
        require(run_id not in run_ids, f"{field} contains duplicate runId")
        require(isinstance(evidence_ref, str) and evidence_ref, f"{field}[{index}].evidenceRef invalid")
        _, full = dedicated_ref(evidence_ref, canonical_dir, f"{field}[{index}].evidenceRef")
        require(fnmatch.fnmatch(full.name, canonical_glob), f"{field}[{index}] must reference canonical LOCAL_LONG_SOAK run file")
        require(evidence_ref not in refs, f"{field} contains duplicate evidenceRef")
        require(isinstance(digest, str) and SHA256.fullmatch(digest) is not None, f"{field}[{index}].sha256 invalid")
        actual_digest = hashlib.sha256(full.read_bytes()).hexdigest()
        require(digest == actual_digest, f"{field}[{index}] evidence digest mismatch")
        try:
            validated_run_id, _ = result_validator.validate_result(full)
        except result_validator.Fail as exc:
            raise Fail(f"{field}[{index}] per-run validation failed: {exc}") from exc
        require(validated_run_id == run_id, f"{field}[{index}] runId/evidence mismatch")
        run_ids.add(run_id)
        refs.add(evidence_ref)
        normalized.append({"runId": run_id, "evidenceRef": evidence_ref, "sha256": digest})
    return normalized


def validate_human_evidence(ref: Any, directory: str, required_fields: set[str], schema_version: str, bindings: dict[str, Any], field: str) -> None:
    _, path = dedicated_ref(ref, directory, field)
    document = load(path)
    require(set(document) == required_fields, f"{field} field drift")
    require(document.get("schemaVersion") == schema_version, f"{field} schema drift")
    for key, expected in bindings.items():
        require(document.get(key) == expected, f"{field} {key} binding mismatch")
    for key in ("productionTraffic", "productionCredentials", "automaticPromotion"):
        require(document.get(key) is False, f"{field} {key} must remain false")


def validate_criteria_record(record: Any, index: int, contract: dict[str, Any], record_authority: dict[str, Any], result_validator: Any, previous_id: str | None) -> tuple[str, str, dt.datetime, list[dict[str, str]]]:
    required = set(record_authority.get("criteriaRequiredFields", []))
    require(isinstance(record, dict) and set(record) == required, f"criteria[{index}] field drift")
    require(record.get("schemaVersion") == contract.get("criteriaRecordSchemaVersion"), f"criteria[{index}] schema drift")
    criteria_id = record.get("criteriaId")
    require(isinstance(criteria_id, str) and CRITERIA_ID.fullmatch(criteria_id) is not None, f"criteria[{index}].criteriaId invalid")
    require(record.get("supersedesCriteriaId") == previous_id, f"criteria[{index}] must supersede current criteria authority")
    require(record.get("reviewScope") == record_authority.get("criteriaReviewScope"), f"criteria[{index}].reviewScope invalid")
    approver = record.get("approverPseudonym")
    require(isinstance(approver, str) and PSEUDONYM.fullmatch(approver) is not None, f"criteria[{index}].approverPseudonym invalid")
    approved_at = parse_utc(record.get("approvedAt"), f"criteria[{index}].approvedAt")
    run_bindings = validate_run_bindings(record.get("runBindings"), record_authority, result_validator, f"criteria[{index}].runBindings")
    criterion_fields = set(record_authority.get("criterionRequiredFields", []))
    criteria = record.get("criteria")
    require(isinstance(criteria, list) and criteria, f"criteria[{index}].criteria must be non-empty")
    seen_metrics: set[str] = set()
    for criterion_index, criterion in enumerate(criteria):
        require(isinstance(criterion, dict) and set(criterion) == criterion_fields, f"criteria[{index}].criteria[{criterion_index}] field drift")
        metric = bounded_text(criterion.get("metric"), f"criteria[{index}].criteria[{criterion_index}].metric", 120)
        require(metric not in seen_metrics, f"criteria[{index}] duplicate metric")
        seen_metrics.add(metric)
        bounded_text(criterion.get("unit"), f"criteria[{index}].criteria[{criterion_index}].unit", 80)
        bounded_text(criterion.get("direction"), f"criteria[{index}].criteria[{criterion_index}].direction", 120)
        bounded_text(criterion.get("acceptanceRule"), f"criteria[{index}].criteria[{criterion_index}].acceptanceRule", 500)
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, f"criteria[{index}] cannot promote production")
    approval_fields = set(record_authority.get("criteriaApprovalEvidenceRequiredFields", []))
    validate_human_evidence(
        record.get("approvalEvidenceRef"),
        record_authority.get("criteriaApprovalEvidenceDirectory"),
        approval_fields,
        record_authority.get("criteriaApprovalEvidenceSchemaVersion"),
        {
            "criteriaId": criteria_id,
            "criteriaRecordSha256": canonical_record_sha256(record),
            "decision": "APPROVED",
            "approvedAt": record.get("approvedAt"),
            "approverPseudonym": approver,
        },
        f"criteria[{index}].approvalEvidenceRef",
    )
    return criteria_id, approver, approved_at, run_bindings


def validate_review_record(record: Any, index: int, contract: dict[str, Any], record_authority: dict[str, Any], result_validator: Any, criteria_records: dict[str, tuple[str, dt.datetime, list[dict[str, str]]]]) -> tuple[str, str]:
    required = set(record_authority.get("reviewRequiredFields", []))
    require(isinstance(record, dict) and set(record) == required, f"reviews[{index}] field drift")
    require(record.get("schemaVersion") == contract.get("reviewRecordSchemaVersion"), f"reviews[{index}] schema drift")
    review_id = record.get("reviewId")
    require(isinstance(review_id, str) and REVIEW_ID.fullmatch(review_id) is not None, f"reviews[{index}].reviewId invalid")
    criteria_id = record.get("criteriaId")
    require(isinstance(criteria_id, str) and criteria_id in criteria_records, f"reviews[{index}].criteriaId must reference approved criteria")
    criteria_approver, approved_at, expected_bindings = criteria_records[criteria_id]
    reviewer = record.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and PSEUDONYM.fullmatch(reviewer) is not None, f"reviews[{index}].reviewerPseudonym invalid")
    require(reviewer != criteria_approver, f"reviews[{index}] reviewer must differ from criteria approver")
    reviewed_at = parse_utc(record.get("reviewedAt"), f"reviews[{index}].reviewedAt")
    require(reviewed_at >= approved_at, f"reviews[{index}] cannot predate criteria approval")
    actual_bindings = validate_run_bindings(record.get("runBindings"), record_authority, result_validator, f"reviews[{index}].runBindings")
    require(actual_bindings == expected_bindings, f"reviews[{index}] run bindings must exactly match criteria")
    outcomes = contract.get("reviewAuthority", {}).get("reviewOutcomeValues")
    outcome = record.get("outcome")
    require(isinstance(outcomes, list) and outcome in outcomes, f"reviews[{index}].outcome invalid")
    findings = record.get("findings")
    require(isinstance(findings, list), f"reviews[{index}].findings must be list")
    for finding_index, finding in enumerate(findings):
        bounded_text(finding, f"reviews[{index}].findings[{finding_index}]", 1000)
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, f"reviews[{index}] cannot promote production")
    review_fields = set(record_authority.get("independentReviewEvidenceRequiredFields", []))
    validate_human_evidence(
        record.get("reviewEvidenceRef"),
        record_authority.get("independentReviewEvidenceDirectory"),
        review_fields,
        record_authority.get("independentReviewEvidenceSchemaVersion"),
        {
            "reviewId": review_id,
            "criteriaId": criteria_id,
            "reviewRecordSha256": canonical_record_sha256(record),
            "outcome": outcome,
            "reviewedAt": record.get("reviewedAt"),
            "reviewerPseudonym": reviewer,
        },
        f"reviews[{index}].reviewEvidenceRef",
    )
    return review_id, outcome


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    local = load(LOCAL_CONTRACT)
    review = load(TREND_REVIEW)

    require(contract.get("schemaVersion") == "memory-os-sustained-soak-independent-review.v1", "contract schema drift")
    require(contract.get("appendOnlyRegistry") is True, "independent review registry must remain append-only")
    require(contract.get("appendLockPath") == CANONICAL_LOCK_REF, "independent review append lock contract authority drift")
    require((ROOT / CANONICAL_LOCK_REF).resolve() == LOCK_PATH.resolve(), "independent review append lock path drift")
    criteria = contract.get("criteriaAuthority")
    require(isinstance(criteria, dict), "criteriaAuthority must be object")
    for key in (
        "humanApprovedCriteriaRequired", "automaticCriteriaGenerationForbidden", "automaticThresholdSelectionForbidden",
        "criteriaMustBindExactRunIds", "criteriaMustBindExactRunEvidenceDigests", "criteriaMustDeclareMetricAndUnit",
        "criteriaMustDeclareDirectionAndAcceptanceRule", "criteriaMustDeclareReviewScope", "criteriaMustPreexistIndependentReview",
        "supersededCriteriaCannotRemainCurrentReviewAuthority", "approvalEvidenceMustBindCriteriaRecordDigest",
    ):
        require(criteria.get(key) is True, f"criteria safeguard missing: {key}")

    authority = contract.get("reviewAuthority")
    require(isinstance(authority, dict), "reviewAuthority must be object")
    for key in (
        "independentReviewerRequired", "criteriaApproverAndReviewerMustBeDistinct", "reviewMustBindApprovedCriteriaRecord",
        "reviewMustBindExactRunIds", "reviewMustBindExactRunEvidenceDigests", "atMostOneIndependentReviewPerCriteria",
        "onlyCurrentCriteriaPassCountsAsPassingIndependentReview", "descriptiveTrendReviewIsNotIndependentReview",
        "passingReviewDoesNotCreateProductionEvidence", "passingReviewDoesNotAuthorizeProductionPromotion",
        "independentReviewEvidenceMustBindReviewRecordDigest",
    ):
        require(authority.get(key) is True, f"review safeguard missing: {key}")
    require(authority.get("reviewOutcomeValues") == ["PASS", "FAIL"], "review outcomes must remain closed")

    record_authority = contract.get("recordAuthority")
    require(isinstance(record_authority, dict), "recordAuthority must be object")
    for key in (
        "humanEvidenceMustUseDedicatedDirectory", "humanEvidenceMustBeTrackedAtHead", "humanEvidenceMustMatchHeadBlob",
        "humanEvidenceMustBeSymlinkFree", "runEvidenceMustBeCanonicalAndPerRunValidated", "runEvidenceMustBeTrackedAtHead",
        "runEvidenceMustMatchHeadBlob", "runEvidenceMustBeSymlinkFree", "runEvidenceDigestMustMatchBytes",
        "reviewRunBindingsMustExactlyMatchCriteria", "reviewerMustDifferFromCriteriaApprover", "reviewCannotPredateCriteriaApproval",
        "criteriaApprovalMustBindCanonicalRecordDigest", "independentReviewMustBindCanonicalRecordDigest",
        "productionEvidenceForbidden", "productionReadyForbidden",
    ):
        require(record_authority.get(key) is True, f"record safeguard missing: {key}")
    require(record_authority.get("criteriaApprovalEvidenceSchemaVersion") == "memory-os-sustained-soak-criteria-approval.v2", "criteria approval evidence schema must remain digest-bound v2")
    require(record_authority.get("independentReviewEvidenceSchemaVersion") == "memory-os-sustained-soak-independent-review-evidence.v2", "independent review evidence schema must remain digest-bound v2")
    require("criteriaRecordSha256" in set(record_authority.get("criteriaApprovalEvidenceRequiredFields", [])), "criteria approval evidence digest field missing")
    require("reviewRecordSha256" in set(record_authority.get("independentReviewEvidenceRequiredFields", [])), "independent review evidence digest field missing")

    promotion = contract.get("promotionBoundary")
    require(isinstance(promotion, dict), "promotionBoundary must be object")
    require(promotion.get("localSustainedSoakEvidenceMaySatisfyReviewInput") is True, "local evidence may only be review input")
    for key in ("localSustainedSoakEvidenceAloneCreatesLeakProof", "emptyRegistryCreatesLeakProof", "productionEvidence", "productionReady"):
        require(promotion.get(key) is False, f"promotion boundary cannot enable {key}")
    for key in ("automaticLeakProofForbidden", "automaticCapacityBoundaryPromotionForbidden", "automaticOperationalThresholdPromotionForbidden", "automaticProductionSoakPromotionForbidden"):
        require(promotion.get(key) is True, f"automatic promotion safeguard missing: {key}")

    validate_registry_aggregates(registry)
    criteria_rows = registry.get("criteria")
    review_rows = registry.get("reviews")
    require(isinstance(criteria_rows, list), "criteria registry must be list")
    require(isinstance(review_rows, list), "review registry must be list")

    result_validator = load_result_validator()
    criteria_records: dict[str, tuple[str, dt.datetime, list[dict[str, str]]]] = {}
    previous_id: str | None = None
    for index, row in enumerate(criteria_rows):
        criteria_id, approver, approved_at, run_bindings = validate_criteria_record(row, index, contract, record_authority, result_validator, previous_id)
        require(criteria_id not in criteria_records, "duplicate criteriaId")
        criteria_records[criteria_id] = (approver, approved_at, run_bindings)
        previous_id = criteria_id
    current_criteria_id = previous_id

    review_ids: set[str] = set()
    reviewed_criteria_ids: set[str] = set()
    passing_reviews = 0
    for index, row in enumerate(review_rows):
        review_id, outcome = validate_review_record(row, index, contract, record_authority, result_validator, criteria_records)
        require(review_id not in review_ids, "duplicate reviewId")
        review_ids.add(review_id)
        criteria_id = row.get("criteriaId")
        require(criteria_id not in reviewed_criteria_ids, "at most one independent review may be registered per criteria record")
        reviewed_criteria_ids.add(criteria_id)
        if outcome == "PASS" and criteria_id == current_criteria_id:
            passing_reviews += 1

    require(passing_reviews in (0, 1), "current criteria can have at most one passing independent review")
    require_count(registry.get("registeredCriteriaCount"), len(criteria_rows), "registeredCriteriaCount")
    require_count(registry.get("approvedLeakStabilityCriteriaCount"), len(criteria_rows), "approvedLeakStabilityCriteriaCount")
    require_count(registry.get("registeredReviewCount"), len(review_rows), "registeredReviewCount")
    require_count(registry.get("passingIndependentReviewCount"), passing_reviews, "passingIndependentReviewCount")

    local_boundary = local.get("evidenceBoundary")
    local_readiness = local.get("readiness")
    require(isinstance(local_boundary, dict) and isinstance(local_readiness, dict), "local soak authority shape drift")
    for field in ("leakProof", "capacityBoundaryEstablished", "operationalThresholdApproved", "independentReviewCompleted", "productionReady"):
        require(local_boundary.get(field) is False, f"local soak evidence cannot enable {field}")
    for field in ("leakProofAvailable", "capacityBoundaryEstablished", "operationalThresholdApproved", "independentReviewCompleted", "productionReady"):
        require(local_readiness.get(field) is False, f"local soak readiness cannot enable {field}")

    require(review.get("leakProof") is False, "descriptive trend review cannot become leak proof")
    require(review.get("productionEvidence") is False, "descriptive trend review cannot become production evidence")
    require(review.get("productionReady") is False, "descriptive trend review cannot become production ready")

    print("Memory OS sustained-soak independent review authority PASS")
    print(f"approved leak/stability criteria: {len(criteria_rows)}")
    print(f"independent reviews: {len(review_rows)}")
    print(f"current passing independent reviews: {passing_reviews}")
    print("superseded criteria review remains current authority: false")
    print("typed human criteria/review records accepted without dedicated evidence: false")
    print("untracked or modified human evidence accepted: false")
    print("symlinked human evidence accepted: false")
    print("untracked or modified run evidence accepted: false")
    print("symlinked run evidence accepted: false")
    print("human approval evidence without exact record digest binding accepted: false")
    print("review run-binding drift accepted: false")
    print("descriptive trend review implies independent review: false")
    print("leak proof: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED SOAK INDEPENDENT REVIEW AUTHORITY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)