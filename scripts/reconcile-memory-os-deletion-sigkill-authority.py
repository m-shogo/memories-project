#!/usr/bin/env python3
"""Fold exact-source local SIGKILL deletion-worker recovery into canonical load/chaos authority."""

from __future__ import annotations

import json
import subprocess
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
    subprocess.run(["python", str(READINESS_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(MISSING_EVIDENCE_NORMALIZER)], cwd=ROOT, check=True)
    subprocess.run(["python", str(LOAD_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)


def main() -> int:
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
    # Keep the current aggregate readiness boundary: the exact local SIGKILL result is evidence,
    # but raw process-kill readiness remains deliberately unpromoted.
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
        LOAD_CONTRACT.write_bytes(original_load)
        STATUS.write_bytes(original_status)
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
