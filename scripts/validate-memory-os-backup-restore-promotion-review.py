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


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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

    rows = writer.validate_registry_for_append(registry)
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    latest_id = registry.get("latestDecisionId")
    current_id = registry.get("currentDecisionId")
    candidate_count = generation.get("productionEquivalentRecoveryCandidateCount")
    typed_covered = typed.get("candidateCoveredCount")
    require(valid_count(candidate_count), "recovery candidate count invalid")
    require(valid_count(typed_covered), "typed candidate coverage count invalid")
    require(candidate_count == typed_covered, "promotion review requires typed-final candidate count coherence")
    if current_id is not None:
        require(candidate_count > 0, "current promotion review cannot exist without a current final recovery candidate")
        require(current_id == latest_id, "only the latest historical review may hold current promotion authority")
    if candidate_count == 0:
        require(current_id is None, "zero final recovery candidates requires revoked current promotion authority")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    expected = {
        "registeredReviewCount": count,
        "goRecommendationCount": go_count,
        "noGoCount": no_go_count,
        "deferCount": defer_count,
        "latestDecisionId": latest_id,
        "currentDecisionId": current_id,
    }
    for field, value in expected.items():
        require(boundary.get(field) == value, f"promotion review boundary drift: {field}")
    require(boundary.get("productionTrafficChanged") is False and boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "promotion review boundary cannot promote production")

    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"promotion review negative suite failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")
    print("Memory OS backup/restore promotion review validation PASS")
    print(f"final recovery candidates: {candidate_count}")
    print(f"registered historical promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print(f"latest historical decision: {latest_id}")
    print(f"current promotion authority decision: {current_id}")
    print("historical review/current authority separation: PASS")
    print("review changes production traffic: false")
    print("review creates production ready: false")
    print("negative admission suite: PASS")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            print(f"BACKUP RESTORE PROMOTION REVIEW VALIDATION FAILED: {exc}", file=sys.stderr)
            raise SystemExit(1)
        raise
