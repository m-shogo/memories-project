#!/usr/bin/env python3
"""Fail-closed validation for rollback rehearsal admission authority."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    require((ROOT / path).is_file(), f"{field} path missing: {value}")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-rollback-rehearsal-gate-contract.v1",
            "rollback rehearsal gate contract schema drift")
    require(contract.get("appendOnly") is True,
            "rollback rehearsal authority must be append-only")
    for field, expected in {
        "approvedReleaseRegistry": str(RELEASE_REGISTRY_PATH.relative_to(ROOT)),
        "rehearsalRegistry": str(REHEARSAL_REGISTRY_PATH.relative_to(ROOT)),
        "writer": str(WRITER_PATH.relative_to(ROOT)),
        "validator": "scripts/validate-memory-os-rollback-rehearsal-gate.py",
        "reconcile": "scripts/reconcile-memory-os-rollback-rehearsal-gate.py",
        "runbook": "docs/runbooks/memory-os-rollback-rehearsal.md",
        "workflow": ".github/workflows/rollback-rehearsal-gate.yml",
    }.items():
        require(contract.get(field) == expected, f"contract path drift: {field}")
        safe_ref(expected, field)
    strings(contract.get("requiredRequestFields"), "requiredRequestFields", 17)
    strings(contract.get("admissionGuards"), "admissionGuards", 12)
    strings(contract.get("forbiddenAdmissionSources"), "forbiddenAdmissionSources", 8)

    environment = contract.get("environmentPolicy")
    require(isinstance(environment, dict) and
            environment.get("allowedEnvironmentClass") ==
            "ISOLATED_NON_PRODUCTION_REHEARSAL" and
            environment.get("productionTrafficAllowed") is False and
            environment.get("productionCredentialsAllowed") is False and
            environment.get("automaticTrafficPromotionAllowed") is False and
            environment.get("destructiveDownMigrationAllowed") is False and
            environment.get("syntheticOrApprovedSanitizedDataOnly") is True,
            "contract environment policy drift")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict) and
            boundary.get("planningAuthorityOnly") is True and
            all(boundary.get(field) is False for field in (
                "rehearsalExecuted", "rollbackExecuted", "productionEvidence",
                "releaseCompatibilityEvidence", "productionReady",
            )), "rollback rehearsal evidence boundary drift")

    release_registry = load(RELEASE_REGISTRY_PATH)
    rehearsal_registry = load(REHEARSAL_REGISTRY_PATH)
    try:
        writer = load_module(WRITER_PATH, "rollback_rehearsal_writer_validator")
        writer.validate_registry_for_append(rehearsal_registry, contract, release_registry)
    except Exception as exc:
        raise ValidationFailure(f"rollback rehearsal append authority invalid: {exc}") from exc

    releases = release_registry["releases"]
    requests = rehearsal_registry["requests"]
    eligible = [
        item for item in releases
        if isinstance(item, dict) and
        isinstance(item.get("rollbackEligibility"), dict) and
        item["rollbackEligibility"].get("status") in
        {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
        item["rollbackEligibility"].get("verified") is True
    ]
    admissible_pairs = max(0, len(releases) - 1) * len(eligible)

    state = contract.get("currentAdmissionState")
    require(isinstance(state, dict), "currentAdmissionState missing")
    require(state.get("approvedReleaseCount") == len(releases) and
            state.get("rollbackEligibleReleaseCount") == len(eligible) and
            state.get("admissibleReleasePairCount") == admissible_pairs and
            state.get("rehearsalRequestCount") == len(requests),
            "current admission state count drift")
    expected_decision = (
        "ADMISSION_AVAILABLE" if admissible_pairs > 0
        else "BLOCKED_NO_APPROVED_ROLLBACK_PAIR"
    )
    require(state.get("admissionDecision") == expected_decision,
            "rollback rehearsal admission decision drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "rollback rehearsal readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"gate implementation missing: {field}")
    require(readiness.get("approvedReleasePairAvailable") is (admissible_pairs > 0) and
            readiness.get("rollbackTargetAvailable") is (len(eligible) > 0) and
            readiness.get("rehearsalRequested") is (len(requests) > 0),
            "rollback rehearsal readiness count drift")
    require(readiness.get("rehearsalExecuted") is False and
            readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "admission gate cannot claim execution or production readiness")

    if not releases:
        require(not requests and admissible_pairs == 0 and
                expected_decision == "BLOCKED_NO_APPROVED_ROLLBACK_PAIR",
                "empty approved release registry must block all rehearsal admission")

    runbook = (ROOT / contract["runbook"]).read_text(encoding="utf-8")
    for phrase in (
        "Candidate is not a release", "Required release pair",
        "Required environment boundary", "Stop conditions",
        "Production remains **NO_GO**",
    ):
        require(phrase in runbook, f"rollback runbook missing phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "rollback rehearsal gate cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "rollback admission authority cannot make OPS-P0-008 ready")

    print("Memory OS rollback rehearsal admission validation PASS")
    print(f"approved releases: {len(releases)}")
    print(f"rollback eligible releases: {len(eligible)}")
    print(f"admissible pairs: {admissible_pairs}")
    print(f"rehearsal requests: {len(requests)}")
    print(f"admission decision: {expected_decision}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"ROLLBACK REHEARSAL GATE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
