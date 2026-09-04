#!/usr/bin/env python3
"""Reconcile incident-contact routing admission without inventing configured contacts."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/incident-contact-routing-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/incident-contact-routing-admission-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-incident-contact-routing.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-incident-contact-routing.py")
INCIDENT_RESPONSE_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-response.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/incident-contact-routing-admission.yml")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
INCIDENT_RESPONSE_VALIDATOR = ROOT / INCIDENT_RESPONSE_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
POST_WRITE_VALIDATORS = (
    VALIDATOR,
    INCIDENT_RESPONSE_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
WORKFLOW = ROOT / WORKFLOW_REL
STATUS = ROOT / STATUS_REL

EVIDENCE = (
    "incident contact-routing admission is fail-closed and composes with an already-admitted observability stack: future evidence must provide pseudonymous owners and destination digests for incident command, security/privacy, system ownership, provider escalation and user communication, plus delivery/escalation/user-communication drills and independent privacy/operability review; the registry is currently empty"
)
REFS = (
    "contracts/operations/incident-contact-routing-admission-contract.v1.json",
    "contracts/operations/incident-contact-routing-admission-registry.v1.json",
    "scripts/register-memory-os-incident-contact-routing.py",
    "scripts/validate-memory-os-incident-contact-routing.py",
    "scripts/reconcile-memory-os-incident-contact-routing.py",
    ".github/workflows/incident-contact-routing-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (CONTRACT, CONTRACT_REL, "contact routing contract"),
        (REGISTRY, REGISTRY_REL, "contact routing registry"),
        (WRITER, WRITER_REL, "contact routing writer"),
        (VALIDATOR, VALIDATOR_REL, "contact routing validator"),
        (INCIDENT_RESPONSE_VALIDATOR, INCIDENT_RESPONSE_VALIDATOR_REL, "incident response validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW, WORKFLOW_REL, "contact routing workflow"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, relative, field)


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
    require(completed.returncode == 0,
            "canonical contact routing authority is invalid before reconcile")


def atomic_write(path: Path, payload: bytes, mode: int) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    contract_mode = CONTRACT.stat().st_mode & 0o7777
    status_mode = STATUS.stat().st_mode & 0o7777
    try:
        atomic_write(CONTRACT, render(contract), contract_mode)
        atomic_write(STATUS, render(status), status_mode)
        for validator in POST_WRITE_VALIDATORS:
            completed = subprocess.run(["python", str(validator)], cwd=ROOT, check=False)
            require(completed.returncode == 0,
                    f"reconciled contact routing authority failed validation: {validator.name}")
    except BaseException:
        atomic_write(CONTRACT, original_contract, contract_mode)
        atomic_write(STATUS, original_status, status_mode)
        raise


def main() -> int:
    enforce_runtime_authorities()
    for path in (REGISTRY, WRITER, *POST_WRITE_VALIDATORS, WORKFLOW):
        require(path.is_file(), f"contact routing admission missing: {path.relative_to(ROOT)}")

    validate_current_authority()

    registry = load(REGISTRY)
    routings = registry.get("routings")
    require(isinstance(routings, list), "contact routing registry missing")
    pe = sum(1 for row in routings if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for row in routings if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contact routing authority missing")
    current["admittedRoutingCount"] = len(routings)
    current["productionEquivalentRoutingCount"] = pe
    current["productionRoutingCount"] = prod
    current["externalContactTreeOwned"] = len(routings) > 0
    current["pagingAndEscalationDeliveryProven"] = len(routings) > 0
    current["userCommunicationPathProven"] = len(routings) > 0
    current["independentReviewCompleted"] = len(routings) > 0
    current["productionEvidence"] = prod > 0
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["admittedRoutingCount"] = len(routings)
    readiness["productionRoutingAvailable"] = prod > 0
    readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-002"), None)
    require(isinstance(gate, dict), "OPS-P0-002 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-002 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-002 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(refs, ref)

    commit_validated_pair(contract, status)
    print("Memory OS incident contact routing reconciliation PASS")
    print(f"admitted routings: {len(routings)}")
    print("external contact tree owned: false" if not routings else "external contact tree owned: evidence admitted")
    print("OPS-P0-002: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"INCIDENT CONTACT ROUTING RECONCILE FAILED: {exc}")
        raise SystemExit(1)
