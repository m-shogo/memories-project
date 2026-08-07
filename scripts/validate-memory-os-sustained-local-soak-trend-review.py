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


def finite(value: Any, field: str) -> None:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    require(math.isfinite(float(value)), f"{field} must be finite")


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


def main() -> int:
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    minimum_runs = int(contract.get("minimumIndependentRuns", 2))
    require(len(paths) >= minimum_runs,
            f"trend review requires at least {minimum_runs} committed run documents")
    runs = [validate_run(path) for path in paths]
    run_ids = sorted(str(run["runId"]) for run in runs)
    commits = sorted({str(run["commitSha"]) for run in runs})

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
    trend_ids = sorted(str(item.get("runId")) for item in trends if isinstance(item, dict))
    require(trend_ids == run_ids, "runTrends run IDs drift")
    for index, trend in enumerate(trends):
        require(isinstance(trend, dict), f"runTrends[{index}] must be object")
        for field in (
            "rssSlopeBytesPerMinute",
            "heapAllocSlopeBytesPerMinute",
            "heapInuseSlopeBytesPerMinute",
            "goroutineSlopePerMinute",
        ):
            finite(trend.get(field), f"runTrends[{index}].{field}")
        for field in (
            "latencyTrendBySurface", "errorRateTrendBySurface",
            "dbConnectionTrend", "scanQueueTrend", "deletionBacklogTrend",
        ):
            require(isinstance(trend.get(field), dict), f"runTrends[{index}].{field} missing")
        require(trend.get("postRunRecoveryProbePassed") is True,
                f"runTrends[{index}] recovery probe not passed")

    latest_pair = review.get("latestPair")
    require(isinstance(latest_pair, dict), "latestPair missing")
    require(latest_pair.get("runA") in run_ids and latest_pair.get("runB") in run_ids and
            latest_pair.get("runA") != latest_pair.get("runB"),
            "latestPair run IDs invalid")
    for field in (
        "rssSlopeDeltaBytesPerMinute", "heapAllocSlopeDeltaBytesPerMinute",
        "heapInuseSlopeDeltaBytesPerMinute", "goroutineSlopeDeltaPerMinute",
    ):
        finite(latest_pair.get(field), f"latestPair.{field}")

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
