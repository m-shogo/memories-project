#!/usr/bin/env python3
"""Reject unsafe incident authority normalization and prove atomic rollback safety."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-incident-control-authority.py"
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
UNPROVEN_READINESS = (
    "humanTabletopCompleted",
    "pagingAndAcknowledgementExercised",
    "externalContactTreeExercised",
    "productionRecoveryDrillCompleted",
    "independentReviewCompleted",
    "productionReady",
)


def load_module():
    spec = importlib.util.spec_from_file_location("incident_control_authority_reconciler", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load incident control authority reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_runtime_authority_rejected(reconciler, field: str, substitute) -> None:
    original = getattr(reconciler, field)
    try:
        setattr(reconciler, field, substitute)
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            return
        raise RuntimeError(f"reconciler accepted {field} authority substitution")
    finally:
        setattr(reconciler, field, original)


def verify_runtime_authority_identity(reconciler, original_contract: bytes, original_result: bytes, original_status: bytes) -> None:
    reconciler.enforce_runtime_authorities()
    substitutions = (
        ("CONTRACT_PATH", ROOT / "README.md"),
        ("RESULT_PATH", ROOT / "README.md"),
        ("STATUS_PATH", CONTRACT_PATH),
        ("VALIDATOR_PATH", ROOT / "scripts/validate-memory-os-operability.py"),
        ("INCIDENT_RESPONSE_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-tabletop.py"),
        ("TABLETOP_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("WORKFLOW_PATH", ROOT / ".github/workflows/incident-control-exercise.yml"),
    )
    for field, substitute in substitutions:
        expect_runtime_authority_rejected(reconciler, field, substitute)

    original_chain = reconciler.POST_WRITE_VALIDATORS
    try:
        reconciler.POST_WRITE_VALIDATORS = (reconciler.VALIDATOR_PATH,)
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted validator-chain authority substitution")
    finally:
        reconciler.POST_WRITE_VALIDATORS = original_chain

    original_subprocess_run = reconciler.subprocess.run
    try:
        reconciler.subprocess.run = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted subprocess transport substitution")
    finally:
        reconciler.subprocess.run = original_subprocess_run

    original_replace = reconciler.os.replace
    try:
        reconciler.os.replace = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted atomic replacement transport substitution")
    finally:
        reconciler.os.replace = original_replace

    original_atomic_writer = reconciler.atomic_write_bytes
    try:
        reconciler.atomic_write_bytes = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError("reconciler accepted atomic writer substitution")
    finally:
        reconciler.atomic_write_bytes = original_atomic_writer

    reconciler.enforce_runtime_authorities()
    if CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("authority substitution mutated incident control contract")
    if RESULT_PATH.read_bytes() != original_result:
        raise RuntimeError("authority substitution mutated incident control result")
    if STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("authority substitution mutated production operability status")


def verify_atomic_replace_failure(reconciler, original_contract: bytes) -> None:
    original_mode = stat.S_IMODE(CONTRACT_PATH.stat().st_mode)
    before_temps = set(CONTRACT_PATH.parent.glob(f".{CONTRACT_PATH.name}.*.tmp"))
    original_replace = reconciler.os.replace

    def fail_replace(*_args, **_kwargs):
        raise OSError("synthetic incident atomic replacement failure")

    try:
        reconciler.os.replace = fail_replace
        try:
            reconciler.CANONICAL_ATOMIC_WRITE_BYTES(CONTRACT_PATH, original_contract + b" ")
        except OSError:
            pass
        else:
            raise RuntimeError("atomic writer accepted synthetic replacement failure")
    finally:
        reconciler.os.replace = original_replace

    if CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("atomic replacement failure mutated incident control contract")
    if stat.S_IMODE(CONTRACT_PATH.stat().st_mode) != original_mode:
        raise RuntimeError("atomic replacement failure changed incident control contract mode")
    after_temps = set(CONTRACT_PATH.parent.glob(f".{CONTRACT_PATH.name}.*.tmp"))
    if after_temps != before_temps:
        raise RuntimeError("atomic replacement failure left temporary incident authority residue")


def expect_result_rejected(reconciler, result, contract, label: str) -> None:
    try:
        reconciler.validate_result(result, contract)
    except reconciler.ReconcileFailure:
        return
    raise RuntimeError(f"reconciler accepted malformed incident result: {label}")


def main() -> int:
    reconciler = load_module()
    original_contract_bytes = CONTRACT_PATH.read_bytes()
    original_result_bytes = RESULT_PATH.read_bytes()
    original_status_bytes = STATUS_PATH.read_bytes()
    original_contract_mode = stat.S_IMODE(CONTRACT_PATH.stat().st_mode)
    original_status_mode = stat.S_IMODE(STATUS_PATH.stat().st_mode)
    contract = json.loads(original_contract_bytes.decode("utf-8"))
    status = json.loads(original_status_bytes.decode("utf-8"))
    result = json.loads(original_result_bytes.decode("utf-8"))

    verify_runtime_authority_identity(
        reconciler,
        original_contract_bytes,
        original_result_bytes,
        original_status_bytes,
    )
    verify_atomic_replace_failure(reconciler, original_contract_bytes)

    for field in UNPROVEN_READINESS:
        candidate = copy.deepcopy(contract)
        candidate["readiness"][field] = True
        try:
            reconciler.normalize_contract(candidate)
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"reconciler auto-healed unproven readiness: {field}")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["decisions"]["promotionDecision"] = "ALLOW"
    expect_result_rejected(reconciler, malformed, contract, "promotion decision bypass")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["decisions"]["stopConditions"] = []
    expect_result_rejected(reconciler, malformed, contract, "stop-condition removal")

    malformed = copy.deepcopy(result)
    malformed["exercise"]["scenarios"][0]["controls"][0]["outputSha256"] = "0" * 63
    expect_result_rejected(reconciler, malformed, contract, "invalid validator output digest")

    malformed = copy.deepcopy(result)
    malformed["environment"]["syntheticScenariosOnly"] = False
    expect_result_rejected(reconciler, malformed, contract, "synthetic scenario boundary")

    rollback_contract = copy.deepcopy(contract)
    rollback_contract["readiness"]["productionReady"] = True
    try:
        reconciler.commit_validated_pair(rollback_contract, copy.deepcopy(status))
    except reconciler.ReconcileFailure:
        pass
    else:
        raise RuntimeError("reconciler accepted invalid post-write incident authority")

    if CONTRACT_PATH.read_bytes() != original_contract_bytes:
        raise RuntimeError("negative validation mutated incident control contract")
    if RESULT_PATH.read_bytes() != original_result_bytes:
        raise RuntimeError("negative validation mutated incident control result")
    if STATUS_PATH.read_bytes() != original_status_bytes:
        raise RuntimeError("negative validation mutated production operability status")
    if stat.S_IMODE(CONTRACT_PATH.stat().st_mode) != original_contract_mode:
        raise RuntimeError("incident contract mode changed across rollback")
    if stat.S_IMODE(STATUS_PATH.stat().st_mode) != original_status_mode:
        raise RuntimeError("production status mode changed across rollback")
    if list(CONTRACT_PATH.parent.glob(f".{CONTRACT_PATH.name}.*.tmp")):
        raise RuntimeError("incident contract temporary residue remains")
    if list(STATUS_PATH.parent.glob(f".{STATUS_PATH.name}.*.tmp")):
        raise RuntimeError("production status temporary residue remains")

    print("PASS: incident authority reconcile rejects data/executable authority substitution")
    print("PASS: incident authority reconcile rejects validator-chain and execution-transport substitution")
    print("PASS: incident authority atomic replacement failure preserves bytes, mode and temp cleanliness")
    print("PASS: incident authority rejects unsafe input and atomically rolls back post-write validation failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
