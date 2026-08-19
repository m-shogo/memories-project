#!/usr/bin/env python3
"""Reject corrupted generation/load authority before host-failure admission."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CONTRACT = ROOT / "contracts/operations/deletion-worker-host-failure-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-host-failure.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-worker-host-failure.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(value: dict[str, Any]) -> None:
    REGISTRY.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rejected(label: str, mutate: Callable[[dict[str, Any]], None], baseline: dict[str, Any], baseline_bytes: bytes) -> None:
    candidate = copy.deepcopy(baseline)
    mutate(candidate)
    write(candidate)
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode != 0, f"{label}: corrupt generation authority was accepted")
    REGISTRY.write_bytes(baseline_bytes)
    require(REGISTRY.read_bytes() == baseline_bytes, f"{label}: canonical generation registry was not restored")


def generation_progression_preserves_no_go() -> None:
    validator = load_module(VALIDATOR, "memory_os_host_failure_validator_progression_negative")
    reconciler = load_module(RECONCILER, "memory_os_host_failure_reconciler_progression_negative")
    baseline = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(isinstance(baseline, dict), "host-failure contract root must be object")

    stale = copy.deepcopy(baseline)
    try:
        validator.validate_generation_projection(stale, 2)
    except Exception:
        pass
    else:
        raise Fail("registered generation progression accepted stale host-failure projection")

    candidate = copy.deepcopy(baseline)
    stub = SimpleNamespace(
        NO_GENERATION_LIMITATION=validator.NO_GENERATION_LIMITATION,
        canonical_generation_count=lambda: 2,
        validate_generation_projection=validator.validate_generation_projection,
    )
    original_loader = reconciler.load_host_validator
    try:
        reconciler.load_host_validator = lambda: stub
        registered = reconciler.reconcile_generation_projection(candidate)
    finally:
        reconciler.load_host_validator = original_loader

    require(registered == 2, "synthetic registered generation count was not preserved")
    validator.validate_generation_projection(candidate, 2)
    boundary = candidate.get("currentBoundary")
    readiness = candidate.get("readiness")
    limitations = candidate.get("limitations")
    require(isinstance(boundary, dict) and isinstance(readiness, dict) and isinstance(limitations, list), "host-failure projection missing")
    require(boundary.get("environmentGenerationAvailable") is True, "registered generation did not enable availability projection")
    require(readiness.get("environmentGenerationAvailable") is True, "registered generation did not enable readiness availability projection")
    require(validator.NO_GENERATION_LIMITATION not in limitations, "registered generation retained missing-generation limitation")
    for key in (
        "actualPhysicalHostOrVMNodeLossCovered",
        "externalFailureControllerCovered",
        "replacementDifferentNodeCovered",
        "leaseExclusionUntilExpiryCovered",
        "replacementAttempt2Covered",
        "dependencyReconnectCovered",
        "zeroOwnedRowsAfterRecoveryCovered",
        "zeroObjectVersionsAfterRecoveryCovered",
        "independentReviewCompleted",
        "deletionHostFailureRecoveryProven",
        "productionEquivalentEvidence",
        "productionEvidence",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"generation inventory incorrectly promoted host-failure boundary: {key}")
    require(boundary.get("productionDecision") == "NO_GO", "generation inventory changed host-failure production decision")
    for key in (
        "hostFailureDrillExecuted",
        "hostFailureResultCommitted",
        "independentReviewCompleted",
        "deletionHostFailureRecoveryProven",
        "productionEquivalentEvidence",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"generation inventory incorrectly promoted host-failure readiness: {key}")


def load_authority_rejected() -> None:
    load_bytes = LOAD.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    candidate = json.loads(load_bytes.decode("utf-8"))
    require(isinstance(candidate, dict), "load contract root must be object")
    candidate["resultsSchemaVersion"] = "forged-load-results-schema"
    corrupted_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    try:
        LOAD.write_bytes(corrupted_bytes)
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        require(completed.returncode != 0, "corrupt canonical load authority was accepted by host-failure reconciler")
        require(CONTRACT.read_bytes() == contract_bytes, "host-failure contract changed after rejected load authority")
        require(STATUS.read_bytes() == status_bytes, "production status changed after rejected load authority")
        require(LOAD.read_bytes() == corrupted_bytes, "host-failure reconciler mutated corrupt load authority")
    finally:
        LOAD.write_bytes(load_bytes)


def rollback_rejected() -> None:
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    candidate = json.loads(contract_bytes.decode("utf-8"))
    require(isinstance(candidate, dict), "host-failure contract root must be object")
    boundary = candidate.get("currentBoundary")
    require(isinstance(boundary, dict), "host-failure currentBoundary missing")
    boundary["productionReady"] = True
    corrupted_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    try:
        CONTRACT.write_bytes(corrupted_bytes)
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        require(completed.returncode != 0, "post-write host-failure validation failure was accepted")
        require(CONTRACT.read_bytes() == corrupted_bytes, "host-failure contract was partially rewritten after rejected reconcile")
        require(STATUS.read_bytes() == status_bytes, "production status was partially rewritten after rejected host-failure reconcile")
    finally:
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)


def main() -> int:
    baseline_bytes = REGISTRY.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    require(isinstance(baseline, dict), "baseline generation registry root must be object")
    try:
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("registry class drift", lambda value: value.__setitem__("registryClass", "FORGED_GENERATIONS")),
            ("append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
            ("boolean generation count", lambda value: value.__setitem__("registeredGenerationCount", False)),
            ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
            ("empty registry current pointer", lambda value: value.__setitem__("currentGenerationId", "forged-generation")),
        ]
        for label, mutate in cases:
            rejected(label, mutate, baseline, baseline_bytes)
        generation_progression_preserves_no_go()
        load_authority_rejected()
        rollback_rejected()
    finally:
        REGISTRY.write_bytes(baseline_bytes)
    print("PASS: deletion host-failure admission rejects corrupt authority, permits registered generation inventory without promotion, and rolls back post-write failures")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST FAILURE GENERATION NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
