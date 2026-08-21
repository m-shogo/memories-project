#!/usr/bin/env python3
"""Register exact-source controlled saturation evidence without promoting production readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTROLLED_CONTRACT = ROOT / "contracts/operations/controlled-saturation-ramp-contract.v1.json"
CANONICAL_LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-ramp-results.sample.v1.json"
CANONICAL_CONTROLLED_VALIDATOR = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_LOAD_INDEX_VALIDATOR = ROOT / "scripts/validate-memory-os-load-evidence-index.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_WORKFLOW = ROOT / ".github/workflows/controlled-saturation-ramp.yml"
CONTROLLED_CONTRACT = CANONICAL_CONTROLLED_CONTRACT
LOAD_CONTRACT = CANONICAL_LOAD_CONTRACT
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
CONTROLLED_VALIDATOR = CANONICAL_CONTROLLED_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
LOAD_INDEX_VALIDATOR = CANONICAL_LOAD_INDEX_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
WORKFLOW = CANONICAL_WORKFLOW
SCENARIO_ID = "signed-upload-controlled-saturation-ramp-local-dependencies"
EVIDENCE_REFS = (
    "contracts/operations/controlled-saturation-ramp-contract.v1.json",
    "services/import-api/internal/httpserver/controlled_saturation_ramp_test.go",
    "scripts/validate-memory-os-controlled-saturation-ramp.py",
    "scripts/reconcile-memory-os-controlled-saturation-ramp-status.py",
    "docs/fixtures/memory-os-operability/controlled-saturation-ramp-results.sample.v1.json",
    ".github/workflows/controlled-saturation-ramp.yml",
)
TRANSACTION_PATHS = (CONTROLLED_CONTRACT, LOAD_CONTRACT, STATUS_PATH)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTROLLED_CONTRACT, CANONICAL_CONTROLLED_CONTRACT, "controlled saturation contract"),
        (LOAD_CONTRACT, CANONICAL_LOAD_CONTRACT, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "controlled saturation result"),
        (CONTROLLED_VALIDATOR, CANONICAL_CONTROLLED_VALIDATOR, "controlled saturation validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (LOAD_INDEX_VALIDATOR, CANONICAL_LOAD_INDEX_VALIDATOR, "load index validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (WORKFLOW, CANONICAL_WORKFLOW, "controlled saturation workflow"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} root must be object")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[Any], item: Any) -> None:
    if item not in values:
        values.append(item)


def find_by_id(values: list[Any], identifier: str) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict) and value.get("id") == identifier:
            return value
    raise SystemExit(f"missing status area {identifier}")


def find_scenario(values: list[Any], scenario_id: str) -> dict[str, Any] | None:
    for value in values:
        if isinstance(value, dict) and value.get("scenarioId") == scenario_id:
            return value
    return None


def validate_source_authority(expected_sha: str) -> None:
    enforce_runtime_authorities()
    env = os.environ.copy()
    env["EXPECTED_COMMIT_SHA"] = expected_sha
    subprocess.run(
        [sys.executable, str(CONTROLLED_VALIDATOR), "--expected-commit-sha", expected_sha],
        cwd=ROOT,
        env=env,
        check=True,
    )


def validate_post_write(expected_sha: str) -> None:
    enforce_runtime_authorities()
    commands = (
        [sys.executable, str(CONTROLLED_VALIDATOR), "--expected-commit-sha", expected_sha, "--require-reconciled"],
        [sys.executable, str(LOAD_VALIDATOR)],
        [sys.executable, str(LOAD_INDEX_VALIDATOR)],
        [sys.executable, str(OPERABILITY_VALIDATOR)],
    )
    env = os.environ.copy()
    env["EXPECTED_COMMIT_SHA"] = expected_sha
    for command in commands:
        subprocess.run(command, cwd=ROOT, env=env, check=True)


def write_transactionally(
    controlled: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any], expected_sha: str
) -> None:
    enforce_runtime_authorities()
    originals = {path: path.read_bytes() for path in TRANSACTION_PATHS}
    try:
        write(CONTROLLED_CONTRACT, controlled)
        write(LOAD_CONTRACT, load_contract)
        write(STATUS_PATH, status)
        validate_post_write(expected_sha)
    except BaseException:
        for path, content in originals.items():
            path.write_bytes(content)
        raise


def main() -> int:
    enforce_runtime_authorities()
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    if len(expected_sha) != 40:
        raise SystemExit("EXPECTED_COMMIT_SHA must be a full commit SHA")

    validate_source_authority(expected_sha)
    result = load(RESULT_PATH)
    if result.get("commitSha") != expected_sha:
        raise SystemExit("controlled saturation result is stale for expected source")
    environment = result.get("environment")
    scenario = result.get("scenario")
    if not isinstance(environment, dict) or not isinstance(scenario, dict):
        raise SystemExit("controlled saturation result structure invalid")
    if scenario.get("result") != "PASS" or scenario.get("integrityResult") != "PASS":
        raise SystemExit("controlled saturation result is not PASS")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        if environment.get(key) is not False:
            raise SystemExit(f"controlled saturation result cannot enable {key}")

    first_saturation = scenario.get("firstSaturationSignal") is not None
    first_contention = scenario.get("firstPoolContentionSignal") is not None

    controlled = load(CONTROLLED_CONTRACT)
    readiness = controlled.get("readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("controlled saturation readiness missing")
    readiness.update({
        "contractDefined": True,
        "runnerImplemented": True,
        "validatorImplemented": True,
        "automaticWorkflowImplemented": True,
        "exactSourceResultCommitted": True,
        "localRampExecuted": True,
        "localSaturationSignalObserved": first_saturation,
        "poolContentionSignalObserved": first_contention,
        "repeatabilityEstablished": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "independentReviewCompleted": False,
        "productionReady": False,
    })

    load_contract = load(LOAD_CONTRACT)
    external = load_contract.get("externalExecutedScenarios")
    deferred = load_contract.get("deferredScenarios")
    load_readiness = load_contract.get("readiness")
    evidence_refs = load_contract.get("evidenceRefs")
    if not isinstance(external, list) or not isinstance(deferred, list) or not isinstance(load_readiness, dict) or not isinstance(evidence_refs, list):
        raise SystemExit("load contract structure invalid")
    repeatability_already_established = load_readiness.get("repeatableLocalDegradationSignalObserved") is True

    external_item = find_scenario(external, SCENARIO_ID)
    expected_external = {
        "scenarioId": SCENARIO_ID,
        "contractRef": "contracts/operations/controlled-saturation-ramp-contract.v1.json",
        "validatorRef": "scripts/validate-memory-os-controlled-saturation-ramp.py",
        "dependencyMode": "LOCAL_POSTGRES_MINIO",
        "classification": "BOUNDED_LOCAL_CAPACITY_RAMP",
        "productionEvidence": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
        "repeatabilityEstablished": False,
    }
    if external_item is None:
        external.append(expected_external)
    else:
        external_item.clear()
        external_item.update(expected_external)

    deferred_item = find_scenario(deferred, "capacity-ramp-local-postgres-minio")
    if deferred_item is None:
        raise SystemExit("missing capacity-ramp-local-postgres-minio deferred scenario")
    if not repeatability_already_established:
        if first_saturation:
            deferred_item["reason"] = (
                "a bounded local PostgreSQL plus MinIO lifecycle ramp now observes a first overload signal, "
                "but repeatability, queue/backlog interpretation and independently reviewed safe operating thresholds remain deferred"
            )
        else:
            deferred_item["reason"] = (
                "a bounded local PostgreSQL plus MinIO lifecycle ramp now executes through concurrency 48 with pool telemetry, "
                "but no failure/degradation boundary was established; repeatable overload discovery and independently reviewed safe operating thresholds remain deferred"
            )
    deferred_item["requiredDependencyMode"] = "LOCAL_POSTGRES_MINIO"

    load_readiness["controlledLocalDependencySaturationRampExecuted"] = True
    for key in (
        "productionShapedWorkload",
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
    ):
        if load_readiness.get(key) is not False:
            raise SystemExit(f"local controlled saturation evidence cannot enable load readiness.{key}")
    for ref in EVIDENCE_REFS:
        append_unique(evidence_refs, ref)

    status = load(STATUS_PATH)
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("refusing to reconcile controlled local evidence into a non-NO_GO production decision")
    areas = status.get("areas")
    if not isinstance(areas, list):
        raise SystemExit("production operability areas missing")
    load_status = find_by_id(areas, "OPS-P0-006")
    if load_status.get("status") != "PARTIAL":
        raise SystemExit("controlled local evidence must not change OPS-P0-006 away from PARTIAL")
    existing = load_status.get("existingEvidence")
    missing = load_status.get("missingEvidence")
    refs = load_status.get("evidenceRefs")
    if not isinstance(existing, list) or not isinstance(missing, list) or not isinstance(refs, list):
        raise SystemExit("OPS-P0-006 evidence structure invalid")

    append_unique(
        existing,
        "bounded local PostgreSQL plus MinIO signed-upload lifecycle ramp records throughput, latency and pgx pool contention through concurrency 48, preserves exact object/version accounting and proves post-ramp recovery without treating one run as a capacity boundary",
    )
    missing = [
        item for item in missing
        if not (
            isinstance(item, str)
            and (
                item.startswith("deliberate local PostgreSQL plus MinIO saturation ramp")
                or item.startswith("repeatability of the observed local PostgreSQL plus MinIO saturation signal")
                or item.startswith("repeatable local PostgreSQL plus MinIO saturation runs")
            )
        )
    ]
    if not repeatability_already_established:
        if first_saturation:
            missing.append(
                "repeatability of the observed local PostgreSQL plus MinIO saturation signal, queue/backlog interpretation and independently reviewed safe operating thresholds"
            )
        else:
            missing.append(
                "repeatable local PostgreSQL plus MinIO saturation runs that actually observe a first failure/degradation transition, plus queue/backlog interpretation and independently reviewed safe operating thresholds"
            )
    load_status["missingEvidence"] = missing
    for ref in EVIDENCE_REFS:
        append_unique(refs, ref)

    if status.get("productionDecision") != "NO_GO" or load_status.get("status") != "PARTIAL":
        raise SystemExit("controlled local evidence attempted to promote production authority")

    write_transactionally(controlled, load_contract, status, expected_sha)
    print("Memory OS controlled saturation authority reconciled")
    print(f"source: {expected_sha}")
    print(f"local saturation signal observed: {str(first_saturation).lower()}")
    print(f"pool contention signal observed: {str(first_contention).lower()}")
    print(f"stronger repeatability authority preserved: {str(repeatability_already_established).lower()}")
    print("capacity boundary established: false")
    print("operational threshold approved: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
