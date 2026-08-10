#!/usr/bin/env python3
"""Fail closed around sustained-soak independent review and leak-proof promotion."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
LOCAL_CONTRACT = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
TREND_REVIEW = ROOT / "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    local = load(LOCAL_CONTRACT)
    review = load(TREND_REVIEW)

    require(contract.get("schemaVersion") == "memory-os-sustained-soak-independent-review.v1", "contract schema drift")
    require(contract.get("appendOnlyRegistry") is True, "independent review registry must remain append-only")
    criteria = contract.get("criteriaAuthority")
    require(isinstance(criteria, dict), "criteriaAuthority must be object")
    for key in (
        "humanApprovedCriteriaRequired",
        "automaticCriteriaGenerationForbidden",
        "automaticThresholdSelectionForbidden",
        "criteriaMustBindExactRunIds",
        "criteriaMustBindExactRunEvidenceDigests",
        "criteriaMustDeclareMetricAndUnit",
        "criteriaMustDeclareDirectionAndAcceptanceRule",
        "criteriaMustDeclareReviewScope",
        "criteriaMustPreexistIndependentReview",
    ):
        require(criteria.get(key) is True, f"criteria safeguard missing: {key}")

    authority = contract.get("reviewAuthority")
    require(isinstance(authority, dict), "reviewAuthority must be object")
    for key in (
        "independentReviewerRequired",
        "criteriaApproverAndReviewerMustBeDistinct",
        "reviewMustBindApprovedCriteriaRecord",
        "reviewMustBindExactRunIds",
        "reviewMustBindExactRunEvidenceDigests",
        "descriptiveTrendReviewIsNotIndependentReview",
        "passingReviewDoesNotCreateProductionEvidence",
        "passingReviewDoesNotAuthorizeProductionPromotion",
    ):
        require(authority.get(key) is True, f"review safeguard missing: {key}")
    require(authority.get("reviewOutcomeValues") == ["PASS", "FAIL"], "review outcomes must remain closed")

    promotion = contract.get("promotionBoundary")
    require(isinstance(promotion, dict), "promotionBoundary must be object")
    require(promotion.get("localSustainedSoakEvidenceMaySatisfyReviewInput") is True, "local evidence may only be review input")
    for key in (
        "localSustainedSoakEvidenceAloneCreatesLeakProof",
        "emptyRegistryCreatesLeakProof",
        "productionEvidence",
        "productionReady",
    ):
        require(promotion.get(key) is False, f"promotion boundary cannot enable {key}")
    for key in (
        "automaticLeakProofForbidden",
        "automaticCapacityBoundaryPromotionForbidden",
        "automaticOperationalThresholdPromotionForbidden",
        "automaticProductionSoakPromotionForbidden",
    ):
        require(promotion.get(key) is True, f"automatic promotion safeguard missing: {key}")

    require(registry.get("schemaVersion") == "memory-os-sustained-soak-independent-review-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False, "registry cannot claim production evidence")
    for field in (
        "registeredCriteriaCount",
        "registeredReviewCount",
        "approvedLeakStabilityCriteriaCount",
        "passingIndependentReviewCount",
    ):
        require(registry.get(field) == 0, f"{field} must remain zero until explicit human evidence admission is implemented")
    require(registry.get("criteria") == [], "criteria registry must remain empty")
    require(registry.get("reviews") == [], "review registry must remain empty")
    for field in (
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "productionSustainedSoakEvidence",
        "productionReady",
    ):
        require(registry.get(field) is False, f"empty registry cannot enable {field}")

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
    print("approved leak/stability criteria: 0")
    print("independent reviews: 0")
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
