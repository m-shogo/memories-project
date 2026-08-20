#!/usr/bin/env python3
"""Prove deletion mutation evidence reconcile rolls back after aggregate rejection."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-mutation-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deletion_mutation_evidence_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deletion mutation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-mutation-reconcile-") as tmp:
        root = Path(tmp)
        proof_contract = root / "proof-contract.json"
        proof_result = root / "proof-result.json"
        load_contract = root / "load-contract.json"
        status = root / "status.json"
        proof_validator = root / "proof-validator.py"
        load_index_validator = root / "load-index-validator.py"
        load_validator = root / "load-validator.py"
        operability_validator = root / "operability-validator.py"

        write_json(
            proof_contract,
            {"readiness": {"exactSourceResultCommitted": True, "preFenceMutationLinearizationProven": True}},
        )
        write_json(
            proof_result,
            {
                "scenario": {
                    "result": "PASS",
                    "integrityResult": "PASS",
                    "authenticatedBeforeFence": 32,
                    "applyUnauthorizedAfterFence": 16,
                    "uploadAuthorizationUnauthorizedAfterFence": 16,
                    "unexpectedStatusCount": 0,
                    "transportErrors": 0,
                    "preWorkerApplyConfirmationRows": 0,
                    "preWorkerMemoryItemRows": 0,
                    "preWorkerUploadAuthorizationRows": 0,
                    "preWorkerQuarantineRows": 0,
                    "finalOwnedRowCount": 0,
                }
            },
        )
        write_json(
            load_contract,
            {
                "readiness": {
                    "productionEquivalentDependencies": False,
                    "capacityBoundaryEstablished": False,
                    "sustainedSoakEvidence": False,
                    "note": "synthetic local authority",
                },
                "evidenceRefs": [],
                "deferredScenarios": [{"scenarioId": "deletion-under-load", "reason": "synthetic"}],
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
        module.MUTATION_CONTRACT = proof_contract
        module.MUTATION_RESULT = proof_result
        module.LOAD_PATH = load_contract
        module.STATUS_PATH = status
        module.MUTATION_VALIDATOR = proof_validator
        module.LOAD_INDEX_VALIDATOR = load_index_validator
        module.LOAD_VALIDATOR = load_validator
        module.OPERABILITY_VALIDATOR = operability_validator

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
            raise AssertionError("aggregate operability rejection must fail mutation reconcile")

        if load_contract.read_bytes() != before_load:
            raise AssertionError("load authority changed after rejected mutation reconcile")
        if status.read_bytes() != before_status:
            raise AssertionError("production status changed after rejected mutation reconcile")
        expected = [
            str(proof_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected:
            raise AssertionError(f"validator order drift: {calls!r} != {expected!r}")

    print("PASS: deletion mutation evidence reconcile rolls back after aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
