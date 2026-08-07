#!/usr/bin/env python3
"""Reconcile approved release compatibility pairs into canonical compatibility authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
GAPS = ROOT / "contracts/operations/compatibility-admission-gaps.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair.py"
REFS = (
    "contracts/operations/release-compatibility-pair-contract.v1.json",
    "contracts/operations/release-compatibility-pair-registry.v1.json",
    "scripts/register-memory-os-release-compatibility-pair.py",
    "scripts/validate-memory-os-release-compatibility-pair.py",
    "scripts/reconcile-memory-os-release-compatibility-pair.py",
    ".github/workflows/release-compatibility-pair.yml",
)
EVIDENCE_PREFIX = "approved release compatibility-pair authority is append-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    releases = load(RELEASES)
    registry = load(REGISTRY)
    contract = load(CONTRACT)
    execution = load(EXECUTION)
    gaps = load(GAPS)
    release_count = releases.get("approvedReleaseCount")
    pairs = registry.get("pairs")
    pair_count = registry.get("approvedPairCount")
    rollback_count = registry.get("rollbackEligiblePairCount")
    latest_pair = registry.get("latestPairId")
    require(isinstance(release_count, int) and release_count >= 0, "approved release count invalid")
    require(isinstance(pairs, list) and isinstance(pair_count, int) and len(pairs) == pair_count, "pair registry count drift")
    require(isinstance(rollback_count, int) and rollback_count == pair_count, "rollback pair count drift")
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
    write(CONTRACT, contract)

    exec_boundary = execution.get("releaseAuthorityBoundary")
    exec_readiness = execution.get("readiness")
    require(isinstance(exec_boundary, dict) and isinstance(exec_readiness, dict), "execution release authority missing")
    exec_boundary["approvedReleaseCount"] = release_count
    exec_boundary["approvedRollbackPairCount"] = pair_count
    exec_boundary["releaseCompatibilityEvidence"] = pair_count > 0
    exec_boundary["productionEvidence"] = False
    exec_boundary["productionReady"] = False
    exec_boundary["productionDecision"] = "NO_GO"
    exec_readiness["approvedReleasePairAvailable"] = pair_count > 0
    exec_readiness["productionReady"] = False
    write(EXECUTION, execution)

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
    gaps["blockingGapCount"] = sum(1 for gap in blocking_gaps if isinstance(gap, dict) and gap.get("blocking") is True and (
        (isinstance(gap.get("current"), int) and gap.get("current") < gap.get("requiredMinimum", 0))
        or (isinstance(gap.get("current"), bool) and gap.get("current") is not gap.get("required"))
    ))
    gaps["releaseCompatibilityEvidence"] = pair_count > 0
    gaps["productionEvidence"] = False
    gaps["productionReady"] = False
    gaps["productionDecision"] = "NO_GO"
    write(GAPS, gaps)

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
        f"{EVIDENCE_PREFIX} approved releases={release_count}, approved predecessor/successor rollback pairs={pair_count}; pair admission requires two distinct already-approved release baselines, ELIGIBLE predecessor rollback status, pair-specific rolling deployment, application rollback, persisted-route, database-upgrade, artifact-retention and at least two independent review references, while candidate/local evidence cannot create a pair and productionEvidence/productionReady remain false"
    ))
    if pair_count > 0:
        obsolete_prefixes = (
            "approved predecessor release record",
            "rollback-eligible approved release",
        )
        missing[:] = [item for item in missing if not (isinstance(item, str) and item.startswith(obsolete_prefixes))]
    for ref in REFS:
        require((ROOT / ref).is_file(), f"release pair authority ref missing: {ref}")
        append_once(refs, ref)
    write(STATUS, status)

    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    print("Memory OS release compatibility pair reconciliation PASS")
    print(f"approved releases: {release_count}")
    print(f"approved rollback pairs: {pair_count}")
    print(f"release compatibility evidence: {str(pair_count > 0).lower()}")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR RECONCILE FAILED: {exc}")
        raise SystemExit(1)
