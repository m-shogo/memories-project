#!/usr/bin/env python3
"""Reconcile granular pre-fence and multi-account deletion evidence into canonical load authority."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
PREFENCE_CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-linearization-contract.v1.json"
WORKER_CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
PREFENCE_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-linearization-results.sample.v1.json"
WORKER_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
PREFENCE_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-prefence-linearization.py"
WORKER_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-saturation.py"
LOAD_INDEX_VALIDATOR = ROOT / "scripts/validate-memory-os-load-evidence-index.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

PREFENCE_SCENARIO_ID = "account-deletion-prefence-inflight-linearization-local-dependencies"
WORKER_SCENARIO_ID = "multi-account-deletion-worker-saturation-local-dependencies"

PREFENCE_REFS = (
    "contracts/operations/deletion-prefence-linearization-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_prefence_linearization_test.go",
    "scripts/validate-memory-os-deletion-prefence-linearization.py",
    "scripts/reconcile-memory-os-deletion-prefence-linearization.py",
    ".github/workflows/deletion-prefence-linearization.yml",
    "docs/fixtures/memory-os-operability/deletion-prefence-linearization-results.sample.v1.json",
)
WORKER_REFS = (
    "contracts/operations/deletion-worker-saturation-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_worker_saturation_test.go",
    "scripts/validate-memory-os-deletion-worker-saturation.py",
    "scripts/reconcile-memory-os-deletion-worker-saturation.py",
    ".github/workflows/deletion-worker-saturation.yml",
    "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = (path.stat().st_mode & 0o777) if path.exists() else None
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


def run_validator(path: Path, *args: str) -> None:
    subprocess.run(["python", str(path), *args], cwd=ROOT, check=True)


def append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def scenario_map(values: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        if isinstance(value, dict) and isinstance(value.get("scenarioId"), str):
            result[value["scenarioId"]] = value
    return result


def proof_ready(contract: dict[str, Any], result: dict[str, Any], field: str) -> bool:
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "proof readiness missing")
    ready = readiness.get("exactSourceResultCommitted") is True and readiness.get(field) is True
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "proof result scenario missing")
    return ready and scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS"


def main() -> int:
    run_validator(PREFENCE_VALIDATOR, "--require-result")
    run_validator(WORKER_VALIDATOR, "--require-result")

    prefence_contract = load(PREFENCE_CONTRACT_PATH)
    prefence_result = load(PREFENCE_RESULT_PATH)
    worker_contract = load(WORKER_CONTRACT_PATH)
    worker_result = load(WORKER_RESULT_PATH)
    require(
        proof_ready(prefence_contract, prefence_result, "preFenceInFlightLinearizationProven"),
        "pre-fence Preview proof is not reconciled PASS evidence",
    )
    require(
        proof_ready(worker_contract, worker_result, "multiAccountWorkerSaturationProven"),
        "multi-account worker saturation proof is not reconciled PASS evidence",
    )

    prefence_scenario = prefence_result["scenario"]
    require(prefence_scenario.get("authenticatedBeforeFence") == 32, "pre-fence authentication count drift")
    require(prefence_scenario.get("unauthorizedAfterFence") == 32, "pre-fence rejection count drift")
    require(prefence_scenario.get("unexpectedStatusCount") == 0, "pre-fence unexpected statuses present")
    require(prefence_scenario.get("transportErrors") == 0, "pre-fence transport errors present")

    worker_scenario = worker_result["scenario"]
    require(worker_scenario.get("workerReceiptCount") == 24, "worker receipt count drift")
    require(worker_scenario.get("uniqueWorkerReceiptCount") == 24, "worker unique receipt count drift")
    require(worker_scenario.get("duplicateWorkerReceiptCount") == 0, "duplicate worker receipt detected")
    require(worker_scenario.get("controlPreview2xx") == 400, "control Preview success count drift")
    require(worker_scenario.get("finalDeletionPending") == 0, "deletion backlog pending after saturation")
    require(worker_scenario.get("finalDeletionStuck") == 0, "deletion backlog stuck after saturation")
    require(worker_scenario.get("finalOwnedRowCount") == 0, "owned rows survived worker saturation")

    load_contract = load(LOAD_PATH)
    external = load_contract.get("externalExecutedScenarios")
    deferred = load_contract.get("deferredScenarios")
    readiness = load_contract.get("readiness")
    refs = load_contract.get("evidenceRefs")
    require(isinstance(external, list), "load externalExecutedScenarios missing")
    require(isinstance(deferred, list), "load deferredScenarios missing")
    require(isinstance(readiness, dict), "load readiness missing")
    require(isinstance(refs, list), "load evidenceRefs missing")
    require(readiness.get("productionEquivalentDependencies") is False, "local proof cannot reconcile over production equivalence")
    require(readiness.get("capacityBoundaryEstablished") is False, "local proof cannot reconcile over capacity boundary")

    external_by_id = scenario_map(external)
    prefence_entry = {
        "scenarioId": PREFENCE_SCENARIO_ID,
        "contractRef": "contracts/operations/deletion-prefence-linearization-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-deletion-prefence-linearization.py",
        "dependencyMode": "LOCAL_POSTGRES_MINIO",
        "classification": "LOCAL_PREFENCE_LINEARIZATION",
        "surfaceCoverage": "PREVIEW_READ_ONLY",
        "productionEvidence": False,
        "productionEquivalentDependencies": False,
        "requestsStartedBeforeFenceCovered": True,
        "preFenceInFlightLinearizationProven": True,
    }
    worker_entry = {
        "scenarioId": WORKER_SCENARIO_ID,
        "contractRef": "contracts/operations/deletion-worker-saturation-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-deletion-worker-saturation.py",
        "dependencyMode": "LOCAL_POSTGRES_MINIO",
        "classification": "BOUNDED_LOCAL_WORKER_SATURATION",
        "productionEvidence": False,
        "productionEquivalentDependencies": False,
        "multiAccountWorkerSaturationProven": True,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
    }
    if PREFENCE_SCENARIO_ID in external_by_id:
        external[external.index(external_by_id[PREFENCE_SCENARIO_ID])] = prefence_entry
    else:
        external.append(prefence_entry)
    external_by_id = scenario_map(external)
    if WORKER_SCENARIO_ID in external_by_id:
        external[external.index(external_by_id[WORKER_SCENARIO_ID])] = worker_entry
    else:
        external.append(worker_entry)

    deferred[:] = [
        item
        for item in deferred
        if not (isinstance(item, dict) and item.get("scenarioId") == "deletion-worker-under-api-load")
    ]
    deferred_by_id = scenario_map(deferred)
    deletion_deferred = deferred_by_id.get("deletion-under-load")
    require(isinstance(deletion_deferred, dict), "deletion-under-load deferred record missing")
    deletion_deferred["reason"] = (
        "post-fence former-session load, Preview requests authenticated before the fence, and bounded 24-account/four-worker deletion saturation now pass against local PostgreSQL and MinIO; "
        "Apply and Upload authorization requests already in flight before the fence, host/process failure behavior, production dependency behavior and independently reviewed deletion-load thresholds remain deferred"
    )
    deletion_deferred["requiredDependencyMode"] = "PRODUCTION_EQUIVALENT"

    readiness["previewPreFenceInFlightLinearizationProven"] = True
    readiness["multiAccountDeletionWorkerSaturationProven"] = True
    readiness["productionEquivalentDependencies"] = False
    readiness["capacityBoundaryEstablished"] = False
    readiness["operationalThresholds"] = False
    readiness["note"] = (
        "Mock and local dependency checkpoints now include bounded ramp, short CI stability, post-fence deletion load, Preview-only pre-fence in-flight linearization and bounded multi-account deletion-worker saturation. "
        "Apply/Upload pre-fence linearization, sustained-soak/leak proof, production capacity and production-equivalent behavior remain unproven; OPS-P0-006 remains PARTIAL."
    )
    for ref in PREFENCE_REFS + WORKER_REFS:
        append_unique(refs, ref)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "advanced local deletion evidence cannot reconcile into Production GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    load_area = next((area for area in areas if isinstance(area, dict) and area.get("id") == "OPS-P0-006"), None)
    require(isinstance(load_area, dict), "OPS-P0-006 missing")
    require(load_area.get("status") == "PARTIAL", "advanced local deletion evidence cannot promote OPS-P0-006")
    existing = load_area.get("existingEvidence")
    missing = load_area.get("missingEvidence")
    status_refs = load_area.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(status_refs, list), "OPS-P0-006 evidence structure invalid")

    append_unique(
        existing,
        "exact-source local PostgreSQL plus MinIO pre-fence linearization proof pauses 32 Preview requests after successful epoch-1 session resolution, durably advances deletion to epoch 2, then proves all 32 resumed requests return 401 with zero transport errors before worker erasure converges to zero owned rows",
    )
    append_unique(
        existing,
        "bounded local multi-account deletion saturation fences 24 accounts, drains them with four concurrent leased workers into 24 unique receipts with zero duplicates/errors, keeps an unrelated authenticated Preview workload at 400/400 2xx, and converges deletion pending/stuck and owned-row counts to zero",
    )

    old_gap_prefix = "request-linearization proof for operations already in flight before the deletion fence plus multi-account worker saturation"
    new_missing: list[Any] = []
    replaced = False
    for item in missing:
        if isinstance(item, str) and item.startswith(old_gap_prefix):
            new_missing.append(
                "pre-fence in-flight linearization for Apply and Upload authorization surfaces, host/process failure behavior, production topology and independently reviewed deletion-load thresholds"
            )
            replaced = True
        else:
            new_missing.append(item)
    if not replaced:
        append_unique(
            new_missing,
            "pre-fence in-flight linearization for Apply and Upload authorization surfaces, host/process failure behavior, production topology and independently reviewed deletion-load thresholds",
        )
    load_area["missingEvidence"] = new_missing
    for ref in PREFENCE_REFS + WORKER_REFS:
        append_unique(status_refs, ref)

    require(status.get("productionDecision") == "NO_GO", "production decision drift")
    require(load_area.get("status") == "PARTIAL", "OPS-P0-006 status drift")
    require(readiness.get("productionEquivalentDependencies") is False, "production equivalence drift")
    require(readiness.get("capacityBoundaryEstablished") is False, "capacity boundary drift")

    original_load = LOAD_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        write(LOAD_PATH, load_contract)
        write(STATUS_PATH, status)
        run_validator(LOAD_INDEX_VALIDATOR)
        run_validator(LOAD_VALIDATOR)
        run_validator(OPERABILITY_VALIDATOR)
    except BaseException:
        atomic_write_bytes(LOAD_PATH, original_load)
        atomic_write_bytes(STATUS_PATH, original_status)
        raise

    print("Memory OS advanced deletion evidence reconciled")
    print("Preview pre-fence in-flight linearization: true")
    print("multi-account deletion-worker saturation: true")
    print("Apply/Upload pre-fence coverage: false")
    print("capacity boundary: false")
    print("production-equivalent dependencies: false")
    print("OPS-P0-006: PARTIAL")
    print("Production: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADVANCED DELETION EVIDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
