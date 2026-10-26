#!/usr/bin/env python3
"""Validate descriptive cross-run LOCAL_LONG_SOAK trend review authority."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
RESULT_DIR = CANONICAL_RESULT_DIR
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
REVIEW_PATH = RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
TIMESTAMP_DURATION_TOLERANCE_SECONDS = 2.0
GENERATION_LAG_LIMIT_SECONDS = 120.0
UTC_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z$"
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def reject_nonfinite_constant(_token: str) -> None:
    raise Fail("sustained local-soak trend JSON non-finite constant rejected")


def parse_finite_float(token: str) -> float:
    value = float(token)
    require(math.isfinite(value), "sustained local-soak trend JSON non-finite number rejected")
    return value


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "sustained local-soak trend JSON duplicate key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise Fail("sustained local-soak trend JSON unreadable or invalid") from None
    require(isinstance(value, dict), "sustained local-soak trend JSON root must be object")
    return value


def finite(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise Fail(f"{field} must be finite") from None
    require(math.isfinite(number), f"{field} must be finite")
    return number


def bounded_delta(a: Any, b: Any, field: str) -> float:
    left = finite(a, f"{field} runA")
    right = finite(b, f"{field} runB")
    delta = right - left
    require(math.isfinite(delta), f"{field} expected cross-run delta must be finite")
    return delta


def utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            f"{field} must be strict UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Fail(f"{field} must be valid RFC3339") from None
    require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
            f"{field} must resolve to UTC")
    return parsed


def require_local_run_path(path: Path) -> None:
    """Do not admit a symlink or noncanonical run before invoking child validators."""
    require(path.parent == RESULT_DIR, "run path must be in canonical result directory")
    require(not path.is_symlink() and path.is_file(), "run path missing or symlinked")
    try:
        require(path.resolve(strict=True).parent == RESULT_DIR.resolve(strict=True),
                "run path escaped canonical result directory")
    except OSError:
        raise Fail("run path cannot be resolved") from None


def validate_run(path: Path) -> dict[str, Any]:
    require_local_run_path(path)
    completed = subprocess.run(
        [sys.executable, str(RESULT_VALIDATOR), str(path)],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(completed.returncode == 0,
            f"single-run validator rejected (exit {completed.returncode})")
    return load(path)


def run_trend_projection(run: dict[str, Any], path: Path) -> tuple[datetime, dict[str, Any]]:
    scenario = run.get("scenario")
    require(isinstance(scenario, dict), f"{path.name}: scenario missing")
    started_at = utc_timestamp(scenario.get("startedAt"), f"{path.name}.scenario.startedAt")
    completed_at = utc_timestamp(scenario.get("completedAt"), f"{path.name}.scenario.completedAt")
    generated_at = utc_timestamp(run.get("generatedAt"), f"{path.name}.generatedAt")
    duration_seconds = finite(scenario.get("durationSeconds"), f"{path.name}.scenario.durationSeconds")
    wall_duration = (completed_at - started_at).total_seconds()
    require(wall_duration >= 0, f"{path.name}: scenario.completedAt cannot precede scenario.startedAt")
    require(abs(wall_duration - duration_seconds) <= TIMESTAMP_DURATION_TOLERANCE_SECONDS,
            f"{path.name}: scenario timestamps must agree with durationSeconds")
    generation_lag = (generated_at - completed_at).total_seconds()
    require(0 <= generation_lag <= GENERATION_LAG_LIMIT_SECONDS,
            f"{path.name}: generatedAt must follow completion within bounded evidence-write lag")
    trends = scenario.get("trends")
    assertions = scenario.get("assertions")
    require(isinstance(trends, dict), f"{path.name}: trends missing")
    require(isinstance(assertions, dict), f"{path.name}: assertions missing")
    projected = {
        "runId": run.get("runId"),
        "sourceCommitSha": run.get("commitSha"),
        "durationSeconds": duration_seconds,
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
    return completed_at, projected


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
    require(RESULT_DIR == CANONICAL_RESULT_DIR and RESULT_DIR.is_dir() and not RESULT_DIR.is_symlink(),
            "canonical result directory authority drift")
    require(RESULT_DIR.resolve(strict=True) == CANONICAL_RESULT_DIR, "result directory escaped repository")
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    minimum_runs = int(contract.get("minimumIndependentRuns", 2))
    require(len(paths) >= minimum_runs,
            f"trend review requires at least {minimum_runs} committed run documents")
    runs = [validate_run(path) for path in paths]
    run_ids = sorted(str(run["runId"]) for run in runs)
    commits = sorted({str(run["commitSha"]) for run in runs})
    chronological_expected = [run_trend_projection(run, path) for run, path in zip(runs, paths)]
    chronological_expected.sort(key=lambda item: (item[0], str(item[1]["runId"])))
    expected_latest_a = chronological_expected[-2][1]
    expected_latest_b = chronological_expected[-1][1]
    expected_trends = sorted(
        (projected for _, projected in chronological_expected),
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
    require(run_a == expected_latest_a["runId"] and run_b == expected_latest_b["runId"],
            "latestPair must name the two newest validated runs by scenario.completedAt chronology")
    expected_deltas = {
        "rssSlopeDeltaBytesPerMinute": bounded_delta(
            expected_by_id[str(run_a)]["rssSlopeBytesPerMinute"],
            expected_by_id[str(run_b)]["rssSlopeBytesPerMinute"], "rss slope"),
        "heapAllocSlopeDeltaBytesPerMinute": bounded_delta(
            expected_by_id[str(run_a)]["heapAllocSlopeBytesPerMinute"],
            expected_by_id[str(run_b)]["heapAllocSlopeBytesPerMinute"], "heap allocation slope"),
        "heapInuseSlopeDeltaBytesPerMinute": bounded_delta(
            expected_by_id[str(run_a)]["heapInuseSlopeBytesPerMinute"],
            expected_by_id[str(run_b)]["heapInuseSlopeBytesPerMinute"], "heap inuse slope"),
        "goroutineSlopeDeltaPerMinute": bounded_delta(
            expected_by_id[str(run_a)]["goroutineSlopePerMinute"],
            expected_by_id[str(run_b)]["goroutineSlopePerMinute"], "goroutine slope"),
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
    print("run chronology bound to UTC timestamps and measured duration: true")
    print("latest pair selected by validated scenario completion chronology: true")
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
