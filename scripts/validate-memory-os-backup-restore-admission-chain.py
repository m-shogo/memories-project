#!/usr/bin/env python3
"""Validate the end-to-end Memory OS backup/restore admission chain."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
PREFLIGHT_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_admission_chain", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    preflight_contract = load(PREFLIGHT_CONTRACT)
    drill_contract = load(DRILL_CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    gen_contract = load(GEN_CONTRACT)
    gen_registry = load(GEN_REGISTRY)
    typed_contract = load(TYPED_CONTRACT)
    typed_registry = load(TYPED_REGISTRY)
    inventory = load(INVENTORY)
    status = load(STATUS)
    gen_writer = load_generation_writer()

    require(contract.get("schemaVersion") == "memory-os-backup-restore-admission-chain-contract.v1", "chain contract schema drift")
    refs = {
        "drillPreflightContract": PREFLIGHT_CONTRACT,
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "generationEvidenceContract": GEN_CONTRACT,
        "generationEvidenceRegistry": GEN_REGISTRY,
        "typedNonResurrectionContract": TYPED_CONTRACT,
        "typedNonResurrectionRegistry": TYPED_REGISTRY,
        "operabilityInventory": INVENTORY,
        "operabilityStatus": STATUS,
        "validator": Path("scripts/validate-memory-os-backup-restore-admission-chain.py"),
        "workflow": Path(".github/workflows/backup-restore-admission-chain.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"chain ref drift: {field}")
        require((ROOT / expected).is_file(), f"chain artifact missing: {expected}")
    required_chain = contract.get("requiredChain")
    require(isinstance(required_chain, list) and required_chain and required_chain[0] == "readOnlyDrillPreflight", "preflight must remain chain stage zero")
    require(len(required_chain) == len(set(required_chain)), "chain stages must be unique")
    invariants = contract.get("invariants")
    require(isinstance(invariants, dict) and invariants and all(value is True for value in invariants.values()), "chain invariants must remain fail-closed")
    for key in (
        "preflightNeverCreatesMissingPrerequisites",
        "preflightReadyNeverCreatesDrillRequest",
        "preflightBlockedCannotHaveCurrentExecutableDrillRequest",
        "currentExecutableDrillRequestRequiresReadyExistingPreflightDecision",
        "generationEvidenceRequiresRegisteredDrillRequest",
        "staleRequestEvidenceCannotRemainCurrentCandidate",
        "finalCandidateRequiresCompleteTypedEightDomainCoverage",
        "finalCandidateRequiresIndependentEvidenceReview",
        "finalCandidateCannotCompleteHumanProductionPromotionReview",
        "finalCandidateCannotAuthorizeProductionPromotion",
        "humanProductionPromotionReviewRemainsSeparate",
        "chainCannotDeriveProductionEvidence",
        "chainCannotDeriveProductionReady",
    ):
        require(invariants.get(key) is True, f"chain invariant missing: {key}")

    preflight = preflight_contract.get("currentState")
    require(isinstance(preflight, dict), "preflight currentState missing")
    preflight_decision = preflight.get("preflightDecision")
    preflight_eligible = preflight.get("eligibleToSubmitReviewedDrillRequest")
    preflight_pair_count = preflight.get("eligibleDirectedSourceTargetPairCount")
    require(isinstance(preflight_decision, str) and preflight_decision, "preflight decision invalid")
    require(isinstance(preflight_eligible, bool), "preflight eligibility invalid")
    require(isinstance(preflight_pair_count, int) and preflight_pair_count >= 0, "preflight eligible pair count invalid")
    require(all(preflight.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight may not create prerequisites, execute restore or promote production")
    require(preflight.get("productionDecision") == "NO_GO", "preflight production decision drift")

    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(drill_rows, list) and all(isinstance(row, dict) for row in drill_rows), "drill request rows invalid")
    require(isinstance(drill_count, int) and drill_count == len(drill_rows), "drill request count drift")
    require(isinstance(current_drill_count, int) and 0 <= current_drill_count <= drill_count, "current drill request count invalid")
    require(drill_registry.get("productionEvidence") is False and drill_registry.get("productionReady") is False, "drill request registry production boundary drift")
    require(preflight.get("reviewedDrillRequestCount") == drill_count, "preflight reviewed request count drift")
    require(preflight.get("currentExecutableDrillRequestCount") == current_drill_count, "preflight current request count drift")
    if current_drill_count > 0:
        require(preflight_eligible is True, "current executable drill request requires eligible preflight")
        require(preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST", "current executable drill request requires READY_EXISTING preflight")
        require(preflight_pair_count > 0, "current executable drill request requires eligible source-target pair")
    elif preflight_eligible:
        require(preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION", "eligible preflight without current request must be READY_FOR_SUBMISSION")
        require(preflight_pair_count > 0, "eligible preflight requires source-target pair")
    else:
        require(preflight_decision in {
            "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS",
            "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE",
        }, "ineligible preflight must remain explicitly BLOCKED")
        require(current_drill_count == 0, "blocked preflight cannot have current executable drill request")
    drill_execution = drill_contract.get("executionBoundary")
    require(isinstance(drill_execution, dict), "drill execution boundary missing")
    require(drill_execution.get("planningAuthorityOnly") is True and drill_execution.get("requestAloneMayExecuteDrill") is False, "drill request may not become execution authority")
    require(drill_execution.get("backupExecuted") is False and drill_execution.get("restoreExecuted") is False, "planning layer cannot claim drill execution")

    gen_rules = gen_contract.get("recordRules")
    gen_promotion = gen_contract.get("promotionBoundary")
    require(isinstance(gen_rules, dict) and gen_rules.get("drillRequestMustExist") is True, "generation evidence drill request gate missing")
    require(gen_rules.get("drillRequestMustBeCurrentlyExecutableForNewEvidence") is True, "current drill request gate missing")
    require(gen_rules.get("historicalEvidenceMayRemainAuditableAfterDrillRequestBecomesStale") is True, "historical evidence rule missing")
    require(gen_rules.get("typedNonResurrectionCoverageRequiredForProductionEquivalentRestoreCandidate") is True, "typed coverage gate missing")
    require(gen_rules.get("genericNonResurrectionPassAloneCannotCreateCandidate") is True, "generic PASS bypass guard missing")
    require(isinstance(gen_promotion, dict) and gen_promotion.get("completeReviewedRecordAlsoRequiresAdmittedDrillRequestBinding") is True, "generation promotion is not drill-request-bound")
    require(gen_promotion.get("completeReviewedRecordAlsoRequiresTypedNonResurrectionCoverage") is True, "generation promotion is not typed-overlay-bound")

    gen_rows = gen_registry.get("records")
    gen_count = gen_registry.get("registeredEvidenceCount")
    bound_count = gen_registry.get("drillRequestBoundEvidenceCount")
    candidate_count = gen_registry.get("productionEquivalentRecoveryCandidateCount")
    require(isinstance(gen_rows, list) and all(isinstance(row, dict) for row in gen_rows), "generation evidence rows invalid")
    require(isinstance(gen_count, int) and gen_count == len(gen_rows), "generation evidence count drift")
    require(isinstance(bound_count, int) and bound_count == gen_count, "every generation evidence row must be drill-request-bound")
    require(isinstance(candidate_count, int) and 0 <= candidate_count <= gen_count, "candidate count invalid")
    require(gen_registry.get("productionEvidence") is False and gen_registry.get("productionReady") is False, "generation evidence registry production boundary drift")

    drill_ids = {row.get("requestId") for row in drill_rows if isinstance(row.get("requestId"), str)}
    require(len(drill_ids) == drill_count, "drill request IDs must be unique")
    candidate_ids: set[str] = set()
    for row in gen_rows:
        gen_writer.validate_record(row, require_current_drill_request=False)
        request_id = row.get("drillRequestId")
        require(request_id in drill_ids, f"generation evidence references missing drill request: {request_id}")
        if gen_writer.candidate(row):
            evidence_id = row.get("evidenceId")
            require(isinstance(evidence_id, str), "candidate evidenceId invalid")
            candidate_ids.add(evidence_id)
    require(len(candidate_ids) == candidate_count, "candidate derivation/count drift")
    if current_drill_count == 0:
        require(candidate_count == 0, "candidate cannot survive without current executable drill request")

    typed_rules = typed_contract.get("candidateCoverageRule")
    require(isinstance(typed_rules, dict) and typed_rules.get("genericNonResurrectionPassAloneIsInsufficient") is True, "typed generic PASS bypass guard missing")
    require(typed_rules.get("everyProductionEquivalentRecoveryCandidateRequiresOneCompleteTypedRecord") is True, "typed candidate coverage rule missing")
    typed_rows = typed_registry.get("records")
    typed_count = typed_registry.get("registeredRecordCount")
    typed_complete_count = typed_registry.get("completeRecordCount")
    typed_covered_count = typed_registry.get("candidateCoveredCount")
    require(isinstance(typed_rows, list) and all(isinstance(row, dict) for row in typed_rows), "typed non-resurrection rows invalid")
    require(isinstance(typed_count, int) and typed_count == len(typed_rows), "typed record count drift")
    require(isinstance(typed_complete_count, int) and 0 <= typed_complete_count <= typed_count, "typed complete count invalid")
    require(isinstance(typed_covered_count, int) and 0 <= typed_covered_count <= typed_complete_count, "typed candidate coverage count invalid")
    require(typed_registry.get("productionEvidence") is False and typed_registry.get("productionReady") is False, "typed registry production boundary drift")
    complete_typed_ids = {
        row.get("generationEvidenceId")
        for row in typed_rows
        if row.get("evidenceComplete") is True and isinstance(row.get("generationEvidenceId"), str)
    }
    require(candidate_ids.issubset(complete_typed_ids), "final candidate bypasses complete typed non-resurrection evidence")
    require(typed_covered_count == candidate_count, "typed candidate coverage count must equal final candidate count")

    chain_boundary = contract.get("currentBoundary")
    require(isinstance(chain_boundary, dict), "chain currentBoundary missing")
    expected = {
        "preflightDecision": preflight_decision,
        "preflightEligibleToSubmitReviewedDrillRequest": preflight_eligible,
        "preflightEligibleDirectedSourceTargetPairCount": preflight_pair_count,
        "reviewedDrillRequestCount": drill_count,
        "currentExecutableDrillRequestCount": current_drill_count,
        "generationEvidenceCount": gen_count,
        "drillRequestBoundGenerationEvidenceCount": bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete_count,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
        "independentEvidenceReviewCompleted": candidate_count > 0,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
    }
    for field, value in expected.items():
        require(chain_boundary.get(field) == value, f"chain boundary drift: {field}")
    require(chain_boundary.get("productionEvidence") is False and chain_boundary.get("productionReady") is False and chain_boundary.get("productionDecision") == "NO_GO", "chain cannot promote production")

    require(inventory.get("productionDecision") == "NO_GO" and inventory.get("productionEvidence") is False and inventory.get("productionReady") is False, "inventory production boundary drift")
    require(inventory.get("backupRestoreDrillPreflightDecision") == preflight_decision, "inventory preflight decision drift")
    require(inventory.get("backupRestoreDrillPreflightEligible") is preflight_eligible, "inventory preflight eligibility drift")
    require(inventory.get("backupRestoreEligibleDirectedPairCount") == preflight_pair_count, "inventory preflight pair count drift")
    require(inventory.get("reviewedBackupRestoreDrillRequestCount") == drill_count, "inventory drill request count drift")
    require(inventory.get("currentExecutableBackupRestoreDrillRequestCount") == current_drill_count, "inventory current drill request count drift")
    ops7 = next((row for row in inventory.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 inventory row missing")
    require(ops7.get("preflightDecision") == preflight_decision and ops7.get("preflightEligible") is preflight_eligible, "OPS-P0-007 preflight inventory drift")
    deps = ops7.get("dependencyCounts")
    require(isinstance(deps, dict) and deps.get("productionEquivalentRecoveryCandidates") == candidate_count, "inventory candidate dependency drift")
    require(deps.get("reviewedRestoreDrillRequests") == drill_count and deps.get("currentExecutableRestoreDrillRequests") == current_drill_count, "inventory drill request dependency drift")
    require(deps.get("eligibleDirectedRestorePairs") == preflight_pair_count, "inventory preflight pair dependency drift")

    require(status.get("productionDecision") == "NO_GO", "status production decision drift")
    status7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(status7, dict), "OPS-P0-007 status row missing")
    require(status7.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and status7.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    missing = status7.get("missingEvidence")
    require(isinstance(missing, list) and len(missing) == 6, f"canonical OPS-P0-007 blocker count drift: {len(missing) if isinstance(missing, list) else 'invalid'}")
    lowered = "\n".join(str(item).lower() for item in missing)
    for phrase in ("postgresql backup", "independent object", "rpo", "cross-cluster", "non-resurrection", "independent review"):
        require(phrase in lowered, f"canonical OPS-P0-007 blocker disappeared: {phrase}")

    print("Memory OS backup/restore end-to-end admission chain PASS")
    print(f"preflight: {preflight_decision}")
    print(f"preflight eligible pairs: {preflight_pair_count}")
    print(f"reviewed/current drill requests: {drill_count}/{current_drill_count}")
    print(f"generation/drill-bound evidence: {gen_count}/{bound_count}")
    print(f"complete typed non-resurrection records: {typed_complete_count}")
    print(f"final production-equivalent recovery candidates: {candidate_count}")
    print(f"candidate-level independent evidence review completed: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production-promotion authorized: false")
    print("preflight prerequisite/request auto-creation: false")
    print("request bypass to generation evidence: false")
    print("generic non-resurrection PASS bypass: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
