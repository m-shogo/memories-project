#!/usr/bin/env python3
"""Create a descriptive cross-run LOCAL_LONG_SOAK trend review without leak conclusions."""

from __future__ import annotations

import json
import math
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL_RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
CANONICAL_REVIEW_PATH = CANONICAL_RESULT_DIR / "sustained-local-soak-trend-review.v1.json"

CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_DIR = CANONICAL_RESULT_DIR
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
RESULT_VALIDATOR = CANONICAL_RESULT_VALIDATOR
REVIEW_PATH = CANONICAL_REVIEW_PATH
TIMESTAMP_DURATION_TOLERANCE_SECONDS = 2.0
GENERATION_LAG_LIMIT_SECONDS = 120.0


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"{label} authority substitution")
    require(path.is_file() and not path.is_symlink(), f"{label} canonical file missing or symlinked")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Fail(f"{label} canonical authority cannot be resolved") from exc
    require(resolved == expected, f"{label} canonical authority escaped repository path")


def require_exact_optional_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"{label} authority substitution")
    require(path.parent.resolve(strict=True) == expected.parent, f"{label} canonical parent escaped repository path")
    if path.exists():
        require(path.is_file() and not path.is_symlink(), f"{label} canonical file is not a regular file")
        require(path.resolve(strict=True) == expected, f"{label} canonical authority escaped repository path")


def enforce_runtime_authorities() -> None:
    require(RESULT_DIR == CANONICAL_RESULT_DIR, "result directory authority substitution")
    require(RESULT_DIR.is_dir() and not RESULT_DIR.is_symlink(), "canonical result directory missing or symlinked")
    require(RESULT_DIR.resolve(strict=True) == CANONICAL_RESULT_DIR, "canonical result directory escaped repository path")
    require_exact_file(CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "sustained soak contract")
    require_exact_file(RESULT_VALIDATOR, CANONICAL_RESULT_VALIDATOR, "result validator")
    require_exact_optional_file(REVIEW_PATH, CANONICAL_REVIEW_PATH, "sustained soak trend review")


def atomic_replace_bytes(path: Path, payload: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode is None and path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            if mode is not None:
                os.fchmod(handle.fileno(), mode)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def finite_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{field} must be finite")
    return number


def utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} must be valid RFC3339: {value}") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
            f"{field} must resolve to UTC")
    return parsed


def summarize_run(path: Path) -> tuple[datetime, dict[str, Any]]:
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
    value = load(path)
    scenario = value.get("scenario")
    require(isinstance(scenario, dict), f"{path.name}: scenario missing")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS",
            f"{path.name}: result/integrity must PASS")
    started_at = utc_timestamp(scenario.get("startedAt"), f"{path.name}.scenario.startedAt")
    completed_at = utc_timestamp(scenario.get("completedAt"), f"{path.name}.scenario.completedAt")
    generated_at = utc_timestamp(value.get("generatedAt"), f"{path.name}.generatedAt")
    duration_seconds = finite_number(scenario.get("durationSeconds"), f"{path.name}.scenario.durationSeconds")
    wall_duration = (completed_at - started_at).total_seconds()
    require(wall_duration >= 0, f"{path.name}: scenario.completedAt cannot precede scenario.startedAt")
    require(abs(wall_duration - duration_seconds) <= TIMESTAMP_DURATION_TOLERANCE_SECONDS,
            f"{path.name}: scenario timestamps must agree with durationSeconds")
    generation_lag = (generated_at - completed_at).total_seconds()
    require(0 <= generation_lag <= GENERATION_LAG_LIMIT_SECONDS,
            f"{path.name}: generatedAt must follow completion within bounded evidence-write lag")
    trends = scenario.get("trends")
    require(isinstance(trends, dict), f"{path.name}: trends missing")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), f"{path.name}: assertions missing")
    require(assertions.get("postRunRecoveryProbePassed") is True,
            f"{path.name}: recovery probe did not pass")
    require(assertions.get("allRequiredCoverageExecuted") is True,
            f"{path.name}: required coverage incomplete")
    require(assertions.get("productionEvidence") is False and
            assertions.get("productionEquivalentDependencies") is False,
            f"{path.name}: local evidence boundary drift")

    latency = trends.get("latencyTrendBySurface")
    errors = trends.get("errorRateTrendBySurface")
    db = trends.get("dbConnectionTrend")
    queue = trends.get("scanQueueTrend")
    deletion = trends.get("deletionBacklogTrend")
    require(isinstance(latency, dict) and isinstance(errors, dict) and
            isinstance(db, dict) and isinstance(queue, dict) and isinstance(deletion, dict),
            f"{path.name}: trend groups incomplete")

    return completed_at, {
        "runId": value["runId"],
        "sourceCommitSha": value["commitSha"],
        "durationSeconds": duration_seconds,
        "rssSlopeBytesPerMinute": finite_number(trends.get("rssSlopeBytesPerMinute"), "rss slope"),
        "heapAllocSlopeBytesPerMinute": finite_number(trends.get("heapAllocSlopeBytesPerMinute"), "heap alloc slope"),
        "heapInuseSlopeBytesPerMinute": finite_number(trends.get("heapInuseSlopeBytesPerMinute"), "heap inuse slope"),
        "goroutineSlopePerMinute": finite_number(trends.get("goroutineSlopePerMinute"), "goroutine slope"),
        "latencyTrendBySurface": latency,
        "errorRateTrendBySurface": errors,
        "dbConnectionTrend": db,
        "scanQueueTrend": queue,
        "deletionBacklogTrend": deletion,
        "postRunRecoveryProbePassed": True,
    }


def pair_delta(a: dict[str, Any], b: dict[str, Any], field: str) -> float:
    return float(b[field]) - float(a[field])


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    minimum_runs = int(contract.get("minimumIndependentRuns", 2))
    require(len(paths) >= minimum_runs,
            f"trend review requires at least {minimum_runs} committed long-soak runs")
    chronological_runs = [summarize_run(path) for path in paths]
    chronological_runs.sort(key=lambda item: (item[0], str(item[1]["runId"])))
    runs = [summary for _, summary in chronological_runs]
    run_ids = [run["runId"] for run in runs]
    require(len(run_ids) == len(set(run_ids)), "duplicate long-soak run IDs")

    a, b = runs[-2], runs[-1]
    review = {
        "schemaVersion": "memory-os-sustained-local-soak-trend-review.v1",
        "classification": "LOCAL_LONG_SOAK_DESCRIPTIVE_CROSS_RUN_REVIEW",
        "scenarioId": contract["scenarioId"],
        "reviewedRunCount": len(runs),
        "reviewedRunIds": sorted(run_ids),
        "reviewedSourceCommitShas": sorted({run["sourceCommitSha"] for run in runs}),
        "minimumIndependentRunsSatisfied": len(runs) >= minimum_runs,
        "allReviewedRunsPassedPerRunValidator": True,
        "allReviewedRunsPostRecoveryProbePassed": True,
        "latestPair": {
            "runA": a["runId"],
            "runB": b["runId"],
            "rssSlopeDeltaBytesPerMinute": pair_delta(a, b, "rssSlopeBytesPerMinute"),
            "heapAllocSlopeDeltaBytesPerMinute": pair_delta(a, b, "heapAllocSlopeBytesPerMinute"),
            "heapInuseSlopeDeltaBytesPerMinute": pair_delta(a, b, "heapInuseSlopeBytesPerMinute"),
            "goroutineSlopeDeltaPerMinute": pair_delta(a, b, "goroutineSlopePerMinute"),
        },
        "runTrends": sorted(runs, key=lambda item: item["runId"]),
        "reviewFindings": [
            "both corrected 60-minute-or-longer runs passed their per-run fail-closed validator and post-run recovery probe",
            "RSS, Go heap allocation, heap-inuse and goroutine slopes are recorded for each run and compared descriptively; no slope is converted into an automatic leak/no-leak conclusion",
            "latency and error-rate trends are preserved per surface rather than collapsed into an unreviewed production threshold",
            "database connection/acquisition-wait, scan-queue depth/age and deletion backlog trends are preserved for operator review",
            "scan queue accumulation is an intentional bounded local-fixture behavior and is not treated as production queue stability",
        ],
        "trendReviewCompleted": True,
        "localSustainedSoakEvidenceEligible": True,
        "automaticLeakConclusionMade": False,
        "leakProof": False,
        "operationalThresholdApproved": False,
        "capacityBoundaryEstablished": False,
        "productionEquivalentDependencies": False,
        "productionEvidence": False,
        "independentProductionReviewCompleted": False,
        "productionReady": False,
        "decision": "DESCRIPTIVE_LOCAL_REPEATABILITY_REVIEW_COMPLETE_NO_LEAK_OR_PRODUCTION_CONCLUSION",
    }
    atomic_replace_bytes(REVIEW_PATH, (json.dumps(review, indent=2) + "\n").encode("utf-8"))
    print("Memory OS sustained local soak descriptive trend review created")
    print(f"reviewed runs: {len(runs)}")
    print("run chronology bound to UTC timestamps and measured duration: true")
    print("latest pair selected by validated scenario completion chronology: true")
    print("trend review completed: true")
    print("local sustained-soak evidence eligible: true")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK TREND REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
