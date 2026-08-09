#!/usr/bin/env python3
"""Validate deterministic P0 admission inventory against canonical registries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    inventory = load(INVENTORY)
    status = load(STATUS)
    require(inventory.get("schemaVersion") == "memory-os-operability-admission-inventory.v1", "inventory schema drift")
    require(inventory.get("deterministic") is True, "inventory must remain deterministic")
    require(inventory.get("productionEvidence") is False and inventory.get("productionReady") is False, "inventory cannot promote production")
    require(inventory.get("productionDecision") == "NO_GO" and status.get("productionDecision") == "NO_GO", "production decision drift")
    rows = inventory.get("areas")
    require(isinstance(rows, list) and len(rows) == 9, "inventory must contain P0-001 through P0-009")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    require(ids == [f"OPS-P0-{number:03d}" for number in range(1, 10)], f"inventory area order/set drift: {ids}")
    status_rows = {row.get("id"): row for row in status.get("areas", []) if isinstance(row, dict)}
    inventory_rows = {row.get("id"): row for row in rows if isinstance(row, dict)}
    for row in rows:
        area_id = row["id"]
        require(row.get("productionEvidence") is False and row.get("productionReady") is False, f"{area_id} inventory cannot promote production")
        require(isinstance(row.get("foundationImplemented"), bool), f"{area_id}.foundationImplemented invalid")
        require(isinstance(row.get("admittedEvidenceCount"), int) and row["admittedEvidenceCount"] >= 0, f"{area_id}.admittedEvidenceCount invalid")
        require(isinstance(row.get("nextGate"), str) and row["nextGate"], f"{area_id}.nextGate missing")
        source = status_rows.get(area_id)
        require(isinstance(source, dict), f"status row missing: {area_id}")
        require(row.get("status") == source.get("status"), f"{area_id}.status drift")
        require(row.get("blocking") == source.get("blocking"), f"{area_id}.blocking drift")
        missing = source.get("missingEvidence")
        require(isinstance(missing, list), f"{area_id}.missingEvidence invalid")
        require(row.get("missingEvidenceCount") == len(missing), f"{area_id}.missingEvidenceCount drift")

    generations = load(ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    recovery_objectives = load(ROOT / "contracts/operations/recovery-objectives-registry.v1.json")
    backup_binding = load(ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load(ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    non_resurrection_contract = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
    non_resurrection_registry = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
    drill_request_contract = load(ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json")
    drill_request_registry = load(ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json")
    preflight_contract = load(ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json")

    generation_count = generations.get("registeredGenerationCount")
    objective_count = recovery_objectives.get("approvedObjectiveCount")
    require(isinstance(generation_count, int) and generation_count >= 0, "environment generation count invalid")
    require(isinstance(objective_count, int) and objective_count >= 0, "recovery objective count invalid")
    require(inventory.get("productionEquivalentEnvironmentGenerationCount") == generation_count, "environment generation count drift")
    require(inventory.get("approvedRecoveryObjectiveCount") == objective_count, "approved recovery objective count drift")

    drill_request_count = drill_request_registry.get("registeredRequestCount")
    executable_drill_request_count = drill_request_registry.get("currentExecutableRequestCount")
    require(isinstance(drill_request_count, int) and drill_request_count >= 0, "drill request count invalid")
    require(isinstance(executable_drill_request_count, int) and 0 <= executable_drill_request_count <= drill_request_count, "executable drill request count invalid")
    require(drill_request_registry.get("appendOnly") is True, "drill request registry must remain append-only")
    require(drill_request_registry.get("productionEvidence") is False and drill_request_registry.get("productionReady") is False, "drill request registry cannot promote production")
    require(inventory.get("reviewedBackupRestoreDrillRequestCount") == drill_request_count, "inventory drill request count drift")
    require(inventory.get("currentExecutableBackupRestoreDrillRequestCount") == executable_drill_request_count, "inventory executable drill request count drift")
    drill_state = drill_request_contract.get("currentAdmissionState")
    drill_execution = drill_request_contract.get("executionBoundary")
    require(isinstance(drill_state, dict) and isinstance(drill_execution, dict), "drill request contract authority state missing")
    require(drill_state.get("registeredEnvironmentGenerationCount") == generation_count, "drill request generation count drift")
    require(drill_state.get("approvedRecoveryObjectiveCount") == objective_count, "drill request objective count drift")
    require(drill_state.get("registeredRequestCount") == drill_request_count, "drill request contract request count drift")
    require(drill_state.get("currentExecutableRequestCount") == executable_drill_request_count, "drill request contract executable count drift")
    require(drill_state.get("productionEvidence") is False and drill_state.get("productionReady") is False and drill_state.get("productionDecision") == "NO_GO", "drill request contract cannot promote production")
    require(drill_execution.get("planningAuthorityOnly") is True and drill_execution.get("requestAloneMayExecuteDrill") is False, "drill request execution boundary drift")
    require(drill_execution.get("backupExecuted") is False and drill_execution.get("restoreExecuted") is False, "planning authority cannot claim drill execution")
    if generation_count < 2 or objective_count == 0:
        require(drill_request_count == 0 and executable_drill_request_count == 0, "drill request cannot exist before two generations and an approved objective")

    preflight_state = preflight_contract.get("currentState")
    require(isinstance(preflight_state, dict), "restore drill preflight state missing")
    preflight_eligible_generation_count = preflight_state.get("preflightEligibleGenerationCount")
    unsuperseded_generation_count = preflight_state.get("unsupersededGenerationCount")
    unsuperseded_preflight_eligible_generation_count = preflight_state.get("unsupersededPreflightEligibleGenerationCount")
    distinct_unsuperseded_environment_count = preflight_state.get("distinctUnsupersededEnvironmentCount")
    eligible_pair_count = preflight_state.get("eligibleDirectedSourceTargetPairCount")
    preflight_eligible = preflight_state.get("eligibleToSubmitReviewedDrillRequest")
    preflight_decision = preflight_state.get("preflightDecision")
    require(all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in (
        preflight_eligible_generation_count,
        unsuperseded_generation_count,
        unsuperseded_preflight_eligible_generation_count,
        distinct_unsuperseded_environment_count,
        eligible_pair_count,
    )), "restore drill preflight counts invalid")
    require(preflight_eligible_generation_count <= generation_count, "semantic preflight-eligible generation count exceeds registered inventory")
    require(unsuperseded_preflight_eligible_generation_count <= unsuperseded_generation_count, "unsuperseded semantic generation count exceeds unsuperseded inventory")
    require(isinstance(preflight_eligible, bool), "restore drill preflight eligibility invalid")
    require(isinstance(preflight_decision, str) and preflight_decision, "restore drill preflight decision invalid")
    require(preflight_state.get("registeredGenerationCount") == generation_count, "preflight generation count drift")
    require(preflight_state.get("approvedRecoveryObjectiveCount") == objective_count, "preflight objective count drift")
    require(preflight_state.get("reviewedDrillRequestCount") == drill_request_count, "preflight request count drift")
    require(preflight_state.get("currentExecutableDrillRequestCount") == executable_drill_request_count, "preflight executable request count drift")
    require(all(preflight_state.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight execution/production boundary drift")
    require(preflight_state.get("productionDecision") == "NO_GO", "preflight production decision drift")
    require(drill_state.get("preflightEligibleEnvironmentGenerationCount") == preflight_eligible_generation_count, "drill/preflight semantic generation count drift")
    require(drill_state.get("unsupersededPreflightEligibleEnvironmentGenerationCount") == unsuperseded_preflight_eligible_generation_count, "drill/preflight unsuperseded semantic generation count drift")
    require(inventory.get("backupRestorePreflightEligibleEnvironmentGenerationCount") == preflight_eligible_generation_count, "inventory semantic preflight-eligible generation count drift")
    require(inventory.get("backupRestoreUnsupersededEnvironmentGenerationCount") == unsuperseded_generation_count, "inventory unsuperseded generation count drift")
    require(inventory.get("backupRestoreUnsupersededPreflightEligibleEnvironmentGenerationCount") == unsuperseded_preflight_eligible_generation_count, "inventory unsuperseded semantic generation count drift")
    require(inventory.get("backupRestoreDistinctUnsupersededEnvironmentCount") == distinct_unsuperseded_environment_count, "inventory distinct unsuperseded environment count drift")
    require(inventory.get("backupRestoreEligibleDirectedPairCount") == eligible_pair_count, "inventory eligible restore pair count drift")
    require(inventory.get("backupRestoreDrillPreflightEligible") is preflight_eligible, "inventory preflight eligibility drift")
    require(inventory.get("backupRestoreDrillPreflightDecision") == preflight_decision, "inventory preflight decision drift")

    generation_evidence_count = backup_recovery.get("registeredEvidenceCount")
    drill_bound_generation_evidence_count = backup_recovery.get("drillRequestBoundEvidenceCount")
    require(isinstance(generation_evidence_count, int) and generation_evidence_count >= 0, "generation recovery evidence count invalid")
    require(isinstance(drill_bound_generation_evidence_count, int) and drill_bound_generation_evidence_count >= 0, "drill-bound generation evidence count invalid")
    require(drill_bound_generation_evidence_count == generation_evidence_count, "every generation recovery evidence record must remain drill-request-bound")
    require(inventory.get("generationRecoveryEvidenceRecordCount") == generation_evidence_count, "inventory generation recovery evidence count drift")
    require(inventory.get("drillRequestBoundGenerationEvidenceCount") == drill_bound_generation_evidence_count, "inventory drill-bound generation evidence count drift")
    if drill_request_count == 0:
        require(generation_evidence_count == 0, "generation recovery evidence cannot exist without reviewed drill request history")

    typed_record_count = non_resurrection_registry.get("registeredRecordCount")
    typed_complete_count = non_resurrection_registry.get("completeRecordCount")
    typed_covered_count = non_resurrection_registry.get("candidateCoveredCount")
    require(all(isinstance(value, int) and value >= 0 for value in (typed_record_count, typed_complete_count, typed_covered_count)), "typed non-resurrection registry counts invalid")
    require(typed_covered_count <= typed_complete_count <= typed_record_count, "typed non-resurrection registry count ordering invalid")
    require(non_resurrection_registry.get("productionEvidence") is False and non_resurrection_registry.get("productionReady") is False, "typed non-resurrection registry cannot promote production")
    require(inventory.get("typedNonResurrectionRecordCount") == typed_record_count, "inventory typed record count drift")
    require(inventory.get("completeTypedNonResurrectionRecordCount") == typed_complete_count, "inventory complete typed record count drift")

    typed_boundary = non_resurrection_contract.get("currentBoundary")
    require(isinstance(typed_boundary, dict), "typed non-resurrection currentBoundary missing")
    pending_typed = typed_boundary.get("preOverlayEligiblePendingTypedCoverageCount")
    final_candidate_count = backup_recovery.get("productionEquivalentRecoveryCandidateCount")
    require(isinstance(pending_typed, int) and pending_typed >= 0, "pending typed coverage count invalid")
    require(isinstance(final_candidate_count, int) and 0 <= final_candidate_count <= generation_evidence_count, "final recovery candidate count invalid")
    require(typed_boundary.get("productionEquivalentRecoveryCandidateCount") == final_candidate_count, "typed boundary final candidate count drift")
    require(typed_boundary.get("candidateCoveredCount") == typed_covered_count, "typed boundary covered candidate count drift")
    require(final_candidate_count == typed_covered_count, "final recovery candidate must equal complete typed coverage of pre-overlay eligible records")
    require(typed_boundary.get("productionEvidence") is False and typed_boundary.get("productionReady") is False, "typed boundary cannot promote production")
    require(typed_boundary.get("productionDecision") == "NO_GO", "typed boundary production decision drift")
    if executable_drill_request_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot survive without executable restore drill request")

    backup_boundary = backup_binding.get("currentBoundary")
    require(isinstance(backup_boundary, dict), "backup generation boundary missing")
    independent_review_completed = backup_boundary.get("independentReviewCompleted")
    human_promotion_review_completed = backup_boundary.get("humanProductionPromotionReviewCompleted")
    human_promotion_authorized = backup_boundary.get("humanProductionPromotionAuthorized")
    require(all(isinstance(value, bool) for value in (independent_review_completed, human_promotion_review_completed, human_promotion_authorized)), "backup promotion boundary flags invalid")
    require(not human_promotion_authorized or human_promotion_review_completed, "human production promotion cannot be authorized before human review")
    require(inventory.get("backupRestoreIndependentEvidenceReviewCompleted") is independent_review_completed, "inventory independent evidence review drift")
    require(inventory.get("humanProductionPromotionReviewCompleted") is human_promotion_review_completed, "inventory human promotion review drift")
    require(inventory.get("humanProductionPromotionAuthorized") is human_promotion_authorized, "inventory human promotion authorization drift")
    if final_candidate_count > 0:
        require(independent_review_completed is True, "recovery candidate requires independent evidence review")
    require(human_promotion_review_completed is False and human_promotion_authorized is False, "current automated backup/restore authority cannot complete or authorize human production promotion")

    backup_row = inventory_rows.get("OPS-P0-007")
    require(isinstance(backup_row, dict), "OPS-P0-007 inventory row missing")
    require(backup_row.get("authority") == "contracts/operations/backup-restore-generation-evidence-contract.v1.json", "OPS-P0-007 authority drift")
    require(backup_row.get("secondaryAuthority") == "contracts/operations/backup-restore-generation-binding-contract.v1.json", "OPS-P0-007 secondary authority drift")
    require(backup_row.get("tertiaryAuthority") == "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json", "OPS-P0-007 typed authority drift")
    require(backup_row.get("quaternaryAuthority") == "contracts/operations/backup-restore-drill-request-contract.v1.json", "OPS-P0-007 drill request authority drift")
    require(backup_row.get("quinaryAuthority") == "contracts/operations/backup-restore-drill-preflight-contract.v1.json", "OPS-P0-007 preflight authority drift")
    require(backup_row.get("foundationImplemented") is True, "OPS-P0-007 admission foundation incomplete")
    require(backup_row.get("preflightDecision") == preflight_decision, "OPS-P0-007 preflight decision drift")
    require(backup_row.get("preflightEligible") is preflight_eligible, "OPS-P0-007 preflight eligibility drift")
    require(backup_row.get("independentEvidenceReviewCompleted") is independent_review_completed, "OPS-P0-007 independent evidence review drift")
    require(backup_row.get("humanProductionPromotionReviewCompleted") is human_promotion_review_completed, "OPS-P0-007 human promotion review drift")
    require(backup_row.get("humanProductionPromotionAuthorized") is human_promotion_authorized, "OPS-P0-007 human promotion authorization drift")
    deps = backup_row.get("dependencyCounts")
    require(isinstance(deps, dict), "OPS-P0-007 dependencyCounts missing")
    expected_dependencies = {
        "environmentGenerations": generation_count,
        "preflightEligibleEnvironmentGenerations": preflight_eligible_generation_count,
        "unsupersededEnvironmentGenerations": unsuperseded_generation_count,
        "unsupersededPreflightEligibleEnvironmentGenerations": unsuperseded_preflight_eligible_generation_count,
        "distinctUnsupersededEnvironments": distinct_unsuperseded_environment_count,
        "eligibleDirectedRestorePairs": eligible_pair_count,
        "approvedRecoveryObjectives": objective_count,
        "reviewedRestoreDrillRequests": drill_request_count,
        "currentExecutableRestoreDrillRequests": executable_drill_request_count,
        "generationRecoveryEvidenceRecords": generation_evidence_count,
        "drillRequestBoundGenerationEvidence": drill_bound_generation_evidence_count,
        "generationBoundBackups": backup_boundary.get("generationBoundBackupCount"),
        "generationBoundRestores": backup_boundary.get("generationBoundRestoreCount"),
        "typedNonResurrectionRecords": typed_record_count,
        "completeTypedNonResurrectionRecords": typed_complete_count,
        "preOverlayEligiblePendingTypedCoverage": pending_typed,
        "typedCoveredRecoveryCandidates": typed_covered_count,
        "productionEquivalentRecoveryCandidates": final_candidate_count,
    }
    require(deps == expected_dependencies, f"OPS-P0-007 dependencyCounts drift: {deps}")
    require(backup_row.get("admittedEvidenceCount") == backup_boundary.get("generationBoundRestoreCount"), "OPS-P0-007 admitted restore count drift")

    if preflight_decision == "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS":
        expected_next_gate = "register two distinct reviewed production-equivalent environment generations that independently revalidate as unsuperseded and semantically restore-preflight eligible; then approve explicit recovery objectives before submitting any restore drill request"
    elif preflight_decision == "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE":
        expected_next_gate = "approve explicit RPO, RTO and maximum object/database skew for the current recovery objective; then submit a planning-only cross-environment restore drill request for review"
    elif preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION":
        expected_next_gate = "submit an external reviewed planning-only restore drill request bound to one eligible source/target generation pair and the current recovery objective; do not execute from preflight alone"
    elif preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST":
        expected_next_gate = "immediately revalidate the existing reviewed drill request before any isolated restore execution, then admit request-bound generation recovery evidence and all eight typed non-resurrection domains"
    else:
        raise Fail(f"unknown restore drill preflight decision: {preflight_decision}")
    require(backup_row.get("nextGate") == expected_next_gate, "OPS-P0-007 dynamic nextGate drift")

    if typed_record_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot exist without typed non-resurrection record")
    if generation_count == 0 or objective_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot exist without generation and approved objectives")

    print("Memory OS operability admission inventory validation PASS")
    print("P0 areas: 9")
    print(f"production-equivalent generations: {generation_count}")
    print(f"restore preflight semantic/unsuperseded-semantic generations: {preflight_eligible_generation_count}/{unsuperseded_preflight_eligible_generation_count}")
    print(f"restore preflight decision: {preflight_decision}")
    print(f"restore preflight eligible pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"reviewed restore drill requests: {drill_request_count}")
    print(f"current executable restore drill requests: {executable_drill_request_count}")
    print(f"generation/drill-bound recovery evidence: {generation_evidence_count}/{drill_bound_generation_evidence_count}")
    print(f"typed non-resurrection records: {typed_record_count}")
    print(f"final recovery candidates: {final_candidate_count}")
    print(f"candidate evidence review/human promotion review/authorization: {str(independent_review_completed).lower()}/{str(human_promotion_review_completed).lower()}/{str(human_promotion_authorized).lower()}")
    print("preflight auto-creates prerequisites: false")
    print("unbound generation recovery evidence accepted: false")
    print("drill planning request implies execution: false")
    print("generic non-resurrection PASS bypass: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY ADMISSION INVENTORY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
