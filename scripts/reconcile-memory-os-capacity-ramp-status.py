#!/usr/bin/env python3
"""Register a bounded capacity ramp without promoting capacity readiness."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/capacity-ramp-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json"
CANONICAL_CAPACITY_VALIDATOR = ROOT / "scripts/validate-memory-os-capacity-ramp.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
CAPACITY_VALIDATOR = CANONICAL_CAPACITY_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "capacity contract"),
        (LOAD_PATH, CANONICAL_LOAD_PATH, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "capacity result"),
        (CAPACITY_VALIDATOR, CANONICAL_CAPACITY_VALIDATOR, "capacity validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: Any) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path, label: str, *args: str) -> None:
    enforce_runtime_authorities()
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        check=False,
    )
    require(completed.returncode == 0, f"{label} failed")


def write_and_validate_transactionally(
    contract: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any]
) -> None:
    enforce_runtime_authorities()
    paths = (CONTRACT_PATH, LOAD_PATH, STATUS_PATH)
    original_bytes = {path: path.read_bytes() for path in paths}
    try:
        CONTRACT_PATH.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        LOAD_PATH.write_text(
            json.dumps(load_contract, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        run_validator(CAPACITY_VALIDATOR, "post-write capacity ramp validator", "--require-reconciled")
        run_validator(LOAD_VALIDATOR, "post-write load validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except BaseException:
        for path in paths:
            path.write_bytes(original_bytes[path])
        raise


def main() -> int:
    enforce_runtime_authorities()
    expected_sha = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(expected_sha, "EXPECTED_COMMIT_SHA is required")
    run_validator(CAPACITY_VALIDATOR, "capacity ramp result validation", "--expected-commit-sha", expected_sha)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("decision") == "BOUNDARY_NOT_ESTABLISHED" and
            scenario.get("firstSaturationSignal") is None,
            "capacity ramp evidence requires reviewed saturation handling")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "capacity ramp readiness missing")
    for field, value in {
        "exactSourceResultCommitted": True,
        "localRampExecuted": True,
        "localSaturationSignalObserved": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "independentReviewCompleted": False,
        "productionReady": False,
    }.items():
        readiness[field] = value

    load_contract = load(LOAD_PATH)
    external = load_contract.get("externalExecutedScenarios")
    require(isinstance(external, list), "externalExecutedScenarios missing")
    capacity_external = {
        "scenarioId": "authenticated-preview-capacity-ramp-local-postgres",
        "contractRef": "contracts/operations/capacity-ramp-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-capacity-ramp.py",
        "dependencyMode": "LOCAL_POSTGRES",
        "productionEvidence": False,
        "capacityBoundaryEstablished": False,
    }
    existing_index = next((index for index, item in enumerate(external)
                           if isinstance(item, dict) and
                           item.get("scenarioId") == capacity_external["scenarioId"]), None)
    if existing_index is None:
        external.append(capacity_external)
    else:
        external[existing_index] = capacity_external

    deferred = load_contract.get("deferredScenarios")
    require(isinstance(deferred, list), "deferredScenarios missing")
    new_reason = (
        "a bounded authenticated Preview ramp now executes against local PostgreSQL, "
        "but it observed no saturation transition and does not exercise MinIO; deliberate "
        "overload, queue/backlog observation and reviewed safe operating thresholds remain deferred"
    )
    for item in deferred:
        if isinstance(item, dict) and item.get("scenarioId") == "capacity-ramp-local-postgres-minio":
            item["reason"] = new_reason
            break
    else:
        deferred.append({
            "scenarioId": "capacity-ramp-local-postgres-minio",
            "reason": new_reason,
            "requiredDependencyMode": "LOCAL_POSTGRES_MINIO",
        })

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    load_readiness["boundedLocalCapacityRampExecuted"] = True
    require(load_readiness.get("capacityBoundaryEstablished") is False,
            "bounded ramp cannot establish the capacity boundary")
    require(load_readiness.get("operationalThresholds") is False,
            "bounded ramp cannot approve operational thresholds")
    current_note = load_readiness.get("note")
    if not isinstance(current_note, str) or not current_note:
        load_readiness["note"] = (
            "Mock and local dependency checkpoints are supplemented by a bounded authenticated Preview "
            "concurrency ramp. The ramp records a local candidate-safe step but observed no saturation "
            "transition, does not measure MinIO on the ramped path and cannot establish capacity or "
            "operational thresholds. OPS-P0-006 remains PARTIAL."
        )

    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    for ref in (
        "services/import-api/internal/httpserver/capacity_ramp_test.go",
        "contracts/operations/capacity-ramp-contract.v1.json",
        "scripts/validate-memory-os-capacity-ramp.py",
        "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
    ):
        require((ROOT / ref).is_file(), f"capacity ramp evidence missing: {ref}")
        append_once(load_refs, ref)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "capacity ramp cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-006 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list),
            "OPS-P0-006 authority lists missing")

    append_once(
        existing,
        "bounded authenticated Preview concurrency ramp over local PostgreSQL records six concurrency steps with all-2xx integrity and a local candidate-safe concurrency while explicitly leaving the saturation boundary and operating threshold unproven",
    )
    append_once(
        missing,
        "deliberate local PostgreSQL plus MinIO saturation ramp with queue/backlog signals, first-failure transition, repeatability and independently reviewed safe operating thresholds",
    )
    for ref in (
        "contracts/operations/capacity-ramp-contract.v1.json",
        "services/import-api/internal/httpserver/capacity_ramp_test.go",
        "scripts/validate-memory-os-capacity-ramp.py",
        "scripts/reconcile-memory-os-capacity-ramp-status.py",
        "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
        ".github/workflows/capacity-ramp.yml",
    ):
        require((ROOT / ref).is_file(), f"capacity ramp status evidence missing: {ref}")
        append_once(refs, ref)
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "capacity ramp overpromoted readiness")

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_and_validate_transactionally(contract, load_contract, status)
    print("Registered bounded capacity ramp; capacity boundary remains unestablished")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CAPACITY RAMP STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
