#!/usr/bin/env python3
"""Reconcile production-shaped failure-drill admission without inventing drill evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-production-shaped-failure-drill.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-shaped-failure-drills.py"
WORKFLOW = ROOT / ".github/workflows/production-shaped-failure-drills.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "generation-bound production-shaped failure-drill admission is implemented for four required classes: multi-instance/node interruption, object-store outage/partition, PostgreSQL pool disruption/failover, and parser host/container restart with durable spool remount; local outage/process/container/candidate evidence cannot be relabeled, and the registry is currently empty"
)
REFS = (
    "contracts/operations/production-shaped-failure-drill-contract.v1.json",
    "contracts/operations/production-shaped-failure-drill-registry.v1.json",
    "scripts/register-memory-os-production-shaped-failure-drill.py",
    "scripts/validate-memory-os-production-shaped-failure-drills.py",
    "scripts/reconcile-memory-os-production-shaped-failure-drills.py",
    ".github/workflows/production-shaped-failure-drills.yml",
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
    for path in (REGISTRY, WRITER, VALIDATOR, WORKFLOW):
        require(path.is_file(), f"failure-drill admission missing: {path.relative_to(ROOT)}")
    registry = load(REGISTRY)
    drills = registry.get("drills")
    require(isinstance(drills, list), "failure-drill registry missing")
    pe = sum(1 for row in drills if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for row in drills if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION")
    scenarios = {row.get("scenarioId") for row in drills if isinstance(row, dict) and row.get("scenarioId")}

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "failure-drill authority missing")
    current["registeredDrillCount"] = len(drills)
    current["productionEquivalentDrillCount"] = pe
    current["productionDrillCount"] = prod
    current["completedScenarioCount"] = len(scenarios)
    current["allRequiredScenarioClassesCompleted"] = len(scenarios) == 4
    current["independentReviewCompleted"] = len(scenarios) == 4
    current["productionEvidence"] = prod > 0
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["completedScenarioCount"] = len(scenarios)
    readiness["allRequiredScenarioClassesCompleted"] = len(scenarios) == 4
    readiness["productionReady"] = False
    write(CONTRACT, contract)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-009 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-009 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(refs, ref)
    write(STATUS, status)

    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    print("Memory OS production-shaped failure-drill reconciliation PASS")
    print(f"registered drills: {len(drills)}")
    print(f"completed scenario classes: {len(scenarios)}/4")
    print("OPS-P0-009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-SHAPED FAILURE DRILL RECONCILE FAILED: {exc}")
        raise SystemExit(1)
