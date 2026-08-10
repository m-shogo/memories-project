#!/usr/bin/env python3
"""Negative mutation suite for sustained-soak independent review promotion authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def malformed_criteria(registry: dict[str, Any], *, schema: str, run_bindings: list[dict[str, Any]]) -> None:
    registry["criteria"] = [
        {
            "schemaVersion": schema,
            "criteriaId": "soakcrit_negative01",
            "reviewScope": "LOCAL_LONG_SOAK_LEAK_STABILITY",
            "runBindings": run_bindings,
            "criteria": [
                {
                    "metric": "rssSlopeBytesPerMinute",
                    "unit": "bytes/minute",
                    "direction": "upper-bound",
                    "acceptanceRule": "human supplied negative fixture only"
                }
            ],
            "approvedAt": "2026-08-10T00:00:00Z",
            "approverPseudonym": "review-owner-a",
            "approvalEvidenceRef": "docs/evidence/sustained-soak/criteria-approvals/negative.json",
            "supersedesCriteriaId": None,
            "productionEvidence": False,
            "productionReady": False
        }
    ]
    registry["registeredCriteriaCount"] = 1
    registry["approvedLeakStabilityCriteriaCount"] = 1


def malformed_review(registry: dict[str, Any]) -> None:
    registry["reviews"] = [
        {
            "schemaVersion": "memory-os-sustained-soak-independent-review-record.v1",
            "reviewId": "soakrev_negative01",
            "criteriaId": "soakcrit_missing01",
            "runBindings": [],
            "reviewedAt": "2026-08-10T00:01:00Z",
            "reviewerPseudonym": "reviewer-b",
            "outcome": "PASS",
            "findings": [],
            "reviewEvidenceRef": "docs/evidence/sustained-soak/independent-reviews/negative.json",
            "productionEvidence": False,
            "productionReady": False
        }
    ]
    registry["registeredReviewCount"] = 1
    registry["passingIndependentReviewCount"] = 1


def main() -> int:
    spec = importlib.util.spec_from_file_location("soak_review_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import independent review validator")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    canonical_contract = load(ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json")
    canonical_registry = load(ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json")
    canonical_local = load(ROOT / "contracts/operations/sustained-local-soak-contract.v1.json")
    canonical_review = load(ROOT / "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json")

    cases: list[tuple[str, Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], None]]] = [
        ("registry criteria count manufactured", lambda c, r, l, v: r.__setitem__("registeredCriteriaCount", 1)),
        ("registry review count manufactured", lambda c, r, l, v: r.__setitem__("registeredReviewCount", 1)),
        ("registry approved criteria count manufactured", lambda c, r, l, v: r.__setitem__("approvedLeakStabilityCriteriaCount", 1)),
        ("registry leakProof manufactured", lambda c, r, l, v: r.__setitem__("leakProof", True)),
        ("registry independent review count manufactured", lambda c, r, l, v: r.__setitem__("passingIndependentReviewCount", 1)),
        ("registry capacity boundary manufactured", lambda c, r, l, v: r.__setitem__("capacityBoundaryEstablished", True)),
        ("registry threshold approval manufactured", lambda c, r, l, v: r.__setitem__("operationalThresholdApproved", True)),
        ("registry production soak evidence manufactured", lambda c, r, l, v: r.__setitem__("productionSustainedSoakEvidence", True)),
        ("registry production readiness manufactured", lambda c, r, l, v: r.__setitem__("productionReady", True)),
        ("local independent review manufactured", lambda c, r, l, v: l["readiness"].__setitem__("independentReviewCompleted", True)),
        ("descriptive review leakProof manufactured", lambda c, r, l, v: v.__setitem__("leakProof", True)),
        ("descriptive review production evidence manufactured", lambda c, r, l, v: v.__setitem__("productionEvidence", True)),
        ("automatic threshold selection enabled", lambda c, r, l, v: c["criteriaAuthority"].__setitem__("automaticThresholdSelectionForbidden", False)),
        ("criteria may be generated automatically", lambda c, r, l, v: c["criteriaAuthority"].__setitem__("automaticCriteriaGenerationForbidden", False)),
        ("reviewer independence disabled", lambda c, r, l, v: c["reviewAuthority"].__setitem__("independentReviewerRequired", False)),
        ("criteria approver reviewer separation disabled", lambda c, r, l, v: c["reviewAuthority"].__setitem__("criteriaApproverAndReviewerMustBeDistinct", False)),
        ("passing review promotes production", lambda c, r, l, v: c["reviewAuthority"].__setitem__("passingReviewDoesNotAuthorizeProductionPromotion", False)),
        ("dedicated human evidence directory disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("humanEvidenceMustUseDedicatedDirectory", False)),
        ("run digest binding disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("runEvidenceDigestMustMatchBytes", False)),
        ("exact criteria/review run binding disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewRunBindingsMustExactlyMatchCriteria", False)),
        ("criteria/reviewer separation record gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewerMustDifferFromCriteriaApprover", False)),
        ("review chronology gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewCannotPredateCriteriaApproval", False)),
        (
            "typed criteria row wrong schema",
            lambda c, r, l, v: malformed_criteria(r, schema="memory-os-sustained-soak-leak-stability-criteria.v0", run_bindings=[]),
        ),
        (
            "typed criteria row without minimum canonical runs",
            lambda c, r, l, v: malformed_criteria(r, schema="memory-os-sustained-soak-leak-stability-criteria.v1", run_bindings=[]),
        ),
        ("typed review references missing criteria", lambda c, r, l, v: malformed_review(r)),
    ]

    with tempfile.TemporaryDirectory(prefix="soak-review-negative-", dir=ROOT) as tmp:
        base = Path(tmp)
        for name, mutate in cases:
            contract = copy.deepcopy(canonical_contract)
            registry = copy.deepcopy(canonical_registry)
            local = copy.deepcopy(canonical_local)
            review = copy.deepcopy(canonical_review)
            mutate(contract, registry, local, review)

            contract_path = base / "contract.json"
            registry_path = base / "registry.json"
            local_path = base / "local.json"
            review_path = base / "review.json"
            write(contract_path, contract)
            write(registry_path, registry)
            write(local_path, local)
            write(review_path, review)

            validator.CONTRACT = contract_path
            validator.REGISTRY = registry_path
            validator.LOCAL_CONTRACT = local_path
            validator.TREND_REVIEW = review_path
            try:
                validator.main()
            except validator.Fail:
                print(f"PASS reject: {name}")
            else:
                raise RuntimeError(f"mutation unexpectedly accepted: {name}")

    print("Memory OS sustained-soak independent review negative suite PASS")
    print("automatic leak proof accepted: false")
    print("automatic independent review accepted: false")
    print("automatic threshold approval accepted: false")
    print("typed criteria without canonical run binding accepted: false")
    print("typed review without approved criteria binding accepted: false")
    print("human evidence directory/digest/reviewer separation gates weaken silently: false")
    print("automatic production soak evidence accepted: false")
    print("automatic production readiness accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
