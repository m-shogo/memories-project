#!/usr/bin/env python3
"""Fail-closed validation for the short CI process stability sample."""

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
CONTRACT_PATH = ROOT / "contracts/operations/short-stability-sample-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("non-finite short stability JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite short stability JSON number rejected")
    return parsed


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float)
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


def finite_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{field} must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise ValidationFailure(f"{field} must be finite") from None
    require(math.isfinite(number), f"{field} must be finite")
    return number


def positive_number(value: Any, field: str) -> float:
    number = finite_number(value, field)
    require(number > 0, f"{field} must be > 0")
    return number


def linear_slope(values: list[int]) -> float:
    """Recompute the producer's least-squares slope from baseline and windows."""
    n = len(values)
    require(n >= 2, "short stability slope needs baseline and observations")
    sum_x = sum(range(n))
    sum_y = sum(values)
    sum_xy = sum(index * value for index, value in enumerate(values))
    sum_xx = sum(index * index for index in range(n))
    denominator = n * sum_xx - sum_x * sum_x
    require(denominator > 0, "short stability slope denominator invalid")
    try:
        slope = (n * sum_xy - sum_x * sum_y) / denominator
    except OverflowError:
        raise ValidationFailure("short stability slope overflow") from None
    require(math.isfinite(slope), "short stability derived slope must be finite")
    return slope


def is_ancestor(value: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", value, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0



def strict_utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            f"{field} must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValidationFailure(f"{field} is not a valid UTC timestamp") from None


def validate_short_timestamps(result: dict[str, Any]) -> None:
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "short stability scenario missing for timestamps")
    started = strict_utc_timestamp(scenario.get("startedAt"), "scenario.startedAt")
    completed = strict_utc_timestamp(scenario.get("completedAt"), "scenario.completedAt")
    generated = strict_utc_timestamp(result.get("generatedAt"), "generatedAt")
    require(started <= completed <= generated, "short stability timestamps must be chronological")
    observations = scenario.get("observations")
    require(isinstance(observations, list), "short stability observations missing for timestamps")
    previous = started
    for index, observation in enumerate(observations):
        require(isinstance(observation, dict), f"observation[{index}] must be an object")
        observed = strict_utc_timestamp(observation.get("observedAt"),
                                        f"observation[{index}].observedAt")
        require(previous <= observed <= completed,
                f"observation[{index}] must be chronological within scenario")
        previous = observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-commit-sha", default=os.getenv("EXPECTED_COMMIT_SHA", ""))
    parser.add_argument("--require-reconciled", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-short-stability-sample.v1",
            "short stability contract schema drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-short-stability-sample-results.v1",
            "short stability result schema drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES",
            "short stability dependency mode drift")
    require(contract.get("classification") == "SHORT_CI_STABILITY_SAMPLE",
            "short stability classification drift")
    window_count = integer(contract.get("windowCount"), "contract.windowCount", 2)
    requests_per_window = integer(contract.get("requestsPerWindow"),
                                  "contract.requestsPerWindow", 1)
    concurrency = integer(contract.get("concurrency"), "contract.concurrency", 1)
    require((window_count, requests_per_window, concurrency) == (6, 300, 16),
            "short stability workload drift")

    rules = contract.get("interpretationRules")
    require(isinstance(rules, dict), "interpretationRules missing")
    require(rules.get("requiredDecision") == "SHORT_SAMPLE_ONLY",
            "short sample decision drift")
    require(rules.get("sustainedSoakMinimumDurationMinutes") == 60,
            "sustained soak duration boundary drift")
    for field in (
        "positiveSlopeIsNotAutomaticallyALeak", "flatSlopeIsNotLeakProof",
        "shortSampleCannotApproveCapacity", "shortSampleCannotApproveSoakReadiness",
        "sustainedSoakRequiresRepeatedRuns", "sustainedSoakRequiresDependencyAndQueueCoverage",
    ):
        require(rules.get(field) is True, f"interpretation rule missing: {field}")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("syntheticDataOnly") is True,
            "synthetic-data boundary missing")
    for field in (
        "productionTraffic", "productionCredentials", "productionEvidence",
        "productionEquivalentDependencies", "sustainedSoakEvidence", "leakProof",
        "capacityBoundaryEstablished", "operationalThresholdApproved", "productionReady",
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
        "sustainedSoakExecuted", "leakProofAvailable", "capacityBoundaryEstablished",
        "operationalThresholdApproved", "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"unproven readiness cannot be true: {field}")

    result_path = ROOT / contract["resultPath"]
    if not result_path.is_file():
        require(readiness.get("exactSourceResultCommitted") is False and
                readiness.get("shortSampleExecuted") is False,
                "contract claims a missing short stability result")
        require(not args.expected_commit_sha and not args.require_reconciled,
                "exact-source short stability result is required but missing")
        print("Memory OS short stability static validation PASS")
        print("exact-source result present: False")
        print("sustained soak evidence: False")
        print("production decision: NO_GO")
        return 0

    result = load(result_path)
    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "short stability result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "short stability commitSha is invalid")
    require(is_ancestor(commit_sha), "short stability source is not an ancestor of HEAD")
    if args.expected_commit_sha:
        require(SHA_RE.fullmatch(args.expected_commit_sha) is not None,
                "expected commit SHA is invalid")
        require(commit_sha == args.expected_commit_sha,
                "short stability result is not from the expected source")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment missing")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES" and
            environment.get("classification") == "SHORT_CI_STABILITY_SAMPLE" and
            environment.get("syntheticDataOnly") is True and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("productionEvidence") is False and
            environment.get("productionEquivalentDependencies") is False and
            environment.get("containsSecrets") is False,
            "short stability evidence boundary drift")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "short stability scenario missing")
    validate_short_timestamps(result)
    require(scenario.get("scenarioId") == contract["scenarioId"],
            "short stability scenario ID drift")
    require(scenario.get("windowCount") == window_count and
            scenario.get("requestsPerWindow") == requests_per_window and
            scenario.get("concurrency") == concurrency,
            "short stability workload accounting drift")
    require(scenario.get("decision") == "SHORT_SAMPLE_ONLY",
            "short stability decision overclaim")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "short stability result is not PASS")

    baseline_heap_alloc = integer(scenario.get("baselineHeapAllocBytes"),
                                  "baselineHeapAllocBytes", 1)
    baseline_heap_inuse = integer(scenario.get("baselineHeapInuseBytes"),
                                  "baselineHeapInuseBytes", 1)
    baseline_rss = integer(scenario.get("baselineRssBytes"), "baselineRssBytes", 1)
    baseline_goroutines = integer(scenario.get("baselineGoroutines"),
                                  "baselineGoroutines", 1)
    require(all(value > 0 for value in (
        baseline_heap_alloc, baseline_heap_inuse, baseline_rss, baseline_goroutines,
    )), "baseline process observations must be positive")

    observations = scenario.get("observations")
    require(isinstance(observations, list) and len(observations) == window_count,
            "short stability observation count drift")
    metric_series = {
        "heapAllocBytes": [baseline_heap_alloc],
        "heapInuseBytes": [baseline_heap_inuse],
        "rssBytes": [baseline_rss],
        "goroutines": [baseline_goroutines],
    }
    for index, observation in enumerate(observations, start=1):
        require(isinstance(observation, dict), f"observation {index} must be an object")
        require(observation.get("window") == index,
                f"observation {index} window order drift")
        for name, series in metric_series.items():
            series.append(integer(observation.get(name), f"observation[{index}].{name}", 1))
        batch = observation.get("batch")
        require(isinstance(batch, dict), f"observation {index} batch missing")
        require(integer(batch.get("requests"), f"observation[{index}].requests", 1) == requests_per_window and
                integer(batch.get("concurrency"), f"observation[{index}].concurrency", 1) == concurrency and
                integer(batch.get("successes"), f"observation[{index}].successes") == requests_per_window and
                integer(batch.get("failures"), f"observation[{index}].failures") == 0,
                f"observation {index} batch accounting drift")
        counts = batch.get("statusClassCounts")
        require(isinstance(counts, dict), f"observation {index} status counts missing")
        require(set(counts).issubset({"2xx", "3xx", "4xx", "5xx", "transport_error"}),
                f"observation {index} unknown status class")
        require(integer(counts.get("2xx"), f"observation[{index}].statusClassCounts.2xx") == requests_per_window,
                f"observation {index} 2xx accounting drift")
        for status_class in ("3xx", "4xx", "5xx", "transport_error"):
            require(integer(counts.get(status_class, 0),
                            f"observation[{index}].statusClassCounts.{status_class}") == 0,
                    f"observation {index} contains non-2xx or infrastructure failure")
        duration = positive_number(batch.get("durationSeconds"),
                                   f"observation[{index}].durationSeconds")
        throughput = positive_number(batch.get("throughput"), f"observation[{index}].throughput")
        derived_throughput = requests_per_window / duration
        require(math.isfinite(derived_throughput) and
                math.isclose(throughput, derived_throughput, rel_tol=1e-6, abs_tol=1e-6),
                f"observation {index} throughput does not match measured requests and duration")
        p50 = positive_number(batch.get("latencyP50Ms"),
                              f"observation[{index}].latencyP50Ms")
        p95 = positive_number(batch.get("latencyP95Ms"),
                              f"observation[{index}].latencyP95Ms")
        p99 = positive_number(batch.get("latencyP99Ms"),
                              f"observation[{index}].latencyP99Ms")
        require(p50 <= p95 <= p99,
                f"observation {index} latency percentiles are not monotonic")

    delta_bindings = {
        "finalMinusBaselineHeapAllocBytes": "heapAllocBytes",
        "finalMinusBaselineHeapInuseBytes": "heapInuseBytes",
        "finalMinusBaselineRssBytes": "rssBytes",
        "finalMinusBaselineGoroutines": "goroutines",
    }
    for field, metric in delta_bindings.items():
        reported = scenario.get(field)
        require(isinstance(reported, int) and not isinstance(reported, bool),
                f"{field} must be an integer delta")
        series = metric_series[metric]
        require(reported == series[-1] - series[0],
                f"{field} does not match final observation minus baseline")
    slope_bindings = {
        "heapAllocSlopeBytesPerWindow": "heapAllocBytes",
        "heapInuseSlopeBytesPerWindow": "heapInuseBytes",
        "rssSlopeBytesPerWindow": "rssBytes",
        "goroutineSlopePerWindow": "goroutines",
    }
    for field, metric in slope_bindings.items():
        reported = finite_number(scenario.get(field), field)
        derived = linear_slope(metric_series[metric])
        require(math.isclose(reported, derived, rel_tol=1e-9, abs_tol=1e-6),
                f"{field} does not match measured baseline/window slope")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "short stability assertions missing")
    for field, value in contract["successCriteria"].items():
        require(assertions.get(field) == value,
                f"short stability assertion mismatch: {field}")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://", "postgresql://", "Bearer ", "password=",
        "acct_", "job_", "prv_", "idem-", "minioadmin",
    ):
        require(forbidden not in serialized,
                f"short stability result contains forbidden content: {forbidden}")

    if args.require_reconciled:
        require(readiness.get("exactSourceResultCommitted") is True and
                readiness.get("shortSampleExecuted") is True,
                "short stability result is not reconciled")
    else:
        require(readiness.get("exactSourceResultCommitted") in (False, True) and
                readiness.get("shortSampleExecuted") in (False, True),
                "short stability readiness fields must be boolean")

    print("Memory OS short CI stability validation PASS")
    print(f"source: {commit_sha[:12]}")
    print(f"windows: {window_count}")
    print("sustained soak evidence: False")
    print("leak proof: False")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"SHORT STABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
