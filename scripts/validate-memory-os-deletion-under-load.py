#!/usr/bin/env python3
"""Fail-closed validation for the post-fence deletion load checkpoint."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-under-load-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
MAX_JSON_BYTES = 1024 * 1024


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("non-finite deletion load JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite deletion load JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate deletion load JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "deletion load JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "deletion load JSON symlink rejected")
    require(path.is_file(), "deletion load JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise ValidationFailure("deletion load JSON path escaped repository") from None
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "deletion load JSON exceeds reviewed read limit")
        value = json.loads(raw.decode("utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise ValidationFailure("deletion load JSON unreadable or invalid") from None
    require(isinstance(value, dict), "deletion load JSON root must be object")
    return value


def integer(value: Any, field: str, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool),
            f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def positive_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{field} must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise ValidationFailure(f"{field} must be finite and positive") from None
    require(math.isfinite(number) and number > 0,
            f"{field} must be finite and positive")
    return number


def is_ancestor(value: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", value, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def validate_batch(value: Any, field: str, requests: int,
                   expected_status: int, expected_successes: int,
                   expected_failures: int) -> None:
    require(isinstance(value, dict), f"{field} must be an object")
    summary = value.get("summary")
    exact = value.get("statusCodeCounts")
    require(isinstance(summary, dict), f"{field}.summary missing")
    require(isinstance(exact, dict), f"{field}.statusCodeCounts missing")
    require(integer(summary.get("requests"), f"{field}.requests", 1) == requests,
            f"{field} request count drift")
    integer(summary.get("concurrency"), f"{field}.concurrency", 1)
    require(integer(summary.get("successes"), f"{field}.successes") == expected_successes and
            integer(summary.get("failures"), f"{field}.failures") == expected_failures,
            f"{field} success/failure accounting drift")
    duration = positive_number(summary.get("durationSeconds"), f"{field}.durationSeconds")
    throughput = positive_number(summary.get("throughput"), f"{field}.throughput")
    derived_throughput = requests / duration
    require(math.isfinite(derived_throughput) and
            math.isclose(throughput, derived_throughput, rel_tol=1e-6, abs_tol=1e-6),
            f"{field} throughput does not match requests and duration")
    p50 = positive_number(summary.get("latencyP50Ms"), f"{field}.latencyP50Ms")
    p95 = positive_number(summary.get("latencyP95Ms"), f"{field}.latencyP95Ms")
    p99 = positive_number(summary.get("latencyP99Ms"), f"{field}.latencyP99Ms")
    require(p50 <= p95 <= p99, f"{field} latency percentiles are not monotonic")
    require(set(exact) == {str(expected_status)} and
            integer(exact.get(str(expected_status)), f"{field}.statusCodeCounts.{expected_status}") == requests,
            f"{field} exact status code accounting drift")
    classes = summary.get("statusClassCounts")
    require(isinstance(classes, dict), f"{field}.statusClassCounts missing")
    require(set(classes).issubset({"2xx", "3xx", "4xx", "5xx", "transport_error"}),
            f"{field} unknown status class")
    expected_class = "2xx" if 200 <= expected_status < 300 else "4xx"
    require(integer(classes.get(expected_class), f"{field}.statusClassCounts.{expected_class}") == requests,
            f"{field} status class mismatch")
    for status_class in ("2xx", "3xx", "4xx", "5xx", "transport_error"):
        if status_class != expected_class:
            require(integer(classes.get(status_class, 0),
                            f"{field}.statusClassCounts.{status_class}") == 0,
                    f"{field} contains unexpected status class or infrastructure failure")



def strict_utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            f"{field} must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValidationFailure(f"{field} is not a valid UTC timestamp") from None


def validate_deletion_timestamps(result: dict[str, Any]) -> None:
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "deletion scenario missing for timestamps")
    started = strict_utc_timestamp(scenario.get("startedAt"), "scenario.startedAt")
    completed = strict_utc_timestamp(scenario.get("completedAt"), "scenario.completedAt")
    generated = strict_utc_timestamp(result.get("generatedAt"), "generatedAt")
    require(started <= completed <= generated, "deletion load timestamps must be chronological")



REVIEWED_RESULT_PATH = "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json"
REVIEWED_SOURCES = {
    "runner": "services/import-api/internal/httpserver/deletion_under_load_test.go",
    "validator": "scripts/validate-memory-os-deletion-under-load.py",
    "reconcile": "scripts/reconcile-memory-os-deletion-under-load-status.py",
    "workflow": ".github/workflows/deletion-under-load.yml",
}
REVIEWED_CRITERIA = {
    "preFenceAll2xx": True, "deletionRequestStatus": 202, "deletionEpoch": 2,
    "postFenceAllUnauthorized": True, "postFenceUnauthorizedCount": 400,
    "postFenceNo5xx": True, "postFenceNoTransportErrors": True,
    "workerCompleted": True, "workerReceiptCount": 1, "finalOwnedRowCount": 0,
    "finalAccountState": "deleted", "finalAccountEpoch": 2,
    "productionEvidence": False,
}


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == keys,
            f"{label} missing or unreviewed fields")
    return value


def reviewed_values(value: Any, expected: dict[str, Any], label: str) -> None:
    actual = exact_keys(value, set(expected), label)
    for key, reviewed in expected.items():
        require(type(actual[key]) is type(reviewed) and actual[key] == reviewed,
                f"{label}.{key} reviewed type/value drift")


def validate_reviewed_contract(contract: dict[str, Any]) -> None:
    require(contract.get("contractId") == "memory-os.operability.deletion-under-load.v1",
            "deletion-under-load contract identity drift")
    require(contract.get("resultPath") == REVIEWED_RESULT_PATH,
            "deletion-under-load result path authority drift")
    for key, reviewed in REVIEWED_SOURCES.items():
        require(contract.get(key) == reviewed,
                f"deletion-under-load {key} source authority drift")
    reviewed_values(contract.get("successCriteria"), REVIEWED_CRITERIA,
                    "deletion-under-load successCriteria")


def validate_result_shape(result: dict[str, Any]) -> None:
    exact_keys(result, {"schemaVersion", "commitSha", "generatedAt",
                        "environment", "scenario", "limitations"},
               "deletion-under-load result")
    environment = exact_keys(result.get("environment"), {
        "os", "arch", "numCpu", "goVersion", "dependencyMode",
        "syntheticDataOnly", "productionTraffic", "productionCredentials",
        "productionEvidence", "productionEquivalentDependencies", "containsSecrets",
    }, "deletion-under-load environment")
    require(environment["os"] == "linux" and environment["arch"] == "amd64" and
            isinstance(environment["goVersion"], str) and bool(environment["goVersion"].strip()),
            "deletion-under-load environment platform drift")
    integer(environment["numCpu"], "environment.numCpu", 1)
    scenario = exact_keys(result.get("scenario"), {
        "scenarioId", "startedAt", "completedAt", "preFence", "deletionRequestStatus",
        "deletionEpoch", "postFence", "workerDurationSeconds", "workerReceiptCount",
        "finalOwnedRowCount", "finalAccountState", "finalAccountEpoch",
        "assertions", "result", "integrityResult",
    }, "deletion-under-load scenario")
    for field, reviewed in {
        "deletionRequestStatus": 202, "deletionEpoch": 2,
        "workerReceiptCount": 1, "finalOwnedRowCount": 0,
        "finalAccountState": "deleted", "finalAccountEpoch": 2,
        "result": "PASS", "integrityResult": "PASS",
    }.items():
        require(type(scenario.get(field)) is type(reviewed) and
                scenario[field] == reviewed,
                f"deletion-under-load scenario.{field} reviewed type/value drift")
    for name, concurrency in (("preFence", 16), ("postFence", 32)):
        batch = exact_keys(scenario.get(name), {"summary", "statusCodeCounts"},
                           f"deletion-under-load {name}")
        summary = exact_keys(batch.get("summary"), {
            "requests", "concurrency", "successes", "failures",
            "statusClassCounts", "durationSeconds", "throughput",
            "latencyP50Ms", "latencyP95Ms", "latencyP99Ms",
        }, f"deletion-under-load {name}.summary")
        require(integer(summary.get("concurrency"), f"{name}.concurrency", 1) == concurrency,
                f"deletion-under-load {name} concurrency drift")
    reviewed_values(scenario.get("assertions"), REVIEWED_CRITERIA,
                    "deletion-under-load assertions")
    limitations = result.get("limitations")
    require(isinstance(limitations, list) and bool(limitations) and
            all(isinstance(x, str) and bool(x.strip()) for x in limitations),
            "deletion-under-load limitations must be nonempty strings")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-commit-sha", default=os.getenv("EXPECTED_COMMIT_SHA", ""))
    parser.add_argument("--require-reconciled", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-deletion-under-load.v1",
            "deletion-under-load contract schema drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-deletion-under-load-results.v1",
            "deletion-under-load result schema drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO",
            "deletion-under-load dependency mode drift")
    require(contract.get("preFenceRequests") == 120 and
            contract.get("postFenceRequests") == 400 and
            contract.get("concurrency") == 32,
            "deletion-under-load workload drift")

    sequence = contract.get("requiredSequence")
    abort = contract.get("abortCriteria")
    require(isinstance(sequence, list) and len(sequence) >= 7,
            "required deletion sequence is incomplete")
    require(isinstance(abort, list) and len(abort) >= 6,
            "deletion abort criteria are incomplete")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("syntheticDataOnly") is True,
            "synthetic-data boundary missing")
    for field in (
        "productionTraffic", "productionCredentials", "productionEvidence",
        "productionEquivalentDependencies", "requestsStartedBeforeFenceCovered",
        "hostFailureCovered", "productionReady",
    ):
        require(boundary.get(field) is False, f"contract overclaims {field}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for field in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"readiness missing: {field}")
    for field in (
        "preFenceInFlightLinearizationProven", "productionDependenciesTested",
        "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"unproven readiness cannot be true: {field}")

    validate_reviewed_contract(contract)
    result_path = ROOT / REVIEWED_RESULT_PATH
    if not result_path.is_file():
        require(readiness.get("exactSourceResultCommitted") is False and
                readiness.get("postFenceLoadExecuted") is False,
                "contract claims a missing deletion-under-load result")
        require(not args.expected_commit_sha and not args.require_reconciled,
                "exact-source deletion-under-load result is required but missing")
        print("Memory OS deletion-under-load static validation PASS")
        print("exact-source result present: False")
        print("post-fence load executed: False")
        print("production decision: NO_GO")
        return 0

    result = load(result_path)
    validate_result_shape(result)
    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "deletion-under-load result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "deletion-under-load commitSha is invalid")
    require(is_ancestor(commit_sha),
            "deletion-under-load source is not an ancestor of HEAD")
    if args.expected_commit_sha:
        require(SHA_RE.fullmatch(args.expected_commit_sha) is not None,
                "expected commit SHA is invalid")
        require(commit_sha == args.expected_commit_sha,
                "deletion-under-load result is not from the expected source")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment missing")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO" and
            environment.get("syntheticDataOnly") is True and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("productionEvidence") is False and
            environment.get("productionEquivalentDependencies") is False and
            environment.get("containsSecrets") is False,
            "deletion-under-load evidence boundary drift")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "deletion-under-load scenario missing")
    validate_deletion_timestamps(result)
    require(scenario.get("scenarioId") == contract["scenarioId"],
            "deletion-under-load scenario ID drift")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "deletion-under-load result is not PASS")
    validate_batch(scenario.get("preFence"), "preFence", 120, 200, 120, 0)
    validate_batch(scenario.get("postFence"), "postFence", 400, 401, 0, 400)
    require(scenario.get("deletionRequestStatus") == 202 and
            scenario.get("deletionEpoch") == 2,
            "deletion fence receipt drift")
    positive_number(scenario.get("workerDurationSeconds"),
                    "workerDurationSeconds")
    require(scenario.get("workerReceiptCount") == 1 and
            scenario.get("finalOwnedRowCount") == 0 and
            scenario.get("finalAccountState") == "deleted" and
            scenario.get("finalAccountEpoch") == 2,
            "deletion worker or final-state accounting drift")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "deletion-under-load assertions missing")
    reviewed_values(assertions, REVIEWED_CRITERIA, "deletion-under-load assertions")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://", "postgresql://", "Bearer ", "password=", "minioadmin",
        "acct_", "job_", "prv_", "spl_", "upl_", "idem-", "object_key",
    ):
        require(forbidden not in serialized,
                f"deletion-under-load result contains forbidden content: {forbidden}")

    if args.require_reconciled:
        require(readiness.get("exactSourceResultCommitted") is True and
                readiness.get("postFenceLoadExecuted") is True,
                "deletion-under-load result is not reconciled")
    else:
        require(type(readiness.get("exactSourceResultCommitted")) is bool and
                type(readiness.get("postFenceLoadExecuted")) is bool,
                "deletion-under-load readiness fields must be boolean")

    print("Memory OS deletion-under-load validation PASS")
    print(f"source: {commit_sha[:12]}")
    print("post-fence requests: 400 unauthorized")
    print("final owned rows: 0")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"DELETION-UNDER-LOAD VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
