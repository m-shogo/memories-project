#!/usr/bin/env python3
"""Fail-closed validation for Memory OS chaos and failure-drill evidence."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/chaos-failure-drill-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/chaos-failure-drill-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SCENARIOS = {
    "api-graceful-interruption-drain": ("IMPLEMENTED_CI", "CI_SYSTEM_BOUNDARY"),
    "parser-restart-after-protocol-failure": ("IMPLEMENTED_CI", "CI_SYSTEM_BOUNDARY"),
    "database-loss-or-failover": ("NOT_IMPLEMENTED", "PRODUCTION_SHAPED_DRILL"),
    "object-store-outage-and-recovery": ("NOT_IMPLEMENTED", "PRODUCTION_SHAPED_DRILL"),
    "mixed-version-failure-and-rollback": ("NOT_IMPLEMENTED", "PRODUCTION_SHAPED_DRILL"),
}
EXPECTED_IMPLEMENTED = {
    "api-graceful-interruption-drain",
    "parser-restart-after-protocol-failure",
}
EXPECTED_NOT_RUN = set(EXPECTED_SCENARIOS) - EXPECTED_IMPLEMENTED


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


def unique_strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == "memory-os-chaos-failure-drill-results.v1",
            "result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "result commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"result SHA {commit_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment must be an object")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_LINUX",
            "result environment mode drift")
    require(environment.get("productionEvidence") is False,
            "CI failure drills cannot claim production evidence")
    require(environment.get("containsSecrets") is False,
            "result must state containsSecrets false")
    require(environment.get("syntheticDataOnly") is True,
            "result must use synthetic data only")

    scenarios = result.get("scenarios")
    require(isinstance(scenarios, list), "result scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == set(EXPECTED_SCENARIOS),
            f"result scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "result scenarios contain duplicates")

    for scenario_id in EXPECTED_IMPLEMENTED:
        item = by_id[scenario_id]
        require(item.get("result") == "PASS", f"{scenario_id} result is not PASS")
        require(item.get("integrityResult") == "PASS",
                f"{scenario_id} integrity is not PASS")
        require(isinstance(item.get("durationSeconds"), (int, float)) and
                item["durationSeconds"] >= 0,
                f"{scenario_id} duration is invalid")
        require(item.get("exitCode") == 0, f"{scenario_id} exitCode is not zero")
    for scenario_id in EXPECTED_NOT_RUN:
        item = by_id[scenario_id]
        require(item.get("result") == "NOT_RUN", f"{scenario_id} must remain NOT_RUN")
        require(item.get("integrityResult") == "NOT_RUN",
                f"{scenario_id} integrity must remain NOT_RUN")
        require(item.get("exitCode") is None, f"{scenario_id} exitCode must be null")

    require(result.get("overallResult") == "PARTIAL_PASS",
            "two CI drills cannot claim complete chaos PASS")
    limitations = unique_strings(result.get("limitations"), "result.limitations", 5)
    joined = "\n".join(limitations)
    for phrase in (
        "not production chaos",
        "database failover not executed",
        "object-store outage not executed",
        "mixed-version failure not executed",
        "parser restart matrix incomplete",
    ):
        require(phrase in joined, f"result limitation omitted: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "authorization: bearer", "password=",
        "aws_secret_access_key", "minio_root_password", "user content",
    ):
        require(forbidden not in serialized, f"result contains forbidden value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-chaos-failure-drills.v1",
            "contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-chaos-failure-drill-results.v1",
            "results schemaVersion drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-chaos-failure-drills.py",
            "validator path drift")
    require(contract.get("resultPath") ==
            "docs/fixtures/memory-os-operability/chaos-failure-drill-results.sample.v1.json",
            "result path drift")

    classes = unique_strings(contract.get("evidenceClasses"), "evidenceClasses", 4)
    require(classes == [
        "COMPONENT_FAULT_INJECTION",
        "CI_SYSTEM_BOUNDARY",
        "PRODUCTION_SHAPED_DRILL",
        "PRODUCTION_DRILL",
    ], "evidence class order or set drift")

    guards = contract.get("globalGuards")
    require(isinstance(guards, dict), "globalGuards must be an object")
    require(guards.get("productionEvidence") is False,
            "contract cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "exactSourceCommitRequired",
        "secretsInEvidenceForbidden", "userContentInEvidenceForbidden",
        "automaticDestructiveRecoveryForbidden",
        "componentEvidenceCannotSatisfyProductionDrill",
        "failedOrPartialDrillCannotBePromoted",
    ):
        require(guards.get(flag) is True, f"globalGuards.{flag} must be true")

    scenarios = contract.get("scenarios")
    require(isinstance(scenarios, list), "scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == set(EXPECTED_SCENARIOS),
            f"contract scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "contract scenarios contain duplicates")

    for scenario_id, (status, evidence_class) in EXPECTED_SCENARIOS.items():
        item = by_id[scenario_id]
        require(item.get("executionStatus") == status,
                f"{scenario_id} execution status drift")
        require(item.get("evidenceClass") == evidence_class,
                f"{scenario_id} evidence class drift")
        unique_strings(item.get("requiredAssertions"),
                       f"{scenario_id}.requiredAssertions", 5)
        unique_strings(item.get("limitations"), f"{scenario_id}.limitations", 1)
        refs = unique_strings(item.get("evidenceRefs"),
                              f"{scenario_id}.evidenceRefs")
        if scenario_id in EXPECTED_IMPLEMENTED:
            command = item.get("command")
            workdir = item.get("workingDirectory")
            require(isinstance(command, str) and command.startswith("go test "),
                    f"{scenario_id} requires a targeted go test command")
            require(workdir == "services/import-api",
                    f"{scenario_id} workingDirectory drift")
            require(len(refs) >= 2, f"{scenario_id} requires repository evidence")
            for ref in refs:
                require((ROOT / ref).is_file(), f"{scenario_id} evidence missing: {ref}")
        else:
            require(item.get("command") is None,
                    f"unimplemented scenario {scenario_id} cannot have a command")
            require(item.get("workingDirectory") is None,
                    f"unimplemented scenario {scenario_id} cannot have a working directory")
            require(refs == [],
                    f"unimplemented scenario {scenario_id} cannot claim evidence")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in ("contractDefined", "validatorImplemented"):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "exactSourceResultCommitted", "apiInterruptionExecuted",
        "parserRestartExecuted", "databaseFailoverExecuted",
        "objectStoreOutageExecuted", "mixedVersionFailureExecuted",
        "productionChaosCompleted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven readiness cannot be true: {unproven}")

    refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs", 4)
    for ref in refs:
        require((ROOT / ref).is_file(), f"contract evidence missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source drill result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "CI drills cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas
               if isinstance(item, dict) and item.get("id") == "OPS-P0-009"]
    require(len(matches) == 1, "OPS-P0-009 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "two local CI drills cannot make OPS-P0-009 READY")

    print("Memory OS chaos/failure-drill validation PASS")
    print(f"implemented CI scenarios: {len(EXPECTED_IMPLEMENTED)}")
    print(f"unexecuted production-shaped scenarios: {len(EXPECTED_NOT_RUN)}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print(f"OPS-P0-009 status: {matches[0].get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"CHAOS/FAILURE-DRILL VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
