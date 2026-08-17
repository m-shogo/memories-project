#!/usr/bin/env python3
"""Fold exact-source Docker container-kill recovery into canonical load/chaos authority without claiming host failure."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROOF_CONTRACT = ROOT / "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json"
PROOF_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json"
PROOF_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

PROOF_REFS = [
    "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json",
    "services/import-api/cmd/deletion-container-drill/main.go",
    "services/import-api/cmd/deletion-container-drill-helper/main.go",
    "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py",
    "scripts/reconcile-memory-os-deletion-worker-container-kill-recovery.py",
    ".github/workflows/deletion-worker-container-kill-recovery.yml",
    "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json",
]

LOAD_EVIDENCE = (
    "exact-source Docker deletion-worker drill proves container A claims attempt 1 without host-supplied account/object identity, "
    "erases a real MinIO version, is killed with SIGKILL/exit 137 before DB sweep or lease release, preserves the canonical ledger "
    "and lease exclusion, then container B reclaims attempt 2 after expiry and converges to zero backlog, owned rows and object versions"
)

CHAOS_EVIDENCE = (
    "actual Docker worker-container kill/replacement drill verifies SIGKILL exit 137 after real object erasure, lease exclusivity until expiry, "
    "and independent replacement-container attempt-2 convergence under memory_app_login with superuser/BYPASSRLS forbidden"
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


def validate_reconciled_authority() -> None:
    subprocess.run(["python", str(LOAD_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)


def main() -> int:
    subprocess.run(["python", str(PROOF_VALIDATOR), "--require-result"], cwd=ROOT, check=True)
    contract = load(PROOF_CONTRACT)
    result = load(PROOF_RESULT)
    readiness = contract.get("readiness", {})
    if readiness.get("exactSourceResultCommitted") is not True or readiness.get("actualContainerKillRecoveryProven") is not True:
        raise SystemExit("container-kill proof is not reconciled")
    boundary = contract.get("evidenceBoundary", {})
    for key in ("actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        if boundary.get(key) is not True:
            raise SystemExit(f"container proof coverage missing: {key}")
    for key in ("actualHostFailureCovered", "availabilityZoneFailureCovered", "productionEvidence", "productionEquivalentDependencies", "productionReady"):
        if boundary.get(key) is not False:
            raise SystemExit(f"container proof cannot enable {key}")
    environment = result.get("environment", {})
    for key in ("actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        if environment.get(key) is not True:
            raise SystemExit(f"result coverage missing: {key}")
    for key in ("actualHostFailureCovered", "availabilityZoneFailureCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"result cannot enable {key}")

    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()

    load_contract = load(LOAD_CONTRACT)
    load_readiness = load_contract.setdefault("readiness", {})
    if load_readiness.get("deletionActualProcessKillProven") is not True:
        raise SystemExit("actual process-kill proof must remain proven")
    load_readiness["deletionContainerKillRecoveryProven"] = True
    load_readiness["deletionReplacementContainerRecoveryProven"] = True
    load_readiness["deletionHostFailureRecoveryProven"] = False
    note = str(load_readiness.get("note", ""))
    addition = " Docker worker-container kill/replacement recovery is proven locally; physical host/node/AZ failure remains unproven."
    if addition.strip() not in note:
        load_readiness["note"] = note + addition
    for item in load_contract.get("deferredScenarios", []):
        if item.get("scenarioId") == "deletion-under-load":
            item["reason"] = (
                "post-fence former-session load, all primary account-bound pre-fence surfaces, multi-account worker saturation, "
                "lease-expiry/partial-object recovery, actual Linux SIGKILL and Docker worker-container kill/replacement now pass locally; "
                "physical host/node failure, production dependency behavior and independently reviewed deletion-load thresholds remain deferred"
            )
            break
    else:
        raise SystemExit("deletion-under-load deferred scenario missing")
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
    missing = load_gate.setdefault("missingEvidence", [])
    replace_if_present(
        missing,
        "actual deletion-worker host/container failure behavior, production topology and independently reviewed deletion-load thresholds",
        "actual physical host/node failure behavior, production topology and independently reviewed deletion-load thresholds",
    )
    replace_if_present(
        missing,
        "actual deletion-worker host/container interruption recovery, production topology and independently reviewed deletion-load thresholds",
        "actual physical host/node interruption recovery, production topology and independently reviewed deletion-load thresholds",
    )
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
        validate_reconciled_authority()
    except BaseException:
        LOAD_CONTRACT.write_bytes(original_load)
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS deletion container-kill canonical reconciliation PASS")
    print("actual Docker container kill/replacement: proven")
    print("actual physical host/node failure: false")
    print("OPS-P0-006: PARTIAL")
    print("OPS-P0-009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
