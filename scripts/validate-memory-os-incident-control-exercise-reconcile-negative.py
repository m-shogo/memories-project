#!/usr/bin/env python3
"""Prove incident control exercise reconcile fails closed and rolls back atomically."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-control-exercise.py"
CONTRACT = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/incident-control-exercise-results.sample.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("incident_control_exercise_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load incident reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_rejected(module, field: str, substitute) -> None:
    original = getattr(module, field)
    try:
        setattr(module, field, substitute)
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        require(rejected, f"incident reconciler accepted {field} authority substitution")
    finally:
        setattr(module, field, original)


def verify_runtime_authority_identity(module) -> None:
    module.enforce_runtime_authorities()
    substitutions = (
        ("CONTRACT_PATH", ROOT / "README.md"),
        ("RESULT_PATH", ROOT / "README.md"),
        ("STATUS_PATH", CONTRACT),
        ("EXERCISE_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py"),
        ("INCIDENT_RESPONSE_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-tabletop.py"),
        ("TABLETOP_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-incident-response.py"),
        ("RUNNER", ROOT / "scripts/reconcile-memory-os-incident-control-exercise.py"),
        ("WORKFLOW", ROOT / ".github/workflows/reconcile-incident-control-authority.yml"),
        ("load_exercise_validator", lambda: None),
        ("run_validator", lambda _path: None),
        ("run_canonical_validators", lambda: None),
        ("commit_validated_pair", lambda _contract, _status: None),
    )
    for field, substitute in substitutions:
        expect_authority_rejected(module, field, substitute)

    original_subprocess_run = module.subprocess.run
    try:
        module.subprocess.run = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        require(rejected, "incident reconciler accepted subprocess transport substitution")
    finally:
        module.subprocess.run = original_subprocess_run

    original_replace = module.os.replace
    try:
        module.os.replace = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        require(rejected, "incident reconciler accepted atomic replacement transport substitution")
    finally:
        module.os.replace = original_replace

    original_atomic_writer = module.atomic_write_bytes
    try:
        module.atomic_write_bytes = lambda *args, **kwargs: None
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            rejected = True
        require(rejected, "incident reconciler accepted atomic writer substitution")
    finally:
        module.atomic_write_bytes = original_atomic_writer

    module.enforce_runtime_authorities()


def verify_source_validator_delegation(module, original_contract: bytes, original_status: bytes) -> None:
    validator = module.CANONICAL_LOAD_EXERCISE_VALIDATOR()
    contract = json.loads(original_contract.decode("utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    malformed = copy.deepcopy(result)
    malformed["environment"]["syntheticScenariosOnly"] = False
    rejected = False
    try:
        validator.validate_contract(contract)
        validator.validate_result(malformed, contract, None)
    except validator.ValidationFailure:
        rejected = True
    require(rejected, "canonical incident source validator accepted malformed result")
    require(CONTRACT.read_bytes() == original_contract,
            "incident contract changed during source-validator delegation probe")
    require(STATUS.read_bytes() == original_status,
            "production status changed during source-validator delegation probe")


def verify_noop_aggregate_validation(module, original_contract: bytes, original_status: bytes) -> None:
    require(module.main() == 0, "already-current incident authority did not reconcile cleanly")
    require(CONTRACT.read_bytes() == original_contract,
            "incident contract changed during no-op aggregate validation")
    require(STATUS.read_bytes() == original_status,
            "production status changed during no-op aggregate validation")


def verify_atomic_replace_failure(module, original_contract: bytes) -> None:
    original_mode = stat.S_IMODE(CONTRACT.stat().st_mode)
    before_temps = set(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    original_replace = module.os.replace

    def fail_replace(*_args, **_kwargs):
        raise OSError("synthetic incident control exercise replacement failure")

    try:
        module.os.replace = fail_replace
        rejected = False
        try:
            module.CANONICAL_ATOMIC_WRITE_BYTES(CONTRACT, original_contract + b" ")
        except OSError:
            rejected = True
        require(rejected, "atomic writer accepted synthetic replacement failure")
    finally:
        module.os.replace = original_replace

    require(CONTRACT.read_bytes() == original_contract,
            "atomic replacement failure mutated incident contract")
    require(stat.S_IMODE(CONTRACT.stat().st_mode) == original_mode,
            "atomic replacement failure changed incident contract mode")
    after_temps = set(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    require(after_temps == before_temps,
            "atomic replacement failure left incident temporary residue")


def verify_post_write_rollback(module, original_contract: bytes, original_status: bytes) -> None:
    contract = json.loads(original_contract.decode("utf-8"))
    status = json.loads(original_status.decode("utf-8"))
    contract["rollbackProbe"] = "must-not-persist"
    status["rollbackProbe"] = "must-not-persist"

    validator_path = module.OPERABILITY_VALIDATOR
    original_validator_bytes = validator_path.read_bytes()
    original_validator_mode = stat.S_IMODE(validator_path.stat().st_mode)
    contract_mode = stat.S_IMODE(CONTRACT.stat().st_mode)
    status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    try:
        validator_path.write_text("raise SystemExit(1)\n", encoding="utf-8")
        os.chmod(validator_path, original_validator_mode)
        rejected = False
        try:
            module.CANONICAL_COMMIT_VALIDATED_PAIR(contract, status)
        except module.ReconcileFailure as exc:
            require("failed validation" in str(exc), f"unexpected rejection: {exc}")
            rejected = True
        require(rejected, "post-write validator failure was not rejected")
    finally:
        validator_path.write_bytes(original_validator_bytes)
        os.chmod(validator_path, original_validator_mode)

    require(CONTRACT.read_bytes() == original_contract,
            "incident contract changed after rejected reconcile")
    require(STATUS.read_bytes() == original_status,
            "production status changed after rejected reconcile")
    require(stat.S_IMODE(CONTRACT.stat().st_mode) == contract_mode,
            "incident contract mode changed after rollback")
    require(stat.S_IMODE(STATUS.stat().st_mode) == status_mode,
            "production status mode changed after rollback")
    require(not list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp")),
            "incident contract temporary residue remains after rollback")
    require(not list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")),
            "production status temporary residue remains after rollback")


def main() -> int:
    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    module = load_reconciler()

    verify_runtime_authority_identity(module)
    verify_source_validator_delegation(module, original_contract, original_status)
    verify_noop_aggregate_validation(module, original_contract, original_status)
    verify_atomic_replace_failure(module, original_contract)
    verify_post_write_rollback(module, original_contract, original_status)

    print("PASS: incident control exercise reconcile data/executable, helper and transport authorities reject substitution")
    print("PASS: incident control exercise no-op path executes canonical aggregate validation")
    print("PASS: incident control exercise atomic replacement failure preserves bytes, mode and temp cleanliness")
    print("PASS: incident control exercise canonical source validation and atomic reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
