#!/usr/bin/env python3
"""Build a descriptive LOCAL_LONG_SOAK aggregate without auto-promoting trend review or leak proof."""

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
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} root must be object")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    if not paths:
        if AGGREGATE_PATH.exists():
            AGGREGATE_PATH.unlink()
        print("No sustained local soak result documents to aggregate")
        return 0

    run_ids: list[str] = []
    source_shas: list[str] = []
    durations: list[float] = []
    trend_summaries: list[dict[str, Any]] = []
    for path in paths:
        completed = subprocess.run(
            [sys.executable, str(RESULT_VALIDATOR), str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            sys.stderr.write(completed.stdout)
            sys.stderr.write(completed.stderr)
            raise SystemExit(f"result validator rejected {path.relative_to(ROOT)}")
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
    aggregate = {
        "schemaVersion": "memory-os-sustained-local-soak-aggregate.v1",
        "scenarioId": contract["scenarioId"],
        "classification": "LOCAL_LONG_SOAK",
        "runCount": len(paths),
        "runIds": sorted(run_ids),
        "sourceCommitShas": sorted(set(source_shas)),
        "allRunsDurationAtLeast3600Seconds": all(value >= int(contract["minimumRunDurationSeconds"]) for value in durations),
        "allRunsRequiredCoverageComplete": True,
        "minimumIndependentRunsSatisfied": enough_runs,
        "trendReview": {
            "status": "PENDING" if enough_runs else "WAITING_FOR_REPEATED_RUNS",
            "automaticLeakConclusionForbidden": True,
            "automaticOperatingThresholdApprovalForbidden": True,
            "runTrends": sorted(trend_summaries, key=lambda value: value["runId"]),
        },
        "trendReviewCompleted": False,
        "localSustainedSoakEvidence": False,
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
    print("trend review completed: false")
    print("local sustained soak evidence: false")
    print("leak proof: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
