#!/usr/bin/env python3
"""Register exact-source automated incident control exercise evidence."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/incident-control-exercise-contract.v1.json")
RESULT_REL = Path("docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
EXERCISE_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-control-exercise.py")
INCIDENT_RESPONSE_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-response.py")
TABLETOP_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-tabletop.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
RUNNER_REL = Path("scripts/run-memory-os-incident-control-exercise.py")
WORKFLOW_REL = Path(".github/workflows/incident-control-exercise.yml")
CONTRACT_PATH = ROOT / CONTRACT_REL
RESULT_PATH = ROOT / RESULT_REL
STATUS_PATH = ROOT / STATUS_REL
EXERCISE_VALIDATOR = ROOT / EXERCISE_VALIDATOR_REL
INCIDENT_RESPONSE_VALIDATOR = ROOT / INCIDENT_RESPONSE_VALIDATOR_REL
TABLETOP_VALIDATOR = ROOT / TABLETOP_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
RUNNER = ROOT / RUNNER_REL
WORKFLOW = ROOT / WORKFLOW_REL

NEW_EXISTING = (
    "exact-source automated incident control exercise covering tenant isolation, PostgreSQL commit outage, object-store outage, migration/version incompatibility, restore non-resurrection and parser compromise/stall scenarios",
    "all scenario-specific repository validators pass with output stored only as SHA-256 digests and bounded byte counts rather than raw logs",
    "severity, declaration, containment, stop conditions, evidence preservation, recovery verification, promotion block and closure block are retained for all six scenarios",
    "automated exercise explicitly leaves human tabletop, paging, external communications, production recovery drill and independent approval incomplete",
)
NEW_HUMAN_GAP = (
    "human-led completed tabletop evidence for all required scenarios with named command roles, attendance, timed inject responses, decisions, action owners and closure approvals",
)
NEW_REFS = (
    "contracts/operations/incident-control-exercise-contract.v1.json",
    "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json",
    "scripts/run-memory-os-incident-control-exercise.py",
    "scripts/validate-memory-os-incident-control-exercise.py",
    "scripts/reconcile-memory-os-incident-control-exercise.py",
    ".github/workflows/incident-control-exercise.yml",
)
IMPLEMENTED_READINESS = (
    "contractDefined",
    "runnerImplemented",
    "validatorImplemented",
    "automaticWorkflowImplemented",
    "exactSourcePassResultCommitted",
)
UNPROVEN_READINESS = (
    "humanTabletopCompleted",
    "pagingAndAcknowledgementExercised",
    "externalContactTreeExercised",
    "productionRecoveryDrillCompleted",
    "independentReviewCompleted",
    "productionReady",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (CONTRACT_PATH, CONTRACT_REL, "incident exercise contract"),
        (RESULT_PATH, RESULT_REL, "incident exercise result"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (EXERCISE_VALIDATOR, EXERCISE_VALIDATOR_REL, "incident exercise validator"),
        (INCIDENT_RESPONSE_VALIDATOR, INCIDENT_RESPONSE_VALIDATOR_REL, "incident response validator"),
        (TABLETOP_VALIDATOR, TABLETOP_VALIDATOR_REL, "incident tabletop validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (RUNNER, RUNNER_REL, "incident exercise runner"),
        (WORKFLOW, WORKFLOW_REL, "incident exercise workflow"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_exercise_validator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "memory_os_incident_control_exercise_validator",
        EXERCISE_VALIDATOR,
    )
    require(spec is not None and spec.loader is not None,
            "incident exercise validator loader unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(hasattr(module, "validate_contract") and hasattr(module, "validate_result") and
            hasattr(module, "ValidationFailure"),
            "incident exercise validator authority drift")
    return module


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path) -> None:
    completed = subprocess.run(["python", str(path)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            f"reconciled incident authority failed validation: {path.name}")


def run_canonical_validators() -> None:
    for validator in (
        EXERCISE_VALIDATOR,
        INCIDENT_RESPONSE_VALIDATOR,
        TABLETOP_VALIDATOR,
        OPERABILITY_VALIDATOR,
    ):
        run_validator(validator)


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        CONTRACT_PATH.write_bytes(render(contract))
        STATUS_PATH.write_bytes(render(status))
        run_canonical_validators()
    except BaseException:
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    enforce_runtime_authorities()
    result = load(RESULT_PATH)
    contract = load(CONTRACT_PATH)
    validator = load_exercise_validator()
    try:
        validator.validate_contract(contract)
        validator.validate_result(result, contract, None)
    except validator.ValidationFailure as exc:
        raise ReconcileFailure(f"incident exercise source authority rejected: {exc}") from exc

    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict), "incident exercise readiness missing")
    require(isinstance(refs, list), "incident exercise evidenceRefs must be a list")
    contract_changed = False
    for field in IMPLEMENTED_READINESS:
        if readiness.get(field) is not True:
            readiness[field] = True
            contract_changed = True
    for field in UNPROVEN_READINESS:
        require(readiness.get(field) is False,
                f"automated exercise cannot promote readiness.{field}")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"incident exercise evidence missing: {ref}")
        contract_changed = append_once(refs, ref) or contract_changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "automated exercise cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-002"), None)
    require(isinstance(gate, dict), "OPS-P0-002 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-002 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-002 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-002 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-002 evidenceRefs must be a list")

    status_changed = False
    for item in NEW_EXISTING:
        status_changed = append_once(existing, item) or status_changed
    coarse = [item for item in missing
              if isinstance(item, str) and
              "completed tabletop evidence" in item.lower() and
              "human-led" not in item.lower()]
    for item in coarse:
        missing.remove(item)
        status_changed = True
    for item in NEW_HUMAN_GAP:
        status_changed = append_once(missing, item) or status_changed
    for ref in NEW_REFS:
        status_changed = append_once(status_refs, ref) or status_changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "paging": ("paging", "acknowledgement"),
        "external contact tree": ("external", "contact"),
        "human tabletop": ("human-led", "tabletop"),
        "production recovery drill": ("production", "recovery", "drill"),
        "independent review": ("independent", "review"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required OPS-P0-002 gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL", "automated exercise changed readiness")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not contract_changed and not status_changed:
        run_canonical_validators()
        print("Incident control exercise authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_validated_pair(contract, status)
    print("Registered automated incident control exercise; OPS-P0-002 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"INCIDENT CONTROL EXERCISE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)