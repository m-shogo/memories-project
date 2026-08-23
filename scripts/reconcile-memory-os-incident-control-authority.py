#!/usr/bin/env python3
"""Normalize the incident control exercise contract and OPS-P0-002 authority."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/incident-control-exercise-contract.v1.json")
RESULT_REL = Path("docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
VALIDATOR_REL = Path("scripts/validate-memory-os-incident-control-exercise.py")
INCIDENT_RESPONSE_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-response.py")
TABLETOP_VALIDATOR_REL = Path("scripts/validate-memory-os-incident-tabletop.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/reconcile-incident-control-authority.yml")
CONTRACT_PATH = ROOT / CONTRACT_REL
RESULT_PATH = ROOT / RESULT_REL
STATUS_PATH = ROOT / STATUS_REL
VALIDATOR_PATH = ROOT / VALIDATOR_REL
INCIDENT_RESPONSE_VALIDATOR = ROOT / INCIDENT_RESPONSE_VALIDATOR_REL
TABLETOP_VALIDATOR = ROOT / TABLETOP_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL
POST_WRITE_VALIDATORS = (
    VALIDATOR_PATH,
    INCIDENT_RESPONSE_VALIDATOR,
    TABLETOP_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

EVIDENCE_REFS = (
    "contracts/operations/incident-control-exercise-contract.v1.json",
    "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json",
    "scripts/run-memory-os-incident-control-exercise.py",
    "scripts/validate-memory-os-incident-control-exercise.py",
    "scripts/reconcile-memory-os-incident-control-exercise.py",
    "scripts/reconcile-memory-os-incident-control-authority.py",
    ".github/workflows/incident-control-exercise.yml",
    ".github/workflows/reconcile-incident-control-authority.yml",
)
EXISTING = (
    "exact-source automated incident control exercise covering tenant isolation, PostgreSQL commit outage, object-store outage, migration/version incompatibility, restore non-resurrection and parser compromise/stall scenarios",
    "all scenario-specific repository validators pass with output stored only as SHA-256 digests and bounded byte counts rather than raw logs",
    "severity, declaration, containment, stop conditions, evidence preservation, recovery verification, promotion block and closure block are retained for all six scenarios",
    "automated exercise explicitly leaves human tabletop, paging, external communications, production recovery drill and independent approval incomplete",
)
HUMAN_GAP = "human-led completed tabletop evidence for all required scenarios with named command roles, attendance, timed inject responses, decisions, action owners and closure approvals"


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
        (CONTRACT_PATH, CONTRACT_REL, "incident control contract"),
        (RESULT_PATH, RESULT_REL, "incident control result"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (VALIDATOR_PATH, VALIDATOR_REL, "incident control validator"),
        (INCIDENT_RESPONSE_VALIDATOR, INCIDENT_RESPONSE_VALIDATOR_REL, "incident response validator"),
        (TABLETOP_VALIDATOR, TABLETOP_VALIDATOR_REL, "incident tabletop validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "incident control authority workflow"),
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


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def load_canonical_validator() -> Any:
    enforce_runtime_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_incident_control_validator", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None,
            "canonical incident validator cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - import failures are fail-closed
        raise ReconcileFailure(f"canonical incident validator load failed: {exc}") from exc
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT_PATH,
            "canonical incident validator contract authority drift")
    require(getattr(module, "RESULT_PATH", None) == RESULT_PATH,
            "canonical incident validator result authority drift")
    require(callable(getattr(module, "validate_contract", None)),
            "canonical incident contract validator missing")
    require(callable(getattr(module, "validate_result", None)),
            "canonical incident result validator missing")
    return module


def validate_result(result: dict[str, Any], contract: dict[str, Any]) -> None:
    require(source_is_ancestor(result.get("commitSha")),
            "incident control source SHA is not an ancestor")
    validator = load_canonical_validator()
    try:
        validator.validate_contract(contract)
        validator.validate_result(result, contract, None)
    except Exception as exc:
        raise ReconcileFailure(f"canonical incident result validation failed: {exc}") from exc


def validate_current_authority() -> None:
    enforce_runtime_authorities()
    for validator in POST_WRITE_VALIDATORS:
        completed = subprocess.run(["python", str(validator)], cwd=ROOT, check=False)
        require(completed.returncode == 0,
                f"canonical incident authority invalid before reconcile: {validator.name}")


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        CONTRACT_PATH.write_bytes(render(contract))
        STATUS_PATH.write_bytes(render(status))
        for validator in POST_WRITE_VALIDATORS:
            completed = subprocess.run(["python", str(validator)], cwd=ROOT, check=False)
            require(completed.returncode == 0,
                    f"reconciled incident authority failed validation: {validator.name}")
    except BaseException:
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)
        raise


def normalize_contract(contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("schemaVersion") == "memory-os-incident-control-exercise.v1",
            "incident control contract schema drift")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "incident control readiness missing")
    for field in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "exactSourcePassResultCommitted",
    ):
        readiness[field] = True
    for field in (
        "humanTabletopCompleted", "pagingAndAcknowledgementExercised",
        "externalContactTreeExercised", "productionRecoveryDrillCompleted",
        "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"incident authority cannot auto-heal unproven readiness.{field}")
    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list), "incident control evidenceRefs must be a list")
    for ref in EVIDENCE_REFS:
        require((ROOT / ref).is_file(), f"incident control evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
    contract["evidenceRefs"] = unique(refs)
    return contract


def normalize_status(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO",
            "incident authority requires productionDecision NO_GO")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-002"), None)
    require(isinstance(gate, dict), "OPS-P0-002 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-002 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-002 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-002 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-002 evidenceRefs must be a list")

    for item in EXISTING:
        if item not in existing:
            existing.append(item)
    missing[:] = [item for item in missing
                  if not (isinstance(item, str) and
                          "completed tabletop evidence" in item.lower() and
                          "human-led" not in item.lower())]
    if HUMAN_GAP not in missing:
        missing.append(HUMAN_GAP)
    for ref in EVIDENCE_REFS:
        if ref not in refs:
            refs.append(ref)

    gate["existingEvidence"] = unique(existing)
    gate["missingEvidence"] = unique(missing)
    gate["evidenceRefs"] = unique(refs)
    lowered = [str(item).lower() for item in gate["missingEvidence"]]
    for label, terms in {
        "paging": ("paging", "acknowledgement"),
        "external contact": ("external", "contact"),
        "human tabletop": ("human-led", "tabletop"),
        "production recovery": ("production", "recovery", "drill"),
        "independent review": ("independent", "review"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required incident gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL",
            "automated control exercise changed OPS-P0-002 readiness")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    validate_current_authority()
    current_contract = load(CONTRACT_PATH)
    validate_result(load(RESULT_PATH), current_contract)
    current_status = load(STATUS_PATH)
    candidate_contract = normalize_contract(copy.deepcopy(current_contract))
    candidate_status = normalize_status(copy.deepcopy(current_status))
    candidate_status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()

    compare_status_current = copy.deepcopy(current_status)
    compare_status_candidate = copy.deepcopy(candidate_status)
    compare_status_current.pop("asOf", None)
    compare_status_candidate.pop("asOf", None)
    changed = (current_contract != candidate_contract or
               compare_status_current != compare_status_candidate)

    if args.check:
        require(not changed, "incident control authority is not normalized")
        print("Memory OS incident control authority normalization check PASS")
        return 0
    if not changed:
        print("Memory OS incident control authority already normalized")
        return 0

    commit_validated_pair(candidate_contract, candidate_status)
    print("Normalized incident control contract and OPS-P0-002 authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"INCIDENT CONTROL AUTHORITY NORMALIZATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)