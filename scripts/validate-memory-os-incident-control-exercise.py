#!/usr/bin/env python3
"""Fail-closed validation for automated incident control exercise evidence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SCENARIOS = {
    "tenant-isolation-breach",
    "postgresql-unavailable-during-preview-commit",
    "object-store-unavailable-during-import",
    "migration-or-version-incompatibility",
    "restore-non-resurrection-failure",
    "parser-worker-compromise-or-stall",
}


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


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def validate_result(result: dict[str, Any], contract: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") ==
            "memory-os-incident-control-exercise-results.v1",
            "incident exercise result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(source_is_ancestor(commit_sha),
            "incident exercise result SHA is not an ancestor of current HEAD")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"incident exercise SHA {commit_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "incident exercise environment missing")
    require(environment.get("mode") == "GITHUB_ACTIONS_REPOSITORY_CONTROL_EXERCISE",
            "incident exercise environment mode drift")
    require(environment.get("productionEvidence") is False,
            "automated control exercise cannot claim production evidence")
    require(environment.get("humanTabletopCompleted") is False,
            "automated control exercise cannot claim human tabletop completion")
    require(environment.get("pagingConfigured") is False,
            "exercise cannot claim configured paging")
    require(environment.get("syntheticScenariosOnly") is True,
            "exercise must remain synthetic")
    require(environment.get("containsSecrets") is False,
            "exercise must state containsSecrets false")

    exercise = result.get("exercise")
    require(isinstance(exercise, dict), "exercise result missing")
    require(exercise.get("exerciseClass") ==
            "AUTOMATED_CONTROL_EXERCISE_NOT_HUMAN_TABLETOP",
            "exercise class drift")
    require(exercise.get("overallResult") == "AUTOMATED_CONTROL_EXERCISE_PASS",
            "automated control exercise is not PASS")
    require(exercise.get("humanTabletopResult") == "NOT_COMPLETED",
            "human tabletop must remain NOT_COMPLETED")
    require(exercise.get("productionDrillResult") == "NOT_COMPLETED",
            "production drill must remain NOT_COMPLETED")
    require(exercise.get("closureResult") == "BLOCKED_PENDING_HUMAN_APPROVAL",
            "exercise closure must remain blocked")
    require(isinstance(exercise.get("durationSeconds"), (int, float)) and
            exercise["durationSeconds"] >= 0,
            "exercise duration invalid")

    scenarios = exercise.get("scenarios")
    require(isinstance(scenarios, list), "exercise scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == EXPECTED_SCENARIOS,
            f"exercise scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "exercise scenarios contain duplicates")
    contract_scenarios = {
        item["scenarioId"]: item for item in contract["scenarios"]
        if isinstance(item, dict)
    }

    required_decisions = set(contract["requiredDecisionFields"])
    for scenario_id, item in by_id.items():
        definition = contract_scenarios[scenario_id]
        require(item.get("severity") == definition["severity"],
                f"scenario severity drift: {scenario_id}")
        require(item.get("controlResult") == "CONTROL_PATH_PASS",
                f"scenario control path failed: {scenario_id}")
        require(item.get("requiredContainment") == definition["requiredContainment"],
                f"required containment drift: {scenario_id}")
        require(item.get("closureGate") == definition["closureGate"],
                f"closure gate drift: {scenario_id}")
        controls = item.get("controls")
        require(isinstance(controls, list) and len(controls) ==
                len(definition["validatorCommands"]),
                f"scenario control count drift: {scenario_id}")
        require([control.get("command") for control in controls] ==
                definition["validatorCommands"],
                f"scenario command order drift: {scenario_id}")
        for control in controls:
            require(control.get("exitCode") == 0 and control.get("result") == "PASS",
                    f"scenario validator failed: {scenario_id}")
            digest = control.get("outputSha256")
            require(isinstance(digest, str) and DIGEST_RE.fullmatch(digest) is not None,
                    f"scenario output digest invalid: {scenario_id}")
            require(isinstance(control.get("outputBytes"), int) and
                    0 <= control["outputBytes"] <= 1_000_000,
                    f"scenario validator output size invalid: {scenario_id}")
            require(isinstance(control.get("durationSeconds"), (int, float)) and
                    0 <= control["durationSeconds"] <= 180,
                    f"scenario validator duration invalid: {scenario_id}")
        decisions = item.get("decisions")
        require(isinstance(decisions, dict) and set(decisions) == required_decisions,
                f"scenario decision field drift: {scenario_id}")
        require(decisions.get("severity") == definition["severity"],
                f"decision severity drift: {scenario_id}")
        require(decisions.get("declarationDecision") == "DECLARE_INCIDENT",
                f"declaration decision drift: {scenario_id}")
        require(decisions.get("containmentDecision") == "APPLY_REQUIRED_CONTAINMENT",
                f"containment decision drift: {scenario_id}")
        require(decisions.get("stopConditions") == definition["requiredStopConditions"],
                f"stop conditions drift: {scenario_id}")
        require(decisions.get("evidencePreservation") ==
                "PRIVACY_SAFE_APPEND_ONLY_REQUIRED",
                f"evidence preservation drift: {scenario_id}")
        require(decisions.get("recoveryVerification") ==
                "REFERENCED_CONTROLS_PASS_REVERIFY_BEFORE_PROMOTION",
                f"recovery verification drift: {scenario_id}")
        require(decisions.get("promotionDecision") == "BLOCKED",
                f"promotion must remain blocked: {scenario_id}")
        require(decisions.get("closureDecision") ==
                "BLOCKED_PENDING_HUMAN_APPROVAL",
                f"closure must remain blocked: {scenario_id}")
        strings(decisions.get("openRisks"), f"{scenario_id}.openRisks", 3)

    limitations = strings(result.get("limitations"), "result.limitations", 7)
    require(limitations == contract["limitations"],
            "result limitations drift from contract")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "apple_subject",
        "user content", '"output":',
    ):
        require(forbidden not in serialized,
                f"incident exercise result contains forbidden evidence value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-incident-control-exercise.v1",
            "incident control contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-incident-control-exercise-results.v1",
            "incident control result schemaVersion drift")
    require(contract.get("exerciseClass") ==
            "AUTOMATED_CONTROL_EXERCISE_NOT_HUMAN_TABLETOP",
            "incident exercise class drift")
    expected_paths = {
        "runner": "scripts/run-memory-os-incident-control-exercise.py",
        "validator": "scripts/validate-memory-os-incident-control-exercise.py",
        "workflow": ".github/workflows/incident-control-exercise.yml",
        "reconcile": "scripts/reconcile-memory-os-incident-control-exercise.py",
        "resultPath": "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json",
        "diagnosticPath": "docs/fixtures/memory-os-operability/incident-control-exercise-diagnostic.last.json",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"incident control {field} path drift")

    guards = contract.get("globalGuards")
    require(isinstance(guards, dict), "incident globalGuards missing")
    for false_flag in (
        "productionEvidence", "humanTabletopCompleted", "pagingConfigured",
        "externalContactTreeConfigured",
    ):
        require(guards.get(false_flag) is False,
                f"incident guard cannot claim {false_flag}")
    for true_flag in (
        "syntheticScenariosOnly", "exactSourceCommitRequired",
        "secretsInEvidenceForbidden", "userContentInEvidenceForbidden",
        "automaticDestructiveRecoveryForbidden", "automaticPromotionForbidden",
        "closureRequiresHumanApprovals",
    ):
        require(guards.get(true_flag) is True,
                f"incident guard must be true: {true_flag}")

    required_decisions = strings(contract.get("requiredDecisionFields"),
                                 "requiredDecisionFields", 9)
    require(len(required_decisions) == 9,
            "incident decision field count drift")
    scenarios = contract.get("scenarios")
    require(isinstance(scenarios, list), "incident scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == EXPECTED_SCENARIOS,
            f"incident contract scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "incident scenarios contain duplicates")
    for scenario_id, item in by_id.items():
        require(item.get("severity") in {"SEV0", "SEV1"},
                f"incident severity invalid: {scenario_id}")
        commands = strings(item.get("validatorCommands"),
                           f"{scenario_id}.validatorCommands", 2)
        for command in commands:
            require(command.startswith("python scripts/validate-memory-os-") and
                    command.endswith(".py"),
                    f"incident command is not a repository validator: {command}")
            path = command.removeprefix("python ")
            require((ROOT / path).is_file(), f"incident validator missing: {path}")
        strings(item.get("requiredContainment"),
                f"{scenario_id}.requiredContainment", 4)
        strings(item.get("requiredStopConditions"),
                f"{scenario_id}.requiredStopConditions", 3)
        require(isinstance(item.get("closureGate"), str) and
                item["closureGate"].endswith("_REQUIRED"),
                f"incident closure gate invalid: {scenario_id}")

    policy = contract.get("resultPolicy")
    require(isinstance(policy, dict), "incident resultPolicy missing")
    for flag in (
        "allValidatorCommandsMustPass", "allDecisionFieldsMustBePresent",
        "allContainmentAndStopConditionsMustBeRetained",
    ):
        require(policy.get(flag) is True, f"incident result policy must be true: {flag}")
    require(policy.get("humanTabletopResult") == "NOT_COMPLETED",
            "human tabletop result must remain NOT_COMPLETED")
    require(policy.get("productionDrillResult") == "NOT_COMPLETED",
            "production drill result must remain NOT_COMPLETED")
    require(policy.get("closureResult") == "BLOCKED_PENDING_HUMAN_APPROVAL",
            "closure result must remain blocked")
    strings(contract.get("limitations"), "limitations", 7)

    runner = ROOT / contract["runner"]
    require(runner.is_file(), "incident control runner missing")
    source = runner.read_text(encoding="utf-8")
    for snippet in (
        "outputSha256", "BLOCKED_PENDING_HUMAN_APPROVAL",
        "PRIVACY_SAFE_APPEND_ONLY_REQUIRED", "MEMORY_OS_COMMIT_SHA",
        "one or more incident control scenarios failed",
    ):
        require(snippet in source, f"incident runner missing boundary: {snippet}")
    require("completed.stdout" not in source.split("result = {", 1)[-1],
            "incident result must not contain validator output text")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "incident readiness missing")
    require(readiness.get("contractDefined") is True,
            "incident contract foundation missing")
    for unproven in (
        "exactSourcePassResultCommitted", "humanTabletopCompleted",
        "pagingAndAcknowledgementExercised", "externalContactTreeExercised",
        "productionRecoveryDrillCompleted", "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven incident readiness cannot be true: {unproven}")
    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 1)
    for ref in refs:
        require((ROOT / ref).is_file(), f"incident evidence missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source incident exercise result missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), contract, expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "automated incident exercise cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-002"), None)
    require(isinstance(gate, dict), "OPS-P0-002 missing")
    require(gate.get("status") != "READY",
            "automated incident exercise cannot make OPS-P0-002 READY")

    print("Memory OS incident control exercise validation PASS")
    print(f"scenarios: {len(EXPECTED_SCENARIOS)}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"INCIDENT CONTROL EXERCISE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
