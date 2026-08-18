#!/usr/bin/env python3
"""Validate append-only approved predecessor/successor release pairs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
LOCK = ROOT / "contracts/operations/.release-compatibility-pair.lock"
WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-compatibility-pair.py"
INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair-independent-review.py"
INDEPENDENT_REVIEW_NEGATIVE = ROOT / "scripts/validate-memory-os-release-compatibility-pair-independent-review-negative.py"
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
GAPS = ROOT / "contracts/operations/compatibility-admission-gaps.v1.json"


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


def load_authority(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_path(value: Any, expected: Path, field: str) -> None:
    require(isinstance(value, Path) and value.resolve() == expected.resolve(), f"{field} executable authority drift")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    execution = load(EXECUTION)
    gaps = load(GAPS)
    writer = load_authority(WRITER, "memory_os_release_pair_writer")
    reconciler = load_authority(RECONCILER, "memory_os_release_pair_reconciler")

    require(contract.get("schemaVersion") == "memory-os-release-compatibility-pair.v1", "pair contract schema drift")
    require(contract.get("releaseRegistry") == str(RELEASES.relative_to(ROOT)), "release registry ref drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "pair registry ref drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "pair append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)) and WRITER.is_file(), "pair writer ref drift")
    require(contract.get("reconcile") == str(RECONCILER.relative_to(ROOT)) and RECONCILER.is_file(), "pair reconciler ref drift")
    require(contract.get("independentReviewValidator") == str(INDEPENDENT_REVIEW_VALIDATOR.relative_to(ROOT)) and INDEPENDENT_REVIEW_VALIDATOR.is_file(), "independent review validator ref drift")
    require(contract.get("independentReviewNegativeValidator") == str(INDEPENDENT_REVIEW_NEGATIVE.relative_to(ROOT)) and INDEPENDENT_REVIEW_NEGATIVE.is_file(), "independent review negative validator ref drift")
    require(contract.get("independentReviewEvidenceRoot") == "docs/evidence/release-compatibility-pairs/reviews", "independent review evidence root drift")
    for field in ("validator", "workflow"):
        ref = contract.get(field)
        require(isinstance(ref, str) and ref and (ROOT / ref).is_file(), f"pair authority artifact missing: {field}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "pair rules must remain fail-closed")
    require(rules.get("appendLockMustRemainCanonical") is True, "pair append lock rule drift")

    canonical_path(getattr(writer, "LOCK", None), LOCK, "writer append lock")
    canonical_path(getattr(writer, "INDEPENDENT_REVIEW_VALIDATOR", None), INDEPENDENT_REVIEW_VALIDATOR, "writer independent review validator")
    canonical_path(getattr(reconciler, "INDEPENDENT_REVIEW_VALIDATOR", None), INDEPENDENT_REVIEW_VALIDATOR, "reconciler independent review validator")
    canonical_path(getattr(reconciler, "WRITER", None), WRITER, "reconciler writer")
    canonical_path(getattr(reconciler, "VALIDATOR", None), Path(__file__), "reconciler validator")

    try:
        writer.validate_registry_for_append(registry)
        release_registry = writer.validated_release_registry()
    except Exception as exc:
        raise Fail(f"release pair shared authority invalid: {exc}") from exc

    approved_release_count = release_registry.get("approvedReleaseCount")
    releases = release_registry.get("releases")
    require(isinstance(approved_release_count, int) and not isinstance(approved_release_count, bool) and approved_release_count >= 0, "approved release count invalid")
    require(isinstance(releases, list) and len(releases) == approved_release_count, "release registry count drift")

    require(registry.get("schemaVersion") == "memory-os-release-compatibility-pair-registry.v1", "pair registry schema drift")
    require(registry.get("appendOnly") is True, "pair registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "pair registry cannot promote production")
    pairs = registry.get("pairs")
    count = registry.get("approvedPairCount")
    rollback_count = registry.get("rollbackEligiblePairCount")
    require(isinstance(pairs, list) and all(isinstance(row, dict) for row in pairs), "pair rows invalid")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(pairs), "approvedPairCount drift")
    require(isinstance(rollback_count, int) and not isinstance(rollback_count, bool) and rollback_count == count, "rollbackEligiblePairCount drift")
    latest_pair_id = registry.get("latestPairId")
    require(latest_pair_id == (pairs[-1].get("pairId") if pairs else None), "latestPairId drift")
    if approved_release_count < 2:
        require(count == 0, "approved pair cannot exist with fewer than two approved releases")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority missing")
    require(authority.get("approvedPairCount") == count, "pair authority count drift")
    require(authority.get("latestPairId") == latest_pair_id, "pair authority latest ID drift")
    require(authority.get("rollbackEligiblePairCount") == rollback_count, "pair authority rollback count drift")
    require(authority.get("releaseCompatibilityEvidence") is (count > 0), "pair authority compatibility evidence drift")
    require(authority.get("productionEvidence") is False and authority.get("productionReady") is False, "pair authority cannot promote production")
    require(authority.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    exec_boundary = execution.get("releaseAuthorityBoundary")
    require(isinstance(exec_boundary, dict), "candidate execution release boundary missing")
    require(exec_boundary.get("canonicalReleaseMatrixChanged") is False, "candidate execution cannot change release matrix")
    require(exec_boundary.get("releaseCompatibilityEvidence") is False, "candidate execution cannot become approved release evidence")
    require(exec_boundary.get("productionEvidence") is False and exec_boundary.get("productionReady") is False, "candidate execution cannot promote production")

    current_counts = gaps.get("currentCounts")
    require(isinstance(current_counts, dict), "compatibility gap counts missing")
    require(current_counts.get("approvedBackendReleases") == approved_release_count, "gap approved release count drift")
    require(current_counts.get("approvedRollbackPairs") == count, "gap rollback pair count drift")
    require(gaps.get("releaseCompatibilityEvidence") is (count > 0), "gap releaseCompatibilityEvidence drift")
    require(gaps.get("productionEvidence") is False and gaps.get("productionReady") is False, "gap authority cannot promote production")

    print("Memory OS approved release compatibility pair validation PASS")
    print(f"approved releases: {approved_release_count}")
    print(f"approved rollback pairs: {count}")
    print(f"release compatibility evidence: {str(count > 0).lower()}")
    print("typed independent Security/Operability review authority is mandatory for every approved pair")
    print("release pair writer/reconciler executable authorities are canonical")
    print("candidate/local execution remains non-release evidence")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
