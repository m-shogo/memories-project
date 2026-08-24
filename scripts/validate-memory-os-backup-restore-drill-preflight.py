#!/usr/bin/env python3
"""Validate read-only production-equivalent backup/restore drill preflight authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
CHAIN_CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
GEN_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"
OBJECTIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-recovery-objectives.py"
DRILL_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py"
GEN_BLOCKER = "TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS"
OBJECTIVE_BLOCKER = "CURRENT_APPROVED_RECOVERY_OBJECTIVE"
GEN_BLOCKED_DECISION = "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS"
GEN_BLOCKER_SEMANTICS = {
    "requiresRegisteredGeneration": True,
    "requiresUnsupersededGeneration": True,
    "requiresSemanticPreflightEligibility": True,
    "requiresDistinctEnvironmentId": True,
    "minimumEnvironmentGenerationCount": 2,
}
OBJECTIVE_BLOCKER_SEMANTICS = {
    "requiresCurrentApprovedRecoveryObjective": True,
}
STATE_FIELDS = {
    "registeredGenerationCount",
    "preflightEligibleGenerationCount",
    "unsupersededGenerationCount",
    "unsupersededPreflightEligibleGenerationCount",
    "distinctUnsupersededPreflightEligibleEnvironmentCount",
    "eligibleDirectedSourceTargetPairCount",
    "approvedRecoveryObjectiveCount",
    "currentObjectiveId",
    "reviewedDrillRequestCount",
    "currentExecutableDrillRequestCount",
    "blockingPrerequisites",
    "blockingPrerequisiteCount",
    "eligibleToSubmitReviewedDrillRequest",
    "preflightDecision",
    "requestCreated",
    "backupExecuted",
    "restoreExecuted",
    "productionTrafficChanged",
    "productionEvidence",
    "productionReady",
    "productionDecision",
}
STATE_COUNT_FIELDS = {
    "registeredGenerationCount",
    "preflightEligibleGenerationCount",
    "unsupersededGenerationCount",
    "unsupersededPreflightEligibleGenerationCount",
    "distinctUnsupersededPreflightEligibleEnvironmentCount",
    "eligibleDirectedSourceTargetPairCount",
    "approvedRecoveryObjectiveCount",
    "reviewedDrillRequestCount",
    "currentExecutableDrillRequestCount",
    "blockingPrerequisiteCount",
}
READINESS_FIELDS = {
    "contractDefined",
    "validatorImplemented",
    "reconcileImplemented",
    "automaticWorkflowImplemented",
    "twoDistinctUnsupersededPreflightEligibleEnvironmentsAvailable",
    "currentRecoveryObjectiveAvailable",
    "eligibleSourceTargetPairAvailable",
    "reviewedDrillRequestSubmissionEligible",
    "currentExecutableDrillRequestAvailable",
    "drillExecuted",
    "productionReady",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Fail(f"artifact path escapes repository root: {path}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_eligibility_helper():
    try:
        lexical = ELIGIBILITY_HELPER.relative_to(ROOT)
        resolved = ELIGIBILITY_HELPER.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("shared environment generation eligibility authority missing or escapes repository") from exc
    require(
        lexical == ELIGIBILITY_HELPER_REL
        and resolved == ELIGIBILITY_HELPER_REL
        and ELIGIBILITY_HELPER.is_file()
        and not ELIGIBILITY_HELPER.is_symlink(),
        "shared environment generation eligibility authority drift",
    )
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_for_restore_preflight", ELIGIBILITY_HELPER)
    require(spec is not None and spec.loader is not None, "cannot load shared environment generation eligibility authority")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(path: Path, name: str) -> None:
    repo_relative(path)
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{name} validator failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}")


def derive_state(generations: dict[str, Any], objectives: dict[str, Any], drill_registry: dict[str, Any]) -> dict[str, Any]:
    helper = load_eligibility_helper()
    try:
        semantic = helper.derive_registry(generations)
    except helper.Fail as exc:
        raise Fail(f"shared generation semantic derivation failed: {exc}") from exc
    generation_count = semantic.get("registeredGenerationCount")
    preflight_eligible_count = semantic.get("preflightEligibleGenerationCount")
    unsuperseded_count = semantic.get("unsupersededGenerationCount")
    unsuperseded_preflight_eligible_count = semantic.get("unsupersededPreflightEligibleGenerationCount")
    distinct_eligible_environment_count = semantic.get("distinctPreflightEligibleEnvironmentCount")
    pair_count = semantic.get("eligibleDirectedPairCount")
    for value, field in (
        (generation_count, "registeredGenerationCount"),
        (preflight_eligible_count, "preflightEligibleGenerationCount"),
        (unsuperseded_count, "unsupersededGenerationCount"),
        (unsuperseded_preflight_eligible_count, "unsupersededPreflightEligibleGenerationCount"),
        (distinct_eligible_environment_count, "distinctPreflightEligibleEnvironmentCount"),
        (pair_count, "eligibleDirectedPairCount"),
    ):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"shared semantic derivation {field} invalid")
    require(preflight_eligible_count <= generation_count, "shared semantic eligible count exceeds registered generations")
    require(unsuperseded_preflight_eligible_count <= unsuperseded_count, "shared unsuperseded semantic eligible count drift")
    require(distinct_eligible_environment_count <= unsuperseded_preflight_eligible_count, "shared distinct eligible environment count drift")
    if distinct_eligible_environment_count < 2:
        require(pair_count == 0, "shared eligible directed pair requires two distinct semantic environments")

    objective_rows = objectives.get("records")
    objective_count = objectives.get("approvedObjectiveCount")
    current_objective_id = objectives.get("currentObjectiveId")
    require(isinstance(objective_rows, list) and all(isinstance(row, dict) for row in objective_rows), "recovery objective rows invalid")
    require(isinstance(objective_count, int) and not isinstance(objective_count, bool) and objective_count == len(objective_rows), "recovery objective count drift")
    if objective_count == 0:
        require(current_objective_id is None, "empty recovery objective registry cannot have currentObjectiveId")
        current_objective_available = False
    else:
        require(isinstance(current_objective_id, str) and current_objective_id, "currentObjectiveId required")
        require(sum(1 for row in objective_rows if row.get("objectiveId") == current_objective_id) == 1, "current recovery objective is not uniquely registered")
        current_objective_available = True

    requests = drill_registry.get("requests")
    request_count = drill_registry.get("registeredRequestCount")
    current_request_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "drill request rows invalid")
    require(isinstance(request_count, int) and not isinstance(request_count, bool) and request_count == len(requests), "drill request count drift")
    require(isinstance(current_request_count, int) and not isinstance(current_request_count, bool) and 0 <= current_request_count <= request_count, "current executable drill request count invalid")

    pair_available = pair_count > 0
    blocking_prerequisites: list[str] = []
    if not pair_available:
        blocking_prerequisites.append(GEN_BLOCKER)
    if not current_objective_available:
        blocking_prerequisites.append(OBJECTIVE_BLOCKER)
    eligible = len(blocking_prerequisites) == 0

    if not pair_available:
        decision = GEN_BLOCKED_DECISION
    elif not current_objective_available:
        decision = "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE"
    elif current_request_count > 0:
        decision = "READY_EXISTING_EXECUTABLE_DRILL_REQUEST"
    else:
        decision = "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION"
    if not eligible:
        require(current_request_count == 0, "executable drill request cannot survive when preflight prerequisites are absent")

    return {
        "registeredGenerationCount": generation_count,
        "preflightEligibleGenerationCount": preflight_eligible_count,
        "unsupersededGenerationCount": unsuperseded_count,
        "unsupersededPreflightEligibleGenerationCount": unsuperseded_preflight_eligible_count,
        "distinctUnsupersededPreflightEligibleEnvironmentCount": distinct_eligible_environment_count,
        "eligibleDirectedSourceTargetPairCount": pair_count,
        "approvedRecoveryObjectiveCount": objective_count,
        "currentObjectiveId": current_objective_id,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "blockingPrerequisites": blocking_prerequisites,
        "blockingPrerequisiteCount": len(blocking_prerequisites),
        "eligibleToSubmitReviewedDrillRequest": eligible,
        "preflightDecision": decision,
    }


def main() -> int:
    contract = load(CONTRACT)
    generation_contract = load(GEN_CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_contract = load(DRILL_CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    chain = load(CHAIN_CONTRACT)

    require(contract.get("schemaVersion") == "memory-os-backup-restore-drill-preflight-contract.v1", "preflight contract schema drift")
    refs = {
        "environmentGenerationContract": GEN_CONTRACT,
        "environmentGenerationRegistry": GEN_REGISTRY,
        "semanticEligibilityHelper": ELIGIBILITY_HELPER,
        "recoveryObjectivesRegistry": OBJECTIVES,
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "admissionChainContract": CHAIN_CONTRACT,
        "validator": Path("scripts/validate-memory-os-backup-restore-drill-preflight.py"),
        "negativeAdmissionValidator": NEGATIVE_VALIDATOR,
        "reconcile": Path("scripts/reconcile-memory-os-backup-restore-drill-preflight.py"),
        "workflow": Path(".github/workflows/backup-restore-drill-preflight.yml"),
    }
    for field, path in refs.items():
        expected = str(repo_relative(path)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"preflight ref drift: {field}")
        require((ROOT / expected).is_file(), f"preflight artifact missing: {expected}")

    generation_bindings = generation_contract.get("bindingRules")
    require(isinstance(generation_bindings, dict), "environment generation binding rules missing")
    require(generation_bindings.get("registrationDoesNotImplyPreflightEligibility") is True, "generation registration/preflight separation rule missing")
    require(generation_bindings.get("preflightEligibilityRequiresValidatedEquivalentDependenciesAndIndependentReview") is True, "generation semantic preflight eligibility rule missing")

    rules = contract.get("preflightRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "preflight rules must remain fail-closed")
    require(rules.get("allMissingPrerequisitesMustBeEnumerated") is True, "preflight blocker enumeration rule missing")
    require(rules.get("onlySemanticallyPreflightEligibleGenerationsMayFormPairs") is True, "semantic generation eligibility rule missing")
    blocker_kinds = contract.get("blockingPrerequisiteKinds")
    require(isinstance(blocker_kinds, list) and blocker_kinds == [GEN_BLOCKER, OBJECTIVE_BLOCKER], "preflight blocker kind/order drift")
    blocker_semantics = contract.get("blockingPrerequisiteSemantics")
    require(isinstance(blocker_semantics, dict) and set(blocker_semantics) == {GEN_BLOCKER, OBJECTIVE_BLOCKER}, "preflight blocker semantics key drift")
    require(blocker_semantics.get(GEN_BLOCKER) == GEN_BLOCKER_SEMANTICS, "generation blocker semantic authority drift")
    require(blocker_semantics.get(OBJECTIVE_BLOCKER) == OBJECTIVE_BLOCKER_SEMANTICS, "objective blocker semantic authority drift")
    decisions = contract.get("decisionStates")
    expected_decisions = {
        GEN_BLOCKED_DECISION,
        "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE",
        "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION",
        "READY_EXISTING_EXECUTABLE_DRILL_REQUEST",
    }
    require(isinstance(decisions, list) and set(decisions) == expected_decisions and len(decisions) == len(expected_decisions), "preflight decision state drift")

    require(generations.get("appendOnly") is True and generations.get("productionEvidence") is False, "generation registry boundary drift")
    require(objectives.get("appendOnly") is True and objectives.get("productionEvidence") is False and objectives.get("productionReady") is False, "recovery objective boundary drift")
    require(drill_registry.get("appendOnly") is True and drill_registry.get("productionEvidence") is False and drill_registry.get("productionReady") is False, "drill request registry boundary drift")
    execution = drill_contract.get("executionBoundary")
    require(isinstance(execution, dict) and execution.get("planningAuthorityOnly") is True and execution.get("requestAloneMayExecuteDrill") is False, "drill request execution boundary drift")
    require(chain.get("currentBoundary", {}).get("productionEvidence") is False and chain.get("currentBoundary", {}).get("productionReady") is False, "admission chain production boundary drift")

    state = derive_state(generations, objectives, drill_registry)
    canonical = contract.get("currentState")
    readiness = contract.get("readiness")
    require(isinstance(canonical, dict) and isinstance(readiness, dict), "preflight authority state missing")
    require(set(canonical) == STATE_FIELDS, "preflight currentState field drift")
    require(set(readiness) == READINESS_FIELDS, "preflight readiness field drift")
    for field in STATE_COUNT_FIELDS:
        value = canonical.get(field)
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"preflight currentState {field} must be a non-boolean count")
    for field, value in state.items():
        require(canonical.get(field) == value, f"preflight state drift: {field}")
    blockers = canonical.get("blockingPrerequisites")
    blocker_count = canonical.get("blockingPrerequisiteCount")
    require(isinstance(blockers, list) and len(blockers) == len(set(blockers)), "preflight blockers invalid/duplicated")
    require(all(blocker in blocker_kinds for blocker in blockers), "preflight blocker outside canonical kind set")
    require(isinstance(blocker_count, int) and not isinstance(blocker_count, bool) and blocker_count == len(blockers), "preflight blocker count drift")
    require((blocker_count == 0) is state["eligibleToSubmitReviewedDrillRequest"], "preflight blocker/eligibility contradiction")
    for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady"):
        require(canonical.get(field) is False, f"preflight must keep {field}=false")
    require(canonical.get("productionDecision") == "NO_GO", "preflight production decision must remain NO_GO")

    pair_available = state["eligibleDirectedSourceTargetPairCount"] > 0
    objective_available = state["currentObjectiveId"] is not None
    require(readiness.get("twoDistinctUnsupersededPreflightEligibleEnvironmentsAvailable") is pair_available, "preflight semantic generation readiness drift")
    require(readiness.get("currentRecoveryObjectiveAvailable") is objective_available, "preflight objective readiness drift")
    require(readiness.get("eligibleSourceTargetPairAvailable") is pair_available, "preflight pair readiness drift")
    require(readiness.get("reviewedDrillRequestSubmissionEligible") is state["eligibleToSubmitReviewedDrillRequest"], "preflight submission readiness drift")
    require(readiness.get("currentExecutableDrillRequestAvailable") is (state["currentExecutableDrillRequestCount"] > 0), "preflight current request readiness drift")
    require(readiness.get("drillExecuted") is False and readiness.get("productionReady") is False, "preflight cannot claim execution or production readiness")

    run_validator(GEN_VALIDATOR, "environment generation")
    run_validator(OBJECTIVE_VALIDATOR, "recovery objectives")
    run_validator(DRILL_VALIDATOR, "restore drill request")

    print("Memory OS production-equivalent restore drill preflight PASS")
    print(f"registered/preflight-eligible generations: {state['registeredGenerationCount']}/{state['preflightEligibleGenerationCount']}")
    print(f"unsuperseded/preflight-eligible unsuperseded generations: {state['unsupersededGenerationCount']}/{state['unsupersededPreflightEligibleGenerationCount']}")
    print(f"distinct eligible unsuperseded environments: {state['distinctUnsupersededPreflightEligibleEnvironmentCount']}")
    print(f"eligible directed source-target pairs: {state['eligibleDirectedSourceTargetPairCount']}")
    print(f"approved recovery objectives: {state['approvedRecoveryObjectiveCount']}")
    print(f"reviewed/current drill requests: {state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}")
    print(f"blocking prerequisites ({state['blockingPrerequisiteCount']}): {','.join(state['blockingPrerequisites']) if state['blockingPrerequisites'] else 'none'}")
    print(f"preflight decision: {state['preflightDecision']}")
    print("semantic generation authority shared with downstream admission: true")
    print("registered generation blocker semantically requires eligible distinct environments: true")
    print("boolean registry/current-state counts accepted: false")
    print("automatic prerequisite/request creation: false")
    print("restore executed: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
