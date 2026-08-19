#!/usr/bin/env python3
"""Validate deterministic P0 admission inventory against canonical registries."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
SOURCE_AUTHORITY_VALIDATOR = ROOT / "scripts" / "validate-memory-os-operability-admission-inventory-source-authorities.py"
DOMAIN_REJECTIONS = {"Fail", "Failure", "RegistrationFailure"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def require_count_match(value: Any, expected: int, message: str) -> None:
    require(valid_count(value) and value == expected, message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def canonical_registry_validator(script_name: str, module_name: str):
    path = ROOT / "scripts" / script_name
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"canonical registry validator missing or escapes repository: {script_name}") from exc
    require(resolved == Path("scripts") / script_name and path.is_file(), f"canonical registry validator path drift: {script_name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical registry validator: {script_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_registry_for_append", None)
    require(callable(validator), f"canonical registry validator missing validate_registry_for_append: {script_name}")
    return validator


def require_canonical_registry(script_name: str, module_name: str, registry: dict[str, Any], label: str) -> None:
    validator = canonical_registry_validator(script_name, module_name)
    try:
        validator(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise Fail(f"{label} invalid: {exc}") from exc
        raise


def validate_source_authorities() -> None:
    try:
        resolved = SOURCE_AUTHORITY_VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("canonical inventory source-authority validator missing or escapes repository") from exc
    require(
        resolved == Path("scripts") / SOURCE_AUTHORITY_VALIDATOR.name and SOURCE_AUTHORITY_VALIDATOR.is_file(),
        "canonical inventory source-authority validator path drift",
    )
    spec = importlib.util.spec_from_file_location("memory_os_operability_inventory_source_authority", SOURCE_AUTHORITY_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load canonical inventory source-authority validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "main", None)
    require(callable(validator), "canonical inventory source-authority validator missing main")
    try:
        result = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ in DOMAIN_REJECTIONS:
            raise Fail(f"inventory source authority invalid: {exc}") from exc
        raise
    require(isinstance(result, int) and not isinstance(result, bool) and result == 0, f"inventory source-authority validator returned nonzero result: {result}")


def main() -> int:
    validate_source_authorities()
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
        require(valid_count(row.get("admittedEvidenceCount")), f"{area_id}.admittedEvidenceCount invalid")
        require(isinstance(row.get("nextGate"), str) and row["nextGate"], f"{area_id}.nextGate missing")
        source = status_rows.get(area_id)
        require(isinstance(source, dict), f"status row missing: {area_id}")
        require(row.get("status") == source.get("status"), f"{area_id}.status drift")
        require(row.get("blocking") == source.get("blocking"), f"{area_id}.blocking drift")
        missing = source.get("missingEvidence")
        require(isinstance(missing, list), f"{area_id}.missingEvidence invalid")
        require_count_match(row.get("missingEvidenceCount"), len(missing), f"{area_id}.missingEvidenceCount drift")

    generations = load(ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    soak_review = load(ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json")
    recovery_objectives = load(ROOT / "contracts/operations/recovery-objectives-registry.v1.json")
    backup_binding = load(ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load(ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    non_resurrection_contract = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
    non_resurrection_registry = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
    drill_request_contract = load(ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json")
    drill_request_registry = load(ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json")
    preflight_contract = load(ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json")
    promotion_registry = load(ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json")

    require_canonical_registry(
        "register-memory-os-production-equivalent-environment-generation.py",
        "memory_os_environment_generation_inventory_authority",
        generations,
        "environment generation registry",
    )
    require_canonical_registry(
        "register-memory-os-sustained-soak-independent-review.py",
        "memory_os_sustained_soak_inventory_authority",
        soak_review,
        "sustained-soak independent review registry",
    )
    require_canonical_registry(
        "register-memory-os-recovery-objectives.py",
        "memory_os_recovery_objective_inventory_authority",
        recovery_objectives,
        "recovery objective registry",
    )
    require_canonical_registry(
        "request-memory-os-backup-restore-drill.py",
        "memory_os_drill_request_inventory_authority",
        drill_request_registry,
        "drill request registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-generation-evidence.py",
        "memory_os_generation_evidence_inventory_authority",
        backup_recovery,
        "generation recovery evidence registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-non-resurrection-evidence.py",
        "memory_os_typed_non_resurrection_inventory_authority",
        non_resurrection_registry,
        "typed non-resurrection registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-promotion-review.py",
        "memory_os_promotion_review_inventory_authority",
        promotion_registry,
        "human promotion review registry",
    )

    promotion_rows = promotion_registry.get("records")
    promotion_count = promotion_registry.get("registeredReviewCount")
    require(promotion_registry.get("schemaVersion") == "memory-os-backup-restore-promotion-review-registry.v1", "promotion review registry schema drift")
    require(promotion_registry.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(all(promotion_registry.get(field) is False for field in ("productionTrafficChanged", "productionEvidence", "productionReady")), "promotion review registry cannot promote production")
    require(isinstance(promotion_rows, list) and all(isinstance(row, dict) for row in promotion_rows), "promotion review registry rows invalid")
    require(valid_count(promotion_count) and promotion_count == len(promotion_rows), "promotion review registry count drift")
    current_promotion_decision_id = promotion_registry.get("currentDecisionId")
    if current_promotion_decision_id is not None:
        current_matches = [row for row in promotion_rows if row.get("decisionId") == current_promotion_decision_id]
        require(len(current_matches) == 1, "promotion review currentDecisionId authority drift")
    human_promotion_review_completed = current_promotion_decision_id is not None
    human_promotion_authorized = False

    generation_count = generations.get("registeredGenerationCount")
    objective_count = recovery_objectives.get("approvedObjectiveCount")
    require(valid_count(generation_count), "environment generation count invalid")
    require(valid_count(objective_count), "recovery objective count invalid")
    require_count_match(inventory.get("productionEquivalentEnvironmentGenerationCount"), generation_count, "environment generation count drift")
    require_count_match(inventory.get("approvedRecoveryObjectiveCount"), objective_count, "approved recovery objective count drift")

    soak_approved_criteria_count = soak_review.get("approvedLeakStabilityCriteriaCount")
    soak_passing_review_count = soak_review.get("passingIndependentReviewCount")
    soak_leak_proof = soak_review.get("leakProof")
    require(valid_count(soak_approved_criteria_count), "approved leak/stability criteria count invalid")
    require(valid_count(soak_passing_review_count) and soak_passing_review_count <= soak_approved_criteria_count, "passing independent sustained-soak review count invalid")
    require(isinstance(soak_leak_proof, bool), "sustained-soak leak proof invalid")
    require(not soak_leak_proof or soak_passing_review_count > 0, "sustained-soak leak proof requires a passing independent review")
    require(soak_review.get("appendOnly") is True, "sustained-soak independent review registry must remain append-only")
    require(soak_review.get("productionEvidence") is False and soak_review.get("productionReady") is False, "sustained-soak independent review registry cannot promote production")
    require_count_match(inventory.get("approvedLeakStabilityCriteriaCount"), soak_approved_criteria_count, "inventory approved leak/stability criteria count drift")
    require_count_match(inventory.get("passingIndependentSustainedSoakReviewCount"), soak_passing_review_count, "inventory independent sustained-soak review count drift")
    require(inventory.get("sustainedSoakLeakProof") is soak_leak_proof, "inventory sustained-soak leak proof drift")
    soak_row = inventory_rows.get("OPS-P0-006")
    require(isinstance(soak_row, dict), "OPS-P0-006 inventory row missing")
    require(soak_row.get("authority") == "contracts/operations/load-test-scenario-contract.v1.json", "OPS-P0-006 authority drift")
    require(soak_row.get("secondaryAuthority") == "contracts/operations/sustained-soak-independent-review-registry.v1.json", "OPS-P0-006 independent review authority drift")
    require_count_match(soak_row.get("approvedLeakStabilityCriteriaCount"), soak_approved_criteria_count, "OPS-P0-006 approved criteria count drift")
    require_count_match(soak_row.get("passingIndependentReviewCount"), soak_passing_review_count, "OPS-P0-006 independent review count drift")
    require(soak_row.get("leakProof") is soak_leak_proof, "OPS-P0-006 leak proof drift")
    soak_deps = soak_row.get("dependencyCounts")
    require(isinstance(soak_deps, dict), "OPS-P0-006 dependencyCounts missing")
    require_count_match(soak_deps.get("environmentGenerations"), generation_count, "OPS-P0-006 generation count drift")
    require_count_match(soak_deps.get("approvedLeakStabilityCriteria"), soak_approved_criteria_count, "OPS-P0-006 criteria dependency drift")
    require_count_match(soak_deps.get("passingIndependentReviews"), soak_passing_review_count, "OPS-P0-006 review dependency drift")
    require(isinstance(soak_deps.get("localSustainedSoakEvidence"), bool), "OPS-P0-006 local sustained-soak evidence flag invalid")
    require(isinstance(soak_deps.get("repeatableLocalDegradationSignalObserved"), bool), "OPS-P0-006 degradation signal flag invalid")
    if soak_approved_criteria_count == 0 or soak_passing_review_count == 0:
        require(soak_leak_proof is False, "OPS-P0-006 cannot claim leak proof without approved criteria and passing independent review")

    drill_request_count = drill_request_registry.get("registeredRequestCount")
    executable_drill_request_count = drill_request_registry.get("currentExecutableRequestCount")
    require(valid_count(drill_request_count), "drill request count invalid")
    require(valid_count(executable_drill_request_count) and executable_drill_request_count <= drill_request_count, "executable drill request count invalid")
    require(drill_request_registry.get("appendOnly") is True, "drill request registry must remain append-only")
    require(drill_request_registry.get("productionEvidence") is False and drill_request_registry.get("productionReady") is False, "drill request registry cannot promote production")
    require_count_match(inventory.get("reviewedBackupRestoreDrillRequestCount"), drill_request_count, "inventory drill request count drift")
    require_count_match(inventory.get("currentExecutableBackupRestoreDrillRequestCount"), executable_drill_request_count, "inventory executable drill request count drift")
    drill_state = drill_request_contract.get("currentAdmissionState")
    drill_execution = drill_request_contract.get("executionBoundary")
    require(isinstance(drill_state, dict) and isinstance(drill_execution, dict), "drill request contract authority state missing")
    require_count_match(drill_state.get("registeredEnvironmentGenerationCount"), generation_count, "drill request generation count drift")
    require_count_match(drill_state.get("approvedRecoveryObjectiveCount"), objective_count, "drill request objective count drift")
    require_count_match(drill_state.get("registeredRequestCount"), drill_request_count, "drill request contract request count drift")
    require_count_match(drill_state.get("currentExecutableRequestCount"), executable_drill_request_count, "drill request contract executable count drift")
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
    distinct_unsuperseded_preflight_eligible_environment_count = preflight_state.get("distinctUnsupersededPreflightEligibleEnvironmentCount")
    eligible_pair_count = preflight_state.get("eligibleDirectedSourceTargetPairCount")
    preflight_eligible = preflight_state.get("eligibleToSubmitReviewedDrillRequest")
    preflight_decision = preflight_state.get("preflightDecision")
    require(all(valid_count(value) for value in (
        preflight_eligible_generation_count,
        unsuperseded_generation_count,
        unsuperseded_preflight_eligible_generation_count,
        distinct_unsuperseded_preflight_eligible_environment_count,
        eligible_pair_count,
    )), "restore drill preflight counts invalid")
    require(preflight_eligible_generation_count <= generation_count, "semantic preflight-eligible generation count exceeds registered inventory")
    require(unsuperseded_preflight_eligible_generation_count <= unsuperseded_generation_count, "unsuperseded semantic generation count exceeds unsuperseded inventory")
    require(distinct_unsuperseded_preflight_eligible_environment_count <= unsuperseded_preflight_eligible_generation_count, "distinct semantic preflight-eligible environment count exceeds eligible generation inventory")
    require(isinstance(preflight_eligible, bool), "restore drill preflight eligibility invalid")
    require(isinstance(preflight_decision, str) and preflight_decision, "restore drill preflight decision invalid")
    require_count_match(preflight_state.get("registeredGenerationCount"), generation_count, "preflight generation count drift")
    require_count_match(preflight_state.get("approvedRecoveryObjectiveCount"), objective_count, "preflight objective count drift")
    require_count_match(preflight_state.get("reviewedDrillRequestCount"), drill_request_count, "preflight request count drift")
    require_count_match(preflight_state.get("currentExecutableDrillRequestCount"), executable_drill_request_count, "preflight executable request count drift")
    require(all(preflight_state.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight execution/production boundary drift")
    require(preflight_state.get("productionDecision") == "NO_GO", "preflight production decision drift")
    require_count_match(drill_state.get("preflightEligibleEnvironmentGenerationCount"), preflight_eligible_generation_count, "drill/preflight semantic generation count drift")
    require_count_match(drill_state.get("unsupersededPreflightEligibleEnvironmentGenerationCount"), unsuperseded_preflight_eligible_generation_count, "drill/preflight unsuperseded semantic generation count drift")
    require_count_match(inventory.get("backupRestorePreflightEligibleEnvironmentGenerationCount"), preflight_eligible_generation_count, "inventory semantic preflight-eligible generation count drift")
    require_count_match(inventory.get("backupRestoreUnsupersededEnvironmentGenerationCount"), unsuperseded_generation_count, "inventory unsuperseded generation count drift")
    require_count_match(inventory.get("backupRestoreUnsupersededPreflightEligibleEnvironmentGenerationCount"), unsuperseded_preflight_eligible_generation_count, "inventory unsuperseded semantic generation count drift")
    require_count_match(inventory.get("backupRestoreDistinctUnsupersededPreflightEligibleEnvironmentCount"), distinct_unsuperseded_preflight_eligible_environment_count, "inventory distinct semantic unsuperseded environment count drift")
    require_count_match(inventory.get("backupRestoreEligibleDirectedPairCount"), eligible_pair_count, "inventory eligible restore pair count drift")
    require(inventory.get("backupRestoreDrillPreflightEligible") is preflight_eligible, "inventory preflight eligibility drift")
    require(inventory.get("backupRestoreDrillPreflightDecision") == preflight_decision, "inventory preflight decision drift")

    generation_evidence_count = backup_recovery.get("registeredEvidenceCount")
    drill_bound_generation_evidence_count = backup_recovery.get("drillRequestBoundEvidenceCount")
    require(valid_count(generation_evidence_count), "generation recovery evidence count invalid")
    require(valid_count(drill_bound_generation_evidence_count), "drill-bound generation evidence count invalid")
    require(drill_bound_generation_evidence_count == generation_evidence_count, "every generation recovery evidence record must remain drill-request-bound")
    require_count_match(inventory.get("generationRecoveryEvidenceRecordCount"), generation_evidence_count, "inventory generation recovery evidence count drift")
    require_count_match(inventory.get("drillRequestBoundGenerationEvidenceCount"), drill_bound_generation_evidence_count, "inventory drill-bound generation evidence count drift")
    if drill_request_count == 0:
        require(generation_evidence_count == 0, "generation recovery evidence cannot exist without reviewed drill request history")

    typed_record_count = non_resurrection_registry.get("registeredRecordCount")
    typed_complete_count = non_resurrection_registry.get("completeRecordCount")
    typed_covered_count = non_resurrection_registry.get("candidateCoveredCount")
    require(all(valid_count(value) for value in (typed_record_count, typed_complete_count, typed_covered_count)), "typed non-resurrection registry counts invalid")
    require(typed_covered_count <= typed_complete_count <= typed_record_count, "typed non-resurrection registry count ordering invalid")
    require(non_resurrection_registry.get("productionEvidence") is False and non_resurrection_registry.get("productionReady") is False, "typed non-resurrection registry cannot promote production")
    require_count_match(inventory.get("typedNonResurrectionRecordCount"), typed_record_count, "inventory typed record count drift")
    require_count_match(inventory.get("completeTypedNonResurrectionRecordCount"), typed_complete_count, "inventory complete typed record count drift")

    typed_boundary = non_resurrection_contract.get("currentBoundary")
    require(isinstance(typed_boundary, dict), "typed non-resurrection currentBoundary missing")
    pending_typed = typed_boundary.get("preOverlayEligiblePendingTypedCoverageCount")
    final_candidate_count = backup_recovery.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(pending_typed), "pending typed coverage count invalid")
    require(valid_count(final_candidate_count) and final_candidate_count <= generation_evidence_count, "final recovery candidate count invalid")
    require_count_match(typed_boundary.get("productionEquivalentRecoveryCandidateCount"), final_candidate_count, "typed boundary final candidate count drift")
    require_count_match(typed_boundary.get("candidateCoveredCount"), typed_covered_count, "typed boundary covered candidate count drift")
    require(final_candidate_count == typed_covered_count, "final recovery candidate must equal complete typed coverage of pre-overlay eligible records")
    require(typed_boundary.get("productionEvidence") is False and typed_boundary.get("productionReady") is False, "typed boundary cannot promote production")
    require(typed_boundary.get("productionDecision") == "NO_GO", "typed boundary production decision drift")
    if executable_drill_request_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot survive without executable restore drill request")

    backup_boundary = backup_binding.get("currentBoundary")
    require(isinstance(backup_boundary, dict), "backup generation boundary missing")
    backup_count = backup_boundary.get("generationBoundBackupCount")
    restore_count = backup_boundary.get("generationBoundRestoreCount")
    binding_candidate_count = backup_boundary.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(backup_count), "backup generation-bound backup count invalid")
    require(valid_count(restore_count), "backup generation-bound restore count invalid")
    require(valid_count(binding_candidate_count), "backup recovery candidate count invalid")
    require(binding_candidate_count == final_candidate_count, "backup generation candidate count drift")
    require(final_candidate_count <= restore_count <= backup_count <= generation_evidence_count, "backup recovery aggregate ordering drift")
    independent_review_completed = backup_boundary.get("independentReviewCompleted")
    automated_human_review = backup_boundary.get("humanProductionPromotionReviewCompleted")
    automated_human_authorization = backup_boundary.get("humanProductionPromotionAuthorized")
    require(isinstance(independent_review_completed, bool), "independent evidence review flag invalid")
    require(automated_human_review is False and automated_human_authorization is False, "automated generation binding cannot complete or authorize human production promotion")
    require(inventory.get("backupRestoreIndependentEvidenceReviewCompleted") is independent_review_completed, "inventory independent evidence review drift")
    require(inventory.get("humanProductionPromotionReviewCompleted") is human_promotion_review_completed, "inventory human promotion review drift")
    require(inventory.get("humanProductionPromotionAuthorized") is human_promotion_authorized, "inventory human promotion authorization drift")
    if final_candidate_count > 0:
        require(independent_review_completed is True, "recovery candidate requires independent evidence review")
    require(human_promotion_authorized is False, "human promotion review remains separate from production authorization")

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
    require(all(valid_count(value) for value in deps.values()), "OPS-P0-007 dependency counts must be non-boolean counts")
    expected_dependencies = {
        "environmentGenerations": generation_count,
        "preflightEligibleEnvironmentGenerations": preflight_eligible_generation_count,
        "unsupersededEnvironmentGenerations": unsuperseded_generation_count,
        "unsupersededPreflightEligibleEnvironmentGenerations": unsuperseded_preflight_eligible_generation_count,
        "distinctUnsupersededPreflightEligibleEnvironments": distinct_unsuperseded_preflight_eligible_environment_count,
        "eligibleDirectedRestorePairs": eligible_pair_count,
        "approvedRecoveryObjectives": objective_count,
        "reviewedRestoreDrillRequests": drill_request_count,
        "currentExecutableRestoreDrillRequests": executable_drill_request_count,
        "generationRecoveryEvidenceRecords": generation_evidence_count,
        "drillRequestBoundGenerationEvidence": drill_bound_generation_evidence_count,
        "generationBoundBackups": backup_count,
        "generationBoundRestores": restore_count,
        "typedNonResurrectionRecords": typed_record_count,
        "completeTypedNonResurrectionRecords": typed_complete_count,
        "preOverlayEligiblePendingTypedCoverage": pending_typed,
        "typedCoveredRecoveryCandidates": typed_covered_count,
        "productionEquivalentRecoveryCandidates": final_candidate_count,
    }
    require(deps == expected_dependencies, f"OPS-P0-007 dependencyCounts drift: {deps}")
    require_count_match(backup_row.get("admittedEvidenceCount"), restore_count, "OPS-P0-007 admitted restore count drift")

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
    print(f"approved leak/stability criteria: {soak_approved_criteria_count}")
    print(f"passing independent sustained-soak reviews: {soak_passing_review_count}")
    print(f"sustained-soak leak proof: {str(soak_leak_proof).lower()}")
    print(f"restore preflight semantic/unsuperseded-semantic generations: {preflight_eligible_generation_count}/{unsuperseded_preflight_eligible_generation_count}")
    print(f"restore preflight distinct semantic unsuperseded environments: {distinct_unsuperseded_preflight_eligible_environment_count}")
    print(f"restore preflight decision: {preflight_decision}")
    print(f"restore preflight eligible pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"reviewed restore drill requests: {drill_request_count}")
    print(f"current executable restore drill requests: {executable_drill_request_count}")
    print(f"generation/drill-bound recovery evidence: {generation_evidence_count}/{drill_bound_generation_evidence_count}")
    print(f"typed non-resurrection records: {typed_record_count}")
    print(f"final recovery candidates: {final_candidate_count}")
    print("boolean cross-authority counts accepted: false")
    print(f"candidate evidence review/human promotion review/authorization: {str(independent_review_completed).lower()}/{str(human_promotion_review_completed).lower()}/{str(human_promotion_authorized).lower()}")
    print("automated generation binding substitutes for human promotion review: false")
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
