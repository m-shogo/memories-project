#!/usr/bin/env python3
"""Reconcile production-shaped failure-drill admission without inventing drill evidence."""

from __future__ import annotations

import importlib.util
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
CHAOS_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

LEGACY_EMPTY_EVIDENCE = (
    "generation-bound production-shaped failure-drill admission is implemented for four required classes: multi-instance/node interruption, object-store outage/partition, PostgreSQL pool disruption/failover, and parser host/container restart with durable spool remount; local outage/process/container/candidate evidence cannot be relabeled, and the registry is currently empty"
)
EVIDENCE = (
    "generation-bound production-shaped failure-drill admission is implemented for four required classes: multi-instance/node interruption, object-store outage/partition, PostgreSQL pool disruption/failover, and parser host/container restart with durable spool remount; local outage/process/container/candidate evidence cannot be relabeled and admitted drill counts remain derived only from the canonical append-only registry"
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


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_registry_before_reconcile(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validator = load_module(VALIDATOR, "memory_os_production_failure_validator_for_reconcile")
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "failure-drill registry validator authority drift")
    require(validator.WRITER.resolve() == WRITER.resolve(), "failure-drill writer validator authority drift")
    try:
        return validator.validate_registry_for_append(registry)
    except validator.Fail as exc:
        raise Fail(f"existing failure-drill registry rejected before reconcile: {exc}") from exc


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def replace_legacy_evidence(values: list[Any]) -> None:
    while LEGACY_EMPTY_EVIDENCE in values:
        values.remove(LEGACY_EMPTY_EVIDENCE)
    append_once(values, EVIDENCE)


def run_validator(path: Path, failure_label: str) -> None:
    completed = subprocess.run(
        ["python", str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        failure_label + ":\n" + completed.stdout[-4000:] + completed.stderr[-4000:],
    )


def commit_outputs_transactionally(outputs: dict[Path, dict[str, Any]]) -> None:
    originals = {path: path.read_bytes() for path in outputs}
    try:
        for path, value in outputs.items():
            write(path, value)
        run_validator(VALIDATOR, "failure-drill authority rejected after reconcile")
        run_validator(CHAOS_VALIDATOR, "chaos authority rejected after failure-drill reconcile")
        run_validator(OPERABILITY_VALIDATOR, "operability authority rejected after failure-drill reconcile")
    except Exception as exc:
        for path, data in originals.items():
            path.write_bytes(data)
        raise Fail(f"failure-drill reconcile validation failed; restored prior authority: {exc}") from exc


def main() -> int:
    for path in (REGISTRY, WRITER, VALIDATOR, WORKFLOW, CHAOS_VALIDATOR, OPERABILITY_VALIDATOR):
        require(path.is_file(), f"failure-drill admission missing: {path.relative_to(ROOT)}")
    registry = load(REGISTRY)
    drills = validate_registry_before_reconcile(registry)
    pe = sum(1 for row in drills if row.get("environmentClass") == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for row in drills if row.get("environmentClass") == "PRODUCTION")
    scenarios = {row.get("scenarioId") for row in drills if row.get("scenarioId")}

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

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-009 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-009 authority arrays missing")
    replace_legacy_evidence(existing)
    for ref in REFS:
        append_once(refs, ref)

    commit_outputs_transactionally({CONTRACT: contract, STATUS: status})

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
