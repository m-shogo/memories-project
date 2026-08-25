#!/usr/bin/env python3
"""Register post-fence deletion load evidence without overclaiming linearization."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/deletion-under-load-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json"
CANONICAL_DELETION_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
DELETION_VALIDATOR = CANONICAL_DELETION_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
LEGACY_DELETION_GAP = (
    "request-linearization proof for operations already in flight before the deletion fence plus "
    "multi-account worker saturation, production topology and independently reviewed deletion-load thresholds"
)
BASE_DELETION_REASON = (
    "post-fence former-session load and concurrent worker erasure now pass against local "
    "PostgreSQL and MinIO; request linearization for calls already in flight before the 202 "
    "fence, multiple-account worker saturation and production dependency behavior remain deferred"
)
BASE_NOTE = (
    "Mock and local dependency checkpoints now include bounded ramp, short CI stability and "
    "post-fence deletion load. They establish neither production capacity nor pre-fence request "
    "linearization, sustained-soak/leak proof or production-equivalent behavior; OPS-P0-006 remains PARTIAL."
)


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
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "deletion-under-load contract"),
        (LOAD_PATH, CANONICAL_LOAD_PATH, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "deletion-under-load result"),
        (DELETION_VALIDATOR, CANONICAL_DELETION_VALIDATOR, "deletion-under-load validator"),
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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"canonical {label} validation failed: {completed.stdout[-2000:]}",
    )


def stronger_deletion_authority_present(load_readiness: dict[str, Any]) -> bool:
    return all(
        load_readiness.get(field) is True
        for field in (
            "primaryAccountBoundPreFenceLinearizationAggregateProven",
            "multiAccountDeletionWorkerSaturationProven",
            "deletionLeaseExpiryRecoverySimulationProven",
            "deletionContainerKillRecoveryProven",
        )
    )


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def write_and_validate_transactionally(
    contract: dict[str, Any],
    load_contract: dict[str, Any],
    status: dict[str, Any],
) -> None:
    enforce_runtime_authorities()
    originals = {
        CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
        LOAD_PATH: LOAD_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        atomic_write_json(CONTRACT_PATH, contract)
        atomic_write_json(LOAD_PATH, load_contract)
        atomic_write_json(STATUS_PATH, status)
        run_validator(DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        run_validator(LOAD_VALIDATOR, "load")
        run_validator(OPERABILITY_VALIDATOR, "operability")
    except BaseException:
        rollback_error: BaseException | None = None
        for path, data in originals.items():
            try:
                atomic_write_bytes(path, data)
            except BaseException as exc:
                if rollback_error is None:
                    rollback_error = exc
        if rollback_error is not None:
            raise ReconcileFailure(f"deletion-under-load authority rollback failed: {rollback_error}") from rollback_error
        raise


def main() -> int:
    enforce_runtime_authorities()
    expected_sha = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(expected_sha, "EXPECTED_COMMIT_SHA is required")
    run_validator(DELETION_VALIDATOR, "deletion-under-load", "--expected-commit-sha", expected_sha)

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
    for current in deferred:
        if isinstance(current, dict) and current.get("scenarioId") == "deletion-under-load":
            if current.get("requiredDependencyMode") != "PRODUCTION_EQUIVALENT":
                current["requiredDependencyMode"] = "PRODUCTION_EQUIVALENT"
                changed_load = True
            break
    else:
        deferred.append({
            "scenarioId": "deletion-under-load",
            "reason": BASE_DELETION_REASON,
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
    current_note = load_readiness.get("note")
    if not isinstance(current_note, str) or not current_note.strip():
        load_readiness["note"] = BASE_NOTE
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
    if not stronger_deletion_authority_present(load_readiness):
        changed_status = append_once(missing, LEGACY_DELETION_GAP) or changed_status
    elif LEGACY_DELETION_GAP in missing:
        missing.remove(LEGACY_DELETION_GAP)
        changed_status = True
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

    if not (changed_contract or changed_load or changed_status):
        run_validator(DELETION_VALIDATOR, "deletion-under-load", "--require-reconciled")
        run_validator(LOAD_VALIDATOR, "load")
        run_validator(OPERABILITY_VALIDATOR, "operability")
        print("Deletion-under-load authority already reconciled without weakening stronger proofs")
        return 0

    if changed_status:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_and_validate_transactionally(contract, load_contract, status)
    print("Registered post-fence deletion load without weakening stronger deletion authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"DELETION-UNDER-LOAD STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
