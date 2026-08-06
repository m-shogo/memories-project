#!/usr/bin/env python3
"""Register a short CI stability sample without claiming sustained-soak proof."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/short-stability-sample-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json"


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
        [sys.executable, str(ROOT / "scripts/validate-memory-os-short-stability-sample.py"),
         "--expected-commit-sha", expected_sha],
        cwd=ROOT,
        check=False,
    )
    require(validation.returncode == 0, "short stability result validation failed")

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

    changed_contract = False
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
        if readiness.get(field) != value:
            readiness[field] = value
            changed_contract = True

    load_contract = load(LOAD_PATH)
    changed_load = False
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
        changed_load = True
    elif external[existing_index] != item:
        external[existing_index] = item
        changed_load = True

    deferred = load_contract.get("deferredScenarios")
    require(isinstance(deferred, list), "deferredScenarios missing")
    sustained_reason = (
        "a six-window short CI process sample now records RSS, heap and goroutine trends, "
        "but it is not a 60-minute repeated soak, does not cover MinIO/parser/queue/deletion/Apple "
        "dependencies and cannot prove leak freedom or production stability"
    )
    for current in deferred:
        if isinstance(current, dict) and current.get("scenarioId") == "soak":
            if current.get("reason") != sustained_reason:
                current["reason"] = sustained_reason
                changed_load = True
            break
    else:
        deferred.append({
            "scenarioId": "soak",
            "reason": sustained_reason,
            "requiredDependencyMode": "PRODUCTION_EQUIVALENT",
        })
        changed_load = True

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    if load_readiness.get("shortCIStabilitySampleExecuted") is not True:
        load_readiness["shortCIStabilitySampleExecuted"] = True
        changed_load = True
    for field in ("sustainedSoak", "operationalThresholds", "capacityBoundaryEstablished"):
        require(load_readiness.get(field) is False,
                f"short sample cannot promote load readiness: {field}")
    note = (
        "Mock and local dependency checkpoints are supplemented by bounded ramp and short CI "
        "stability samples. These record local concurrency and process trends but establish neither "
        "a saturation boundary nor sustained-soak/leak proof; OPS-P0-006 remains PARTIAL."
    )
    if load_readiness.get("note") != note:
        load_readiness["note"] = note
        changed_load = True

    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    for ref in (
        "services/import-api/internal/httpserver/short_stability_sample_test.go",
        "contracts/operations/short-stability-sample-contract.v1.json",
        "scripts/validate-memory-os-short-stability-sample.py",
        "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
    ):
        require((ROOT / ref).is_file(), f"short stability evidence missing: {ref}")
        changed_load = append_once(load_refs, ref) or changed_load

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

    changed_status = append_once(
        existing,
        "six-window authenticated Preview short CI stability sample records Linux RSS, Go heap and goroutine observations plus per-window throughput and latency while explicitly refusing sustained-soak, leak-proof or capacity claims",
    )
    changed_status = append_once(
        missing,
        "60-minute-or-longer repeated soak over PostgreSQL, object storage, parser, queue, deletion and authentication paths with RSS/heap/goroutine slope review and independently approved leak/stability criteria",
    ) or changed_status
    for ref in (
        "contracts/operations/short-stability-sample-contract.v1.json",
        "services/import-api/internal/httpserver/short_stability_sample_test.go",
        "scripts/validate-memory-os-short-stability-sample.py",
        "scripts/reconcile-memory-os-short-stability-status.py",
        "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json",
        ".github/workflows/short-stability-sample.yml",
    ):
        require((ROOT / ref).is_file(), f"short stability status evidence missing: {ref}")
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
    print("Registered short CI stability sample; sustained soak and leak proof remain false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"SHORT STABILITY STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
