#!/usr/bin/env python3
"""Reconcile append-only human backup/restore promotion review authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-promotion-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-promotion-review.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_writer_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load promotion review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation = load(GEN_REGISTRY)
    status = load(STATUS)
    writer = load_writer()
    rows, expected_current = writer.reconcile_current_decision(registry)
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    latest_id = registry.get("latestDecisionId")
    current_id = registry.get("currentDecisionId")
    require(expected_current == current_id, "promotion review current authority reconcile drift")
    candidate_count = generation.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(candidate_count), "recovery candidate count invalid")
    if candidate_count == 0:
        require(current_id is None, "zero final recovery candidates must revoke current promotion authority")
    if current_id is not None:
        require(current_id == latest_id, "only latest historical review may remain current")

    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    boundary["registeredReviewCount"] = count
    boundary["goRecommendationCount"] = go_count
    boundary["noGoCount"] = no_go_count
    boundary["deferCount"] = defer_count
    boundary["latestDecisionId"] = latest_id
    boundary["currentDecisionId"] = current_id
    boundary["productionTrafficChanged"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    require(status.get("productionDecision") == "NO_GO", "global production decision must remain NO_GO")
    ops7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 status missing")
    missing = ops7.get("missingEvidence")
    require(isinstance(missing, list) and len(missing) == 6, "canonical OPS-P0-007 six-blocker boundary drift")
    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile promotion review validator failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}")
    print("Memory OS backup/restore promotion review reconciliation PASS")
    print(f"final recovery candidates: {candidate_count}")
    print(f"registered historical promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print(f"latest historical decision: {latest_id}")
    print(f"current promotion authority decision: {current_id}")
    print("historical review rows retained: true")
    print("current authority may only be revoked automatically: true")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production traffic changed: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
