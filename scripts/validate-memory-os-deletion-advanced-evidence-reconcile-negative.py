#!/usr/bin/env python3
"""Prove advanced deletion evidence reconcile rolls back after aggregate rejection."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-advanced-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deletion_advanced_evidence_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load advanced deletion evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def atomic_writer_is_fail_closed(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-advanced-deletion-atomic-") as tmp:
        root = Path(tmp)
        target = root / "authority.json"
        target.write_bytes(b"before\n")
        os.chmod(target, 0o640)

        module.atomic_write_bytes(target, b"after\n")
        if target.read_bytes() != b"after\n":
            raise AssertionError("advanced deletion atomic writer payload drift")
        if stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("advanced deletion atomic writer changed existing file mode")
        if list(root.glob(f".{target.name}.*.tmp")):
            raise AssertionError("advanced deletion atomic writer left temp residue")

        target.write_bytes(b"before\n")
        original_replace = module.os.replace

        def fail_replace(_source, _destination):
            raise OSError("synthetic advanced deletion atomic replacement failure")

        module.os.replace = fail_replace
        try:
            try:
                module.atomic_write_bytes(target, b"after\n")
            except OSError as exc:
                if "synthetic advanced deletion atomic replacement failure" not in str(exc):
                    raise AssertionError(f"unexpected atomic failure: {exc}") from exc
            else:
                raise AssertionError("advanced deletion atomic writer accepted replacement failure")
        finally:
            module.os.replace = original_replace
        if target.read_bytes() != b"before\n":
            raise AssertionError("atomic replacement failure mutated advanced deletion authority")
        if list(root.glob(f".{target.name}.*.tmp")):
            raise AssertionError("atomic replacement failure left advanced deletion temp residue")


def main() -> int:
    module = load_module()
    atomic_writer_is_fail_closed(module)
    with tempfile.TemporaryDirectory(prefix="memory-os-advanced-deletion-reconcile-") as tmp:
        root = Path(tmp)
        prefence_contract = root / "prefence-contract.json"
        prefence_result = root / "prefence-result.json"
        worker_contract = root / "worker-contract.json"
        worker_result = root / "worker-result.json"
        load_contract = root / "load-contract.json"
        status = root / "status.json"
        prefence_validator = root / "prefence-validator.py"
        worker_validator = root / "worker-validator.py"
        load_index_validator = root / "load-index-validator.py"
        load_validator = root / "load-validator.py"
        operability_validator = root / "operability-validator.py"

        write_json(prefence_contract, {"readiness": {"exactSourceResultCommitted": True, "preFenceInFlightLinearizationProven": True}})
        write_json(
            prefence_result,
            {
                "scenario": {
                    "result": "PASS",
                    "integrityResult": "PASS",
                    "authenticatedBeforeFence": 32,
                    "unauthorizedAfterFence": 32,
                    "unexpectedStatusCount": 0,
                    "transportErrors": 0,
                }
            },
        )
        write_json(worker_contract, {"readiness": {"exactSourceResultCommitted": True, "multiAccountWorkerSaturationProven": True}})
        write_json(
            worker_result,
            {
                "scenario": {
                    "result": "PASS",
                    "integrityResult": "PASS",
                    "workerReceiptCount": 24,
                    "uniqueWorkerReceiptCount": 24,
                    "duplicateWorkerReceiptCount": 0,
                    "controlPreview2xx": 400,
                    "finalDeletionPending": 0,
                    "finalDeletionStuck": 0,
                    "finalOwnedRowCount": 0,
                }
            },
        )
        write_json(
            load_contract,
            {
                "externalExecutedScenarios": [],
                "deferredScenarios": [{"scenarioId": "deletion-under-load", "reason": "synthetic"}],
                "readiness": {"productionEquivalentDependencies": False, "capacityBoundaryEstablished": False},
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
        module.PREFENCE_CONTRACT_PATH = prefence_contract
        module.PREFENCE_RESULT_PATH = prefence_result
        module.WORKER_CONTRACT_PATH = worker_contract
        module.WORKER_RESULT_PATH = worker_result
        module.LOAD_PATH = load_contract
        module.STATUS_PATH = status
        module.PREFENCE_VALIDATOR = prefence_validator
        module.WORKER_VALIDATOR = worker_validator
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
        load_mode = stat.S_IMODE(load_contract.stat().st_mode)
        status_mode = stat.S_IMODE(status.stat().st_mode)

        try:
            module.main()
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("aggregate operability rejection must fail advanced deletion reconcile")

        if load_contract.read_bytes() != before_load:
            raise AssertionError("load authority changed after rejected advanced deletion reconcile")
        if status.read_bytes() != before_status:
            raise AssertionError("production status changed after rejected advanced deletion reconcile")
        if stat.S_IMODE(load_contract.stat().st_mode) != load_mode:
            raise AssertionError("load authority mode changed after advanced deletion rollback")
        if stat.S_IMODE(status.stat().st_mode) != status_mode:
            raise AssertionError("production status mode changed after advanced deletion rollback")
        if list(root.glob(".*.tmp")):
            raise AssertionError("advanced deletion rollback left temporary residue")
        expected = [
            str(prefence_validator),
            str(worker_validator),
            str(load_index_validator),
            str(load_validator),
            str(operability_validator),
        ]
        if calls != expected:
            raise AssertionError(f"validator order drift: {calls!r} != {expected!r}")

    print("PASS: advanced deletion evidence reconcile uses atomic mode-preserving publication and rolls back after aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
