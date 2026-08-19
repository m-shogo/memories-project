#!/usr/bin/env python3
"""Prove incident control exercise reconcile fails closed."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-control-exercise.py"
CONTRACT = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
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


def verify_source_validator_delegation(module, original_contract: bytes, original_status: bytes) -> None:
    class SourceValidationFailure(RuntimeError):
        pass

    class RejectingValidator:
        ValidationFailure = SourceValidationFailure

        @staticmethod
        def validate_contract(_contract):
            return None

        @staticmethod
        def validate_result(_result, _contract, _expected_sha):
            raise SourceValidationFailure("synthetic canonical result rejection")

    original_loader = module.load_exercise_validator
    module.load_exercise_validator = lambda: RejectingValidator
    try:
        rejected = False
        try:
            module.main()
        except module.ReconcileFailure as exc:
            require("source authority rejected" in str(exc),
                    f"unexpected source-validator rejection: {exc}")
            rejected = True
        require(rejected, "canonical result validator rejection was not propagated")
        require(CONTRACT.read_bytes() == original_contract,
                "incident contract changed after source-validator rejection")
        require(STATUS.read_bytes() == original_status,
                "production status changed after source-validator rejection")
    finally:
        module.load_exercise_validator = original_loader


def verify_post_write_rollback(module, original_contract: bytes, original_status: bytes) -> None:
    contract = json.loads(original_contract.decode("utf-8"))
    status = json.loads(original_status.decode("utf-8"))
    contract["rollbackProbe"] = "must-not-persist"
    status["rollbackProbe"] = "must-not-persist"

    with tempfile.TemporaryDirectory(prefix="incident-reconcile-negative-") as tmp:
        tmp_path = Path(tmp)
        pass_validator = tmp_path / "pass.py"
        fail_validator = tmp_path / "fail.py"
        pass_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")

        module.EXERCISE_VALIDATOR = pass_validator
        module.INCIDENT_RESPONSE_VALIDATOR = pass_validator
        module.TABLETOP_VALIDATOR = pass_validator
        module.OPERABILITY_VALIDATOR = fail_validator

        rejected = False
        try:
            module.commit_validated_pair(contract, status)
        except module.ReconcileFailure as exc:
            require("failed validation" in str(exc), f"unexpected rejection: {exc}")
            rejected = True

    require(rejected, "post-write validator failure was not rejected")
    require(CONTRACT.read_bytes() == original_contract,
            "incident contract changed after rejected reconcile")
    require(STATUS.read_bytes() == original_status,
            "production status changed after rejected reconcile")


def main() -> int:
    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    module = load_reconciler()

    verify_source_validator_delegation(module, original_contract, original_status)
    verify_post_write_rollback(module, original_contract, original_status)

    print("PASS: incident control exercise source delegation and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
