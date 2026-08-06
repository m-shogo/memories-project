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
CONTRACT_PATH = ROOT / "contracts/operations/capacity-ramp-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json"


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
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: Any) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def main() -> int:
    expected_sha = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(expected_sha, "EXPECTED_COMMIT_SHA is required")
    validation = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate-memory-os-capacity-ramp.py"),
         "--expected-commit-sha", expected_sha],
        cwd=ROOT,
        check=False,
    )
    require(validation.returncode == 0, "capacity ramp result validation failed")

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("decision") == "BOUNDARY_NOT_ESTABLISHED" and
            scenario.get("firstSaturationSignal") is None,
            "capacity ramp evidence requires reviewed saturation handling")

    changed_contract = False
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
        if readiness.get(field) != value:
            readiness[field] = value
            changed_contract = True

    load_contract = load(LOAD_PATH)
    changed_load = False
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
        changed_load = True
    elif external[existing_index] != capacity_external:
        external[existing_index] = capacity_external
        changed_load = True

    deferred = load_contract.get("deferredScenarios")
    require(isinstance(deferred, list), "deferredScenarios missing")
    for item in deferred:
        if isinstance(item, dict) and item.get("scenarioId") == "capacity-ramp-local-postgres-minio":
            new_reason = (
                "a bounded authenticated Preview ramp now executes against local PostgreSQL, "
                "but it observed no saturation transition and does not exercise MinIO; deliberate "
                "overload, queue/backlog observation and reviewed safe operating thresholds remain deferred"
            )
            if item.get("reason") != new_reason:
                item["reason"] = new_reason
                changed_load = True
            break
    else:
        deferred.append({
            "scenarioId": "capacity-ramp-local-postgres-minio",
            "reason": (
                "a bounded authenticated Preview ramp now executes against local PostgreSQL, "
                "but it observed no saturation transition and does not exercise MinIO; deliberate "
                "overload, queue/backlog observation and reviewed safe operating thresholds remain deferred"
            ),
            "requiredDependencyMode": "LOCAL_POSTGRES_MINIO",
        })
        changed_load = True

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    if load_readiness.get("boundedLocalCapacityRampExecuted") is not True:
        load_readiness["boundedLocalCapacityRampExecuted"] = True
        changed_load = True
    require(load_readiness.get("capacityBoundaryEstablished") is False,
            "bounded ramp cannot establish the capacity boundary")
    require(load_readiness.get("operationalThresholds") is False,
            "bounded ramp cannot approve operational thresholds")
    new_note = (
        "Mock and local dependency checkpoints are supplemented by a bounded authenticated Preview "
        "concurrency ramp. The ramp records a local candidate-safe step but observed no saturation "
        "transition, does not measure MinIO on the ramped path and cannot establish capacity or "
        "operational thresholds. OPS-P0-006 remains PARTIAL."
    )
    if load_readiness.get("note") != new_note:
        load_readiness["note"] = new_note
        changed_load = True

    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    for ref in (
        "services/import-api/internal/httpserver/capacity_ramp_test.go",
        "contracts/operations/capacity-ramp-contract.v1.json",
        "scripts/validate-memory-os-capacity-ramp.py",
        "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
    ):
        require((ROOT / ref).is_file(), f"capacity ramp evidence missing: {ref}")
        changed_load = append_once(load_refs, ref) or changed_load

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

    changed_status = append_once(
        existing,
        "bounded authenticated Preview concurrency ramp over local PostgreSQL records six concurrency steps with all-2xx integrity and a local candidate-safe concurrency while explicitly leaving the saturation boundary and operating threshold unproven",
    )
    changed_status = append_once(
        missing,
        "deliberate local PostgreSQL plus MinIO saturation ramp with queue/backlog signals, first-failure transition, repeatability and independently reviewed safe operating thresholds",
    ) or changed_status
    for ref in (
        "contracts/operations/capacity-ramp-contract.v1.json",
        "services/import-api/internal/httpserver/capacity_ramp_test.go",
        "scripts/validate-memory-os-capacity-ramp.py",
        "scripts/reconcile-memory-os-capacity-ramp-status.py",
        "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
        ".github/workflows/capacity-ramp.yml",
    ):
        require((ROOT / ref).is_file(), f"capacity ramp status evidence missing: {ref}")
        changed_status = append_once(refs, ref) or changed_status
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "capacity ramp overpromoted readiness")

    if changed_contract:
        CONTRACT_PATH.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    if changed_load:
        LOAD_PATH.write_text(json.dumps(load_contract, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    if changed_status:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print("Registered bounded capacity ramp; capacity boundary remains unestablished")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CAPACITY RAMP STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
