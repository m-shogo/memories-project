#!/usr/bin/env python3
"""Register a short CI stability sample without claiming sustained-soak proof."""

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
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/short-stability-sample-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json"
CANONICAL_SHORT_VALIDATOR = ROOT / "scripts/validate-memory-os-short-stability-sample.py"
CANONICAL_SOAK_RECONCILER = ROOT / "scripts/reconcile-memory-os-sustained-local-soak-status.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
SHORT_VALIDATOR = CANONICAL_SHORT_VALIDATOR
SOAK_RECONCILER = CANONICAL_SOAK_RECONCILER
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
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "short stability contract"),
        (LOAD_PATH, CANONICAL_LOAD_PATH, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "short stability result"),
        (SHORT_VALIDATOR, CANONICAL_SHORT_VALIDATOR, "short stability validator"),
        (SOAK_RECONCILER, CANONICAL_SOAK_RECONCILER, "sustained soak reconciler"),
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
    contract: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any], expected_sha: str
) -> None:
    enforce_runtime_authorities()
    paths = (CONTRACT_PATH, LOAD_PATH, STATUS_PATH)
    original_bytes = {path: path.read_bytes() for path in paths}
    try:
        atomic_write_json(CONTRACT_PATH, contract)
        atomic_write_json(LOAD_PATH, load_contract)
        atomic_write_json(STATUS_PATH, status)
        run_validator(SOAK_RECONCILER, "sustained local soak authority reconcile")
        run_validator(SHORT_VALIDATOR, "post-write short stability validator", "--require-reconciled")
        run_validator(LOAD_VALIDATOR, "post-write load validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except BaseException:
        rollback_error: BaseException | None = None
        for path in paths:
            try:
                atomic_write_bytes(path, original_bytes[path])
            except BaseException as exc:
                if rollback_error is None:
                    rollback_error = exc
        if rollback_error is not None:
            raise ReconcileFailure(f"short stability authority rollback failed: {rollback_error}") from rollback_error
        raise


def main() -> int:
    enforce_runtime_authorities()
    expected_sha = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(expected_sha, "EXPECTED_COMMIT_SHA is required")
    run_validator(SHORT_VALIDATOR, "short stability result validation", "--expected-commit-sha", expected_sha)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("decision") == "SHORT_SAMPLE_ONLY",
            "short stability decision drift")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and
            assertions.get("sustainedSoakEvidence") is False and
            assertions.get("leakProof") is False and
            assertions.get("capacityBoundaryEstablished") is False and
            assertions.get("operationalThresholdApproved") is False,
            "short stability result overclaims readiness")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "short stability readiness missing")
    for field, value in {
        "exactSourceResultCommitted": True,
        "shortSampleExecuted": True,
        "sustainedSoakExecuted": False,
        "leakProofAvailable": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "independentReviewCompleted": False,
        "productionReady": False,
    }.items():
        readiness[field] = value

    load_contract = load(LOAD_PATH)
    external = load_contract.get("externalExecutedScenarios")
    require(isinstance(external, list), "externalExecutedScenarios missing")
    item = {
        "scenarioId": "authenticated-preview-short-ci-stability-local-postgres",
        "contractRef": "contracts/operations/short-stability-sample-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-short-stability-sample.py",
        "dependencyMode": "LOCAL_POSTGRES",
        "classification": "SHORT_CI_STABILITY_SAMPLE",
        "productionEvidence": False,
        "sustainedSoakEvidence": False,
        "leakProof": False,
    }
    existing_index = next((index for index, current in enumerate(external)
                           if isinstance(current, dict) and
                           current.get("scenarioId") == item["scenarioId"]), None)
    if existing_index is None:
        external.append(item)
    else:
        external[existing_index] = item

    deferred = load_contract.get("deferredScenarios")
    require(isinstance(deferred, list), "deferredScenarios missing")
    short_reason = (
        "a six-window short CI process sample records RSS, heap and goroutine trends, but this short sample alone cannot prove leak freedom, a capacity boundary or production stability"
    )
    for current in deferred:
        if isinstance(current, dict) and current.get("scenarioId") == "soak":
            current["reason"] = short_reason
            current["requiredDependencyMode"] = "LOCAL_POSTGRES_MINIO"
            break
    else:
        deferred.append({
            "scenarioId": "soak",
            "reason": short_reason,
            "requiredDependencyMode": "LOCAL_POSTGRES_MINIO",
        })

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    load_readiness["shortCIStabilitySampleExecuted"] = True
    for field in ("sustainedSoakEvidence", "operationalThresholds", "capacityBoundaryEstablished"):
        require(load_readiness.get(field) is False,
                f"short sample cannot promote load readiness: {field}")
    if load_readiness.get("localSustainedSoakEvidence") is not True:
        load_readiness["note"] = (
            "Mock and local dependency checkpoints are supplemented by bounded ramp and short CI "
            "stability samples. These record local concurrency and process trends but establish neither "
            "a saturation boundary nor sustained-soak/leak proof; OPS-P0-006 remains PARTIAL."
        )

    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    for ref in (
        "services/import-api/internal/httpserver/short_stability_sample_test.go",
        "contracts/operations/short-stability-sample-contract.v1.json",
        "scripts/validate-memory-os-short-stability-sample.py",
        "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
    ):
        require((ROOT / ref).is_file(), f"short stability evidence missing: {ref}")
        append_once(load_refs, ref)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "short stability sample cannot change production decision")
    gate = next((current for current in status.get("areas", [])
                 if isinstance(current, dict) and current.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-006 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list),
            "OPS-P0-006 authority lists missing")

    append_once(
        existing,
        "six-window authenticated Preview short CI stability sample records Linux RSS, Go heap and goroutine observations plus per-window throughput and latency while explicitly refusing sustained-soak, leak-proof or capacity claims",
    )
    if load_readiness.get("localSustainedSoakEvidence") is not True:
        append_once(
            missing,
            "60-minute-or-longer repeated soak over PostgreSQL, object storage, parser, queue, deletion and authentication paths with RSS/heap/goroutine slope review and independently approved leak/stability criteria",
        )
    for ref in (
        "contracts/operations/short-stability-sample-contract.v1.json",
        "services/import-api/internal/httpserver/short_stability_sample_test.go",
        "scripts/validate-memory-os-short-stability-sample.py",
        "scripts/reconcile-memory-os-short-stability-status.py",
        "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
        ".github/workflows/short-stability-sample.yml",
    ):
        require((ROOT / ref).is_file(), f"short stability status evidence missing: {ref}")
        append_once(refs, ref)

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_and_validate_transactionally(contract, load_contract, status, expected_sha)
    print("Registered short CI stability sample; canonical repeated-soak authority preserved")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"SHORT STABILITY STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
