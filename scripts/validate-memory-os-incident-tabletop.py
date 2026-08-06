#!/usr/bin/env python3
"""Fail-closed validation for incident tabletop plans and exercise evidence."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/incident-tabletop-record-contract.v1.json"
INCIDENT_POLICY_PATH = ROOT / "contracts/operations/incident-response-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
TABLETOP_REFS = {
    "contracts/operations/incident-tabletop-record-contract.v1.json",
    "docs/fixtures/memory-os-operability/incident-tabletop-plan.v1.json",
    "scripts/validate-memory-os-incident-tabletop.py",
}
EXECUTION_FIELDS = (
    "participants",
    "timeline",
    "decisions",
    "verificationResults",
    "observedGaps",
    "remediationItems",
    "evidenceRefs",
    "reviewers",
)


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def unique_strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    if not allow_empty:
        require(value, f"{field} must not be empty")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def parse_time(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value, f"{field} must be an RFC3339 timestamp")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationFailure(f"{field} must be an RFC3339 timestamp") from exc


def scenario_map(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    drills = policy.get("requiredDrillScenarios")
    require(isinstance(drills, list), "incident policy requiredDrillScenarios must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in drills:
        require(isinstance(item, dict), "incident drill entries must be objects")
        drill_id = item.get("id")
        require(isinstance(drill_id, str) and drill_id, "incident drill id is required")
        require(drill_id not in result, f"duplicate incident drill id: {drill_id}")
        result[drill_id] = item
    return result


def validate_planned(exercise: dict[str, Any], exercise_id: str) -> None:
    require(exercise.get("result") == "NOT_RUN",
            f"{exercise_id}: PLANNED exercise result must be NOT_RUN")
    require(exercise.get("startedAt") is None and exercise.get("completedAt") is None,
            f"{exercise_id}: PLANNED exercise must not carry execution timestamps")
    require(exercise.get("facilitator") == "UNASSIGNED",
            f"{exercise_id}: PLANNED template facilitator must remain UNASSIGNED")
    for field in EXECUTION_FIELDS:
        value = exercise.get(field)
        require(value == [], f"{exercise_id}: PLANNED {field} must be empty")


def validate_completed(
    exercise: dict[str, Any],
    exercise_id: str,
    contract: dict[str, Any],
) -> None:
    require(exercise.get("result") in {"PASS", "FAIL", "PARTIAL"},
            f"{exercise_id}: COMPLETED result must be PASS, FAIL or PARTIAL")
    started = parse_time(exercise.get("startedAt"), f"{exercise_id}.startedAt")
    completed = parse_time(exercise.get("completedAt"), f"{exercise_id}.completedAt")
    require(completed >= started, f"{exercise_id}: completedAt precedes startedAt")
    require(exercise.get("facilitator") not in {None, "", "UNASSIGNED"},
            f"{exercise_id}: COMPLETED exercise requires a facilitator")

    completed_non_empty = contract["recordFields"]["completedNonEmpty"]
    for field in completed_non_empty:
        value = exercise.get(field)
        require(isinstance(value, list) and value,
                f"{exercise_id}: COMPLETED {field} must be non-empty")

    injects = exercise["plannedInjects"]
    timeline = exercise["timeline"]
    observed_inject_sequences = {
        item.get("injectSequence")
        for item in timeline
        if isinstance(item, dict) and item.get("injectSequence") is not None
    }
    expected_sequences = {item["sequence"] for item in injects}
    require(expected_sequences <= observed_inject_sequences,
            f"{exercise_id}: every inject requires an observed timeline response")

    decisions = exercise["decisions"]
    decision_types = {
        item.get("type")
        for item in decisions
        if isinstance(item, dict)
    }
    for required_type in ("SEVERITY", "CONTAINMENT", "RECOVERY"):
        require(required_type in decision_types,
                f"{exercise_id}: missing {required_type} decision")

    verification = exercise["verificationResults"]
    require(any(
        isinstance(item, dict)
        and item.get("independent") is True
        and item.get("result") in {"PASS", "FAIL", "PARTIAL"}
        for item in verification
    ), f"{exercise_id}: independent verification is required")

    remediation = exercise["remediationItems"]
    remediation_gap_ids = {
        item.get("gapId")
        for item in remediation
        if isinstance(item, dict)
        and item.get("owner") not in {None, "", "UNASSIGNED"}
        and item.get("targetDate") not in {None, ""}
    }
    for gap in exercise["observedGaps"]:
        require(isinstance(gap, dict) and isinstance(gap.get("gapId"), str),
                f"{exercise_id}: observed gap requires gapId")
        require(gap["gapId"] in remediation_gap_ids,
                f"{exercise_id}: gap {gap['gapId']} lacks owned remediation")


def main() -> int:
    contract = load(CONTRACT_PATH)
    policy = load(INCIDENT_POLICY_PATH)
    plan_path = ROOT / contract.get("planPath", "")
    plan = load(plan_path)

    require(contract.get("schemaVersion") == "memory-os-incident-tabletop-record-contract.v1",
            "unsupported tabletop record contract schemaVersion")
    require(contract.get("incidentPolicyRef") == INCIDENT_POLICY_PATH.relative_to(ROOT).as_posix(),
            "incidentPolicyRef drift")
    require(contract.get("validator") == "scripts/validate-memory-os-incident-tabletop.py",
            "tabletop validator path drift")
    require(contract.get("planPath") == "docs/fixtures/memory-os-operability/incident-tabletop-plan.v1.json",
            "tabletop plan path drift")

    allowed_statuses = set(unique_strings(contract.get("allowedStatuses"), "allowedStatuses"))
    allowed_results = set(unique_strings(contract.get("allowedResults"), "allowedResults"))
    require(allowed_statuses == {"PLANNED", "IN_PROGRESS", "COMPLETED", "ABORTED"},
            "allowedStatuses drift")
    require(allowed_results == {"NOT_RUN", "PASS", "FAIL", "PARTIAL", "ABORTED"},
            "allowedResults drift")

    policy_scenarios = scenario_map(policy)
    required_ids = set(unique_strings(contract.get("requiredScenarioIds"), "requiredScenarioIds"))
    require(required_ids == set(policy_scenarios),
            "tabletop requiredScenarioIds differ from incident policy")

    record_fields = contract.get("recordFields")
    require(isinstance(record_fields, dict), "recordFields must be an object")
    always_required = set(unique_strings(record_fields.get("alwaysRequired"),
                                         "recordFields.alwaysRequired"))
    completed_non_empty = set(unique_strings(record_fields.get("completedNonEmpty"),
                                             "recordFields.completedNonEmpty"))
    require(completed_non_empty <= always_required,
            "completedNonEmpty must be a subset of alwaysRequired")

    completion = contract.get("completionRules")
    require(isinstance(completion, dict), "completionRules must be an object")
    for rule in (
        "startedAtAndCompletedAtRequired",
        "completedAtMustNotPrecedeStartedAt",
        "resultCannotBeNotRun",
        "everyInjectRequiresObservedResponse",
        "severityDecisionRequired",
        "containmentDecisionRequired",
        "recoveryDecisionRequired",
        "independentVerificationRequired",
        "eachGapRequiresOwnedRemediation",
        "secretsAndPersonalContentForbidden",
        "appendOnlyEvidenceRequired",
    ):
        require(completion.get(rule) is True, f"completionRules.{rule} must be true")

    privacy = contract.get("privacyRules")
    require(isinstance(privacy, dict), "privacyRules must be an object")
    require(privacy.get("privacyClass") == "operational_sensitive_no_secrets",
            "tabletop privacy class drift")
    for rule in (
        "rawTokensForbidden",
        "passwordsAndPrivateKeysForbidden",
        "rawDatabaseURLsForbidden",
        "unnecessaryPersonalContentForbidden",
        "factsHypothesesOpinionsSeparated",
    ):
        require(privacy.get(rule) is True, f"privacyRules.{rule} must be true")

    require(plan.get("schemaVersion") == "memory-os-incident-tabletop-plan.v1",
            "tabletop plan schemaVersion drift")
    require(plan.get("productionEvidence") is False,
            "planned tabletop records cannot claim production evidence")
    parse_time(plan.get("generatedAt"), "plan.generatedAt")

    exercises = plan.get("exercises")
    require(isinstance(exercises, list), "plan exercises must be a list")
    exercise_map: dict[str, dict[str, Any]] = {}
    scenario_ids: set[str] = set()
    completed_count = 0
    for exercise in exercises:
        require(isinstance(exercise, dict), "exercise entries must be objects")
        missing = always_required - set(exercise)
        require(not missing, f"exercise missing fields: {sorted(missing)}")

        exercise_id = exercise.get("exerciseId")
        scenario_id = exercise.get("scenarioId")
        require(isinstance(exercise_id, str) and exercise_id,
                "exerciseId is required")
        require(exercise_id not in exercise_map, f"duplicate exerciseId: {exercise_id}")
        exercise_map[exercise_id] = exercise
        require(isinstance(scenario_id, str) and scenario_id in required_ids,
                f"{exercise_id}: unknown scenarioId {scenario_id!r}")
        require(scenario_id not in scenario_ids,
                f"more than one active plan for scenarioId: {scenario_id}")
        scenario_ids.add(scenario_id)

        status = exercise.get("status")
        result = exercise.get("result")
        require(status in allowed_statuses, f"{exercise_id}: invalid status {status!r}")
        require(result in allowed_results, f"{exercise_id}: invalid result {result!r}")
        require(exercise.get("plannedSeverity") == policy_scenarios[scenario_id]["expectedSeverity"],
                f"{exercise_id}: plannedSeverity differs from incident policy")
        require(isinstance(exercise.get("objective"), str) and exercise["objective"].strip(),
                f"{exercise_id}: objective is required")
        unique_strings(exercise.get("scope"), f"{exercise_id}.scope")
        unique_strings(exercise.get("assumptions"), f"{exercise_id}.assumptions")
        unique_strings(exercise.get("safetyConstraints"), f"{exercise_id}.safetyConstraints")
        require(isinstance(exercise.get("openRisks"), list),
                f"{exercise_id}.openRisks must be a list")

        injects = exercise.get("plannedInjects")
        require(isinstance(injects, list) and len(injects) >= 3,
                f"{exercise_id}: at least three planned injects are required")
        sequences: list[int] = []
        for inject in injects:
            require(isinstance(inject, dict), f"{exercise_id}: injects must be objects")
            sequence = inject.get("sequence")
            require(isinstance(sequence, int) and not isinstance(sequence, bool) and sequence > 0,
                    f"{exercise_id}: inject sequence must be a positive integer")
            sequences.append(sequence)
            require(isinstance(inject.get("inject"), str) and inject["inject"].strip(),
                    f"{exercise_id}: inject text is required")
            require(isinstance(inject.get("expectedDecision"), str)
                    and inject["expectedDecision"].strip(),
                    f"{exercise_id}: expectedDecision is required")
        require(sequences == list(range(1, len(sequences) + 1)),
                f"{exercise_id}: inject sequences must be contiguous from 1")

        if status == "PLANNED":
            validate_planned(exercise, exercise_id)
        elif status == "COMPLETED":
            completed_count += 1
            validate_completed(exercise, exercise_id, contract)
        elif status == "ABORTED":
            require(result == "ABORTED", f"{exercise_id}: ABORTED status requires ABORTED result")
            parse_time(exercise.get("startedAt"), f"{exercise_id}.startedAt")
            require(exercise.get("completedAt") is not None,
                    f"{exercise_id}: ABORTED exercise requires completedAt")
            require(isinstance(exercise.get("observedGaps"), list)
                    and exercise["observedGaps"],
                    f"{exercise_id}: ABORTED exercise must record why")
        else:
            require(result == "NOT_RUN",
                    f"{exercise_id}: IN_PROGRESS result must remain NOT_RUN")
            parse_time(exercise.get("startedAt"), f"{exercise_id}.startedAt")
            require(exercise.get("completedAt") is None,
                    f"{exercise_id}: IN_PROGRESS completedAt must be null")

    require(scenario_ids == required_ids,
            f"tabletop plan coverage mismatch: missing={sorted(required_ids - scenario_ids)}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "tabletop readiness must be an object")
    require(readiness.get("recordContractDefined") is True,
            "recordContractDefined must be true")
    require(readiness.get("allRequiredScenariosPlanned") is True,
            "allRequiredScenariosPlanned must be true")
    require(readiness.get("completedScenarioCount") == completed_count,
            "completedScenarioCount does not match plan records")
    require(readiness.get("allRequiredScenariosCompleted") is (completed_count == len(required_ids)),
            "allRequiredScenariosCompleted does not match plan records")
    require(readiness.get("productionRecoveryDrillCompleted") is False,
            "tabletop records cannot claim a production recovery drill")
    require(readiness.get("ready") is False,
            "tabletop contract alone cannot be READY")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "tabletop planning cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-002"]
    require(len(matches) == 1, "OPS-P0-002 must exist exactly once")
    area = matches[0]
    refs = area.get("evidenceRefs")
    require(isinstance(refs, list), "OPS-P0-002 evidenceRefs must be a list")
    missing_refs = TABLETOP_REFS - set(refs)
    require(not missing_refs,
            f"OPS-P0-002 omits tabletop planning evidence: {sorted(missing_refs)}")
    if completed_count < len(required_ids):
        require(area.get("status") != "READY",
                "OPS-P0-002 cannot be READY before every required tabletop is completed")
        missing_evidence = area.get("missingEvidence")
        require(isinstance(missing_evidence, list)
                and any("completed tabletop" in item for item in missing_evidence),
                "OPS-P0-002 must retain the completed tabletop evidence gap")

    print("Memory OS incident tabletop validation PASS")
    print(f"planned scenarios: {len(exercises)}")
    print(f"completed scenarios: {completed_count}")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"INCIDENT TABLETOP VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
