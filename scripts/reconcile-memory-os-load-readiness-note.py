#!/usr/bin/env python3
"""Normalize human-readable load summaries from canonical machine-readable proof flags."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
LOAD_PATH = CANONICAL_LOAD_PATH
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR

REQUIRED_TRUE = (
    "previewPreFenceInFlightLinearizationProven",
    "applyPreFenceInFlightLinearizationProven",
    "uploadAuthorizationPreFenceInFlightLinearizationProven",
    "uploadCompletionPreFenceInFlightLinearizationProven",
    "primaryAccountBoundPreFenceLinearizationAggregateProven",
    "multiAccountDeletionWorkerSaturationProven",
    "deletionLeaseExpiryRecoverySimulationProven",
    "deletionPartialObjectErasureRecoveryProven",
    "deletionContainerKillRecoveryProven",
    "deletionReplacementContainerRecoveryProven",
    "localSustainedSoakEvidence",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def validate_authorities() -> None:
    require_exact_authority(LOAD_PATH, CANONICAL_LOAD_PATH, "load contract")
    require_exact_authority(LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator_module():
    validate_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_load_validator", LOAD_VALIDATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load canonical load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_canonical_load() -> None:
    validate_authorities()
    result = load_validator_module().main()
    if isinstance(result, bool) or not isinstance(result, int) or result != 0:
        raise SystemExit(f"canonical load validator rejected authority: {result!r}")


def main() -> int:
    validate_authorities()
    original_bytes = LOAD_PATH.read_bytes()
    validate_canonical_load()

    document = load(LOAD_PATH)
    readiness = document.get("readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("load readiness missing")
    for key in REQUIRED_TRUE:
        if readiness.get(key) is not True:
            raise SystemExit(f"cannot summarize unproven readiness flag: {key}")
    for key in (
        "deletionActualProcessKillProven",
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
        "productionEquivalentEnvironmentProvisioned",
        "deletionHostFailureRecoveryProven",
    ):
        if readiness.get(key) is not False:
            raise SystemExit(f"blocking flag unexpectedly promoted: {key}")

    readiness["note"] = (
        "Local evidence now proves post-fence deletion rejection, Preview/Apply/upload-authorization/upload-completion "
        "pre-fence linearization across the primary account-bound HTTP surfaces, bounded multi-account deletion-worker "
        "saturation, lease-expiry attempt-2 recovery including partial object erasure, Docker worker-container SIGKILL plus "
        "independent replacement-container attempt-2 convergence, and repeated 60-minute-or-longer LOCAL_LONG_SOAK execution "
        "with descriptive trend review. The current canonical readiness flags do not claim raw process-kill recovery, and the "
        "local evidence still does not establish leak proof, a production capacity boundary, physical host/node/AZ failure "
        "recovery, production-equivalent dependency behavior, production-shaped sustained-soak evidence or independently "
        "reviewed operating thresholds; OPS-P0-006 remains PARTIAL and Production remains NO_GO."
    )

    deferred = document.get("deferredScenarios")
    if not isinstance(deferred, list):
        raise SystemExit("deferredScenarios missing")
    deletion = next(
        (item for item in deferred if isinstance(item, dict) and item.get("scenarioId") == "deletion-under-load"),
        None,
    )
    if not isinstance(deletion, dict):
        raise SystemExit("deletion-under-load deferred scenario missing")
    deletion["reason"] = (
        "post-fence former-session load, primary Preview/Apply/upload-authorization/upload-completion pre-fence linearization, "
        "bounded multi-account worker saturation, lease-expiry recovery and Docker container kill/replacement recovery are "
        "proven against local dependencies; raw process-kill readiness, physical host/node/AZ loss, production-equivalent "
        "multi-instance topology and dependency behavior, capacity boundary and independently reviewed operating thresholds remain deferred"
    )
    if deletion.get("requiredDependencyMode") != "PRODUCTION_EQUIVALENT":
        raise SystemExit("deletion-under-load deferred dependency boundary drift")

    LOAD_PATH.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    try:
        validate_canonical_load()
    except BaseException:
        LOAD_PATH.write_bytes(original_bytes)
        raise

    print("Memory OS load readiness summary reconciliation PASS")
    print("primary account-bound pre-fence aggregate: proven")
    print("multi-account deletion-worker saturation: proven")
    print("raw process-kill readiness: false")
    print("Docker container kill/replacement recovery: proven")
    print("repeated local sustained soak evidence: proven")
    print("physical host/node/AZ recovery: false")
    print("production-shaped sustained soak evidence: false")
    print("production-equivalent dependencies: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
