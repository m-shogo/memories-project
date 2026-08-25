#!/usr/bin/env python3
"""Fold local deletion lease-expiry recovery evidence into canonical load/chaos authority without claiming process or host failure."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROOF_CONTRACT = ROOT / "contracts/operations/deletion-lease-recovery-contract.v1.json"
PROOF_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json"
PROOF_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-lease-recovery.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
READINESS_NORMALIZER = ROOT / "scripts/reconcile-memory-os-load-readiness-note.py"
MISSING_EVIDENCE_NORMALIZER = ROOT / "scripts/reconcile-memory-os-load-missing-evidence.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

PROOF_REFS = [
    "contracts/operations/deletion-lease-recovery-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_lease_recovery_test.go",
    "scripts/validate-memory-os-deletion-lease-recovery.py",
    "scripts/reconcile-memory-os-deletion-lease-recovery.py",
    ".github/workflows/deletion-lease-recovery.yml",
    "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json",
]

EVIDENCE_TEXT = (
    "exact-source local PostgreSQL plus MinIO deletion lease-recovery proof abandons two one-second leases without "
    "Release/Sweep/Complete, proves no reclaim before expiry, erases one real object before the database sweep while "
    "retaining its canonical ledger, then proves a replacement worker reclaims both jobs at attempt 2 and converges "
    "to zero pending/stuck backlog, zero owned rows, two deleted epoch-2 tombstones and zero object versions without resurrection"
)

CHAOS_TEXT = (
    "deterministic deletion-worker disappearance simulation proves an unreleased lease blocks competing claims until expiry, "
    "then a replacement worker reclaims at attempt 2; a case interrupted after real MinIO object erasure but before the DB "
    "sweep recovers idempotently because the database ledger survives"
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[Any], item: str) -> None:
    if item not in values:
        values.append(item)


def replace_if_present(values: list[Any], old: str, new: str) -> None:
    for index, value in enumerate(values):
        if value == old:
            values[index] = new
            return


def normalize_and_validate_authority() -> None:
    # Normalize the human-readable missing-evidence projection first. It is
    # allowed to deduplicate stale deterministic blocker text while deriving
    # only from already-validated load readiness flags; running the readiness
    # normalizer first would ask aggregate Operability to accept stale duplicate
    # blocker text before the canonical dedupe had a chance to repair it.
    subprocess.run(["python", str(MISSING_EVIDENCE_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(READINESS_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(LOAD_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)


def main() -> int:
    subprocess.run(["python", str(PROOF_VALIDATOR), "--require-result"], cwd=ROOT, check=True)
    contract = load(PROOF_CONTRACT)
    result = load(PROOF_RESULT)
    readiness = contract.get("readiness", {})
    for key in ("exactSourceResultCommitted", "leaseExpiryReclaimProven", "partialObjectErasureRecoveryProven"):
        if readiness.get(key) is not True:
            raise SystemExit(f"lease recovery contract is not reconciled: {key}")
    for key in ("actualProcessKillCovered", "actualHostFailureCovered", "productionDependenciesTested", "productionReady"):
        if readiness.get(key) is not False:
            raise SystemExit(f"local lease recovery may not enable {key}")
    environment = result.get("environment", {})
    if environment.get("leaseAbandonmentSimulation") is not True:
        raise SystemExit("lease recovery result must be classified as simulation")
    for key in ("actualProcessKillCovered", "actualHostFailureCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"local lease recovery result may not enable {key}")

    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()

    load_contract = load(LOAD_CONTRACT)
    load_readiness = load_contract.setdefault("readiness", {})
    if load_readiness.get("primaryAccountBoundPreFenceLinearizationAggregateProven") is not True:
        raise SystemExit("pre-fence aggregate proof must remain true")
    load_readiness["deletionLeaseExpiryRecoverySimulationProven"] = True
    load_readiness["deletionPartialObjectErasureRecoveryProven"] = True
    load_readiness["deletionActualProcessKillProven"] = False
    load_readiness["deletionHostFailureRecoveryProven"] = False
    note = str(load_readiness.get("note", ""))
    addition = (
        " Local lease-expiry recovery now also proves attempt-2 reclaim and idempotent recovery from object-erased-before-DB-sweep "
        "interruption simulation; actual process kill and host failure remain unproven."
    )
    if addition.strip() not in note:
        load_readiness["note"] = note + addition

    for item in load_contract.get("deferredScenarios", []):
        if item.get("scenarioId") == "deletion-under-load":
            item["reason"] = (
                "post-fence former-session load, all primary account-bound pre-fence surfaces, bounded multi-account worker "
                "saturation, lease-expiry reclaim and partial-object-erasure recovery simulation now pass against local PostgreSQL "
                "and MinIO; actual process kill, host failure, production dependency behavior and independently reviewed deletion-load "
                "thresholds remain deferred"
            )
            break
    else:
        raise SystemExit("deletion-under-load deferred scenario missing")
    load_refs = load_contract.setdefault("evidenceRefs", [])
    for ref in PROOF_REFS:
        append_unique(load_refs, ref)

    status = load(STATUS)
    areas = {area.get("id"): area for area in status.get("areas", [])}
    load_gate = areas.get("OPS-P0-006")
    chaos_gate = areas.get("OPS-P0-009")
    if load_gate is None or chaos_gate is None:
        raise SystemExit("OPS-P0-006 or OPS-P0-009 missing")
    for gate in (load_gate, chaos_gate):
        if gate.get("status") != "PARTIAL" or gate.get("blocking") is not True:
            raise SystemExit(f"{gate.get('id')} must remain blocking PARTIAL")

    append_unique(load_gate.setdefault("existingEvidence", []), EVIDENCE_TEXT)
    load_missing = load_gate.setdefault("missingEvidence", [])
    replace_if_present(
        load_missing,
        "host/process failure behavior during deletion-worker execution, production topology and independently reviewed deletion-load thresholds",
        "actual deletion-worker process kill and host failure behavior, production topology and independently reviewed deletion-load thresholds",
    )
    replace_if_present(
        load_missing,
        "deletion-worker process/host interruption recovery, production topology and independently reviewed deletion-load thresholds",
        "actual deletion-worker process kill and host/container interruption recovery, production topology and independently reviewed deletion-load thresholds",
    )
    for ref in PROOF_REFS:
        append_unique(load_gate.setdefault("evidenceRefs", []), ref)

    append_unique(chaos_gate.setdefault("existingEvidence", []), CHAOS_TEXT)
    for ref in PROOF_REFS:
        append_unique(chaos_gate.setdefault("evidenceRefs", []), ref)

    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")

    try:
        write(LOAD_CONTRACT, load_contract)
        write(STATUS, status)
        normalize_and_validate_authority()
    except BaseException:
        LOAD_CONTRACT.write_bytes(original_load)
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS deletion lease recovery canonical reconciliation PASS")
    print("lease expiry recovery simulation: proven")
    print("partial object erasure recovery: proven")
    print("raw process-kill readiness: false")
    print("Docker container kill/replacement recovery: preserved")
    print("actual host failure: false")
    print("OPS-P0-006: PARTIAL")
    print("OPS-P0-009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
