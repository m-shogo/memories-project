#!/usr/bin/env python3
"""Fold exact-source local SIGKILL deletion-worker recovery into canonical load/chaos authority."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROOF_CONTRACT = ROOT / "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json"
PROOF_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json"
PROOF_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-sigkill-recovery.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
READINESS_NORMALIZER = ROOT / "scripts/reconcile-memory-os-load-readiness-note.py"
MISSING_EVIDENCE_NORMALIZER = ROOT / "scripts/reconcile-memory-os-load-missing-evidence.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

CANONICAL_AUTHORITIES = {
    "proof contract": PROOF_CONTRACT,
    "proof result": PROOF_RESULT,
    "proof validator": PROOF_VALIDATOR,
    "load contract": LOAD_CONTRACT,
    "production status": STATUS,
    "readiness normalizer": READINESS_NORMALIZER,
    "missing-evidence normalizer": MISSING_EVIDENCE_NORMALIZER,
    "load validator": LOAD_VALIDATOR,
    "operability validator": OPERABILITY_VALIDATOR,
}
CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_OS_REPLACE = os.replace

PROOF_REFS = [
    "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_worker_sigkill_recovery_linux_test.go",
    "scripts/validate-memory-os-deletion-worker-sigkill-recovery.py",
    "scripts/reconcile-memory-os-deletion-worker-sigkill-recovery.py",
    ".github/workflows/deletion-worker-sigkill-recovery.yml",
    "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json",
]

LOAD_EVIDENCE = (
    "exact-source Linux deletion-worker recovery proof launches an independent child test process that claims deletion work "
    "without parent-supplied account/object identifiers, erases a real MinIO object version, is then verified killed by operating-system "
    "SIGKILL before DB sweep or lease release, preserves the canonical DB ledger, blocks reclaim until lease expiry, and converges through "
    "an attempt-2 replacement receipt to zero backlog, owned rows and object versions"
)

CHAOS_EVIDENCE = (
    "actual Linux SIGKILL deletion-worker drill verifies WaitStatus=SIGKILL after real object erasure and before DB sweep/release; "
    "the unreleased lease remains exclusive until expiry and a replacement worker reclaims at attempt 2 without data resurrection"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


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


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


def append_unique(values: list[Any], item: str) -> None:
    if item not in values:
        values.append(item)


def replace_if_present(values: list[Any], old: str, new: str) -> None:
    for index, value in enumerate(values):
        if value == old:
            values[index] = new
            return


def require_canonical_authorities() -> None:
    actual = {
        "proof contract": PROOF_CONTRACT,
        "proof result": PROOF_RESULT,
        "proof validator": PROOF_VALIDATOR,
        "load contract": LOAD_CONTRACT,
        "production status": STATUS,
        "readiness normalizer": READINESS_NORMALIZER,
        "missing-evidence normalizer": MISSING_EVIDENCE_NORMALIZER,
        "load validator": LOAD_VALIDATOR,
        "operability validator": OPERABILITY_VALIDATOR,
    }
    for label, expected in CANONICAL_AUTHORITIES.items():
        path = actual[label]
        require(path == expected, f"{label} authority substitution")
        require(path.is_file() and not path.is_symlink(), f"{label} authority missing or non-canonical")
        require(path.resolve() == expected, f"{label} authority escapes canonical path")
    require(subprocess.run is CANONICAL_SUBPROCESS_RUN, "SIGKILL subprocess transport is not canonical")
    require(os.replace is CANONICAL_OS_REPLACE, "SIGKILL atomic replacement transport is not canonical")
    require(atomic_write_bytes is CANONICAL_ATOMIC_WRITE_BYTES, "SIGKILL atomic writer authority is not canonical")


def normalize_and_validate_authority() -> None:
    require_canonical_authorities()
    subprocess.run(["python", str(READINESS_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(MISSING_EVIDENCE_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(LOAD_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)


def main() -> int:
    require_canonical_authorities()
    subprocess.run(["python", str(PROOF_VALIDATOR), "--require-result"], cwd=ROOT, check=True)
    contract = load(PROOF_CONTRACT)
    result = load(PROOF_RESULT)
    readiness = contract.get("readiness", {})
    if readiness.get("exactSourceResultCommitted") is not True or readiness.get("actualSIGKILLRecoveryProven") is not True:
        raise SystemExit("SIGKILL proof is not reconciled")
    boundary = contract.get("evidenceBoundary", {})
    if boundary.get("actualProcessKillCovered") is not True:
        raise SystemExit("SIGKILL contract must cover actual process kill")
    for key in ("actualHostFailureCovered", "containerRestartCovered", "productionEvidence", "productionEquivalentDependencies", "productionReady"):
        if boundary.get(key) is not False:
            raise SystemExit(f"local SIGKILL proof cannot enable {key}")
    environment = result.get("environment", {})
    if environment.get("actualProcessKillCovered") is not True or result.get("scenario", {}).get("actualSIGKILLObserved") is not True:
        raise SystemExit("actual SIGKILL result evidence missing")
    for key in ("actualHostFailureCovered", "containerRestartCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"local SIGKILL result cannot enable {key}")

    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()

    load_contract = load(LOAD_CONTRACT)
    load_readiness = load_contract.setdefault("readiness", {})
    if load_readiness.get("deletionLeaseExpiryRecoverySimulationProven") is not True:
        raise SystemExit("lease-expiry simulation evidence must remain proven")
    load_readiness["deletionActualProcessKillProven"] = False
    load_readiness["deletionHostFailureRecoveryProven"] = False
    for ref in PROOF_REFS:
        append_unique(load_contract.setdefault("evidenceRefs", []), ref)

    status = load(STATUS)
    areas = {area.get("id"): area for area in status.get("areas", [])}
    load_gate = areas.get("OPS-P0-006")
    chaos_gate = areas.get("OPS-P0-009")
    if load_gate is None or chaos_gate is None:
        raise SystemExit("OPS-P0-006 or OPS-P0-009 missing")
    for gate in (load_gate, chaos_gate):
        if gate.get("status") != "PARTIAL" or gate.get("blocking") is not True:
            raise SystemExit(f"{gate.get('id')} must remain blocking PARTIAL")

    append_unique(load_gate.setdefault("existingEvidence", []), LOAD_EVIDENCE)
    for ref in PROOF_REFS:
        append_unique(load_gate.setdefault("evidenceRefs", []), ref)

    append_unique(chaos_gate.setdefault("existingEvidence", []), CHAOS_EVIDENCE)
    for ref in PROOF_REFS:
        append_unique(chaos_gate.setdefault("evidenceRefs", []), ref)

    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")

    try:
        write(LOAD_CONTRACT, load_contract)
        write(STATUS, status)
        normalize_and_validate_authority()
    except BaseException:
        CANONICAL_ATOMIC_WRITE_BYTES(LOAD_CONTRACT, original_load)
        CANONICAL_ATOMIC_WRITE_BYTES(STATUS, original_status)
        raise

    print("Memory OS deletion SIGKILL canonical reconciliation PASS")
    print("exact local SIGKILL evidence: retained")
    print("raw process-kill readiness: false")
    print("actual host/container failure: false")
    print("OPS-P0-006: PARTIAL")
    print("OPS-P0-009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
