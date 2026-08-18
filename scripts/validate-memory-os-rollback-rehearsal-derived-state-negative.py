#!/usr/bin/env python3
"""Reject rollback derived-state drift while preserving deterministic reconciliation."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REHEARSAL_REGISTRY = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-rollback-rehearsal-gate.py"
WRITER = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-rollback-rehearsal-gate.py"
COUNT_FIELDS = (
    "approvedReleaseCount",
    "rollbackEligibleReleaseCount",
    "admissibleReleasePairCount",
    "rehearsalRequestCount",
)


def load_writer():
    spec = importlib.util.spec_from_file_location("rollback_rehearsal_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rollback rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rejected(candidate: dict, label: str) -> None:
    CONTRACT.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        raise RuntimeError(f"standalone rollback validator accepted {label}")


def writer_rejected(writer, candidate: dict, label: str) -> None:
    try:
        writer.validate_contract_for_append(candidate)
    except writer.RequestFailure:
        return
    raise RuntimeError(f"rollback writer accepted {label}")


def writer_registry_rejected(writer, candidate: dict, label: str) -> None:
    release_registry = json.loads(RELEASE_REGISTRY.read_text(encoding="utf-8"))
    rehearsal_registry = json.loads(REHEARSAL_REGISTRY.read_text(encoding="utf-8"))
    try:
        writer.validate_registry_for_append(rehearsal_registry, candidate, release_registry)
    except writer.RequestFailure:
        return
    raise RuntimeError(f"rollback writer registry guard accepted {label}")


def reconciler_repairs_derived_drift(base: dict, contract_bytes: bytes, status_bytes: bytes) -> None:
    candidate = copy.deepcopy(base)
    candidate["currentAdmissionState"]["approvedReleaseCount"] = 1
    CONTRACT.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(RECONCILER)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "rollback reconciler failed to repair deterministic derived-state drift: "
            + completed.stderr.strip()
        )
    if CONTRACT.read_bytes() != contract_bytes:
        raise RuntimeError("rollback reconciler did not restore canonical derived contract bytes")
    if STATUS.read_bytes() != status_bytes:
        raise RuntimeError("rollback reconciler changed production status while repairing derived drift")


def main() -> int:
    original = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    base = json.loads(original.decode("utf-8"))
    writer = load_writer()
    try:
        for field in COUNT_FIELDS:
            for bad in (False, -1):
                candidate = copy.deepcopy(base)
                candidate["currentAdmissionState"][field] = bad
                rejected(candidate, f"invalid {field}={bad!r}")
                writer_rejected(writer, candidate, f"invalid {field}={bad!r}")

        candidate = copy.deepcopy(base)
        candidate["currentAdmissionState"]["automaticPromotionAuthorized"] = True
        rejected(candidate, "unknown currentAdmissionState field")
        writer_rejected(writer, candidate, "unknown currentAdmissionState field")

        candidate = copy.deepcopy(base)
        candidate["currentAdmissionState"].pop("admissionDecision")
        rejected(candidate, "missing currentAdmissionState field")
        writer_rejected(writer, candidate, "missing currentAdmissionState field")

        candidate = copy.deepcopy(base)
        candidate["readiness"]["productionAuthorization"] = True
        rejected(candidate, "unknown readiness field")
        writer_rejected(writer, candidate, "unknown readiness field")

        candidate = copy.deepcopy(base)
        candidate["readiness"].pop("productionReady")
        rejected(candidate, "missing readiness field")
        writer_rejected(writer, candidate, "missing readiness field")

        candidate = copy.deepcopy(base)
        candidate["currentAdmissionState"]["approvedReleaseCount"] = 1
        writer_registry_rejected(writer, candidate, "approved release source-count drift")

        candidate = copy.deepcopy(base)
        candidate["currentAdmissionState"]["rehearsalRequestCount"] = 1
        candidate["readiness"]["rehearsalRequested"] = True
        writer_registry_rejected(writer, candidate, "rehearsal request source-count drift")

        CONTRACT.write_bytes(original)
        STATUS.write_bytes(original_status)
        reconciler_repairs_derived_drift(base, original, original_status)
    finally:
        CONTRACT.write_bytes(original)
        STATUS.write_bytes(original_status)

    if CONTRACT.read_bytes() != original:
        raise RuntimeError("rollback contract bytes changed after derived-state negative suite")
    if STATUS.read_bytes() != original_status:
        raise RuntimeError("production status bytes changed after derived-state negative suite")
    print("PASS: rollback direct authority is strict while deterministic derived drift remains repairable")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL DERIVED STATE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
