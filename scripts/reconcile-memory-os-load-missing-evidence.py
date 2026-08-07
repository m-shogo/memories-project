#!/usr/bin/env python3
"""Normalize OPS-P0-006 missing evidence from canonical load readiness flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

PROVEN_FLAGS = (
    "previewPreFenceInFlightLinearizationProven",
    "applyPreFenceInFlightLinearizationProven",
    "uploadAuthorizationPreFenceInFlightLinearizationProven",
    "uploadCompletionPreFenceInFlightLinearizationProven",
    "primaryAccountBoundPreFenceLinearizationAggregateProven",
    "multiAccountDeletionWorkerSaturationProven",
    "deletionLeaseExpiryRecoverySimulationProven",
    "deletionPartialObjectErasureRecoveryProven",
    "deletionActualProcessKillProven",
    "deletionContainerKillRecoveryProven",
    "deletionReplacementContainerRecoveryProven",
    "repeatableLocalDegradationSignalObserved",
)

STALE_RESOLVED = {
    "request-linearization proof for operations already in flight before the deletion fence plus multi-account worker saturation, production topology and independently reviewed deletion-load thresholds",
    "repeatable local PostgreSQL plus MinIO saturation runs that actually observe a first failure/degradation transition, plus queue/backlog interpretation and independently reviewed safe operating thresholds",
}

CANONICAL_HOST_BLOCKER = (
    "physical deletion-worker host/node/AZ interruption recovery in a registered production-equivalent generation, plus production topology and independently reviewed deletion-load thresholds"
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    load_contract = load(LOAD)
    readiness = load_contract.get("readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("load readiness missing")
    for flag in PROVEN_FLAGS:
        if readiness.get(flag) is not True:
            raise SystemExit(f"cannot remove blocker while proof flag is not true: {flag}")
    for flag in (
        "deletionHostFailureRecoveryProven",
        "capacityBoundaryEstablished",
        "localSustainedSoakEvidence",
        "productionEquivalentDependencies",
    ):
        if readiness.get(flag) is not False:
            raise SystemExit(f"unresolved load flag unexpectedly promoted: {flag}")

    status = load(STATUS)
    area = next((item for item in status.get("areas", []) if item.get("id") == "OPS-P0-006"), None)
    if area is None:
        raise SystemExit("OPS-P0-006 missing")
    if area.get("status") != "PARTIAL" or area.get("blocking") is not True:
        raise SystemExit("OPS-P0-006 must remain blocking PARTIAL")

    missing = area.get("missingEvidence")
    if not isinstance(missing, list):
        raise SystemExit("OPS-P0-006 missingEvidence must be array")
    normalized: list[str] = []
    host_blocker_added = False
    host_legacy_fragments = (
        "deletion-worker container/host interruption recovery",
        "deletion-worker host/container failure behavior",
        "deletion-worker host/container interruption recovery",
        "deletion-worker process kill and host failure behavior",
        "deletion-worker process kill and host/container interruption recovery",
    )
    for item in missing:
        if not isinstance(item, str):
            raise SystemExit("OPS-P0-006 missingEvidence entries must be strings")
        if item in STALE_RESOLVED:
            continue
        if any(fragment in item for fragment in host_legacy_fragments):
            if not host_blocker_added:
                normalized.append(CANONICAL_HOST_BLOCKER)
                host_blocker_added = True
            continue
        if item not in normalized:
            normalized.append(item)
    if not host_blocker_added and CANONICAL_HOST_BLOCKER not in normalized:
        normalized.append(CANONICAL_HOST_BLOCKER)

    required_remaining_fragments = (
        "capacity boundary",
        "sustained soak",
        "production-equivalent dependency behavior",
        "production object-store TLS",
        "two independent 60-minute-or-longer LOCAL_LONG_SOAK runs",
        "physical deletion-worker host/node/AZ interruption recovery",
    )
    joined = "\n".join(normalized)
    for fragment in required_remaining_fragments:
        if fragment not in joined:
            raise SystemExit(f"required unresolved blocker disappeared: {fragment}")
    for stale in STALE_RESOLVED:
        if stale in normalized:
            raise SystemExit(f"resolved blocker remained: {stale}")

    area["missingEvidence"] = normalized
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")
    write(STATUS, status)

    print("Memory OS load missing-evidence reconciliation PASS")
    print("primary pre-fence/multi-account blockers: resolved")
    print("repeatable local degradation blocker: resolved")
    print("physical host/node/AZ blocker: retained")
    print("sustained soak blocker: retained")
    print("production-equivalent blocker: retained")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
