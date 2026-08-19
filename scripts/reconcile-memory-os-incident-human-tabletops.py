#!/usr/bin/env python3
"""Reconcile human tabletop admission infrastructure without creating completion evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/incident-human-tabletop-evidence-contract.v1.json"
LEDGER = ROOT / "docs/evidence/incident-tabletops"
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-human-tabletops.py"
INCIDENT_TABLETOP_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-tabletop.py"
INCIDENT_RESPONSE_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-response.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
POST_WRITE_VALIDATORS = (
    VALIDATOR,
    INCIDENT_TABLETOP_VALIDATOR,
    INCIDENT_RESPONSE_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
WORKFLOW = ROOT / ".github/workflows/incident-human-tabletop-evidence.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "human-led incident tabletop completion admission is append-only and fail-closed: accepted records must preserve the canonical plan, bind an exact source commit, record required command-role assignments and severity-specific closure approvals, and pass the canonical completed-tabletop validator; automated control exercises cannot manufacture human attendance"
)
REFS = (
    "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
    "docs/evidence/incident-tabletops/README.md",
    "scripts/register-memory-os-incident-human-tabletop.py",
    "scripts/validate-memory-os-incident-human-tabletops.py",
    "scripts/reconcile-memory-os-incident-human-tabletops.py",
    ".github/workflows/incident-human-tabletop-evidence.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def validate_current_authority() -> None:
    completed = subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=False)
    require(completed.returncode == 0, "canonical human tabletop authority is invalid before reconcile")


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    try:
        CONTRACT.write_bytes(render(contract))
        STATUS.write_bytes(render(status))
        for validator in POST_WRITE_VALIDATORS:
            completed = subprocess.run(["python", str(validator)], cwd=ROOT, check=False)
            require(completed.returncode == 0,
                    f"reconciled human tabletop authority failed validation: {validator.name}")
    except BaseException:
        CONTRACT.write_bytes(original_contract)
        STATUS.write_bytes(original_status)
        raise


def main() -> int:
    for path in (WRITER, *POST_WRITE_VALIDATORS, WORKFLOW):
        require(path.is_file(), f"human tabletop admission missing: {path.relative_to(ROOT)}")
    validate_current_authority()
    required = set(load(CONTRACT).get("requiredScenarioIds", []))
    accepted = {path.stem for path in LEDGER.glob("IR-DRILL-*.json") if path.is_file()}
    require(accepted <= required, "ledger contains unrecognized scenario")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    count = len(accepted)
    complete = accepted == required
    current["acceptedCompletedScenarioCount"] = count
    current["requiredScenarioCount"] = len(required)
    current["allRequiredScenariosCompleted"] = complete
    current["humanTabletopEvidenceComplete"] = complete
    current["productionRecoveryDrillCompleted"] = False
    current["pagingConfigured"] = False
    current["externalContactTreeOwned"] = False
    current["independentIncidentControlReviewCompleted"] = False
    current["productionEvidence"] = False
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["acceptedCompletedScenarioCount"] = count
    readiness["allRequiredScenariosCompleted"] = complete
    readiness["productionRecoveryDrillCompleted"] = False
    readiness["independentIncidentControlReviewCompleted"] = False
    readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-002"), None)
    require(isinstance(gate, dict), "OPS-P0-002 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-002 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-002 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(refs, ref)
    if complete:
        gate["missingEvidence"] = [item for item in missing if "human-led completed tabletop evidence" not in str(item).lower()]

    commit_validated_pair(contract, status)
    print("Memory OS human tabletop admission reconciliation PASS")
    print(f"accepted completed scenarios: {count}/{len(required)}")
    print(f"human tabletop evidence complete: {complete}")
    print("production recovery drill: false")
    print("OPS-P0-002: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"HUMAN TABLETOP RECONCILE FAILED: {exc}")
        raise SystemExit(1)
