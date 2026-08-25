#!/usr/bin/env python3
"""Prove deletion-worker saturation authority identity and rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-deletion-worker-saturation.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_result(contract: dict, expected: str) -> dict:
    criteria = contract.get("successCriteria")
    if not isinstance(criteria, dict):
        raise AssertionError("canonical saturation contract successCriteria missing")
    scenario = dict(criteria)
    scenario.update(
        {
            "scenarioId": contract["scenarioId"],
            "deletingAccounts": contract["deletingAccounts"],
            "workerCount": contract["workerCount"],
            "maxAccountsPerWorker": contract["maxAccountsPerWorker"],
            "controlPreviewRequests": contract["controlPreviewRequests"],
            "controlPreviewConcurrency": contract["controlPreviewConcurrency"],
            "result": "PASS",
            "integrityResult": "PASS",
            "assertions": {
                "allDeletionRequestsAccepted": True,
                "workerReceiptsUnique": True,
                "controlPreviewAll2xx": True,
                "deletionBacklogConverged": True,
                "finalOwnedRowsZero": True,
                "allDeletionTombstonesEpoch2": True,
                "capacityBoundaryEstablished": False,
                "operationalThresholdApproved": False,
                "productionEvidence": False,
            },
        }
    )
    return {
        "schemaVersion": contract["resultsSchemaVersion"],
        "commitSha": expected,
        "environment": {
            "dependencyMode": "LOCAL_POSTGRES_MINIO",
            "syntheticDataOnly": True,
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "productionEquivalentDependencies": False,
            "containsSecrets": False,
        },
        "scenario": scenario,
    }


def expect_authority_rejection(reconciler, attr: str, replacement: Path) -> None:
    original = getattr(reconciler, attr)
    setattr(reconciler, attr, replacement)
    try:
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution must be rejected")
    finally:
        setattr(reconciler, attr, original)


def main() -> int:
    reconciler = load_module(RECONCILER_PATH, "memory_os_deletion_worker_saturation_reconciler_negative")
    expect_authority_rejection(reconciler, "CONTRACT_PATH", reconciler.RESULT_PATH)
    expect_authority_rejection(reconciler, "RESULT_PATH", reconciler.CONTRACT_PATH)
    expect_authority_rejection(reconciler, "VALIDATOR_PATH", reconciler.CONTRACT_PATH)

    source = RECONCILER_PATH.read_text(encoding="utf-8")
    if "CONTRACT_PATH.write_text(" in source or "CONTRACT_PATH.write_bytes(" in source:
        raise AssertionError("deletion-worker saturation authority regressed to direct contract publication")

    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_result = reconciler.RESULT_PATH.read_bytes() if reconciler.RESULT_PATH.exists() else None
    contract = json.loads(original_contract.decode("utf-8"))
    expected = "0" * 40
    reconciler.RESULT_PATH.write_text(json.dumps(synthetic_result(contract, expected), indent=2) + "\n", encoding="utf-8")

    reconciler.enforce_runtime_authorities()
    real_validator = reconciler.load_validator()

    class Fail(RuntimeError):
        pass

    class FailingValidator:
        def __init__(self) -> None:
            self.contract_calls = 0

        def validate_contract(self, candidate) -> None:
            self.contract_calls += 1
            real_validator.validate_contract(candidate)
            if self.contract_calls == 2:
                raise Fail("synthetic post-write validation failure")

        def validate_result(self, candidate, expected_sha) -> None:
            real_validator.validate_result(candidate, expected_sha)

    old_expected = os.environ.get("EXPECTED_COMMIT_SHA")
    reconciler.load_validator = lambda: FailingValidator()
    os.environ["EXPECTED_COMMIT_SHA"] = expected
    try:
        try:
            reconciler.main()
        except RuntimeError as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise AssertionError(f"unexpected reconcile rejection: {exc}") from exc
        else:
            raise AssertionError("reconciler accepted synthetic post-write validator failure")

        if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("reconciler failed to restore contract bytes after post-write validation failure")
        if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("reconciler left atomic temp authority after rollback")
    finally:
        reconciler.atomic_write_bytes(reconciler.CONTRACT_PATH, original_contract)
        if original_result is None:
            reconciler.RESULT_PATH.unlink(missing_ok=True)
        else:
            reconciler.RESULT_PATH.write_bytes(original_result)
        if old_expected is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = old_expected

    with tempfile.TemporaryDirectory(prefix="memory-os-deletion-worker-saturation-atomic-") as tmp:
        target = Path(tmp) / "authority.json"
        target.write_bytes(b"before\n")
        original_replace = reconciler.os.replace
        failed = False

        def fail_replace(source_path, destination_path):
            nonlocal failed
            if Path(destination_path) == target and not failed:
                failed = True
                raise OSError("synthetic atomic replace failure")
            return original_replace(source_path, destination_path)

        reconciler.os.replace = fail_replace
        try:
            try:
                reconciler.atomic_write_bytes(target, b"after\n")
            except OSError as exc:
                if "synthetic atomic replace failure" not in str(exc):
                    raise AssertionError(f"unexpected atomic replacement failure: {exc}") from exc
            else:
                raise AssertionError("atomic writer accepted synthetic replacement failure")
        finally:
            reconciler.os.replace = original_replace

        if not failed:
            raise AssertionError("synthetic atomic replacement failure was not exercised")
        if target.read_bytes() != b"before\n":
            raise AssertionError("atomic replacement failure mutated canonical target bytes")
        if list(target.parent.glob(f".{target.name}.*.tmp")):
            raise AssertionError("atomic replacement failure left a temp file")

    print("PASS: deletion-worker saturation authority identity, atomic publication and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
