#!/usr/bin/env python3
"""Validate repeated LOCAL_LONG_SOAK documents and descriptive aggregate authority."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
AGGREGATE_PATH = RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
REVIEW_PATH = RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py"


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


def run_validator(command: list[str], label: str) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise Fail(
            f"{label} failed:\n"
            f"{completed.stdout[-4000:]}{completed.stderr[-4000:]}"
        )


def finite_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{field} must be finite")
    return number


def trend_summary(value: dict[str, Any], path: Path) -> dict[str, Any]:
    scenario = value.get("scenario")
    require(isinstance(scenario, dict), f"{path.name}: scenario missing")
    trends = scenario.get("trends")
    require(isinstance(trends, dict), f"{path.name}: trends missing")
    summary = {
        "runId": value.get("runId"),
        "sourceCommitSha": value.get("commitSha"),
        "rssSlopeBytesPerMinute": finite_number(trends.get("rssSlopeBytesPerMinute"), f"{path.name} rss slope"),
        "heapAllocSlopeBytesPerMinute": finite_number(trends.get("heapAllocSlopeBytesPerMinute"), f"{path.name} heap alloc slope"),
        "heapInuseSlopeBytesPerMinute": finite_number(trends.get("heapInuseSlopeBytesPerMinute"), f"{path.name} heap inuse slope"),
        "goroutineSlopePerMinute": finite_number(trends.get("goroutineSlopePerMinute"), f"{path.name} goroutine slope"),
        "latencyTrendBySurface": trends.get("latencyTrendBySurface"),
        "errorRateTrendBySurface": trends.get("errorRateTrendBySurface"),
        "dbConnectionTrend": trends.get("dbConnectionTrend"),
        "scanQueueTrend": trends.get("scanQueueTrend"),
        "deletionBacklogTrend": trends.get("deletionBacklogTrend"),
    }
    for field in (
        "latencyTrendBySurface",
        "errorRateTrendBySurface",
        "dbConnectionTrend",
        "scanQueueTrend",
        "deletionBacklogTrend",
    ):
        require(isinstance(summary[field], dict), f"{path.name}: {field} missing")
    return summary


def validate_run(path: Path) -> tuple[str, str, dict[str, Any]]:
    run_validator([sys.executable, str(RESULT_VALIDATOR), str(path)],
                  f"single-run validator for {path.relative_to(ROOT)}")
    value = load(path)
    run_id = value.get("runId")
    commit_sha = value.get("commitSha")
    require(isinstance(run_id, str) and run_id, f"{path.name}: runId required")
    require(isinstance(commit_sha, str) and len(commit_sha) == 40, f"{path.name}: commitSha required")
    return run_id, commit_sha, trend_summary(value, path)


def review_trend_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "runId": value.get("runId"),
        "sourceCommitSha": value.get("sourceCommitSha"),
        "rssSlopeBytesPerMinute": value.get("rssSlopeBytesPerMinute"),
        "heapAllocSlopeBytesPerMinute": value.get("heapAllocSlopeBytesPerMinute"),
        "heapInuseSlopeBytesPerMinute": value.get("heapInuseSlopeBytesPerMinute"),
        "goroutineSlopePerMinute": value.get("goroutineSlopePerMinute"),
        "latencyTrendBySurface": value.get("latencyTrendBySurface"),
        "errorRateTrendBySurface": value.get("errorRateTrendBySurface"),
        "dbConnectionTrend": value.get("dbConnectionTrend"),
        "scanQueueTrend": value.get("scanQueueTrend"),
        "deletionBacklogTrend": value.get("deletionBacklogTrend"),
    }


def pair_delta(a: dict[str, Any], b: dict[str, Any], field: str) -> float:
    return float(b[field]) - float(a[field])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-local-evidence", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    if not paths:
        require(not AGGREGATE_PATH.exists(), "aggregate cannot exist without run documents")
        require(not REVIEW_PATH.exists(), "trend review cannot exist without run documents")
        require(not args.require_local_evidence, "no LOCAL_LONG_SOAK result documents have been committed")
        print("Memory OS sustained local soak aggregate validation PASS (foundation only)")
        print("committed long runs: 0")
        print("local sustained soak evidence: false")
        print("production sustained soak evidence: false")
        return 0

    run_ids: set[str] = set()
    commits: set[str] = set()
    expected_trends: list[dict[str, Any]] = []
    for path in paths:
        run_id, commit, summary = validate_run(path)
        require(run_id not in run_ids, f"duplicate long-soak runId: {run_id}")
        run_ids.add(run_id)
        commits.add(commit)
        expected_trends.append(summary)
    expected_trends.sort(key=lambda item: item["runId"])

    aggregate = load(AGGREGATE_PATH)
    require(aggregate.get("schemaVersion") == "memory-os-sustained-local-soak-aggregate.v1", "aggregate schema drift")
    require(aggregate.get("scenarioId") == contract.get("scenarioId"), "aggregate scenario drift")
    require(aggregate.get("classification") == "LOCAL_LONG_SOAK", "aggregate classification drift")
    require(aggregate.get("runCount") == len(paths), "aggregate run count drift")
    require(aggregate.get("runIds") == sorted(run_ids), "aggregate runIds drift")
    require(aggregate.get("sourceCommitShas") == sorted(commits), "aggregate source commits drift")
    require(aggregate.get("allRunsDurationAtLeast3600Seconds") is True, "aggregate duration assertion required")
    require(aggregate.get("allRunsRequiredCoverageComplete") is True, "aggregate coverage assertion required")

    enough_runs = len(paths) >= int(contract.get("minimumIndependentRuns", 2))
    require(aggregate.get("minimumIndependentRunsSatisfied") is enough_runs, "aggregate repeated-run decision drift")
    review = aggregate.get("trendReview")
    require(isinstance(review, dict), "trendReview object required")
    require(review.get("automaticLeakConclusionForbidden") is True, "automatic leak conclusion must remain forbidden")
    require(review.get("automaticOperatingThresholdApprovalForbidden") is True, "automatic operating-threshold approval must remain forbidden")
    run_trends = review.get("runTrends")
    require(isinstance(run_trends, list), "aggregate trend summary missing")
    require(run_trends == expected_trends,
            "aggregate trend summary must be re-derived exactly from validated run documents")

    local_evidence = aggregate.get("localSustainedSoakEvidence")
    trend_review_completed = aggregate.get("trendReviewCompleted")
    require(isinstance(local_evidence, bool), "localSustainedSoakEvidence must be boolean")
    require(isinstance(trend_review_completed, bool), "trendReviewCompleted must be boolean")

    review_ref = review.get("reviewEvidenceRef")
    if trend_review_completed:
        require(enough_runs, "trend review cannot complete before repeated runs")
        require(review.get("status") == "COMPLETED_DESCRIPTIVE_LOCAL_ONLY",
                "completed review status drift")
        require(review_ref == str(REVIEW_PATH.relative_to(ROOT)),
                "completed aggregate must reference canonical trend-review evidence")
        require(REVIEW_PATH.is_file(), "completed trend review evidence file missing")
        run_validator([sys.executable, str(REVIEW_VALIDATOR)], "trend-review validator")
        review_doc = load(REVIEW_PATH)
        require(review_doc.get("reviewedRunIds") == sorted(run_ids),
                "trend-review evidence run set drift")
        require(review_doc.get("reviewedSourceCommitShas") == sorted(commits),
                "trend-review evidence source set drift")
        require(review_doc.get("localSustainedSoakEvidenceEligible") is True,
                "completed trend review does not permit local-only evidence")
        require(review_doc.get("automaticLeakConclusionMade") is False and
                review_doc.get("leakProof") is False,
                "trend review cannot conclude leak/no-leak proof")
        require(review_doc.get("productionEvidence") is False and
                review_doc.get("productionReady") is False,
                "trend review cannot be production evidence")

        review_trends = review_doc.get("runTrends")
        require(isinstance(review_trends, list) and len(review_trends) == len(expected_trends),
                "trend-review runTrends coverage drift")
        projected_review_trends = sorted(
            (review_trend_projection(item) for item in review_trends if isinstance(item, dict)),
            key=lambda item: str(item.get("runId")),
        )
        require(projected_review_trends == expected_trends,
                "trend-review values must be re-derived exactly from validated run documents")

        latest_pair = review_doc.get("latestPair")
        require(isinstance(latest_pair, dict), "trend-review latestPair missing")
        expected_by_id = {item["runId"]: item for item in expected_trends}
        run_a = latest_pair.get("runA")
        run_b = latest_pair.get("runB")
        require(run_a in expected_by_id and run_b in expected_by_id and run_a != run_b,
                "trend-review latestPair run IDs invalid")
        a = expected_by_id[str(run_a)]
        b = expected_by_id[str(run_b)]
        expected_deltas = {
            "rssSlopeDeltaBytesPerMinute": pair_delta(a, b, "rssSlopeBytesPerMinute"),
            "heapAllocSlopeDeltaBytesPerMinute": pair_delta(a, b, "heapAllocSlopeBytesPerMinute"),
            "heapInuseSlopeDeltaBytesPerMinute": pair_delta(a, b, "heapInuseSlopeBytesPerMinute"),
            "goroutineSlopeDeltaPerMinute": pair_delta(a, b, "goroutineSlopePerMinute"),
        }
        for field, expected in expected_deltas.items():
            actual = finite_number(latest_pair.get(field), f"trend-review latestPair.{field}")
            require(actual == expected,
                    f"trend-review latestPair.{field} must be derived from validated run trends")
    else:
        require(review_ref is None, "pending aggregate cannot reference completed trend review")
        require(review.get("status") in {"PENDING", "WAITING_FOR_REPEATED_RUNS"},
                "pending trend review status drift")

    if local_evidence:
        require(enough_runs, "local sustained-soak evidence requires at least two independent runs")
        require(trend_review_completed is True, "local sustained-soak evidence requires completed trend review")
        require(REVIEW_PATH.is_file(), "local sustained-soak evidence requires trend-review evidence")
    if not enough_runs:
        require(local_evidence is False, "one run can never become local sustained-soak evidence")
        require(trend_review_completed is False, "trend review cannot complete before repeated runs")

    for key in (
        "productionSustainedSoakEvidence",
        "leakProof",
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "productionReady",
    ):
        require(aggregate.get(key) is False, f"LOCAL_LONG_SOAK aggregate cannot enable {key}")

    if args.require_local_evidence:
        require(enough_runs, "fewer than two independent 60-minute-or-longer runs")
        require(trend_review_completed is True, "trend review remains pending")
        require(local_evidence is True, "local sustained-soak evidence is not approved")

    print("Memory OS sustained local soak aggregate validation PASS")
    print(f"committed long runs: {len(paths)}")
    print(f"minimum independent runs satisfied: {str(enough_runs).lower()}")
    print(f"trend review completed: {str(trend_review_completed).lower()}")
    print("aggregate/review trends re-derived from run documents: true")
    print(f"local sustained soak evidence: {str(local_evidence).lower()}")
    print("production sustained soak evidence: false")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK AGGREGATE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
