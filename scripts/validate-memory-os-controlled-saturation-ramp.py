#!/usr/bin/env python3
"""Fail-closed validator for the bounded local PostgreSQL + MinIO saturation ramp."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/controlled-saturation-ramp-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-ramp-results.sample.v1.json"
EXPECTED_STEPS = [4, 8, 16, 24, 32, 48]
REQUESTS_PER_STEP = 64
SCENARIO_ID = "signed-upload-controlled-saturation-ramp-local-dependencies"
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
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def integer(value: Any, field: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer")
    return value


def number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    result = float(value)
    require(result >= 0, f"{field} must be non-negative")
    return result


def status_count(batch: dict[str, Any], key: str, field: str) -> int:
    counts = batch.get("statusClassCounts")
    require(isinstance(counts, dict), f"{field}.statusClassCounts must be object")
    value = counts.get(key, 0)
    return integer(value, f"{field}.statusClassCounts.{key}")


def validate_batch(batch: Any, concurrency: int, total: int, field: str) -> bool:
    require(isinstance(batch, dict), f"{field} must be object")
    requests = integer(batch.get("requests"), f"{field}.requests")
    actual_concurrency = integer(batch.get("concurrency"), f"{field}.concurrency")
    successes = integer(batch.get("successes"), f"{field}.successes")
    failures = integer(batch.get("failures"), f"{field}.failures")
    require(requests == total, f"{field}: requests drift")
    require(actual_concurrency == concurrency, f"{field}: concurrency drift")
    require(successes + failures == total, f"{field}: successes + failures must equal requests")
    require(status_count(batch, "3xx", field) == 0, f"{field}: 3xx is not an overload signal")
    require(status_count(batch, "4xx", field) == 0, f"{field}: 4xx is not an overload signal")
    two_xx = status_count(batch, "2xx", field)
    five_xx = status_count(batch, "5xx", field)
    transport = status_count(batch, "transport_error", field)
    require(two_xx == successes, f"{field}: every success must be the final 202 lifecycle response")
    require(two_xx + five_xx + transport == total, f"{field}: status accounting mismatch")
    number(batch.get("durationSeconds"), f"{field}.durationSeconds")
    number(batch.get("throughput"), f"{field}.throughput")
    number(batch.get("latencyP50Ms"), f"{field}.latencyP50Ms")
    number(batch.get("latencyP95Ms"), f"{field}.latencyP95Ms")
    number(batch.get("latencyP99Ms"), f"{field}.latencyP99Ms")
    return failures == 0 and two_xx == total and five_xx == 0 and transport == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-commit-sha", default=os.environ.get("EXPECTED_COMMIT_SHA", ""))
    parser.add_argument("--require-reconciled", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)

    require(contract.get("schemaVersion") == "memory-os-controlled-saturation-ramp.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-controlled-saturation-ramp-results.v1", "results schema binding drift")
    require(contract.get("scenarioId") == SCENARIO_ID, "contract scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "contract dependency mode drift")
    require(contract.get("concurrencySteps") == EXPECTED_STEPS, "contract concurrency steps drift")
    require(contract.get("requestsPerStep") == REQUESTS_PER_STEP, "contract request count drift")
    require(contract.get("maximumMeasuredRequests") == len(EXPECTED_STEPS) * REQUESTS_PER_STEP, "contract maximum measured requests drift")
    require(contract.get("maximumTotalLifecycleRequests") == len(EXPECTED_STEPS) * REQUESTS_PER_STEP + 1, "contract maximum total requests drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "contract evidenceBoundary must be object")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"contract cannot enable {key}")
    require(boundary.get("syntheticDataOnly") is True, "contract must remain synthetic-only")

    require(result.get("schemaVersion") == "memory-os-controlled-saturation-ramp-results.v1", "result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None, "result commitSha must be full lowercase SHA")
    if args.expected_commit_sha:
        require(SHA_RE.fullmatch(args.expected_commit_sha) is not None, "expected commit SHA must be full lowercase SHA")
        require(commit_sha == args.expected_commit_sha, "result is stale for expected source commit")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment must be object")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "result dependency mode drift")
    require(environment.get("syntheticDataOnly") is True, "result must remain synthetic-only")
    require(environment.get("loopbackDependenciesOnly") is True, "result must prove loopback-only dependency admission")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"result cannot enable environment.{key}")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in ("postgres://", "postgresql://", "minioadmin", "Bearer ", "acct_controlled_saturation_", "X-Amz-Credential"):
        require(forbidden not in serialized, f"result contains forbidden sensitive/runtime material: {forbidden}")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario must be object")
    require(scenario.get("scenarioId") == SCENARIO_ID, "scenario id drift")
    require(scenario.get("workloadType") == "CONTROLLED_RAMP", "workload type drift")
    require(scenario.get("requestsPerStep") == REQUESTS_PER_STEP, "scenario request count drift")
    steps = scenario.get("steps")
    require(isinstance(steps, list) and len(steps) == len(EXPECTED_STEPS), "all controlled ramp steps must execute")

    first_failure: int | None = None
    first_contention: int | None = None
    ramp_successes = 0
    highest_clean = 0
    for index, expected_concurrency in enumerate(EXPECTED_STEPS):
        step = steps[index]
        require(isinstance(step, dict), f"steps[{index}] must be object")
        require(step.get("concurrency") == expected_concurrency, f"steps[{index}] concurrency drift")
        clean = validate_batch(step.get("batch"), expected_concurrency, REQUESTS_PER_STEP, f"steps[{index}].batch")
        batch = step["batch"]
        ramp_successes += integer(batch.get("successes"), f"steps[{index}].batch.successes")
        if clean:
            highest_clean = expected_concurrency
        elif first_failure is None:
            first_failure = expected_concurrency

        before = step.get("poolBefore")
        after = step.get("poolAfter")
        delta = step.get("poolDelta")
        require(isinstance(before, dict) and isinstance(after, dict) and isinstance(delta, dict), f"steps[{index}] pool snapshots/delta required")
        max_before = integer(before.get("maxConns"), f"steps[{index}].poolBefore.maxConns")
        max_after = integer(after.get("maxConns"), f"steps[{index}].poolAfter.maxConns")
        require(max_before > 0 and max_before == max_after, f"steps[{index}] pool maxConns drift")
        for name in ("totalConns", "acquiredConns", "idleConns", "emptyAcquireCount", "canceledAcquireCount"):
            integer(before.get(name), f"steps[{index}].poolBefore.{name}")
            integer(after.get(name), f"steps[{index}].poolAfter.{name}")
        number(before.get("acquireDurationMs"), f"steps[{index}].poolBefore.acquireDurationMs")
        number(after.get("acquireDurationMs"), f"steps[{index}].poolAfter.acquireDurationMs")
        empty_delta = integer(delta.get("emptyAcquireCount"), f"steps[{index}].poolDelta.emptyAcquireCount")
        canceled_delta = integer(delta.get("canceledAcquireCount"), f"steps[{index}].poolDelta.canceledAcquireCount")
        duration_delta = number(delta.get("acquireDurationMs"), f"steps[{index}].poolDelta.acquireDurationMs")
        require(empty_delta >= 0 and canceled_delta >= 0 and duration_delta >= 0, f"steps[{index}] pool deltas must be non-negative")
        require(empty_delta == after["emptyAcquireCount"] - before["emptyAcquireCount"], f"steps[{index}] empty-acquire delta mismatch")
        require(canceled_delta == after["canceledAcquireCount"] - before["canceledAcquireCount"], f"steps[{index}] canceled-acquire delta mismatch")
        if empty_delta > 0 and first_contention is None:
            first_contention = expected_concurrency

    require(scenario.get("rampSuccessfulLifecycles") == ramp_successes, "ramp success accounting drift")
    require(scenario.get("candidateCleanConcurrency") == highest_clean, "candidate clean concurrency drift")
    require(scenario.get("firstSaturationSignal") == first_failure, "first saturation signal drift")
    require(scenario.get("firstPoolContentionSignal") == first_contention, "first pool contention signal drift")
    expected_decision = "BOUNDARY_NOT_ESTABLISHED" if first_failure is None else "LOCAL_SATURATION_SIGNAL_REQUIRES_REPEATABILITY_REVIEW"
    require(scenario.get("decision") == expected_decision, "decision does not match measured saturation signal")

    recovery = scenario.get("postRampRecoveryProbe")
    require(validate_batch(recovery, 1, 1, "postRampRecoveryProbe"), "post-ramp recovery probe must succeed exactly once")

    final_counts = scenario.get("finalDatabaseAssertions")
    require(isinstance(final_counts, dict), "finalDatabaseAssertions must be object")
    expected_final = ramp_successes + 1
    for key in (
        "consumedAuthorizations",
        "scanPendingQuarantineRows",
        "distinctObjectVersionIds",
        "distinctObjectKeys",
    ):
        require(final_counts.get(key) == expected_final, f"final database accounting mismatch: {key}")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "scenario assertions must be object")
    require(assertions.get("allStepsExecuted") is True, "allStepsExecuted must be true")
    require(assertions.get("boundedMaximumConcurrency") == 48, "boundedMaximumConcurrency drift")
    require(assertions.get("boundedRequestsPerStep") == REQUESTS_PER_STEP, "boundedRequestsPerStep drift")
    require(assertions.get("postRampRecoveryProbePassed") is True, "recovery assertion must remain true")
    for key in (
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "repeatabilityEstablished",
        "independentReviewCompleted",
    ):
        require(assertions.get(key) is False, f"single local ramp cannot enable assertions.{key}")
    require(scenario.get("result") == "PASS", "scenario result must be PASS")
    require(scenario.get("integrityResult") == "PASS", "scenario integrityResult must be PASS")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "contract readiness must be object")
    for key in (
        "repeatabilityEstablished",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"contract readiness cannot enable {key}")
    if args.require_reconciled:
        for key in (
            "contractDefined",
            "runnerImplemented",
            "validatorImplemented",
            "automaticWorkflowImplemented",
            "exactSourceResultCommitted",
            "localRampExecuted",
        ):
            require(readiness.get(key) is True, f"reconciled readiness requires {key}=true")
        require(readiness.get("localSaturationSignalObserved") is (first_failure is not None), "reconciled saturation signal drift")
        require(readiness.get("poolContentionSignalObserved") is (first_contention is not None), "reconciled pool contention signal drift")

    print("Memory OS controlled saturation ramp validation PASS")
    print(f"source: {commit_sha}")
    print(f"first saturation signal: {first_failure}")
    print(f"first pool contention signal: {first_contention}")
    print(f"decision: {expected_decision}")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"CONTROLLED SATURATION RAMP FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
