#!/usr/bin/env python3
"""Reconcile the non-runtime rate-limit emergency ledger foundation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-emergency-ledger-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-emergency-ledger.v1.json"
WRITER = ROOT / "scripts/register-memory-os-rate-limit-emergency-operation.py"
EVALUATOR = ROOT / "scripts/evaluate-memory-os-rate-limit-emergency-state.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-emergency-ledger.py"
WORKFLOW = ROOT / ".github/workflows/rate-limit-emergency-ledger.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "append-only rate-limit emergency-operation ledger foundation is implemented with bounded activation-intent validation, distinct operator/reviewer identities, exact-source and policy binding, a hard 60-minute maximum, fail-open prohibition and a read-only effective-state evaluator that expires stale intent fail-closed; runtime policy is deliberately not mutated and production evidence remains false"
)
REFS = (
    "contracts/operations/rate-limit-emergency-ledger-contract.v1.json",
    "contracts/operations/rate-limit-emergency-ledger.v1.json",
    "scripts/register-memory-os-rate-limit-emergency-operation.py",
    "scripts/evaluate-memory-os-rate-limit-emergency-state.py",
    "scripts/validate-memory-os-rate-limit-emergency-ledger.py",
    "scripts/reconcile-memory-os-rate-limit-emergency-ledger.py",
    ".github/workflows/rate-limit-emergency-ledger.yml",
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


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    for path in (REGISTRY, WRITER, EVALUATOR, VALIDATOR, WORKFLOW):
        require(path.is_file(), f"rate-limit ledger foundation missing: {path.relative_to(ROOT)}")
    registry = load(REGISTRY)
    contract = load(CONTRACT)
    events = registry.get("events")
    require(isinstance(events, list), "ledger events missing")
    event_count = len(events)
    operation_count = len({row.get("operationId") for row in events if isinstance(row, dict) and row.get("operationId")})
    production_operations = len({row.get("operationId") for row in events if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION" and row.get("operationId")})
    runtime_applied = sum(1 for row in events if isinstance(row, dict) and row.get("runtimeApplied") is True)
    production_evidence = sum(1 for row in events if isinstance(row, dict) and row.get("productionEvidence") is True)
    registry["registeredEventCount"] = event_count
    registry["registeredOperationCount"] = operation_count
    registry["productionOperationCount"] = production_operations
    registry["runtimeAppliedEventCount"] = runtime_applied
    registry["productionEvidenceEventCount"] = production_evidence
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    write(REGISTRY, registry)

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "ledger contract authority missing")
    current["registeredEventCount"] = event_count
    current["registeredOperationCount"] = operation_count
    current["productionOperationCount"] = production_operations
    current["runtimeAppliedEventCount"] = runtime_applied
    current["productionEvidenceEventCount"] = production_evidence
    current["runtimeControlPlaneIntegrated"] = False
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["effectiveStateEvaluatorImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["automaticExpiryAuthorityImplemented"] = True
    readiness["runtimeControlPlaneIntegrated"] = False
    readiness["productionEmergencyOperationRecorded"] = production_operations > 0 and runtime_applied > 0
    readiness["completedRuntimeDrill"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False
    require(readiness["productionEmergencyOperationRecorded"] is False, "ledger-only records cannot become production emergency proof")
    write(CONTRACT, contract)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-005"), None)
    require(isinstance(gate, dict), "OPS-P0-005 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-005 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-005 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(refs, ref)
    write(STATUS, status)

    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    print("Memory OS rate-limit emergency ledger reconciliation PASS")
    print(f"registered events: {event_count}")
    print("automatic expiry authority: implemented")
    print("runtime control plane integrated: false")
    print("OPS-P0-005: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE-LIMIT EMERGENCY LEDGER RECONCILE FAILED: {exc}")
        raise SystemExit(1)
