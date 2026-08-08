#!/usr/bin/env python3
"""Validate append-only human backup/restore promotion review authority."""

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
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"
NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-promotion-review-negative.py"


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


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_writer_validator", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load promotion review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation = load(GEN_REGISTRY)
    typed = load(TYPED_REGISTRY)
    writer = load_writer()

    require(contract.get("schemaVersion") == "memory-os-backup-restore-promotion-review-contract.v1", "promotion review contract schema drift")
    refs = {
        "registry": REGISTRY,
        "generationEvidenceRegistry": GEN_REGISTRY,
        "typedNonResurrectionRegistry": TYPED_REGISTRY,
        "writer": WRITER,
        "validator": Path("scripts/validate-memory-os-backup-restore-promotion-review.py"),
        "negativeAdmissionValidator": NEGATIVE,
        "workflow": Path(".github/workflows/backup-restore-promotion-review.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"promotion review ref drift: {field}")
        require((ROOT / expected).is_file(), f"promotion review artifact missing: {expected}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "promotion review rules must remain fail-closed")
    decisions = contract.get("decisionValues")
    require(isinstance(decisions, list) and set(decisions) == {"GO_RECOMMENDATION", "NO_GO", "DEFER"}, "promotion review decision values drift")

    rows = registry.get("records")
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    require(registry.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "promotion review rows invalid")
    require(isinstance(count, int) and count == len(rows), "promotion review count drift")
    require(all(isinstance(value, int) and value >= 0 for value in (go_count, no_go_count, defer_count)), "promotion review decision counts invalid")
    require(go_count + no_go_count + defer_count == count, "promotion review decision counts do not partition registry")
    require(registry.get("productionTrafficChanged") is False and registry.get("productionEvidence") is False and registry.get("productionReady") is False, "promotion review registry cannot promote production")

    ids: set[str] = set()
    for row in rows:
        decision_id = row.get("decisionId")
        require(isinstance(decision_id, str) and decision_id not in ids, f"duplicate decisionId: {decision_id}")
        ids.add(decision_id)
        writer.validate_record(row)
    derived_go = sum(1 for row in rows if row.get("decision") == "GO_RECOMMENDATION")
    derived_no_go = sum(1 for row in rows if row.get("decision") == "NO_GO")
    derived_defer = sum(1 for row in rows if row.get("decision") == "DEFER")
    require((go_count, no_go_count, defer_count) == (derived_go, derived_no_go, derived_defer), "promotion review derived decision count drift")
    current_id = registry.get("currentDecisionId")
    require(current_id == (rows[-1].get("decisionId") if rows else None), "promotion review currentDecisionId drift")

    candidate_count = generation.get("productionEquivalentRecoveryCandidateCount")
    typed_covered = typed.get("candidateCoveredCount")
    require(isinstance(candidate_count, int) and candidate_count >= 0, "recovery candidate count invalid")
    require(isinstance(typed_covered, int) and typed_covered >= 0, "typed candidate coverage count invalid")
    require(candidate_count == typed_covered, "promotion review requires typed-final candidate count coherence")
    if candidate_count == 0:
        require(count == 0, "promotion review cannot exist without final recovery candidate")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    expected = {
        "registeredReviewCount": count,
        "goRecommendationCount": go_count,
        "noGoCount": no_go_count,
        "deferCount": defer_count,
        "currentDecisionId": current_id,
    }
    for field, value in expected.items():
        require(boundary.get(field) == value, f"promotion review boundary drift: {field}")
    require(boundary.get("productionTrafficChanged") is False and boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "promotion review boundary cannot promote production")

    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"promotion review negative suite failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")

    print("Memory OS backup/restore promotion review validation PASS")
    print(f"final recovery candidates: {candidate_count}")
    print(f"registered promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print("review changes production traffic: false")
    print("review creates production ready: false")
    print("negative admission suite: PASS")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
