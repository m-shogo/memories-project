#!/usr/bin/env python3
"""Register exact-source automated incident control exercise evidence."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXERCISE_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-control-exercise.py"
INCIDENT_RESPONSE_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-response.py"
TABLETOP_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-tabletop.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path) -> None:
    completed = subprocess.run(["python", str(path)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            f"reconciled incident authority failed validation: {path.name}")


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        CONTRACT_PATH.write_bytes(render(contract))
        STATUS_PATH.write_bytes(render(status))
        for validator in (
            EXERCISE_VALIDATOR,
            INCIDENT_RESPONSE_VALIDATOR,
            TABLETOP_VALIDATOR,
            OPERABILITY_VALIDATOR,
        ):
            run_validator(validator)
    except BaseException:
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") ==
            "memory-os-incident-control-exercise-results.v1",
            "incident exercise result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "incident exercise source SHA is not an ancestor")
    environment = result.get("environment")
    require(isinstance(environment, dict), "incident exercise environment missing")
    require(environment.get("productionEvidence") is False and
            environment.get("humanTabletopCompleted") is False and
            environment.get("pagingConfigured") is False and
            environment.get("containsSecrets") is False,
            "incident exercise evidence boundary drift")
    exercise = result.get("exercise")
    require(isinstance(exercise, dict), "incident exercise body missing")
    require(exercise.get("overallResult") == "AUTOMATED_CONTROL_EXERCISE_PASS",
            "automated control exercise is not PASS")
    require(exercise.get("humanTabletopResult") == "NOT_COMPLETED" and
            exercise.get("productionDrillResult") == "NOT_COMPLETED" and
            exercise.get("closureResult") == "BLOCKED_PENDING_HUMAN_APPROVAL",
            "incident exercise overclaims completion")
    scenarios = exercise.get("scenarios")
    require(isinstance(scenarios, list) and len(scenarios) == 6,
            "incident exercise must contain six scenarios")
    require(all(isinstance(item, dict) and item.get("controlResult") == "CONTROL_PATH_PASS"
                for item in scenarios),
            "incident exercise contains a failed control path")

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-incident-control-exercise.v1",
            "incident exercise contract schema drift")
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
