#!/usr/bin/env python3
"""Reject incident authority normalization that would auto-heal unproven readiness."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-incident-control-authority.py"
CONTRACT_PATH = ROOT / "contracts/operations/incident-control-exercise-contract.v1.json"
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


def main() -> int:
    reconciler = load_module()
    original_contract_bytes = CONTRACT_PATH.read_bytes()
    original_status_bytes = STATUS_PATH.read_bytes()
    contract = json.loads(original_contract_bytes.decode("utf-8"))

    for field in UNPROVEN_READINESS:
        candidate = copy.deepcopy(contract)
        candidate["readiness"][field] = True
        try:
            reconciler.normalize_contract(candidate)
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"reconciler auto-healed unproven readiness: {field}")

    if CONTRACT_PATH.read_bytes() != original_contract_bytes:
        raise RuntimeError("negative validation mutated incident control contract")
    if STATUS_PATH.read_bytes() != original_status_bytes:
        raise RuntimeError("negative validation mutated production operability status")

    print("PASS: incident authority reconcile rejects unproven readiness without mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
