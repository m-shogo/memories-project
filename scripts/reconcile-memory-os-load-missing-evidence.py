#!/usr/bin/env python3
"""Normalize OPS-P0-006 missing evidence from canonical load readiness flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

PREFENCE_PROVEN_FLAGS = (
    "previewPreFenceInFlightLinearizationProven",
    "applyPreFenceInFlightLinearizationProven",
    "uploadAuthorizationPreFenceInFlightLinearizationProven",
    "uploadCompletionPreFenceInFlightLinearizationProven",
    "primaryAccountBoundPreFenceLinearizationAggregateProven",
    "multiAccountDeletionWorkerSaturationProven",
)

PREFENCE_STALE_BLOCKER = (
    "request-linearization proof for operations already in flight before the deletion fence plus multi-account worker saturation, production topology and independently reviewed deletion-load thresholds"
)
REPEATABILITY_STALE_BLOCKER = (
    "repeatable local PostgreSQL plus MinIO saturation runs that actually observe a first failure/degradation transition, plus queue/backlog interpretation and independently reviewed safe operating thresholds"
)
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

    for flag in PREFENCE_PROVEN_FLAGS:
        if readiness.get(flag) is not True:
            raise SystemExit(f"cannot remove pre-fence blocker while proof flag is not true: {flag}")
    if readiness.get("repeatableLocalDegradationSignalObserved") is not True:
        raise SystemExit("cannot remove repeatability blocker while degradation signal is not proven")
    if readiness.get("localSustainedSoakEvidence") is not True:
        raise SystemExit("repeated local sustained-soak evidence must remain proven")
    for flag in (
        "deletionHostFailureRecoveryProven",
        "capacityBoundaryEstablished",
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
    for item in missing:
        if not isinstance(item, str):
            raise SystemExit("OPS-P0-006 missingEvidence entries must be strings")
        if item in (PREFENCE_STALE_BLOCKER, REPEATABILITY_STALE_BLOCKER):
            continue
        if item not in normalized:
            normalized.append(item)

    if CANONICAL_HOST_BLOCKER not in normalized:
        normalized.append(CANONICAL_HOST_BLOCKER)

    required_remaining_fragments = (
        "capacity boundary",
        "production-equivalent dependency behavior",
        "production object-store TLS",
        "physical deletion-worker host/node/AZ interruption recovery",
        "independently approved leak/stability criteria",
        "production-shaped sustained soak",
    )
    joined = "\n".join(normalized)
    for fragment in required_remaining_fragments:
        if fragment not in joined:
            raise SystemExit(f"required unresolved blocker disappeared: {fragment}")
    for stale in (PREFENCE_STALE_BLOCKER, REPEATABILITY_STALE_BLOCKER):
        if stale in normalized:
            raise SystemExit(f"resolved blocker remained: {stale}")

    area["missingEvidence"] = normalized
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")
    write(STATUS, status)

    print("Memory OS load missing-evidence reconciliation PASS")
    print("primary pre-fence/multi-account blocker: resolved")
    print("repeatable local degradation blocker: resolved")
    print("repeated local sustained soak evidence: retained as local-only proof")
    print("physical host/node/AZ blocker: retained")
    print("production-shaped soak blocker: retained")
    print("production-equivalent blocker: retained")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
