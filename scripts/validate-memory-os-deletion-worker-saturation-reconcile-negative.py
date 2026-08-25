#!/usr/bin/env python3
"""Prove deletion-worker saturation authority identity, loader transport and rollback are fail-closed."""

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


def expect_callable_rejection(reconciler, attr: str, replacement) -> None:
    original = getattr(reconciler, attr)
    setattr(reconciler, attr, replacement)
    try:
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.Fail:
            pass
        else:
            raise AssertionError(f"{attr} execution substitution must be rejected")
    finally:
        setattr(reconciler, attr, original)


def expect_import_transport_rejection(reconciler) -> None:
    original_spec = reconciler.importlib.util.spec_from_file_location
    original_module = reconciler.importlib.util.module_from_spec
    try:
        reconciler.importlib.util.spec_from_file_location = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.Fail as exc:
            if "validator spec loader transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("validator spec loader transport substitution was accepted")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec

    try:
        reconciler.importlib.util.module_from_spec = lambda *args, **kwargs: None
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.Fail as exc:
            if "validator module loader transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("validator module loader transport substitution was accepted")
    finally:
        reconciler.importlib.util.module_from_spec = original_module


def expect_atomic_transport_rejection(reconciler) -> None:
    original_replace = reconciler.os.replace
    reconciler.os.replace = lambda *args, **kwargs: None
    try:
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.Fail as exc:
            if "atomic replacement transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("atomic replacement transport substitution was accepted")
    finally:
        reconciler.os.replace = original_replace


def main() -> int:
    reconciler = load_module(RECONCILER_PATH, "memory_os_deletion_worker_saturation_reconciler_negative")
    expect_authority_rejection(reconciler, "CONTRACT_PATH", reconciler.RESULT_PATH)
    expect_authority_rejection(reconciler, "RESULT_PATH", reconciler.CONTRACT_PATH)
    expect_authority_rejection(reconciler, "VALIDATOR_PATH", reconciler.CONTRACT_PATH)
    expect_callable_rejection(reconciler, "atomic_write_bytes", lambda *args, **kwargs: None)
    expect_callable_rejection(reconciler, "load_validator", lambda: None)
    expect_callable_rejection(reconciler, "validate_canonical", lambda *args, **kwargs: None)
    expect_import_transport_rejection(reconciler)
    expect_atomic_transport_rejection(reconciler)

    source = RECONCILER_PATH.read_text(encoding="utf-8")
    if "CONTRACT_PATH.write_text(" in source or "CONTRACT_PATH.write_bytes(" in source:
        raise AssertionError("deletion-worker saturation authority regressed to direct contract publication")

    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_result = reconciler.RESULT_PATH.read_bytes() if reconciler.RESULT_PATH.exists() else None
    original_validator = reconciler.VALIDATOR_PATH.read_bytes()
    contract = json.loads(original_contract.decode("utf-8"))
    expected = "0" * 40
    reconciler.RESULT_PATH.write_text(json.dumps(synthetic_result(contract, expected), indent=2) + "\n", encoding="utf-8")

    failing_validator = '''class Fail(RuntimeError):\n    pass\n\n_contract_calls = 0\n\ndef validate_contract(candidate):\n    global _contract_calls\n    _contract_calls += 1\n    if _contract_calls == 2:\n        raise Fail("synthetic post-write validation failure")\n\ndef validate_result(candidate, expected_sha):\n    return None\n'''
    reconciler.VALIDATOR_PATH.write_text(failing_validator, encoding="utf-8")

    old_expected = os.environ.get("EXPECTED_COMMIT_SHA")
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
        reconciler.VALIDATOR_PATH.write_bytes(original_validator)
        if original_result is None:
            reconciler.RESULT_PATH.unlink(missing_ok=True)
        else:
            reconciler.RESULT_PATH.write_bytes(original_result)
        if old_expected is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = old_expected

    reconciler.enforce_runtime_authorities()

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

    print("PASS: deletion-worker saturation authority, loader transport, atomic writer transport, atomic publication and rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
