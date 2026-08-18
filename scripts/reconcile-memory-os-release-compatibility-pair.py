#!/usr/bin/env python3
"""Reconcile approved release compatibility pairs into canonical compatibility authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
GAPS = ROOT / "contracts/operations/compatibility-admission-gaps.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair.py"
WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair-independent-review.py"
REFS = (
    "contracts/operations/release-compatibility-pair-contract.v1.json",
    "contracts/operations/release-compatibility-pair-registry.v1.json",
    "scripts/register-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair-negative.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review.py",
    "scripts/validate-memory-os-release-compatibility-pair-independent-review-negative.py",
    "scripts/reconcile-memory-os-release-compatibility-pair.py",
    ".github/workflows/release-compatibility-pair.yml",
)
EVIDENCE_PREFIX = "approved release compatibility-pair authority is append-only and fail-closed:"
PAIR_COUNT_GAP_IDS = {
    "COMPAT-GAP-APPROVED-RELEASE-PAIR",
    "COMPAT-GAP-ROLLBACK-PAIR",
}


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


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def gap_unsatisfied(gap: dict[str, Any]) -> bool:
    current = gap.get("current")
    if isinstance(current, bool):
        return current is not gap.get("required")
    if isinstance(current, int) and not isinstance(current, bool):
        minimum = gap.get("requiredMinimum")
        return isinstance(minimum, int) and not isinstance(minimum, bool) and current < minimum
    return True


def remove_satisfied_pair_count_gaps(blocking_gaps: list[Any]) -> None:
    blocking_gaps[:] = [
        gap for gap in blocking_gaps
        if not (
            isinstance(gap, dict)
            and gap.get("id") in PAIR_COUNT_GAP_IDS
            and not gap_unsatisfied(gap)
        )
    ]


def commit_authority_transaction(
    contract: dict[str, Any],
    gaps: dict[str, Any],
    status: dict[str, Any],
    *,
    validator_runner: Callable[[], None] | None = None,
) -> None:
    """Write all derived pair authorities atomically with rollback on post-write failure."""
    originals = {
        CONTRACT: CONTRACT.read_bytes(),
        GAPS: GAPS.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    try:
        write(CONTRACT, contract)
        write(GAPS, gaps)
        write(STATUS, status)
        if validator_runner is None:
            subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
        else:
            validator_runner()
    except BaseException:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise


def main() -> int:
    registry = load(REGISTRY)
    writer = load_module(WRITER, "memory_os_release_pair_writer_for_reconcile")
    review_validator = load_module(INDEPENDENT_REVIEW_VALIDATOR, "memory_os_release_pair_review_for_reconcile")
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"release pair append-only authority invalid: {exc}") from exc

    pairs = registry.get("pairs")
    require(isinstance(pairs, list), "pair registry pairs invalid")
    try:
        for row in pairs:
            require(isinstance(row, dict), "pair registry row must be object")
            review_validator.validate_pair_reviews(row)
    except Exception as exc:
        raise Fail(f"release pair typed independent review authority invalid: {exc}") from exc

    releases = writer.validated_release_registry()
    contract = load(CONTRACT)
    execution = load(EXECUTION)
    gaps = load(GAPS)
    release_count = releases.get("approvedReleaseCount")
    pair_count = registry.get("approvedPairCount")
    rollback_count = registry.get("rollbackEligiblePairCount")
    latest_pair = registry.get("latestPairId")
    require(isinstance(release_count, int) and not isinstance(release_count, bool) and release_count >= 0, "approved release count invalid")
    require(isinstance(pair_count, int) and not isinstance(pair_count, bool) and len(pairs) == pair_count, "pair registry count drift")
    require(isinstance(rollback_count, int) and not isinstance(rollback_count, bool) and rollback_count == pair_count, "rollback pair count drift")
    require(latest_pair == (pairs[-1].get("pairId") if pairs else None), "latestPairId drift")
    if release_count < 2:
        require(pair_count == 0, "pair cannot exist with fewer than two approved releases")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "pair currentAuthority missing")
    authority["approvedPairCount"] = pair_count
    authority["latestPairId"] = latest_pair
    authority["rollbackEligiblePairCount"] = rollback_count
    authority["releaseCompatibilityEvidence"] = pair_count > 0
    authority["productionEvidence"] = False
    authority["productionReady"] = False
    authority["productionDecision"] = "NO_GO"

    exec_boundary = execution.get("releaseAuthorityBoundary")
    require(isinstance(exec_boundary, dict), "candidate execution release authority missing")
    require(exec_boundary.get("canonicalReleaseMatrixChanged") is False, "candidate execution release matrix drift")
    require(exec_boundary.get("releaseCompatibilityEvidence") is False, "candidate execution cannot be relabeled as approved release evidence")
    require(exec_boundary.get("productionEvidence") is False and exec_boundary.get("productionReady") is False, "candidate execution cannot promote production")

    current_counts = gaps.get("currentCounts")
    blocking_gaps = gaps.get("blockingGaps")
    require(isinstance(current_counts, dict) and isinstance(blocking_gaps, list), "compatibility gap authority missing")
    current_counts["approvedBackendReleases"] = release_count
    current_counts["approvedRollbackPairs"] = pair_count
    for gap in blocking_gaps:
        if not isinstance(gap, dict):
            continue
        if gap.get("id") == "COMPAT-GAP-APPROVED-RELEASE-PAIR":
            gap["current"] = release_count
        elif gap.get("id") == "COMPAT-GAP-ROLLBACK-PAIR":
            gap["current"] = pair_count
    remove_satisfied_pair_count_gaps(blocking_gaps)
    gaps["blockingGapCount"] = sum(
        1 for gap in blocking_gaps
        if isinstance(gap, dict) and gap.get("blocking") is True and gap_unsatisfied(gap)
    )
    gaps["releaseCompatibilityEvidence"] = pair_count > 0
    gaps["productionEvidence"] = False
    gaps["productionReady"] = False
    gaps["productionDecision"] = "NO_GO"

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-008 authority arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(existing, (
        f"{EVIDENCE_PREFIX} approved releases={release_count}, approved predecessor/successor rollback pairs={pair_count}; pair admission revalidates the canonical source-bound approved-release registry, requires two distinct approved release baselines, ELIGIBLE predecessor rollback status, committed digest-bound rolling/rollback/persisted-route/database/artifact evidence, and exactly two typed pair-bound Security/Operability APPROVED reviews from distinct reviewers; candidate/local execution remains separate non-release authority and productionEvidence/productionReady remain false"
    ))
    if pair_count > 0:
        obsolete_prefixes = (
            "approved predecessor release record",
            "rollback-eligible approved release",
            "approved predecessor and successor release pair",
        )
        missing[:] = [item for item in missing if not (isinstance(item, str) and item.startswith(obsolete_prefixes))]
    for ref in REFS:
        require((ROOT / ref).is_file(), f"release pair authority ref missing: {ref}")
        append_once(refs, ref)

    commit_authority_transaction(contract, gaps, status)
    print("Memory OS release compatibility pair reconciliation PASS")
    print(f"approved releases: {release_count}")
    print(f"approved rollback pairs: {pair_count}")
    print(f"release compatibility evidence: {str(pair_count > 0).lower()}")
    print("typed independent review authority: enforced before derived writes")
    print("candidate/local execution authority: unchanged")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR RECONCILE FAILED: {exc}")
        raise SystemExit(1)
