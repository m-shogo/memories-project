#!/usr/bin/env python3
"""Fail-closed validation for the v2 Memory OS failure-drill authority."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/chaos-failure-drill-contract.v2.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMPLEMENTED = {
    "api-graceful-interruption-drain",
    "parser-restart-after-protocol-failure",
    "object-store-outage-and-recovery",
}
NOT_RUN = {
    "database-loss-or-failover",
    "mixed-version-failure-and-rollback",
}
EXPECTED = IMPLEMENTED | NOT_RUN


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


def strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == "memory-os-chaos-failure-drill-results.v2",
            "v2 result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "v2 result commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"v2 result SHA {commit_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "v2 result environment must be an object")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_LINUX_POSTGRES16_MINIO",
            "v2 result environment mode drift")
    require(environment.get("productionEvidence") is False,
            "local CI dependency drills cannot claim production evidence")
    require(environment.get("containsSecrets") is False,
            "v2 result must state containsSecrets false")
    require(environment.get("syntheticDataOnly") is True,
            "v2 result must use synthetic data only")

    scenarios = result.get("scenarios")
    require(isinstance(scenarios, list), "v2 result scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == EXPECTED, f"v2 result scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "v2 result scenarios contain duplicates")

    for scenario_id in IMPLEMENTED:
        item = by_id[scenario_id]
        require(item.get("result") == "PASS", f"{scenario_id} result is not PASS")
        require(item.get("integrityResult") == "PASS",
                f"{scenario_id} integrity is not PASS")
        require(item.get("exitCode") == 0, f"{scenario_id} exitCode is not zero")
        require(isinstance(item.get("durationSeconds"), (int, float)) and
                item["durationSeconds"] >= 0,
                f"{scenario_id} duration is invalid")
    for scenario_id in NOT_RUN:
        item = by_id[scenario_id]
        require(item.get("result") == "NOT_RUN", f"{scenario_id} must remain NOT_RUN")
        require(item.get("integrityResult") == "NOT_RUN",
                f"{scenario_id} integrity must remain NOT_RUN")
        require(item.get("exitCode") is None, f"{scenario_id} exitCode must be null")

    object_assertions = by_id["object-store-outage-and-recovery"].get("assertions")
    require(isinstance(object_assertions, dict), "object outage assertions missing")
    for field, expected in {
        "durablePreviewRowsDuringOutage": 0,
        "spoolEntriesDuringOutage": 0,
        "durablePreviewRowsAfterRecovery": 1,
        "acceptedRecordsAfterRecovery": 2,
        "rejectedRecordsAfterRecovery": 1,
    }.items():
        require(object_assertions.get(field) == expected,
                f"object outage assertion failed: {field}")

    require(result.get("overallResult") == "PARTIAL_PASS",
            "three local CI drills cannot claim complete chaos PASS")
    limitations = strings(result.get("limitations"), "v2 result limitations", 6)
    joined = "\n".join(limitations)
    for phrase in (
        "not production chaos",
        "database failover not executed",
        "mixed-version failure not executed",
        "object outage uses an unreachable client endpoint",
        "parser restart matrix incomplete",
        "multi-instance API interruption not executed",
    ):
        require(phrase in joined, f"v2 result limitation omitted: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "authorization: bearer", "password=",
        "aws_secret_access_key", "minio_root_password", "synthetic-outage-secret",
        "objectversionid", "accesskeyid", "secretaccesskey",
    ):
        require(forbidden not in serialized, f"v2 result contains forbidden value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-chaos-failure-drills.v2",
            "v2 contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-chaos-failure-drill-results.v2",
            "v2 results schemaVersion drift")
    require(contract.get("supersedes") ==
            "contracts/operations/chaos-failure-drill-contract.v1.json",
            "v2 supersession target drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-chaos-failure-drills-v2.py",
            "v2 validator path drift")
    require(contract.get("resultPath") ==
            "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json",
            "v2 result path drift")

    guards = contract.get("globalGuards")
    require(isinstance(guards, dict), "v2 globalGuards must be an object")
    require(guards.get("productionEvidence") is False,
            "v2 contract cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "exactSourceCommitRequired",
        "secretsInEvidenceForbidden", "automaticDestructiveRecoveryForbidden",
        "componentEvidenceCannotSatisfyProductionDrill",
        "localDependencyEvidenceCannotSatisfyProductionDrill",
    ):
        require(guards.get(flag) is True, f"v2 globalGuards.{flag} must be true")

    scenarios = contract.get("scenarios")
    require(isinstance(scenarios, list), "v2 scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    require(set(by_id) == EXPECTED, f"v2 contract scenario set drift: {sorted(by_id)}")
    require(len(scenarios) == len(by_id), "v2 contract scenarios contain duplicates")

    for scenario_id in IMPLEMENTED:
        item = by_id[scenario_id]
        require(item.get("executionStatus") == "IMPLEMENTED_CI",
                f"{scenario_id} execution status drift")
        require(str(item.get("evidenceClass", "")).startswith("CI_SYSTEM_BOUNDARY"),
                f"{scenario_id} evidence class drift")
        command = item.get("command")
        require(isinstance(command, str) and command.startswith("go test "),
                f"{scenario_id} requires a targeted go test command")
        require(item.get("workingDirectory") == "services/import-api",
                f"{scenario_id} workingDirectory drift")
        refs = strings(item.get("evidenceRefs"), f"{scenario_id}.evidenceRefs", 2)
        strings(item.get("limitations"), f"{scenario_id}.limitations", 3)
        for ref in refs:
            require((ROOT / ref).is_file(), f"{scenario_id} evidence missing: {ref}")
    for scenario_id in NOT_RUN:
        item = by_id[scenario_id]
        require(item.get("executionStatus") == "NOT_IMPLEMENTED",
                f"{scenario_id} must remain NOT_IMPLEMENTED")
        require(item.get("evidenceClass") == "PRODUCTION_SHAPED_DRILL",
                f"{scenario_id} evidence class drift")
        require(item.get("command") is None and item.get("workingDirectory") is None,
                f"{scenario_id} cannot claim an executable command")
        require(strings(item.get("evidenceRefs"), f"{scenario_id}.evidenceRefs") == [],
                f"{scenario_id} cannot claim evidence")
        strings(item.get("limitations"), f"{scenario_id}.limitations", 1)

    object_assertions = strings(
        by_id["object-store-outage-and-recovery"].get("requiredAssertions"),
        "object-store-outage-and-recovery.requiredAssertions",
        5,
    )
    require(any("same request" in value for value in object_assertions),
            "object outage contract must require exact request reuse after recovery")

    refs = strings(contract.get("evidenceRefs"), "v2 evidenceRefs", 7)
    for ref in refs:
        require((ROOT / ref).is_file(), f"v2 contract evidence missing: {ref}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "v2 readiness must be an object")
    for foundation in (
        "contractDefined", "validatorImplemented", "automaticCiWorkflowImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"v2 readiness.{foundation} must be true")
    for unproven in (
        "databaseFailoverExecuted", "mixedVersionFailureExecuted",
        "productionChaosCompleted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven v2 readiness cannot be true: {unproven}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source v2 drill result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "v2 CI drills cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas
               if isinstance(item, dict) and item.get("id") == "OPS-P0-009"]
    require(len(matches) == 1, "OPS-P0-009 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "three local CI drills cannot make OPS-P0-009 READY")

    print("Memory OS chaos/failure-drill v2 validation PASS")
    print(f"implemented CI scenarios: {len(IMPLEMENTED)}")
    print(f"unexecuted production-shaped scenarios: {len(NOT_RUN)}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"CHAOS/FAILURE-DRILL V2 VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
