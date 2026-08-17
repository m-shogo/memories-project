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
REGISTER_PATH = ROOT / "scripts/register-memory-os-sustained-soak-independent-review.py"
RECONCILE_PATH = ROOT / "scripts/reconcile-memory-os-sustained-local-soak-status.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
RECONCILE_OUTPUTS = (
    ROOT / "contracts/operations/sustained-local-soak-contract.v1.json",
    ROOT / "contracts/operations/load-test-scenario-contract.v1.json",
    ROOT / "contracts/operations/production-operability-status.json",
)


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_current_criteria_counting(register) -> None:
    registry = {
        "criteria": [
            {"criteriaId": "soakcrit_history01"},
            {"criteriaId": "soakcrit_current01"},
        ],
        "reviews": [
            {"criteriaId": "soakcrit_history01", "outcome": "PASS"},
        ],
    }
    register.recompute_counts(registry)
    if registry.get("passingIndependentReviewCount") != 0:
        raise RuntimeError("superseded PASS review remained current authority")
    registry["reviews"].append(
        {"criteriaId": "soakcrit_current01", "outcome": "PASS"}
    )
    register.recompute_counts(registry)
    if registry.get("passingIndependentReviewCount") != 1:
        raise RuntimeError("current criteria PASS review was not counted")
    if registry.get("leakProof") is not False or registry.get("productionEvidence") is not False:
        raise RuntimeError("review count recompute manufactured promotion")
    print("PASS current-criteria review count: historical PASS excluded; current PASS counted")


def prove_append_lock_authority(register) -> None:
    """Canonical writer must reject contract lock substitution before taking any lock."""
    original = CANONICAL_CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["appendLockPath"] = "contracts/operations/.sustained-soak-independent-review.alternate.lock"
    write(CANONICAL_CONTRACT, contract)
    corrupted = CANONICAL_CONTRACT.read_bytes()
    try:
        try:
            register.validate_lock_authority()
        except register.Fail:
            print("PASS append-lock reject: contract lock substitution")
        else:
            raise RuntimeError("sustained-soak writer accepted alternate append lock authority")
        if CANONICAL_CONTRACT.read_bytes() != corrupted:
            raise RuntimeError("append-lock guard mutated rejected contract authority")
    finally:
        CANONICAL_CONTRACT.write_bytes(original)


def prove_preappend_registry_guard(register) -> None:
    """Corrupt canonical aggregate authority must be rejected without mutation."""
    original = CANONICAL_REGISTRY.read_bytes()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("registry class drift", lambda r: r.__setitem__("registryClass", "BROKEN")),
        ("unknown registry field", lambda r: r.__setitem__("unexpectedAuthority", True)),
        ("boolean criteria count", lambda r: r.__setitem__("registeredCriteriaCount", False)),
        ("boolean review count", lambda r: r.__setitem__("registeredReviewCount", False)),
        ("criteria count drift", lambda r: r.__setitem__("registeredCriteriaCount", 1)),
        ("review count drift", lambda r: r.__setitem__("registeredReviewCount", 1)),
        ("production readiness promotion", lambda r: r.__setitem__("productionReady", True)),
        ("production evidence promotion", lambda r: r.__setitem__("productionEvidence", True)),
    ]
    try:
        for name, mutate in cases:
            registry = json.loads(original.decode("utf-8"))
            mutate(registry)
            write(CANONICAL_REGISTRY, registry)
            corrupted = CANONICAL_REGISTRY.read_bytes()
            try:
                register.validate_existing_registry()
            except register.Fail:
                print(f"PASS pre-append reject: {name}")
            else:
                raise RuntimeError(f"pre-append registry guard unexpectedly accepted: {name}")
            if CANONICAL_REGISTRY.read_bytes() != corrupted:
                raise RuntimeError(f"pre-append registry guard mutated rejected authority: {name}")
            CANONICAL_REGISTRY.write_bytes(original)
    finally:
        CANONICAL_REGISTRY.write_bytes(original)


def prove_reconcile_rejects_corrupt_registry(reconciler) -> None:
    """Status reconcile must stop before writing when review authority is corrupt."""
    original_registry = CANONICAL_REGISTRY.read_bytes()
    original_outputs = {path: path.read_bytes() for path in RECONCILE_OUTPUTS}
    registry = json.loads(original_registry.decode("utf-8"))
    registry["registeredCriteriaCount"] = False
    write(CANONICAL_REGISTRY, registry)
    corrupted_registry = CANONICAL_REGISTRY.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError("status reconcile accepted corrupt sustained-soak review authority")
        if CANONICAL_REGISTRY.read_bytes() != corrupted_registry:
            raise RuntimeError("status reconcile mutated corrupt review authority")
        for path, original in original_outputs.items():
            if path.read_bytes() != original:
                raise RuntimeError(f"status reconcile wrote before rejecting corrupt review authority: {path.relative_to(ROOT)}")
        print("PASS reconcile reject: corrupt review authority leaves derived contracts/status unchanged")
    finally:
        CANONICAL_REGISTRY.write_bytes(original_registry)
        for path, original in original_outputs.items():
            path.write_bytes(original)


def main() -> int:
    validator = load_module(VALIDATOR_PATH, "soak_review_validator")
    register = load_module(REGISTER_PATH, "soak_review_register")
    reconciler = load_module(RECONCILE_PATH, "soak_review_reconciler")
    prove_current_criteria_counting(register)
    prove_append_lock_authority(register)
    prove_preappend_registry_guard(register)
    prove_reconcile_rejects_corrupt_registry(reconciler)

    canonical_contract = load(CANONICAL_CONTRACT)
    canonical_registry = load(CANONICAL_REGISTRY)
    canonical_local = load(ROOT / "contracts/operations/sustained-local-soak-contract.v1.json")
    canonical_review = load(ROOT / "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json")

    cases: list[tuple[str, Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], None]]] = [
        ("append lock authority substituted", lambda c, r, l, v: c.__setitem__("appendLockPath", "contracts/operations/.sustained-soak-independent-review.alternate.lock")),
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
        ("superseded criteria may remain current authority", lambda c, r, l, v: c["criteriaAuthority"].__setitem__("supersededCriteriaCannotRemainCurrentReviewAuthority", False)),
        ("criteria approval record digest binding disabled", lambda c, r, l, v: c["criteriaAuthority"].__setitem__("approvalEvidenceMustBindCriteriaRecordDigest", False)),
        ("reviewer independence disabled", lambda c, r, l, v: c["reviewAuthority"].__setitem__("independentReviewerRequired", False)),
        ("criteria approver reviewer separation disabled", lambda c, r, l, v: c["reviewAuthority"].__setitem__("criteriaApproverAndReviewerMustBeDistinct", False)),
        ("historical PASS may count as current review", lambda c, r, l, v: c["reviewAuthority"].__setitem__("onlyCurrentCriteriaPassCountsAsPassingIndependentReview", False)),
        ("passing review promotes production", lambda c, r, l, v: c["reviewAuthority"].__setitem__("passingReviewDoesNotAuthorizeProductionPromotion", False)),
        ("independent review record digest binding disabled", lambda c, r, l, v: c["reviewAuthority"].__setitem__("independentReviewEvidenceMustBindReviewRecordDigest", False)),
        ("dedicated human evidence directory disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("humanEvidenceMustUseDedicatedDirectory", False)),
        ("run digest binding disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("runEvidenceDigestMustMatchBytes", False)),
        ("exact criteria/review run binding disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewRunBindingsMustExactlyMatchCriteria", False)),
        ("criteria/reviewer separation record gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewerMustDifferFromCriteriaApprover", False)),
        ("review chronology gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("reviewCannotPredateCriteriaApproval", False)),
        ("criteria approval canonical digest gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("criteriaApprovalMustBindCanonicalRecordDigest", False)),
        ("independent review canonical digest gate disabled", lambda c, r, l, v: c["recordAuthority"].__setitem__("independentReviewMustBindCanonicalRecordDigest", False)),
        ("criteria approval evidence schema downgraded", lambda c, r, l, v: c["recordAuthority"].__setitem__("criteriaApprovalEvidenceSchemaVersion", "memory-os-sustained-soak-criteria-approval.v1")),
        ("independent review evidence schema downgraded", lambda c, r, l, v: c["recordAuthority"].__setitem__("independentReviewEvidenceSchemaVersion", "memory-os-sustained-soak-independent-review-evidence.v1")),
        ("criteria approval digest field removed", lambda c, r, l, v: c["recordAuthority"].__setitem__("criteriaApprovalEvidenceRequiredFields", [field for field in c["recordAuthority"]["criteriaApprovalEvidenceRequiredFields"] if field != "criteriaRecordSha256"])),
        ("independent review digest field removed", lambda c, r, l, v: c["recordAuthority"].__setitem__("independentReviewEvidenceRequiredFields", [field for field in c["recordAuthority"]["independentReviewEvidenceRequiredFields"] if field != "reviewRecordSha256"])),
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
    print("historical PASS review counted as current authority: false")
    print("alternate append lock authority accepted: false")
    print("standalone validator alternate append lock authority accepted: false")
    print("corrupt append-only registry normalized by append: false")
    print("corrupt append-only registry projected by reconcile: false")
    print("boolean registry counts accepted before append: false")
    print("automatic leak proof accepted: false")
    print("automatic independent review accepted: false")
    print("automatic threshold approval accepted: false")
    print("typed criteria without canonical run binding accepted: false")
    print("typed review without approved criteria binding accepted: false")
    print("human approval/review record-digest gates weaken silently: false")
    print("human evidence directory/digest/reviewer separation gates weaken silently: false")
    print("automatic production soak evidence accepted: false")
    print("automatic production readiness accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())