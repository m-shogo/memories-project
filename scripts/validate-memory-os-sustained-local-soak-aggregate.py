#!/usr/bin/env python3
"""Validate repeated local long-soak result documents and their aggregate authority."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
AGGREGATE_PATH = RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
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
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    return float(value)


def validate_run(path: Path, contract: dict[str, Any]) -> tuple[str, str]:
    doc = load(path)
    require(doc.get("schemaVersion") == contract.get("resultsSchemaVersion"), f"{path.name}: schema drift")
    commit = doc.get("commitSha")
    run_id = doc.get("runId")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, f"{path.name}: full source commit required")
    require(isinstance(run_id, str) and run_id, f"{path.name}: runId required")

    environment = doc.get("environment")
    require(isinstance(environment, dict), f"{path.name}: environment required")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", f"{path.name}: dependency mode drift")
    require(environment.get("classification") == "LOCAL_LONG_SOAK", f"{path.name}: classification drift")
    require(environment.get("syntheticDataOnly") is True, f"{path.name}: synthetic-only required")
    require(environment.get("loopbackDependenciesOnly") is True, f"{path.name}: loopback-only required")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"{path.name}: environment.{key} must remain false")

    scenario = doc.get("scenario")
    require(isinstance(scenario, dict), f"{path.name}: scenario required")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), f"{path.name}: scenario id drift")
    duration = number(scenario.get("durationSeconds"), f"{path.name}.durationSeconds")
    require(duration >= contract.get("minimumRunDurationSeconds", 3600), f"{path.name}: run shorter than 60 minutes")
    require(duration <= contract.get("maximumSingleRunDurationSeconds", 5400) + 120, f"{path.name}: run exceeded bounded duration tolerance")
    require(scenario.get("result") == "PASS", f"{path.name}: run must PASS")
    require(scenario.get("integrityResult") == "PASS", f"{path.name}: integrity must PASS")

    coverage = scenario.get("coverage")
    require(isinstance(coverage, dict), f"{path.name}: coverage required")
    for key, required in contract.get("requiredCoverage", {}).items():
        if required is True:
            require(coverage.get(key) is True, f"{path.name}: missing coverage {key}")

    observations = scenario.get("observations")
    require(isinstance(observations, list) and len(observations) >= 12, f"{path.name}: at least 12 observation windows required")
    required_observations = contract.get("requiredObservationsPerWindow", [])
    previous_elapsed = -1.0
    for index, observation in enumerate(observations):
        require(isinstance(observation, dict), f"{path.name}: observation {index} must be object")
        for key in required_observations:
            require(key in observation, f"{path.name}: observation {index} missing {key}")
        elapsed = number(observation.get("elapsedSeconds"), f"{path.name}: observation {index}.elapsedSeconds")
        require(elapsed > previous_elapsed, f"{path.name}: observation elapsed time must be monotonic")
        previous_elapsed = elapsed

    trends = scenario.get("trends")
    require(isinstance(trends, dict), f"{path.name}: trends required")
    for key in (
        "rssSlopeBytesPerMinute",
        "heapAllocSlopeBytesPerMinute",
        "heapInuseSlopeBytesPerMinute",
        "goroutineSlopePerMinute",
    ):
        number(trends.get(key), f"{path.name}.trends.{key}")
    require(isinstance(trends.get("latencyTrendBySurface"), dict), f"{path.name}: latency trend required")
    require(isinstance(trends.get("errorRateTrendBySurface"), dict), f"{path.name}: error trend required")
    require(isinstance(trends.get("dbConnectionTrend"), dict), f"{path.name}: DB trend required")
    require(isinstance(trends.get("scanQueueTrend"), dict), f"{path.name}: queue trend required")
    require(isinstance(trends.get("deletionBacklogTrend"), dict), f"{path.name}: deletion trend required")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), f"{path.name}: assertions required")
    require(assertions.get("postRunRecoveryProbePassed") is True, f"{path.name}: recovery probe required")
    require(assertions.get("allRequiredCoverageExecuted") is True, f"{path.name}: all coverage assertion required")
    for key in (
        "productionEvidence",
        "productionEquivalentDependencies",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
    ):
        require(assertions.get(key) is False, f"{path.name}: one local run cannot enable {key}")

    serialized = json.dumps(doc, ensure_ascii=False)
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "Bearer ",
        "X-Amz-Credential",
        "acct_",
    ):
        require(forbidden not in serialized, f"{path.name}: forbidden sensitive/runtime material: {forbidden}")
    return run_id, commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    if not paths:
        require(not AGGREGATE_PATH.exists(), "aggregate cannot exist without run documents")
        require(not args.require_evidence, "no local long-soak evidence has been committed")
        print("Memory OS sustained local soak aggregate validation PASS (foundation only)")
        print("committed long runs: 0")
        print("sustained soak evidence: false")
        return 0

    run_ids: set[str] = set()
    commits: set[str] = set()
    for path in paths:
        run_id, commit = validate_run(path, contract)
        require(run_id not in run_ids, f"duplicate long-soak runId: {run_id}")
        run_ids.add(run_id)
        commits.add(commit)

    aggregate = load(AGGREGATE_PATH)
    require(aggregate.get("schemaVersion") == "memory-os-sustained-local-soak-aggregate.v1", "aggregate schema drift")
    require(aggregate.get("scenarioId") == contract.get("scenarioId"), "aggregate scenario drift")
    require(aggregate.get("runCount") == len(paths), "aggregate run count drift")
    require(aggregate.get("runIds") == sorted(run_ids), "aggregate runIds drift")
    require(aggregate.get("sourceCommitShas") == sorted(commits), "aggregate source commits drift")
    require(aggregate.get("allRunsDurationAtLeast3600Seconds") is True, "aggregate duration assertion required")
    require(aggregate.get("allRunsRequiredCoverageComplete") is True, "aggregate coverage assertion required")
    for key in (
        "productionEvidence",
        "productionEquivalentDependencies",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "productionReady",
    ):
        require(aggregate.get(key) is False, f"aggregate local evidence cannot enable {key}")

    enough_runs = len(paths) >= contract.get("minimumIndependentRuns", 2)
    require(aggregate.get("minimumIndependentRunsSatisfied") is enough_runs, "aggregate repeated-run decision drift")
    if args.require_evidence:
        require(enough_runs, "fewer than two independent 60-minute-or-longer runs")
        require(aggregate.get("trendReviewCompleted") is True, "trend review must be completed before sustained-soak evidence")
        require(aggregate.get("sustainedSoakEvidence") is True, "aggregate must explicitly register sustained local soak evidence")
    else:
        require(isinstance(aggregate.get("sustainedSoakEvidence"), bool), "aggregate sustainedSoakEvidence must be boolean")

    print("Memory OS sustained local soak aggregate validation PASS")
    print(f"committed long runs: {len(paths)}")
    print(f"minimum independent runs satisfied: {str(enough_runs).lower()}")
    print(f"sustained soak evidence: {str(aggregate.get('sustainedSoakEvidence')).lower()}")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK AGGREGATE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
