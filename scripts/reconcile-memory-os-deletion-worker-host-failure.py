#!/usr/bin/env python3
"""Register physical host/node deletion-failure admission without claiming execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/deletion-worker-host-failure-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-host-failure.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
WORKFLOW = ROOT / ".github/workflows/deletion-worker-host-failure-admission.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"

EVIDENCE = (
    "physical host/node deletion-worker failure admission is now fail-closed: actual process SIGKILL and Docker container kill remain local evidence only; "
    "host/node proof requires a registered production-equivalent environment generation, an external failure controller outside the target node, a replacement "
    "worker on a distinct node, lease exclusion until expiry, attempt-2 reclaim, dependency reconnect, zero-row/object convergence and independent review"
)
REFS = (
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "scripts/validate-memory-os-deletion-worker-host-failure.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    ".github/workflows/deletion-worker-host-failure-admission.yml",
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


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def write_transactionally(contract: dict[str, Any], status: dict[str, Any]) -> None:
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    try:
        CONTRACT.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
        subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)
    except Exception as exc:
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)
        if isinstance(exc, Fail):
            raise
        raise Fail(f"host-failure post-write authority validation failed: {exc}") from exc


def main() -> int:
    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "host-failure readiness missing")
    require(readiness.get("contractDefined") is True and readiness.get("validatorImplemented") is True, "host-failure foundation incomplete")
    if WORKFLOW.is_file():
        readiness["automaticWorkflowImplemented"] = True

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    for gate_id in ("OPS-P0-006", "OPS-P0-009"):
        gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == gate_id), None)
        require(isinstance(gate, dict), f"{gate_id} missing")
        require(str(gate.get("status")).startswith("PARTIAL"), f"{gate_id} must remain PARTIAL")
        existing = gate.get("existingEvidence")
        missing = gate.get("missingEvidence")
        refs = gate.get("evidenceRefs")
        require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), f"{gate_id} authority arrays missing")
        append_once(existing, EVIDENCE)
        for ref in REFS:
            require((ROOT / ref).is_file(), f"host-failure evidence ref missing: {ref}")
            append_once(refs, ref)
        joined = "\n".join(str(item).lower() for item in missing)
        require("host" in joined or "node" in joined, f"{gate_id} must retain physical host/node blocker")

    load_contract = load(LOAD)
    readiness_load = load_contract.get("readiness")
    require(isinstance(readiness_load, dict), "load readiness missing")
    require(readiness_load.get("deletionContainerKillRecoveryProven") is True, "container recovery must remain proven")
    require(readiness_load.get("deletionHostFailureRecoveryProven") is False, "host recovery cannot be promoted by admission foundation")

    write_transactionally(contract, status)
    print("Memory OS deletion-worker host-failure admission reconciliation PASS")
    print("container recovery: proven locally")
    print("physical host/node recovery: unexecuted")
    print("OPS-P0-006/009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST FAILURE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
