#!/usr/bin/env python3
"""Register post-fence deletion load evidence without overclaiming linearization."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-under-load-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json"


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
        [sys.executable, str(ROOT / "scripts/validate-memory-os-deletion-under-load.py"),
         "--expected-commit-sha", expected_sha],
        cwd=ROOT,
        check=False,
    )
    require(validation.returncode == 0,
            "deletion-under-load result validation failed")

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("result") == "PASS" and
            scenario.get("finalOwnedRowCount") == 0,
            "deletion-under-load result is not reconcilable")

    changed_contract = False
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "deletion-under-load readiness missing")
    for field, value in {
        "exactSourceResultCommitted": True,
        "postFenceLoadExecuted": True,
        "preFenceInFlightLinearizationProven": False,
        "productionDependenciesTested": False,
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
    item = {
        "scenarioId": "account-deletion-post-fence-load-local-dependencies",
        "contractRef": "contracts/operations/deletion-under-load-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-deletion-under-load.py",
        "dependencyMode": "LOCAL_POSTGRES_MINIO",
        "productionEvidence": False,
        "requestsStartedBeforeFenceCovered": False,
    }
    existing_index = next((index for index, current in enumerate(external)
                           if isinstance(current, dict) and
                           current.get("scenarioId") == item["scenarioId"]), None)
    if existing_index is None:
        external.append(item)
        changed_load = True
    elif external[existing_index] != item:
        external[existing_index] = item
        changed_load = True

    deferred = load_contract.get("deferredScenarios")
    require(isinstance(deferred, list), "deferredScenarios missing")
    reason = (
        "post-fence former-session load and concurrent worker erasure now pass against local "
        "PostgreSQL and MinIO; request linearization for calls already in flight before the 202 "
        "fence, multiple-account worker saturation and production dependency behavior remain deferred"
    )
    for current in deferred:
        if isinstance(current, dict) and current.get("scenarioId") == "deletion-under-load":
            if current.get("reason") != reason:
                current["reason"] = reason
                changed_load = True
            current["requiredDependencyMode"] = "PRODUCTION_EQUIVALENT"
            break
    else:
        deferred.append({
            "scenarioId": "deletion-under-load",
            "reason": reason,
            "requiredDependencyMode": "PRODUCTION_EQUIVALENT",
        })
        changed_load = True

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    if load_readiness.get("deletionPostFenceLoadExecuted") is not True:
        load_readiness["deletionPostFenceLoadExecuted"] = True
        changed_load = True
    for field in ("operationalThresholds", "capacityBoundaryEstablished", "productionEquivalentDependencies"):
        require(load_readiness.get(field) is False,
                f"deletion load cannot promote load readiness: {field}")
    note = (
        "Mock and local dependency checkpoints now include bounded ramp, short CI stability and "
        "post-fence deletion load. They establish neither production capacity nor pre-fence request "
        "linearization, sustained-soak/leak proof or production-equivalent behavior; OPS-P0-006 remains PARTIAL."
    )
    if load_readiness.get("note") != note:
        load_readiness["note"] = note
        changed_load = True

    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    for ref in (
        "services/import-api/internal/httpserver/deletion_under_load_test.go",
        "contracts/operations/deletion-under-load-contract.v1.json",
        "scripts/validate-memory-os-deletion-under-load.py",
        "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json",
    ):
        require((ROOT / ref).is_file(), f"deletion-under-load evidence missing: {ref}")
        changed_load = append_once(load_refs, ref) or changed_load

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "deletion load cannot change production decision")
    gate = next((current for current in status.get("areas", [])
                 if isinstance(current, dict) and current.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-006 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list),
            "OPS-P0-006 authority lists missing")

    changed_status = append_once(
        existing,
        "local PostgreSQL and MinIO deletion-under-load checkpoint proves that after a durable 202 epoch fence, 400 concurrent requests using the former session all return 401 while the leased deletion worker completes and leaves zero owned rows",
    )
    changed_status = append_once(
        missing,
        "request-linearization proof for operations already in flight before the deletion fence plus multi-account worker saturation, production topology and independently reviewed deletion-load thresholds",
    ) or changed_status
    for ref in (
        "contracts/operations/deletion-under-load-contract.v1.json",
        "services/import-api/internal/httpserver/deletion_under_load_test.go",
        "scripts/validate-memory-os-deletion-under-load.py",
        "scripts/reconcile-memory-os-deletion-under-load-status.py",
        "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json",
        ".github/workflows/deletion-under-load.yml",
    ):
        require((ROOT / ref).is_file(), f"deletion-under-load status evidence missing: {ref}")
        changed_status = append_once(refs, ref) or changed_status

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
    print("Registered post-fence deletion load; pre-fence linearization remains unproven")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"DELETION-UNDER-LOAD STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
