#!/usr/bin/env python3
"""Validate the end-to-end Memory OS backup/restore admission chain."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-admission-chain-contract.v1.json")
PREFLIGHT_CONTRACT_REL = Path("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
DRILL_CONTRACT_REL = Path("contracts/operations/backup-restore-drill-request-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
GEN_CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
BINDING_CONTRACT_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
TYPED_CONTRACT_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
TYPED_REGISTRY_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
INVENTORY_REL = Path("contracts/operations/operability-admission-inventory.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
GEN_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
TYPED_WRITER_REL = Path("scripts/register-memory-os-backup-restore-non-resurrection-evidence.py")
BLOCKER_AUTHORITY_REL = Path("scripts/memory_os_backup_restore_blockers.py")
SELF_REL = Path("scripts/validate-memory-os-backup-restore-admission-chain.py")
WORKFLOW_REL = Path(".github/workflows/backup-restore-admission-chain.yml")
CONTRACT = ROOT / CONTRACT_REL
PREFLIGHT_CONTRACT = ROOT / PREFLIGHT_CONTRACT_REL
DRILL_CONTRACT = ROOT / DRILL_CONTRACT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
GEN_CONTRACT = ROOT / GEN_CONTRACT_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
BINDING_CONTRACT = ROOT / BINDING_CONTRACT_REL
TYPED_CONTRACT = ROOT / TYPED_CONTRACT_REL
TYPED_REGISTRY = ROOT / TYPED_REGISTRY_REL
INVENTORY = ROOT / INVENTORY_REL
STATUS = ROOT / STATUS_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
GEN_WRITER = ROOT / GEN_WRITER_REL
TYPED_WRITER = ROOT / TYPED_WRITER_REL
BLOCKER_AUTHORITY = ROOT / BLOCKER_AUTHORITY_REL
SELF = ROOT / SELF_REL
WORKFLOW = ROOT / WORKFLOW_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative
        and resolved == expected_relative
        and path.is_file()
        and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "admission-chain contract"),
        (PREFLIGHT_CONTRACT, PREFLIGHT_CONTRACT_REL, "drill preflight contract"),
        (DRILL_CONTRACT, DRILL_CONTRACT_REL, "drill request contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (GEN_CONTRACT, GEN_CONTRACT_REL, "generation evidence contract"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "generation evidence registry"),
        (BINDING_CONTRACT, BINDING_CONTRACT_REL, "generation binding contract"),
        (TYPED_CONTRACT, TYPED_CONTRACT_REL, "typed non-resurrection contract"),
        (TYPED_REGISTRY, TYPED_REGISTRY_REL, "typed non-resurrection registry"),
        (INVENTORY, INVENTORY_REL, "operability admission inventory"),
        (STATUS, STATUS_REL, "production operability status"),
        (DRILL_WRITER, DRILL_WRITER_REL, "drill request writer"),
        (GEN_WRITER, GEN_WRITER_REL, "generation evidence writer"),
        (TYPED_WRITER, TYPED_WRITER_REL, "typed non-resurrection writer"),
        (BLOCKER_AUTHORITY, BLOCKER_AUTHORITY_REL, "OPS-P0-007 blocker authority"),
        (SELF, SELF_REL, "admission-chain validator"),
        (WORKFLOW, WORKFLOW_REL, "admission-chain workflow"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_module(path: Path, name: str):
    relative = repo_relative(path)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def validate_shared_registry(module: Any, registry: dict[str, Any], label: str) -> list[dict[str, Any]]:
    validator = getattr(module, "validate_registry_for_append", None)
    require(callable(validator), f"{label} shared registry validator missing")
    try:
        rows = validator(registry)
    except Exception as exc:
        fail_type = getattr(module, "Fail", None)
        if isinstance(fail_type, type) and isinstance(exc, fail_type):
            raise Fail(f"{label} registry authority invalid: {exc}") from exc
        raise
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), f"{label} shared registry rows invalid")
    return rows


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    preflight_contract = load(PREFLIGHT_CONTRACT)
    drill_contract = load(DRILL_CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    gen_contract = load(GEN_CONTRACT)
    gen_registry = load(GEN_REGISTRY)
    binding_contract = load(BINDING_CONTRACT)
    typed_contract = load(TYPED_CONTRACT)
    typed_registry = load(TYPED_REGISTRY)
    inventory = load(INVENTORY)
    status = load(STATUS)
    drill_writer = load_module(DRILL_WRITER, "memory_os_drill_writer_admission_chain")
    gen_writer = load_module(GEN_WRITER, "memory_os_generation_writer_admission_chain")
    typed_writer = load_module(TYPED_WRITER, "memory_os_typed_writer_admission_chain")
    blocker_authority = load_module(BLOCKER_AUTHORITY, "memory_os_backup_restore_blockers_admission_chain")

    require(contract.get("schemaVersion") == "memory-os-backup-restore-admission-chain-contract.v1", "chain contract schema drift")
    refs = {
        "drillPreflightContract": PREFLIGHT_CONTRACT,
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "generationEvidenceContract": GEN_CONTRACT,
        "generationEvidenceRegistry": GEN_REGISTRY,
        "generationBindingContract": BINDING_CONTRACT,
        "typedNonResurrectionContract": TYPED_CONTRACT,
        "typedNonResurrectionRegistry": TYPED_REGISTRY,
        "operabilityInventory": INVENTORY,
        "operabilityStatus": STATUS,
        "validator": SELF,
        "workflow": WORKFLOW,
    }
    for field, path in refs.items():
        expected = str(require_repo_file(path, f"chain artifact missing: {path}"))
        require(contract.get(field) == expected, f"chain ref drift: {field}")
    require_repo_file(DRILL_WRITER, "restore drill request writer authority missing")
    require_repo_file(GEN_WRITER, "generation evidence writer authority missing")
    require_repo_file(TYPED_WRITER, "typed non-resurrection writer authority missing")
    require_repo_file(BLOCKER_AUTHORITY, "canonical OPS-P0-007 blocker authority missing")

    drill_rows = validate_shared_registry(drill_writer, drill_registry, "drill request")
    gen_rows = validate_shared_registry(gen_writer, gen_registry, "generation evidence")
    typed_rows = validate_shared_registry(typed_writer, typed_registry, "typed non-resurrection")

    expected_chain = [
        "readOnlyDrillPreflight",
        "reviewedDrillRequest",
        "currentExecutableDrillRequestAtEvidenceAdmission",
        "drillRequestBoundGenerationEvidence",
        "generationBoundBackup",
        "generationBoundRestore",
        "preOverlayRecoveryGates",
        "typedNonResurrectionEightDomainCoverage",
        "finalProductionEquivalentRecoveryCandidate",
        "separateHumanProductionPromotionDecision",
    ]
    required_chain = contract.get("requiredChain")
    require(required_chain == expected_chain, "chain stage sequence drift")

    expected_invariants = {
        "preflightNeverCreatesMissingPrerequisites",
        "preflightReadyNeverCreatesDrillRequest",
        "preflightBlockedCannotHaveCurrentExecutableDrillRequest",
        "currentExecutableDrillRequestRequiresReadyExistingPreflightDecision",
        "generationEvidenceRequiresRegisteredDrillRequest",
        "generationEvidenceRequestSourceGenerationMustMatch",
        "generationEvidenceRequestRestoreTargetGenerationMustMatch",
        "generationEvidenceRequestRecoveryObjectiveMustMatch",
        "newEvidenceRequiresCurrentlyExecutableDrillRequest",
        "historicalEvidenceMayRemainAuditableAfterDrillRequestStales",
        "staleRequestEvidenceCannotRemainCurrentCandidate",
        "generationBoundBackupCountMustBeRederivedFromImmutableEvidence",
        "generationBoundRestoreCountMustBeRederivedFromImmutableEvidence",
        "generationBoundBackupCountMustMatchBindingAuthority",
        "generationBoundRestoreCountMustMatchBindingAuthority",
        "recoveryAggregateOrderingMustRemainMonotonic",
        "typedCompleteCountMustBeRederivedFromValidatedEightDomainEvidence",
        "genericNonResurrectionPassCannotCreateFinalCandidate",
        "finalCandidateRequiresCompleteTypedEightDomainCoverage",
        "finalCandidateRequiresCurrentApprovedRecoveryObjective",
        "finalCandidateRequiresMeasuredObjectivesToPass",
        "finalCandidateRequiresIndependentSecurityAndOperabilityReview",
        "finalCandidateRequiresIndependentEvidenceReview",
        "finalCandidateCannotCompleteHumanProductionPromotionReview",
        "finalCandidateCannotAuthorizeProductionPromotion",
        "humanProductionPromotionReviewRemainsSeparate",
        "planningRequestCannotExecuteRestore",
        "chainCannotDeriveProductionEvidence",
        "chainCannotDeriveProductionReady",
        "canonicalOpsP0007SixBlockersMustRemainUntilRealEvidenceExists",
    }
    invariants = contract.get("invariants")
    require(isinstance(invariants, dict), "chain invariants missing")
    require(set(invariants) == expected_invariants, "chain invariant key set drift")
    require(all(invariants[key] is True for key in expected_invariants), "chain invariants must remain fail-closed")

    preflight = preflight_contract.get("currentState")
    require(isinstance(preflight, dict), "preflight currentState missing")
    preflight_decision = preflight.get("preflightDecision")
    preflight_eligible = preflight.get("eligibleToSubmitReviewedDrillRequest")
    preflight_pair_count = preflight.get("eligibleDirectedSourceTargetPairCount")
    require(isinstance(preflight_decision, str) and preflight_decision, "preflight decision invalid")
    require(isinstance(preflight_eligible, bool), "preflight eligibility invalid")
    require(valid_count(preflight_pair_count), "preflight eligible pair count invalid")
    for field in ("reviewedDrillRequestCount", "currentExecutableDrillRequestCount"):
        require(valid_count(preflight.get(field)), f"preflight {field} must be a non-boolean count")
    require(all(preflight.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight may not create prerequisites, execute restore or promote production")
    require(preflight.get("productionDecision") == "NO_GO", "preflight production decision drift")

    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(valid_count(drill_count) and drill_count == len(drill_rows), "drill request count drift")
    require(valid_count(current_drill_count) and current_drill_count <= drill_count, "current drill request count invalid")
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

    gen_count = gen_registry.get("registeredEvidenceCount")
    bound_count = gen_registry.get("drillRequestBoundEvidenceCount")
    registry_backup_count = gen_registry.get("completeGenerationBoundBackupCount")
    registry_restore_count = gen_registry.get("completeGenerationBoundRestoreCount")
    candidate_count = gen_registry.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(gen_count) and gen_count == len(gen_rows), "generation evidence count drift")
    require(valid_count(bound_count) and bound_count == gen_count, "every generation evidence row must be drill-request-bound")
    for value, field in ((registry_backup_count, "backup"), (registry_restore_count, "restore"), (candidate_count, "candidate")):
        require(valid_count(value) and value <= gen_count, f"generation evidence {field} count invalid")
    require(candidate_count <= registry_restore_count <= registry_backup_count, "generation evidence recovery aggregate ordering drift")

    drill_ids = {row.get("requestId") for row in drill_rows if isinstance(row.get("requestId"), str)}
    require(len(drill_ids) == drill_count, "drill request IDs must be unique")
    candidate_ids: set[str] = set()
    derived_backup_count = 0
    derived_restore_count = 0
    for row in gen_rows:
        request_id = row.get("drillRequestId")
        require(request_id in drill_ids, f"generation evidence references missing drill request: {request_id}")
        if row.get("evidenceComplete") is True:
            derived_backup_count += 1
        if (
            row.get("evidenceComplete") is True
            and row.get("isolatedRestoreVerified") is True
            and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
        ):
            derived_restore_count += 1
        if gen_writer.candidate(row):
            evidence_id = row.get("evidenceId")
            require(isinstance(evidence_id, str), "candidate evidenceId invalid")
            candidate_ids.add(evidence_id)
    require(derived_backup_count == registry_backup_count, "generation-bound backup aggregate drift from revalidated immutable evidence rows")
    require(derived_restore_count == registry_restore_count, "generation-bound restore aggregate drift from revalidated immutable evidence rows")
    require(len(candidate_ids) == candidate_count, "candidate derivation/count drift")
    if current_drill_count == 0:
        require(candidate_count == 0, "candidate cannot survive without current executable drill request")

    typed_rules = typed_contract.get("candidateCoverageRule")
    require(isinstance(typed_rules, dict) and typed_rules.get("genericNonResurrectionPassAloneIsInsufficient") is True, "typed generic PASS bypass guard missing")
    require(typed_rules.get("everyProductionEquivalentRecoveryCandidateRequiresOneCompleteTypedRecord") is True, "typed candidate coverage rule missing")
    typed_count = typed_registry.get("registeredRecordCount")
    typed_complete_count = typed_registry.get("completeRecordCount")
    typed_covered_count = typed_registry.get("candidateCoveredCount")
    require(valid_count(typed_count) and typed_count == len(typed_rows), "typed record count drift")
    require(valid_count(typed_complete_count) and typed_complete_count <= typed_count, "typed complete count invalid")
    require(valid_count(typed_covered_count) and typed_covered_count <= typed_complete_count, "typed candidate coverage count invalid")
    complete_typed_ids: set[str] = set()
    derived_typed_complete_count = 0
    for row in typed_rows:
        if row.get("evidenceComplete") is True:
            derived_typed_complete_count += 1
            generation_evidence_id = row.get("generationEvidenceId")
            require(isinstance(generation_evidence_id, str), "complete typed generationEvidenceId invalid")
            complete_typed_ids.add(generation_evidence_id)
    require(derived_typed_complete_count == typed_complete_count, "typed complete aggregate drift from revalidated eight-domain records")
    require(candidate_ids.issubset(complete_typed_ids), "final candidate bypasses revalidated complete typed non-resurrection evidence")
    require(typed_covered_count == candidate_count, "typed candidate coverage count must equal final candidate count")

    binding_rules = binding_contract.get("promotionRules")
    binding_boundary = binding_contract.get("currentBoundary")
    require(isinstance(binding_rules, dict) and isinstance(binding_boundary, dict), "generation binding promotion authority missing")
    require(binding_rules.get("independentReviewRequired") is True, "generation binding independent review gate missing")
    require(binding_rules.get("backupCountMustBeRederivedFromImmutableEvidence") is True, "generation-bound backup rederivation gate missing")
    require(binding_rules.get("restoreCountMustBeRederivedFromImmutableEvidence") is True, "generation-bound restore rederivation gate missing")
    require(binding_rules.get("candidateCountMustBeRederivedFromCurrentExecutableReviewedEvidence") is True, "recovery candidate rederivation gate missing")
    require(binding_rules.get("recoveryCandidateAutomaticallyCompletesHumanProductionPromotionReview") is False, "candidate cannot complete human promotion review")
    require(binding_rules.get("recoveryCandidateAutomaticallyAuthorizesProductionPromotion") is False, "candidate cannot authorize production promotion")
    require(binding_rules.get("humanProductionPromotionReviewRemainsSeparate") is True, "human promotion review must remain separate")
    backup_count = binding_boundary.get("generationBoundBackupCount")
    restore_count = binding_boundary.get("generationBoundRestoreCount")
    binding_candidate_count = binding_boundary.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(backup_count), "generation-bound backup count invalid")
    require(valid_count(restore_count), "generation-bound restore count invalid")
    require(valid_count(binding_candidate_count), "generation binding candidate count invalid")
    require(backup_count == derived_backup_count, "generation binding backup count drift from revalidated immutable evidence")
    require(restore_count == derived_restore_count, "generation binding restore count drift from revalidated immutable evidence")
    require(binding_candidate_count == candidate_count, "generation binding candidate count drift")
    require(candidate_count <= restore_count <= backup_count <= gen_count, "recovery aggregate ordering drift")
    require(binding_boundary.get("independentReviewCompleted") is (candidate_count > 0), "generation binding independent review state drift")
    require(binding_boundary.get("humanProductionPromotionReviewCompleted") is False, "human production promotion review must remain unclaimed")
    require(binding_boundary.get("humanProductionPromotionAuthorized") is False, "human production promotion authorization must remain unclaimed")
    require(binding_boundary.get("productionEvidence") is False and binding_boundary.get("productionReady") is False and binding_boundary.get("productionDecision") == "NO_GO", "generation binding cannot promote production")

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
        "generationBoundBackupCount": backup_count,
        "generationBoundRestoreCount": restore_count,
        "completeTypedNonResurrectionRecordCount": typed_complete_count,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
        "independentEvidenceReviewCompleted": candidate_count > 0,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
    }
    chain_count_fields = {
        "preflightEligibleDirectedSourceTargetPairCount",
        "reviewedDrillRequestCount",
        "currentExecutableDrillRequestCount",
        "generationEvidenceCount",
        "drillRequestBoundGenerationEvidenceCount",
        "generationBoundBackupCount",
        "generationBoundRestoreCount",
        "completeTypedNonResurrectionRecordCount",
        "finalProductionEquivalentRecoveryCandidateCount",
    }
    for field in chain_count_fields:
        require(valid_count(chain_boundary.get(field)), f"chain boundary {field} must be a non-boolean count")
    chain_boolean_fields = {
        "preflightEligibleToSubmitReviewedDrillRequest",
        "independentEvidenceReviewCompleted",
        "humanProductionPromotionReviewCompleted",
        "humanProductionPromotionAuthorized",
    }
    for field in chain_boolean_fields:
        require(isinstance(chain_boundary.get(field), bool), f"chain boundary {field} must be boolean")
    for field, value in expected.items():
        require(chain_boundary.get(field) == value, f"chain boundary drift: {field}")
    require(chain_boundary.get("productionEvidence") is False and chain_boundary.get("productionReady") is False and chain_boundary.get("productionDecision") == "NO_GO", "chain cannot promote production")

    require(inventory.get("productionDecision") == "NO_GO" and inventory.get("productionEvidence") is False and inventory.get("productionReady") is False, "inventory production boundary drift")
    inventory_count_fields = {
        "backupRestoreEligibleDirectedPairCount",
        "reviewedBackupRestoreDrillRequestCount",
        "currentExecutableBackupRestoreDrillRequestCount",
    }
    for field in inventory_count_fields:
        require(valid_count(inventory.get(field)), f"inventory {field} must be a non-boolean count")
    require(inventory.get("backupRestoreDrillPreflightDecision") == preflight_decision, "inventory preflight decision drift")
    require(inventory.get("backupRestoreDrillPreflightEligible") is preflight_eligible, "inventory preflight eligibility drift")
    require(inventory.get("backupRestoreEligibleDirectedPairCount") == preflight_pair_count, "inventory preflight pair count drift")
    require(inventory.get("reviewedBackupRestoreDrillRequestCount") == drill_count, "inventory drill request count drift")
    require(inventory.get("currentExecutableBackupRestoreDrillRequestCount") == current_drill_count, "inventory current drill request count drift")
    require(inventory.get("backupRestoreIndependentEvidenceReviewCompleted") is (candidate_count > 0), "inventory independent evidence review drift")
    require(inventory.get("humanProductionPromotionReviewCompleted") is False, "inventory human production-promotion review must remain unclaimed")
    require(inventory.get("humanProductionPromotionAuthorized") is False, "inventory human production-promotion authorization must remain unclaimed")
    ops7 = next((row for row in inventory.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 inventory row missing")
    require(ops7.get("preflightDecision") == preflight_decision and ops7.get("preflightEligible") is preflight_eligible, "OPS-P0-007 preflight inventory drift")
    require(ops7.get("independentEvidenceReviewCompleted") is (candidate_count > 0), "OPS-P0-007 independent evidence review drift")
    require(ops7.get("humanProductionPromotionReviewCompleted") is False, "OPS-P0-007 human production-promotion review must remain unclaimed")
    require(ops7.get("humanProductionPromotionAuthorized") is False, "OPS-P0-007 human production-promotion authorization must remain unclaimed")
    require(ops7.get("productionEvidence") is False and ops7.get("productionReady") is False, "OPS-P0-007 inventory row cannot promote production")
    deps = ops7.get("dependencyCounts")
    require(isinstance(deps, dict), "OPS-P0-007 dependencyCounts missing")
    dependency_count_fields = {
        "productionEquivalentRecoveryCandidates",
        "generationBoundBackups",
        "generationBoundRestores",
        "reviewedRestoreDrillRequests",
        "currentExecutableRestoreDrillRequests",
        "eligibleDirectedRestorePairs",
    }
    for field in dependency_count_fields:
        require(valid_count(deps.get(field)), f"inventory dependency {field} must be a non-boolean count")
    require(deps.get("productionEquivalentRecoveryCandidates") == candidate_count, "inventory candidate dependency drift")
    require(deps.get("generationBoundBackups") == backup_count, "inventory generation-bound backup dependency drift")
    require(deps.get("generationBoundRestores") == restore_count, "inventory generation-bound restore dependency drift")
    require(deps.get("reviewedRestoreDrillRequests") == drill_count and deps.get("currentExecutableRestoreDrillRequests") == current_drill_count, "inventory drill request dependency drift")
    require(deps.get("eligibleDirectedRestorePairs") == preflight_pair_count, "inventory preflight pair dependency drift")

    require(status.get("productionDecision") == "NO_GO", "status production decision drift")
    status7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(status7, dict), "OPS-P0-007 status row missing")
    require(status7.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and status7.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    blocker_authority.require_canonical_gaps(status7.get("missingEvidence"), Fail)

    print("Memory OS backup/restore end-to-end admission chain PASS")
    print("canonical data/writer/blocker/workflow authority substitution accepted: false")
    print("shared drill/generation/typed append-only registry authority validated: true")
    print(f"preflight: {preflight_decision}")
    print(f"preflight eligible pairs: {preflight_pair_count}")
    print(f"reviewed/current drill requests: {drill_count}/{current_drill_count}")
    print(f"generation/drill-bound evidence: {gen_count}/{bound_count}")
    print(f"generation-bound backup/restore: {backup_count}/{restore_count}")
    print("backup/restore aggregates re-derived from immutable generation evidence: true")
    print(f"revalidated complete typed non-resurrection records: {typed_complete_count}")
    print(f"final production-equivalent recovery candidates: {candidate_count}")
    print("boolean chain/inventory aggregate counts accepted: false")
    print("chain review/promotion authority fields strictly typed boolean: true")
    print("inventory review/promotion authority bound to candidate and human separation: true")
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
