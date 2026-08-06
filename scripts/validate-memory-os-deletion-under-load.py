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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-under-load-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def integer(value: Any, field: str, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool),
            f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def positive_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{field} must be numeric")
    number = float(value)
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
    require(summary.get("requests") == requests,
            f"{field} request count drift")
    integer(summary.get("concurrency"), f"{field}.concurrency", 1)
    require(summary.get("successes") == expected_successes and
            summary.get("failures") == expected_failures,
            f"{field} success/failure accounting drift")
    positive_number(summary.get("durationSeconds"), f"{field}.durationSeconds")
    positive_number(summary.get("throughput"), f"{field}.throughput")
    p50 = positive_number(summary.get("latencyP50Ms"), f"{field}.latencyP50Ms")
    p95 = positive_number(summary.get("latencyP95Ms"), f"{field}.latencyP95Ms")
    p99 = positive_number(summary.get("latencyP99Ms"), f"{field}.latencyP99Ms")
    require(p50 <= p95 <= p99, f"{field} latency percentiles are not monotonic")
    require(exact == {str(expected_status): requests},
            f"{field} exact status code accounting drift: {exact}")
    classes = summary.get("statusClassCounts")
    require(isinstance(classes, dict), f"{field}.statusClassCounts missing")
    expected_class = "2xx" if 200 <= expected_status < 300 else "4xx"
    require(classes.get(expected_class) == requests,
            f"{field} status class mismatch")
    require(classes.get("5xx", 0) == 0 and classes.get("transport_error", 0) == 0,
            f"{field} contains infrastructure failure")


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

    result_path = ROOT / contract["resultPath"]
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
    for field, expected in contract["successCriteria"].items():
        require(assertions.get(field) == expected,
                f"deletion-under-load assertion mismatch: {field}")

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
        require(readiness.get("exactSourceResultCommitted") in (False, True) and
                readiness.get("postFenceLoadExecuted") in (False, True),
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
