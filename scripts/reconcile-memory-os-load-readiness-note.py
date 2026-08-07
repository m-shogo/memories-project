#!/usr/bin/env python3
"""Normalize the human-readable load readiness note from canonical machine-readable proof flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"

REQUIRED_TRUE = (
    "previewPreFenceInFlightLinearizationProven",
    "applyPreFenceInFlightLinearizationProven",
    "uploadAuthorizationPreFenceInFlightLinearizationProven",
    "uploadCompletionPreFenceInFlightLinearizationProven",
    "primaryAccountBoundPreFenceLinearizationAggregateProven",
    "multiAccountDeletionWorkerSaturationProven",
    "deletionLeaseExpiryRecoverySimulationProven",
    "deletionPartialObjectErasureRecoveryProven",
    "deletionActualProcessKillProven",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    document = load(LOAD_PATH)
    readiness = document.get("readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("load readiness missing")
    for key in REQUIRED_TRUE:
        if readiness.get(key) is not True:
            raise SystemExit(f"cannot summarize unproven readiness flag: {key}")
    for key in (
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
        "productionEquivalentEnvironmentProvisioned",
        "localSustainedSoakEvidence",
        "deletionHostFailureRecoveryProven",
    ):
        if readiness.get(key) is not False:
            raise SystemExit(f"blocking flag unexpectedly promoted: {key}")

    readiness["note"] = (
        "Local evidence now proves post-fence deletion rejection, Preview/Apply/upload-authorization/upload-completion "
        "pre-fence linearization across the primary account-bound HTTP surfaces, bounded multi-account deletion-worker "
        "saturation, lease-expiry attempt-2 recovery including partial object erasure, and actual Linux SIGKILL worker "
        "recovery. It still does not establish a production capacity boundary, repeated 60-minute sustained-soak evidence, "
        "leak proof, host/container failure recovery, production-equivalent dependency behavior or independently reviewed "
        "operating thresholds; OPS-P0-006 remains PARTIAL and Production remains NO_GO."
    )
    LOAD_PATH.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print("Memory OS load readiness note reconciliation PASS")
    print("primary account-bound pre-fence aggregate: proven")
    print("actual Linux SIGKILL recovery: proven")
    print("host/container failure recovery: false")
    print("local sustained soak evidence: false")
    print("production-equivalent dependencies: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
