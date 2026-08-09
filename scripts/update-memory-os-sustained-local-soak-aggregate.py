#!/usr/bin/env python3
"""Build descriptive LOCAL_LONG_SOAK aggregate without leak or production promotion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
AGGREGATE_PATH = RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
REVIEW_PATH = RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} root must be object")
    return value


def validate(path: Path, validator: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(validator), str(path)] if validator == RESULT_VALIDATOR else
        [sys.executable, str(validator)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(f"validator rejected {path.relative_to(ROOT)}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    if not paths:
        if AGGREGATE_PATH.exists():
            AGGREGATE_PATH.unlink()
        if REVIEW_PATH.exists():
            REVIEW_PATH.unlink()
        print("No sustained local soak result documents to aggregate")
        return 0

    run_ids: list[str] = []
    source_shas: list[str] = []
    durations: list[float] = []
    trend_summaries: list[dict[str, Any]] = []
    for path in paths:
        validate(path, RESULT_VALIDATOR)
        document = load(path)
        scenario = document["scenario"]
        run_ids.append(document["runId"])
        source_shas.append(document["commitSha"])
        durations.append(float(scenario["durationSeconds"]))
        trends = scenario["trends"]
        trend_summaries.append({
            "runId": document["runId"],
            "sourceCommitSha": document["commitSha"],
            "rssSlopeBytesPerMinute": trends["rssSlopeBytesPerMinute"],
            "heapAllocSlopeBytesPerMinute": trends["heapAllocSlopeBytesPerMinute"],
            "heapInuseSlopeBytesPerMinute": trends["heapInuseSlopeBytesPerMinute"],
            "goroutineSlopePerMinute": trends["goroutineSlopePerMinute"],
            "latencyTrendBySurface": trends["latencyTrendBySurface"],
            "errorRateTrendBySurface": trends["errorRateTrendBySurface"],
            "dbConnectionTrend": trends["dbConnectionTrend"],
            "scanQueueTrend": trends["scanQueueTrend"],
            "deletionBacklogTrend": trends["deletionBacklogTrend"],
        })

    if len(run_ids) != len(set(run_ids)):
        raise SystemExit("duplicate long-soak runId")

    minimum_runs = int(contract["minimumIndependentRuns"])
    enough_runs = len(paths) >= minimum_runs
    review_completed = False
    local_evidence = False
    review_ref: str | None = None
    stale_review_ignored = False
    if enough_runs and REVIEW_PATH.is_file():
        review = load(REVIEW_PATH)
        current_run_ids = sorted(run_ids)
        current_source_shas = sorted(set(source_shas))
        review_is_current = (
            review.get("reviewedRunIds") == current_run_ids
            and review.get("reviewedSourceCommitShas") == current_source_shas
            and review.get("reviewedRunCount") == len(paths)
        )
        if review_is_current:
            validate(REVIEW_PATH, REVIEW_VALIDATOR)
            review_completed = review.get("trendReviewCompleted") is True
            local_evidence = (
                review_completed and
                review.get("localSustainedSoakEvidenceEligible") is True and
                review.get("leakProof") is False and
                review.get("productionEvidence") is False and
                review.get("productionReady") is False
            )
            review_ref = str(REVIEW_PATH.relative_to(ROOT))
        else:
            stale_review_ignored = True

    aggregate = {
        "schemaVersion": "memory-os-sustained-local-soak-aggregate.v1",
        "scenarioId": contract["scenarioId"],
        "classification": "LOCAL_LONG_SOAK",
        "runCount": len(paths),
        "runIds": sorted(run_ids),
        "sourceCommitShas": sorted(set(source_shas)),
        "allRunsDurationAtLeast3600Seconds": all(
            value >= int(contract["minimumRunDurationSeconds"]) for value in durations
        ),
        "allRunsRequiredCoverageComplete": True,
        "minimumIndependentRunsSatisfied": enough_runs,
        "trendReview": {
            "status": "COMPLETED_DESCRIPTIVE_LOCAL_ONLY" if review_completed else
                      ("PENDING" if enough_runs else "WAITING_FOR_REPEATED_RUNS"),
            "reviewEvidenceRef": review_ref,
            "automaticLeakConclusionForbidden": True,
            "automaticOperatingThresholdApprovalForbidden": True,
            "runTrends": sorted(trend_summaries, key=lambda value: value["runId"]),
        },
        "trendReviewCompleted": review_completed,
        "localSustainedSoakEvidence": local_evidence,
        "productionSustainedSoakEvidence": False,
        "leakProof": False,
        "productionEvidence": False,
        "productionEquivalentDependencies": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "productionReady": False,
    }
    AGGREGATE_PATH.write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    print("Memory OS sustained local soak aggregate updated")
    print(f"run count: {len(paths)}")
    print(f"minimum independent runs satisfied: {str(enough_runs).lower()}")
    print(f"stale trend review ignored pending regeneration: {str(stale_review_ignored).lower()}")
    print(f"trend review completed: {str(review_completed).lower()}")
    print(f"local sustained soak evidence: {str(local_evidence).lower()}")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
