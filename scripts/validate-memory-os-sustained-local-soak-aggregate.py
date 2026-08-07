#!/usr/bin/env python3
"""Validate repeated LOCAL_LONG_SOAK documents and descriptive aggregate authority."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
AGGREGATE_PATH = RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"


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


def validate_run(path: Path) -> tuple[str, str]:
    completed = subprocess.run(
        [sys.executable, str(RESULT_VALIDATOR), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise Fail(
            f"single-run validator rejected {path.relative_to(ROOT)}:\n"
            f"{completed.stdout[-4000:]}{completed.stderr[-4000:]}"
        )
    value = load(path)
    run_id = value.get("runId")
    commit_sha = value.get("commitSha")
    require(isinstance(run_id, str) and run_id, f"{path.name}: runId required")
    require(isinstance(commit_sha, str) and len(commit_sha) == 40, f"{path.name}: commitSha required")
    return run_id, commit_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-local-evidence", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    if not paths:
        require(not AGGREGATE_PATH.exists(), "aggregate cannot exist without run documents")
        require(not args.require_local_evidence, "no LOCAL_LONG_SOAK result documents have been committed")
        print("Memory OS sustained local soak aggregate validation PASS (foundation only)")
        print("committed long runs: 0")
        print("local sustained soak evidence: false")
        print("production sustained soak evidence: false")
        return 0

    run_ids: set[str] = set()
    commits: set[str] = set()
    for path in paths:
        run_id, commit = validate_run(path)
        require(run_id not in run_ids, f"duplicate long-soak runId: {run_id}")
        run_ids.add(run_id)
        commits.add(commit)

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
    require(isinstance(run_trends, list) and len(run_trends) == len(paths), "trend summary must cover every committed run")

    local_evidence = aggregate.get("localSustainedSoakEvidence")
    trend_review_completed = aggregate.get("trendReviewCompleted")
    require(isinstance(local_evidence, bool), "localSustainedSoakEvidence must be boolean")
    require(isinstance(trend_review_completed, bool), "trendReviewCompleted must be boolean")
    if local_evidence:
        require(enough_runs, "local sustained-soak evidence requires at least two independent runs")
        require(trend_review_completed is True, "local sustained-soak evidence requires completed trend review")
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
