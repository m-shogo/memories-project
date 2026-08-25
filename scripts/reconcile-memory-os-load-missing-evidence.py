#!/usr/bin/env python3
"""Normalize OPS-P0-006 missing evidence from canonical load readiness flags."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
LOAD = CANONICAL_LOAD
STATUS = CANONICAL_STATUS
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR

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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def validate_authorities() -> None:
    require_exact_authority(LOAD, CANONICAL_LOAD, "load contract")
    require_exact_authority(STATUS, CANONICAL_STATUS, "production status")
    require_exact_authority(LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator")
    require_exact_authority(OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, existing_mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


def validate(path: Path) -> None:
    subprocess.run(["python", str(path)], cwd=ROOT, check=True)


def main() -> int:
    validate_authorities()
    validate(LOAD_VALIDATOR)

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

    status_bytes = STATUS.read_bytes()
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

    try:
        write(STATUS, status)
        validate(LOAD_VALIDATOR)
        validate(OPERABILITY_VALIDATOR)
    except BaseException:
        atomic_write_bytes(STATUS, status_bytes)
        raise

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
