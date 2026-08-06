#!/usr/bin/env python3
"""Execute the exact-source automated incident control exercise."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
DEFAULT_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"


class ExerciseFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExerciseFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExerciseFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ExerciseFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def source_sha() -> str:
    expected = os.environ.get("MEMORY_OS_COMMIT_SHA", "")
    require(len(expected) == 40 and all(character in "0123456789abcdef" for character in expected),
            "MEMORY_OS_COMMIT_SHA must be a full lowercase SHA")
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    require(actual == expected, "working tree HEAD does not equal MEMORY_OS_COMMIT_SHA")
    require(not subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip(), "working tree must be clean")
    return actual


def command_result(command_text: str) -> dict[str, Any]:
    arguments = shlex.split(command_text)
    require(arguments and arguments[0] == "python",
            f"exercise command must invoke a Python validator: {command_text}")
    started = time.monotonic()
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=180,
    )
    duration = round(time.monotonic() - started, 6)
    output = completed.stdout.encode("utf-8", errors="replace")
    return {
        "command": command_text,
        "exitCode": completed.returncode,
        "durationSeconds": duration,
        "outputSha256": hashlib.sha256(output).hexdigest(),
        "outputBytes": len(output),
        "result": "PASS" if completed.returncode == 0 else "FAIL",
    }


def main() -> int:
    contract = load(CONTRACT_PATH)
    commit_sha = source_sha()
    result_path = Path(os.environ.get(
        "MEMORY_OS_INCIDENT_CONTROL_RESULTS_PATH", str(DEFAULT_RESULT_PATH)
    ))
    if not result_path.is_absolute():
        result_path = ROOT / result_path
    require(ROOT == result_path.resolve().parents[3],
            "incident control result path must remain under repository docs/fixtures")

    started_at = dt.datetime.now(dt.timezone.utc)
    scenarios_out: list[dict[str, Any]] = []

    scenarios = contract.get("scenarios")
    require(isinstance(scenarios, list) and len(scenarios) == 6,
            "incident control contract must contain six scenarios")
    for scenario in scenarios:
        require(isinstance(scenario, dict), "scenario must be an object")
        commands = scenario.get("validatorCommands")
        require(isinstance(commands, list) and commands,
                f"scenario validatorCommands missing: {scenario.get('scenarioId')}")
        command_results = [command_result(command) for command in commands]
        controls_passed = all(item["result"] == "PASS" for item in command_results)
        scenarios_out.append({
            "scenarioId": scenario["scenarioId"],
            "severity": scenario["severity"],
            "controls": command_results,
            "decisions": {
                "severity": scenario["severity"],
                "declarationDecision": "DECLARE_INCIDENT",
                "containmentDecision": "APPLY_REQUIRED_CONTAINMENT",
                "stopConditions": scenario["requiredStopConditions"],
                "evidencePreservation": "PRIVACY_SAFE_APPEND_ONLY_REQUIRED",
                "recoveryVerification": (
                    "REFERENCED_CONTROLS_PASS_REVERIFY_BEFORE_PROMOTION"
                    if controls_passed
                    else "CONTROL_FAILURE_STOP_AND_REMEDIATE"
                ),
                "promotionDecision": "BLOCKED",
                "closureDecision": "BLOCKED_PENDING_HUMAN_APPROVAL",
                "openRisks": [
                    "human incident command not exercised",
                    "production dependencies and traffic not exercised",
                    "paging, communications and independent approval not exercised",
                ],
            },
            "requiredContainment": scenario["requiredContainment"],
            "closureGate": scenario["closureGate"],
            "controlResult": "CONTROL_PATH_PASS" if controls_passed else "CONTROL_PATH_FAIL",
        })

    failed_commands = [
        control["command"]
        for scenario in scenarios_out
        for control in scenario["controls"]
        if control["result"] != "PASS"
    ]
    require(
        not failed_commands,
        "failed repository validators: " + ", ".join(failed_commands),
    )

    completed_at = dt.datetime.now(dt.timezone.utc)
    result = {
        "schemaVersion": "memory-os-incident-control-exercise-results.v1",
        "commitSha": commit_sha,
        "generatedAt": completed_at.isoformat().replace("+00:00", "Z"),
        "environment": {
            "mode": "GITHUB_ACTIONS_REPOSITORY_CONTROL_EXERCISE",
            "productionEvidence": False,
            "humanTabletopCompleted": False,
            "pagingConfigured": False,
            "syntheticScenariosOnly": True,
            "containsSecrets": False,
        },
        "exercise": {
            "exerciseClass": "AUTOMATED_CONTROL_EXERCISE_NOT_HUMAN_TABLETOP",
            "startedAt": started_at.isoformat().replace("+00:00", "Z"),
            "completedAt": completed_at.isoformat().replace("+00:00", "Z"),
            "durationSeconds": round((completed_at - started_at).total_seconds(), 6),
            "scenarios": scenarios_out,
            "overallResult": "AUTOMATED_CONTROL_EXERCISE_PASS",
            "humanTabletopResult": "NOT_COMPLETED",
            "productionDrillResult": "NOT_COMPLETED",
            "closureResult": "BLOCKED_PENDING_HUMAN_APPROVAL",
        },
        "limitations": contract["limitations"],
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Memory OS automated incident control exercise PASS")
    print(f"scenarios: {len(scenarios_out)}")
    print(f"result: {result_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExerciseFailure, subprocess.TimeoutExpired) as exc:
        print(f"INCIDENT CONTROL EXERCISE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
