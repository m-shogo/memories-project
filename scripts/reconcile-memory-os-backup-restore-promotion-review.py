#!/usr/bin/env python3
"""Reconcile append-only human backup/restore promotion review authority."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-promotion-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
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


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation = load(GEN_REGISTRY)
    status = load(STATUS)

    require(registry.get("schemaVersion") == "memory-os-backup-restore-promotion-review-registry.v1", "promotion review registry schema drift")
    require(registry.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(
        registry.get("productionTrafficChanged") is False
        and registry.get("productionEvidence") is False
        and registry.get("productionReady") is False,
        "promotion review registry production boundary drift",
    )

    rows = registry.get("records")
    count = registry.get("registeredReviewCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "promotion review registry rows invalid")
    require(valid_count(count) and count == len(rows), "promotion review registry count drift")

    go_count = sum(1 for row in rows if row.get("decision") == "GO_RECOMMENDATION")
    no_go_count = sum(1 for row in rows if row.get("decision") == "NO_GO")
    defer_count = sum(1 for row in rows if row.get("decision") == "DEFER")
    require(go_count + no_go_count + defer_count == count, "promotion review decision partition drift")

    stored_counts = (
        registry.get("goRecommendationCount"),
        registry.get("noGoCount"),
        registry.get("deferCount"),
    )
    require(all(valid_count(value) for value in stored_counts), "promotion review derived counts invalid")
    require(stored_counts == (go_count, no_go_count, defer_count), "promotion review derived count authority drift")

    current_id = rows[-1].get("decisionId") if rows else None
    require(registry.get("currentDecisionId") == current_id, "promotion review currentDecisionId authority drift")

    candidate_count = generation.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(candidate_count), "recovery candidate count invalid")
    if candidate_count == 0:
        require(count == 0, "promotion reviews cannot exist without final recovery candidate")

    # The registry is append-only authority. Reconciliation may project its
    # already-valid values into the contract boundary, but must never heal a
    # corrupted registry counter, pointer, or production boundary in place.
    registry["goRecommendationCount"] = go_count
    registry["noGoCount"] = no_go_count
    registry["deferCount"] = defer_count
    registry["currentDecisionId"] = current_id
    registry["productionTrafficChanged"] = False
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    boundary["registeredReviewCount"] = count
    boundary["goRecommendationCount"] = go_count
    boundary["noGoCount"] = no_go_count
    boundary["deferCount"] = defer_count
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
    print(f"registered promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("registry corruption auto-healed: false")
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
