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
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
CHAIN_CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
GEN_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"
OBJECTIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-recovery-objectives.py"
DRILL_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
GEN_BLOCKER = "TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS"
OBJECTIVE_BLOCKER = "CURRENT_APPROVED_RECOVERY_OBJECTIVE"
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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_restore_preflight", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(path: Path, name: str) -> None:
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{name} validator failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}")


def derive_state(generations: dict[str, Any], objectives: dict[str, Any], drill_registry: dict[str, Any]) -> dict[str, Any]:
    rows = generations.get("generations")
    generation_count = generations.get("registeredGenerationCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation registry rows invalid")
    require(isinstance(generation_count, int) and generation_count == len(rows), "generation registry count drift")
    ids = [row.get("generationId") for row in rows]
    require(all(isinstance(value, str) and value for value in ids) and len(set(ids)) == len(ids), "generation IDs invalid or duplicated")

    writer = load_generation_writer()
    eligibility_by_id: dict[str, bool] = {}
    for row in rows:
        generation_id = row.get("generationId")
        try:
            eligible = writer.validate_record(row)
        except Exception as exc:
            raise Fail(f"generation semantic validation failed for {generation_id}: {exc}") from exc
        require(isinstance(eligible, bool), "generation semantic eligibility predicate invalid")
        eligibility_by_id[generation_id] = eligible

    superseded_ids = {row.get("supersedesGenerationId") for row in rows if isinstance(row.get("supersedesGenerationId"), str)}
    unsuperseded = [row for row in rows if row.get("generationId") not in superseded_ids]
    preflight_eligible = [row for row in rows if eligibility_by_id.get(row.get("generationId")) is True]
    unsuperseded_preflight_eligible = [row for row in unsuperseded if eligibility_by_id.get(row.get("generationId")) is True]
    environments = {
        row.get("environmentId")
        for row in unsuperseded_preflight_eligible
        if isinstance(row.get("environmentId"), str) and row.get("environmentId")
    }
    pair_count = sum(
        1
        for source in unsuperseded_preflight_eligible
        for target in unsuperseded_preflight_eligible
        if source.get("generationId") != target.get("generationId")
        and source.get("environmentId") != target.get("environmentId")
    )

    objective_rows = objectives.get("records")
    objective_count = objectives.get("approvedObjectiveCount")
    current_objective_id = objectives.get("currentObjectiveId")
    require(isinstance(objective_rows, list) and all(isinstance(row, dict) for row in objective_rows), "recovery objective rows invalid")
    require(isinstance(objective_count, int) and objective_count == len(objective_rows), "recovery objective count drift")
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
    require(isinstance(request_count, int) and request_count == len(requests), "drill request count drift")
    require(isinstance(current_request_count, int) and 0 <= current_request_count <= request_count, "current executable drill request count invalid")

    pair_available = pair_count > 0
    blocking_prerequisites: list[str] = []
    if not pair_available:
        blocking_prerequisites.append(GEN_BLOCKER)
    if not current_objective_available:
        blocking_prerequisites.append(OBJECTIVE_BLOCKER)
    eligible = len(blocking_prerequisites) == 0

    if not pair_available:
        decision = "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS"
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
        "preflightEligibleGenerationCount": len(preflight_eligible),
        "unsupersededGenerationCount": len(unsuperseded),
        "unsupersededPreflightEligibleGenerationCount": len(unsuperseded_preflight_eligible),
        "distinctUnsupersededPreflightEligibleEnvironmentCount": len(environments),
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
        "recoveryObjectivesRegistry": OBJECTIVES,
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "admissionChainContract": CHAIN_CONTRACT,
        "validator": Path("scripts/validate-memory-os-backup-restore-drill-preflight.py"),
        "reconcile": Path("scripts/reconcile-memory-os-backup-restore-drill-preflight.py"),
        "workflow": Path(".github/workflows/backup-restore-drill-preflight.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
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
    decisions = contract.get("decisionStates")
    expected_decisions = {
        "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS",
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
    for field, value in state.items():
        require(canonical.get(field) == value, f"preflight state drift: {field}")
    blockers = canonical.get("blockingPrerequisites")
    blocker_count = canonical.get("blockingPrerequisiteCount")
    require(isinstance(blockers, list) and len(blockers) == len(set(blockers)), "preflight blockers invalid/duplicated")
    require(all(blocker in blocker_kinds for blocker in blockers), "preflight blocker outside canonical kind set")
    require(isinstance(blocker_count, int) and blocker_count == len(blockers), "preflight blocker count drift")
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
