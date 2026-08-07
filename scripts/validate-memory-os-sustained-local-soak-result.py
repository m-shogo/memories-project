#!/usr/bin/env python3
"""Validate one exact-source LOCAL_LONG_SOAK result before it can be published."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def integer(value: Any, field: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer")
    return value


def number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    result = float(value)
    require(math.isfinite(result), f"{field} must be finite")
    return result


def nonnegative(value: Any, field: str) -> float:
    result = number(value, field)
    require(result >= 0, f"{field} must be non-negative")
    return result


def slope(observations: list[dict[str, Any]], getter: Callable[[dict[str, Any]], float]) -> float:
    if len(observations) < 2:
        return 0.0
    xs = [number(item["elapsedSeconds"], "elapsedSeconds") / 60.0 for item in observations]
    ys = [getter(item) for item in observations]
    n = float(len(xs))
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_xx = sum(x * x for x in xs)
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denominator


def close(actual: Any, expected: float, field: str) -> None:
    value = number(actual, field)
    tolerance = max(1e-9, abs(expected) * 1e-9)
    require(abs(value - expected) <= tolerance, f"{field} drift: got {value}, expected {expected}")


def validate_result(path: Path, expected_commit_sha: str | None = None) -> tuple[str, str]:
    contract = load(CONTRACT_PATH)
    doc = load(path)
    require(doc.get("schemaVersion") == "memory-os-sustained-local-soak-results.v1", "result schema drift")
    commit_sha = doc.get("commitSha")
    run_id = doc.get("runId")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None, "full lowercase commitSha required")
    require(isinstance(run_id, str) and run_id and len(run_id) <= 160, "bounded runId required")
    if expected_commit_sha is not None:
        require(SHA_RE.fullmatch(expected_commit_sha) is not None, "expected commit SHA must be full lowercase SHA")
        require(commit_sha == expected_commit_sha, "result is stale for expected source commit")

    environment = doc.get("environment")
    require(isinstance(environment, dict), "environment must be object")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(environment.get("classification") == "LOCAL_LONG_SOAK", "classification drift")
    require(environment.get("syntheticDataOnly") is True, "syntheticDataOnly must be true")
    require(environment.get("loopbackDependenciesOnly") is True, "loopbackDependenciesOnly must be true")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"environment.{key} must remain false")

    serialized = json.dumps(doc, ensure_ascii=False)
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "Bearer ",
        "X-Amz-Credential",
        "X-Amz-Signature",
        "acct_soak_",
        "quarantine/",
    ):
        require(forbidden not in serialized, f"result contains forbidden runtime/sensitive material: {forbidden}")

    scenario = doc.get("scenario")
    require(isinstance(scenario, dict), "scenario must be object")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), "scenario id drift")
    duration = nonnegative(scenario.get("durationSeconds"), "scenario.durationSeconds")
    require(duration >= integer(contract.get("minimumRunDurationSeconds"), "contract.minimumRunDurationSeconds"), "result is shorter than the 60-minute minimum")
    require(duration <= integer(contract.get("maximumSingleRunDurationSeconds"), "contract.maximumSingleRunDurationSeconds") + 120, "result exceeds bounded duration tolerance")
    require(scenario.get("windowCount") == contract.get("windowCount"), "windowCount drift")
    require(scenario.get("result") == "PASS", "scenario result must be PASS")
    require(scenario.get("integrityResult") == "PASS", "scenario integrityResult must be PASS")

    coverage = scenario.get("coverage")
    require(isinstance(coverage, dict), "coverage must be object")
    for key, required in contract.get("requiredCoverage", {}).items():
        if required is True:
            require(coverage.get(key) is True, f"required coverage missing: {key}")

    observations = scenario.get("observations")
    window_count = integer(contract.get("windowCount"), "contract.windowCount")
    require(isinstance(observations, list) and len(observations) == window_count, "exact observation window count required")
    required_keys = contract.get("requiredObservationsPerWindow")
    require(isinstance(required_keys, list), "requiredObservationsPerWindow must be list")

    preview_requests = integer(contract.get("previewRequestsPerWindow"), "contract.previewRequestsPerWindow")
    upload_requests = integer(contract.get("signedUploadLifecyclesPerWindow"), "contract.signedUploadLifecyclesPerWindow")
    parser_runs = integer(contract.get("parserRecoveryRunsPerWindow"), "contract.parserRecoveryRunsPerWindow")
    delete_every = integer(contract.get("deletionCycleEveryWindows"), "contract.deletionCycleEveryWindows")
    queue_max = integer(contract.get("maximumScanQueuePending"), "contract.maximumScanQueuePending")
    previous_elapsed = -1.0
    previous_empty_acquire = -1
    previous_canceled_acquire = -1
    previous_acquire_duration = -1.0

    for index, observation in enumerate(observations, start=1):
        require(isinstance(observation, dict), f"observation {index} must be object")
        for key in required_keys:
            require(key in observation, f"observation {index} missing {key}")
        require(observation.get("window") == index, f"observation {index} window number drift")
        elapsed = nonnegative(observation.get("elapsedSeconds"), f"observation {index}.elapsedSeconds")
        require(elapsed > previous_elapsed, f"observation {index} elapsedSeconds must be monotonic")
        previous_elapsed = elapsed

        requests = observation.get("requestsBySurface")
        successes = observation.get("successesBySurface")
        failures = observation.get("failuresBySurface")
        status_counts = observation.get("statusClassCountsBySurface")
        require(all(isinstance(value, dict) for value in (requests, successes, failures, status_counts)), f"observation {index} surface maps required")
        expected_deletion = 1 if index % delete_every == 0 else 0
        expected_requests = {
            "previewRead": preview_requests,
            "signedUploadLifecycle": upload_requests,
            "parserSupervisor": parser_runs,
            "deletionWorker": expected_deletion,
        }
        for surface, expected in expected_requests.items():
            require(requests.get(surface) == expected, f"observation {index} {surface} request drift")
            require(successes.get(surface) == expected, f"observation {index} {surface} success drift")
            require(failures.get(surface) == 0, f"observation {index} {surface} failures must be zero")

        for surface in ("previewRead", "signedUploadLifecycle"):
            counts = status_counts.get(surface)
            require(isinstance(counts, dict), f"observation {index} {surface} status counts required")
            require(counts.get("2xx", 0) == expected_requests[surface], f"observation {index} {surface} must be all 2xx")
            for bad in ("3xx", "4xx", "5xx", "transport_error"):
                require(counts.get(bad, 0) == 0, f"observation {index} {surface} unexpected {bad}")
        parser_counts = status_counts.get("parserSupervisor")
        deletion_counts = status_counts.get("deletionWorker")
        require(isinstance(parser_counts, dict) and parser_counts.get("pass") == parser_runs and parser_counts.get("fail") == 0, f"observation {index} parser status drift")
        require(isinstance(deletion_counts, dict) and deletion_counts.get("pass") == expected_deletion and deletion_counts.get("fail") == 0, f"observation {index} deletion status drift")

        for latency_field in ("latencyP50MsBySurface", "latencyP95MsBySurface", "latencyP99MsBySurface"):
            latencies = observation.get(latency_field)
            require(isinstance(latencies, dict), f"observation {index} {latency_field} must be object")
            for surface in expected_requests:
                nonnegative(latencies.get(surface), f"observation {index}.{latency_field}.{surface}")

        require(integer(observation.get("heapAllocBytes"), f"observation {index}.heapAllocBytes") > 0, "heapAllocBytes must be positive")
        require(integer(observation.get("heapInuseBytes"), f"observation {index}.heapInuseBytes") > 0, "heapInuseBytes must be positive")
        require(integer(observation.get("rssBytes"), f"observation {index}.rssBytes") > 0, "rssBytes must be positive")
        require(integer(observation.get("goroutines"), f"observation {index}.goroutines") > 0, "goroutines must be positive")
        require(integer(observation.get("dbPoolMaxConns"), f"observation {index}.dbPoolMaxConns") > 0, "dbPoolMaxConns must be positive")
        for key in ("dbPoolTotalConns", "dbPoolAcquiredConns", "dbPoolIdleConns"):
            require(integer(observation.get(key), f"observation {index}.{key}") >= 0, f"{key} must be non-negative")
        empty_acquire = integer(observation.get("dbPoolEmptyAcquireCount"), f"observation {index}.dbPoolEmptyAcquireCount")
        canceled_acquire = integer(observation.get("dbPoolCanceledAcquireCount"), f"observation {index}.dbPoolCanceledAcquireCount")
        acquire_duration = nonnegative(observation.get("dbPoolAcquireDurationMs"), f"observation {index}.dbPoolAcquireDurationMs")
        require(empty_acquire >= previous_empty_acquire, f"observation {index} empty-acquire count regressed")
        require(canceled_acquire >= previous_canceled_acquire, f"observation {index} canceled-acquire count regressed")
        require(acquire_duration >= previous_acquire_duration, f"observation {index} acquire duration regressed")
        previous_empty_acquire = empty_acquire
        previous_canceled_acquire = canceled_acquire
        previous_acquire_duration = acquire_duration

        queue_pending = integer(observation.get("scanQueuePending"), f"observation {index}.scanQueuePending")
        require(queue_pending == upload_requests * index, f"observation {index} scan queue accounting drift")
        require(queue_pending <= queue_max, f"observation {index} scan queue exceeded hard ceiling")
        nonnegative(observation.get("scanQueueOldestPendingSeconds"), f"observation {index}.scanQueueOldestPendingSeconds")
        require(observation.get("deletionPending") == 0, f"observation {index} deletionPending must converge to zero")
        require(observation.get("deletionStuck") == 0, f"observation {index} deletionStuck must remain zero")
        require(observation.get("minioLifecycleSuccesses") == upload_requests, f"observation {index} MinIO success accounting drift")
        require(observation.get("parserRuns") == parser_runs, f"observation {index} parserRuns drift")
        require(observation.get("parserFailures") == 0, f"observation {index} parserFailures must be zero")

    require(previous_elapsed >= contract.get("minimumRunDurationSeconds", 3600), "final observation occurred before the 60-minute boundary")

    trends = scenario.get("trends")
    require(isinstance(trends, dict), "trends must be object")
    expected_scalar_slopes = {
        "rssSlopeBytesPerMinute": slope(observations, lambda o: float(o["rssBytes"])),
        "heapAllocSlopeBytesPerMinute": slope(observations, lambda o: float(o["heapAllocBytes"])),
        "heapInuseSlopeBytesPerMinute": slope(observations, lambda o: float(o["heapInuseBytes"])),
        "goroutineSlopePerMinute": slope(observations, lambda o: float(o["goroutines"])),
    }
    for key, expected in expected_scalar_slopes.items():
        close(trends.get(key), expected, f"trends.{key}")

    latency_trend = trends.get("latencyTrendBySurface")
    error_trend = trends.get("errorRateTrendBySurface")
    require(isinstance(latency_trend, dict) and isinstance(error_trend, dict), "latency/error trend maps required")
    for surface in ("previewRead", "signedUploadLifecycle", "parserSupervisor", "deletionWorker"):
        item = latency_trend.get(surface)
        require(isinstance(item, dict), f"latency trend missing surface {surface}")
        close(item.get("p95MsPerMinute"), slope(observations, lambda o, s=surface: float(o["latencyP95MsBySurface"][s])), f"trends.latency.{surface}.p95")
        close(item.get("p99MsPerMinute"), slope(observations, lambda o, s=surface: float(o["latencyP99MsBySurface"][s])), f"trends.latency.{surface}.p99")
        close(error_trend.get(surface), 0.0, f"trends.errorRate.{surface}")

    db_trend = trends.get("dbConnectionTrend")
    queue_trend = trends.get("scanQueueTrend")
    deletion_trend = trends.get("deletionBacklogTrend")
    require(isinstance(db_trend, dict) and isinstance(queue_trend, dict) and isinstance(deletion_trend, dict), "DB/queue/deletion trend maps required")
    close(db_trend.get("totalConnsPerMinute"), slope(observations, lambda o: float(o["dbPoolTotalConns"])), "db total conns trend")
    close(db_trend.get("acquiredConnsPerMinute"), slope(observations, lambda o: float(o["dbPoolAcquiredConns"])), "db acquired conns trend")
    close(db_trend.get("emptyAcquireCountPerMinute"), slope(observations, lambda o: float(o["dbPoolEmptyAcquireCount"])), "db empty acquire trend")
    close(db_trend.get("acquireDurationMsPerMinute"), slope(observations, lambda o: float(o["dbPoolAcquireDurationMs"])), "db acquire duration trend")
    close(queue_trend.get("pendingPerMinute"), slope(observations, lambda o: float(o["scanQueuePending"])), "queue pending trend")
    close(queue_trend.get("oldestPendingSecondsPerMinute"), slope(observations, lambda o: float(o["scanQueueOldestPendingSeconds"])), "queue age trend")
    close(deletion_trend.get("pendingPerMinute"), 0.0, "deletion pending trend")
    close(deletion_trend.get("stuckPerMinute"), 0.0, "deletion stuck trend")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions must be object")
    for key in ("allRequiredCoverageExecuted", "postRunRecoveryProbePassed", "scanQueueRemainsWithinBound", "deletionBacklogConverged"):
        require(assertions.get(key) is True, f"assertions.{key} must be true")
    for key in ("productionEvidence", "productionEquivalentDependencies", "leakProof", "capacityBoundaryEstablished", "operationalThresholdApproved"):
        require(assertions.get(key) is False, f"one local long run cannot enable assertions.{key}")

    return run_id, commit_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args()
    run_id, commit_sha = validate_result(args.result, args.expected_commit_sha)
    print("Memory OS sustained local soak result validation PASS")
    print(f"run id: {run_id}")
    print(f"source: {commit_sha}")
    print("duration: >=3600 seconds")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK RESULT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
