#!/usr/bin/env python3
"""Validate descriptive cross-run LOCAL_LONG_SOAK trend review authority."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
REVIEW_PATH = RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def finite(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{field} must be finite")
    return number


def validate_run(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(RESULT_VALIDATOR), str(path)],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(completed.returncode == 0,
            f"single-run validator rejected {path.name}: {(completed.stdout + completed.stderr)[-2000:]}")
    return load(path)


def run_trend_projection(run: dict[str, Any], path: Path) -> dict[str, Any]:
    scenario = run.get("scenario")
    require(isinstance(scenario, dict), f"{path.name}: scenario missing")
    trends = scenario.get("trends")
    assertions = scenario.get("assertions")
    require(isinstance(trends, dict), f"{path.name}: trends missing")
    require(isinstance(assertions, dict), f"{path.name}: assertions missing")
    projected = {
        "runId": run.get("runId"),
        "sourceCommitSha": run.get("commitSha"),
        "durationSeconds": scenario.get("durationSeconds"),
        "rssSlopeBytesPerMinute": trends.get("rssSlopeBytesPerMinute"),
        "heapAllocSlopeBytesPerMinute": trends.get("heapAllocSlopeBytesPerMinute"),
        "heapInuseSlopeBytesPerMinute": trends.get("heapInuseSlopeBytesPerMinute"),
        "goroutineSlopePerMinute": trends.get("goroutineSlopePerMinute"),
        "latencyTrendBySurface": trends.get("latencyTrendBySurface"),
        "errorRateTrendBySurface": trends.get("errorRateTrendBySurface"),
        "dbConnectionTrend": trends.get("dbConnectionTrend"),
        "scanQueueTrend": trends.get("scanQueueTrend"),
        "deletionBacklogTrend": trends.get("deletionBacklogTrend"),
        "postRunRecoveryProbePassed": assertions.get("postRunRecoveryProbePassed"),
    }
    finite(projected["durationSeconds"], f"{path.name}.scenario.durationSeconds")
    for field in (
        "rssSlopeBytesPerMinute",
        "heapAllocSlopeBytesPerMinute",
        "heapInuseSlopeBytesPerMinute",
        "goroutineSlopePerMinute",
    ):
        finite(projected[field], f"{path.name}.scenario.trends.{field}")
    for field in (
        "latencyTrendBySurface", "errorRateTrendBySurface",
        "dbConnectionTrend", "scanQueueTrend", "deletionBacklogTrend",
    ):
        require(isinstance(projected[field], dict), f"{path.name}.scenario.trends.{field} missing")
    require(projected["postRunRecoveryProbePassed"] is True,
            f"{path.name}: post-run recovery probe not passed")
    return projected


def review_trend_projection(trend: dict[str, Any], index: int) -> dict[str, Any]:
    projected = {
        "runId": trend.get("runId"),
        "sourceCommitSha": trend.get("sourceCommitSha"),
        "durationSeconds": trend.get("durationSeconds"),
        "rssSlopeBytesPerMinute": trend.get("rssSlopeBytesPerMinute"),
        "heapAllocSlopeBytesPerMinute": trend.get("heapAllocSlopeBytesPerMinute"),
        "heapInuseSlopeBytesPerMinute": trend.get("heapInuseSlopeBytesPerMinute"),
        "goroutineSlopePerMinute": trend.get("goroutineSlopePerMinute"),
        "latencyTrendBySurface": trend.get("latencyTrendBySurface"),
        "errorRateTrendBySurface": trend.get("errorRateTrendBySurface"),
        "dbConnectionTrend": trend.get("dbConnectionTrend"),
        "scanQueueTrend": trend.get("scanQueueTrend"),
        "deletionBacklogTrend": trend.get("deletionBacklogTrend"),
        "postRunRecoveryProbePassed": trend.get("postRunRecoveryProbePassed"),
    }
    finite(projected["durationSeconds"], f"runTrends[{index}].durationSeconds")
    for field in (
        "rssSlopeBytesPerMinute",
        "heapAllocSlopeBytesPerMinute",
        "heapInuseSlopeBytesPerMinute",
        "goroutineSlopePerMinute",
    ):
        finite(projected[field], f"runTrends[{index}].{field}")
    for field in (
        "latencyTrendBySurface", "errorRateTrendBySurface",
        "dbConnectionTrend", "scanQueueTrend", "deletionBacklogTrend",
    ):
        require(isinstance(projected[field], dict), f"runTrends[{index}].{field} missing")
    require(projected["postRunRecoveryProbePassed"] is True,
            f"runTrends[{index}] recovery probe not passed")
    return projected


def main() -> int:
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    minimum_runs = int(contract.get("minimumIndependentRuns", 2))
    require(len(paths) >= minimum_runs,
            f"trend review requires at least {minimum_runs} committed run documents")
    runs = [validate_run(path) for path in paths]
    run_ids = sorted(str(run["runId"]) for run in runs)
    commits = sorted({str(run["commitSha"]) for run in runs})
    expected_trends = sorted(
        (run_trend_projection(run, path) for run, path in zip(runs, paths)),
        key=lambda item: str(item["runId"]),
    )
    expected_by_id = {str(item["runId"]): item for item in expected_trends}

    review = load(REVIEW_PATH)
    require(review.get("schemaVersion") == "memory-os-sustained-local-soak-trend-review.v1",
            "review schemaVersion drift")
    require(review.get("classification") == "LOCAL_LONG_SOAK_DESCRIPTIVE_CROSS_RUN_REVIEW",
            "review classification drift")
    require(review.get("scenarioId") == contract.get("scenarioId"),
            "review scenario drift")
    require(review.get("reviewedRunCount") == len(paths),
            "reviewedRunCount drift")
    require(review.get("reviewedRunIds") == run_ids,
            "reviewedRunIds drift")
    require(review.get("reviewedSourceCommitShas") == commits,
            "reviewed source commit set drift")
    require(review.get("minimumIndependentRunsSatisfied") is True,
            "minimum independent runs not satisfied")
    require(review.get("allReviewedRunsPassedPerRunValidator") is True,
            "review must cover only per-run PASS documents")
    require(review.get("allReviewedRunsPostRecoveryProbePassed") is True,
            "review must require post-run recovery PASS for every run")

    trends = review.get("runTrends")
    require(isinstance(trends, list) and len(trends) == len(paths),
            "runTrends must cover every run")
    projected_review_trends: list[dict[str, Any]] = []
    for index, trend in enumerate(trends):
        require(isinstance(trend, dict), f"runTrends[{index}] must be object")
        projected_review_trends.append(review_trend_projection(trend, index))
    projected_review_trends.sort(key=lambda item: str(item["runId"]))
    require(projected_review_trends == expected_trends,
            "runTrends must be re-derived exactly from validated run documents")

    latest_pair = review.get("latestPair")
    require(isinstance(latest_pair, dict), "latestPair missing")
    run_a = latest_pair.get("runA")
    run_b = latest_pair.get("runB")
    require(run_a in expected_by_id and run_b in expected_by_id and run_a != run_b,
            "latestPair run IDs invalid")
    expected_deltas = {
        "rssSlopeDeltaBytesPerMinute":
            float(expected_by_id[str(run_b)]["rssSlopeBytesPerMinute"]) -
            float(expected_by_id[str(run_a)]["rssSlopeBytesPerMinute"]),
        "heapAllocSlopeDeltaBytesPerMinute":
            float(expected_by_id[str(run_b)]["heapAllocSlopeBytesPerMinute"]) -
            float(expected_by_id[str(run_a)]["heapAllocSlopeBytesPerMinute"]),
        "heapInuseSlopeDeltaBytesPerMinute":
            float(expected_by_id[str(run_b)]["heapInuseSlopeBytesPerMinute"]) -
            float(expected_by_id[str(run_a)]["heapInuseSlopeBytesPerMinute"]),
        "goroutineSlopeDeltaPerMinute":
            float(expected_by_id[str(run_b)]["goroutineSlopePerMinute"]) -
            float(expected_by_id[str(run_a)]["goroutineSlopePerMinute"]),
    }
    for field, expected in expected_deltas.items():
        actual = finite(latest_pair.get(field), f"latestPair.{field}")
        require(actual == expected,
                f"latestPair.{field} must be derived from validated run trends")

    findings = review.get("reviewFindings")
    require(isinstance(findings, list) and len(findings) >= 5 and
            all(isinstance(item, str) and item for item in findings),
            "reviewFindings incomplete")
    joined = "\n".join(findings)
    for phrase in (
        "no slope is converted into an automatic leak/no-leak conclusion",
        "not treated as production queue stability",
        "post-run recovery probe",
    ):
        require(phrase in joined, f"review finding missing: {phrase}")

    require(review.get("trendReviewCompleted") is True,
            "descriptive trend review must be completed")
    require(review.get("localSustainedSoakEvidenceEligible") is True,
            "review must mark local-only evidence eligible")
    require(review.get("automaticLeakConclusionMade") is False,
            "automatic leak conclusion is forbidden")
    for field in (
        "leakProof", "operationalThresholdApproved", "capacityBoundaryEstablished",
        "productionEquivalentDependencies", "productionEvidence",
        "independentProductionReviewCompleted", "productionReady",
    ):
        require(review.get(field) is False, f"review cannot promote {field}")
    require(review.get("decision") ==
            "DESCRIPTIVE_LOCAL_REPEATABILITY_REVIEW_COMPLETE_NO_LEAK_OR_PRODUCTION_CONCLUSION",
            "review decision drift")

    print("Memory OS sustained local soak trend review validation PASS")
    print(f"reviewed runs: {len(paths)}")
    print("review trends re-derived from validated run documents: true")
    print("latest pair deltas re-derived from validated run trends: true")
    print("local-only evidence eligible: true")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK TREND REVIEW VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
