#!/usr/bin/env python3
"""Build descriptive LOCAL_LONG_SOAK aggregate without leak or production promotion."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL_AGGREGATE_PATH = CANONICAL_RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
CANONICAL_REVIEW_PATH = CANONICAL_RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
CANONICAL_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-trend-review.py"

RESULT_DIR = CANONICAL_RESULT_DIR
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
AGGREGATE_PATH = CANONICAL_AGGREGATE_PATH
REVIEW_PATH = CANONICAL_REVIEW_PATH
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_VALIDATOR = CANONICAL_RESULT_VALIDATOR
REVIEW_VALIDATOR = CANONICAL_REVIEW_VALIDATOR


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
    require_exact_file(REVIEW_VALIDATOR, CANONICAL_REVIEW_VALIDATOR, "review validator")
    require_exact_optional_file(AGGREGATE_PATH, CANONICAL_AGGREGATE_PATH, "sustained soak aggregate")
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
    enforce_runtime_authorities()
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
    atomic_replace_bytes(AGGREGATE_PATH, (json.dumps(aggregate, indent=2) + "\n").encode("utf-8"))
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
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK AGGREGATE UPDATE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
