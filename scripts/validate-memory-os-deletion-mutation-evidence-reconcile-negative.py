#!/usr/bin/env python3
"""Prove deletion mutation evidence reconcile preserves independent authority and rolls back aggregate rejection."""

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


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def expect_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-mutation-atomic-") as tmp:
        root = Path(tmp)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                if "synthetic atomic replacement failure" not in str(exc):
                    raise
            else:
                raise AssertionError("atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise AssertionError("failed atomic replacement changed authority bytes")
        residue = list(root.glob(f".{authority.name}.*.tmp"))
        if residue:
            raise AssertionError(f"failed atomic replacement left temp residue: {residue!r}")


def main() -> int:
    module = load_module()
    substitutions = {
        "MUTATION_CONTRACT": module.LOAD_PATH,
        "MUTATION_RESULT": module.MUTATION_CONTRACT,
        "LOAD_PATH": module.MUTATION_CONTRACT,
        "STATUS_PATH": module.LOAD_PATH,
        "MUTATION_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_INDEX_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.MUTATION_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    expect_atomic_replace_failure(module)

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
                    "uploadCompletionPreFenceInFlightLinearizationProven": True,
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
                        "missingEvidence": [module.UPLOAD_COMPLETION_BLOCKER],
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
        module.enforce_runtime_authorities = lambda: None

        calls: list[str] = []

        def successful_run(command, *, cwd, check):
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            calls.append(str(command[1]))
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = successful_run
        before_load = load_contract.read_bytes()
        before_status = status.read_bytes()
        module.main()
        after_success = json.loads(load_contract.read_text(encoding="utf-8"))
        after_status = json.loads(status.read_text(encoding="utf-8"))
        if after_success["readiness"].get("uploadCompletionPreFenceInFlightLinearizationProven") is not True:
            raise AssertionError("mutation reconcile demoted independently proven upload completion authority")
        if any(
            isinstance(item, str) and item.startswith("pre-fence in-flight linearization for upload-completion requests")
            for item in after_status["areas"][0]["missingEvidence"]
        ):
            raise AssertionError("mutation reconcile reintroduced an independently satisfied upload-completion blocker")
        expected_success = [
            str(proof_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected_success:
            raise AssertionError(f"successful validator order drift: {calls!r} != {expected_success!r}")

        load_contract.write_bytes(before_load)
        status.write_bytes(before_status)
        calls.clear()

        def failing_run(command, *, cwd, check):
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            validator = str(command[1])
            calls.append(validator)
            if validator == str(operability_validator):
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0)

        module.subprocess.run = failing_run
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
        residue = list(root.glob(".*.tmp"))
        if residue:
            raise AssertionError(f"aggregate rollback left atomic temp residue: {residue!r}")
        expected_failure = [
            str(proof_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected_failure:
            raise AssertionError(f"failure validator order drift: {calls!r} != {expected_failure!r}")

    print("PASS: deletion mutation authority preserves independent upload completion, atomic replacement, and rollback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
