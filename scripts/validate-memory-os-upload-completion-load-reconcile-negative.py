#!/usr/bin/env python3
"""Prove upload-completion load reconcile pins authorities and rolls back aggregate rejection."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-upload-completion-load-authority.py"


def load_module():
    spec = importlib.util.spec_from_file_location("upload_completion_load_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load upload-completion load reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def main() -> int:
    module = load_module()

    substitutions = {
        "PROOF_CONTRACT": module.LOAD_CONTRACT,
        "PROOF_RESULT": module.PROOF_CONTRACT,
        "PROOF_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_CONTRACT": module.PROOF_CONTRACT,
        "STATUS": module.LOAD_CONTRACT,
        "LOAD_VALIDATOR": module.PROOF_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()

    with tempfile.TemporaryDirectory(prefix="memory-os-upload-completion-rollback-") as tmp:
        root = Path(tmp)
        proof_contract = root / "proof-contract.json"
        proof_result = root / "proof-result.json"
        load_contract = root / "load-contract.json"
        status = root / "status.json"
        proof_validator = root / "proof-validator.py"
        load_validator = root / "load-validator.py"
        operability_validator = root / "operability-validator.py"

        write_json(
            proof_contract,
            {
                "readiness": {
                    "exactSourceResultCommitted": True,
                    "preFenceUploadCompletionLinearizationProven": True,
                }
            },
        )
        write_json(
            proof_result,
            {
                "environment": {
                    "productionEvidence": False,
                    "productionEquivalentDependencies": False,
                    "containsSecrets": False,
                },
                "scenario": {"result": "PASS", "integrityResult": "PASS"},
            },
        )
        write_json(
            load_contract,
            {
                "readiness": {
                    "previewPreFenceInFlightLinearizationProven": True,
                    "applyPreFenceInFlightLinearizationProven": True,
                    "uploadAuthorizationPreFenceInFlightLinearizationProven": True,
                },
                "deferredScenarios": [{"scenarioId": "deletion-under-load", "reason": "synthetic"}],
                "evidenceRefs": [],
            },
        )
        write_json(
            status,
            {
                "productionDecision": "NO_GO",
                "areas": [
                    {
                        "id": "OPS-P0-006",
                        "status": "PARTIAL",
                        "blocking": True,
                        "existingEvidence": [],
                        "missingEvidence": [],
                        "evidenceRefs": [],
                    }
                ],
            },
        )

        module.ROOT = root
        module.PROOF_CONTRACT = proof_contract
        module.PROOF_RESULT = proof_result
        module.PROOF_VALIDATOR = proof_validator
        module.LOAD_CONTRACT = load_contract
        module.STATUS = status
        module.LOAD_VALIDATOR = load_validator
        module.OPERABILITY_VALIDATOR = operability_validator
        module.enforce_runtime_authorities = lambda: None

        calls: list[str] = []

        def fake_run(command, *, cwd, check):
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            validator = str(command[1])
            calls.append(validator)
            if validator == str(operability_validator):
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = fake_run
        before_load = load_contract.read_bytes()
        before_status = status.read_bytes()

        try:
            module.main()
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("aggregate operability rejection must fail the reconcile")

        if load_contract.read_bytes() != before_load:
            raise AssertionError("load authority changed after rejected transactional reconcile")
        if status.read_bytes() != before_status:
            raise AssertionError("production status changed after rejected transactional reconcile")
        expected_calls = [str(proof_validator), str(load_validator), str(operability_validator)]
        if calls != expected_calls:
            raise AssertionError(f"validator order drift: {calls!r} != {expected_calls!r}")

    print("PASS: upload-completion authority identity and aggregate rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
