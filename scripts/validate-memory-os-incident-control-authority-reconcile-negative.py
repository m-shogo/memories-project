#!/usr/bin/env python3
"""Reject unsafe incident authority normalization and prove rollback on post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
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
        original = getattr(reconciler, field)
        try:
            setattr(reconciler, field, substitute)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.ReconcileFailure:
                pass
            else:
                raise RuntimeError(f"reconciler accepted {field} authority substitution")
        finally:
            setattr(reconciler, field, original)

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

    reconciler.enforce_runtime_authorities()
    if CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("authority substitution mutated incident control contract")
    if RESULT_PATH.read_bytes() != original_result:
        raise RuntimeError("authority substitution mutated incident control result")
    if STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("authority substitution mutated production operability status")


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
    contract = json.loads(original_contract_bytes.decode("utf-8"))
    status = json.loads(original_status_bytes.decode("utf-8"))
    result = json.loads(original_result_bytes.decode("utf-8"))

    verify_runtime_authority_identity(
        reconciler,
        original_contract_bytes,
        original_result_bytes,
        original_status_bytes,
    )

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

    print("PASS: incident authority reconcile rejects data/executable authority substitution")
    print("PASS: incident authority reconcile rejects validator-chain substitution")
    print("PASS: incident authority reconcile rejects unsafe input and rolls back post-write validation failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())