#!/usr/bin/env python3
"""Prove deletion-worker saturation authority identity, loader transport and rollback are fail-closed."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
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
    expect_callable_rejection(reconciler, "require_strict_local_readiness", lambda *args, **kwargs: None)
    expect_import_transport_rejection(reconciler)
    expect_atomic_transport_rejection(reconciler)

    source = RECONCILER_PATH.read_text(encoding="utf-8")
    if "CONTRACT_PATH.write_text(" in source or "CONTRACT_PATH.write_bytes(" in source:
        raise AssertionError("deletion-worker saturation authority regressed to direct contract publication")

    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    original_contract_mode = stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode)
    original_result = reconciler.RESULT_PATH.read_bytes() if reconciler.RESULT_PATH.exists() else None
    original_validator = reconciler.VALIDATOR_PATH.read_bytes()
    contract = json.loads(original_contract.decode("utf-8"))
    expected = "0" * 40
    reconciler.RESULT_PATH.write_text(json.dumps(synthetic_result(contract, expected), indent=2) + "\n", encoding="utf-8")

    failing_validator = '''import sys
print("SYNTHETIC_SECRET_IMPORT_STDOUT")
print("SYNTHETIC_SECRET_IMPORT_STDERR", file=sys.stderr)
class Fail(RuntimeError):\n    pass\n\n_contract_calls = 0\n\ndef validate_contract(candidate):\n    print("SYNTHETIC_SECRET_VALIDATE_STDOUT")\n    print("SYNTHETIC_SECRET_VALIDATE_STDERR", file=sys.stderr)\n    global _contract_calls\n    _contract_calls += 1\n    if _contract_calls == 2:\n        raise Fail("SYNTHETIC_SECRET_VALIDATOR_FAILURE")\n\ndef validate_result(candidate, expected_sha):\n    print("SYNTHETIC_SECRET_RESULT_STDOUT")\n    print("SYNTHETIC_SECRET_RESULT_STDERR", file=sys.stderr)\n    return None\n'''
    reconciler.VALIDATOR_PATH.write_text(failing_validator, encoding="utf-8")

    old_expected = os.environ.get("EXPECTED_COMMIT_SHA")
    os.environ["EXPECTED_COMMIT_SHA"] = expected
    try:
        captured_stdout, captured_stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
                reconciler.main()
        except reconciler.Fail as exc:
            if ("post-write validation failed: Fail" not in str(exc)
                    or "SYNTHETIC_SECRET" in str(exc)
                    or not exc.__suppress_context__):
                raise AssertionError("reconciler leaked validator exception or lost fail-closed diagnostic") from None
        else:
            raise AssertionError("reconciler accepted synthetic post-write validator failure")

        if "SYNTHETIC_SECRET" in captured_stdout.getvalue() + captured_stderr.getvalue():
            raise AssertionError("validator import or execution emitted untrusted Python output")
        if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("reconciler failed to restore contract bytes after post-write validation failure")
        if stat.S_IMODE(reconciler.CONTRACT_PATH.stat().st_mode) != original_contract_mode:
            raise AssertionError("reconciler changed contract mode during failed publication and rollback")
        if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("reconciler left atomic temp authority after rollback")

        original_fsync = reconciler.os.fsync
        fsync_calls = 0

        def reject_rollback_fsync(fd):
            nonlocal fsync_calls
            fsync_calls += 1
            if fsync_calls == 2:
                raise OSError("SYNTHETIC_SECRET_ROLLBACK_FAILURE")
            return original_fsync(fd)

        reconciler.os.fsync = reject_rollback_fsync
        try:
            captured_stdout, captured_stderr = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
                    reconciler.main()
            except reconciler.Fail as exc:
                diagnostic = str(exc)
                if ("post-write validation failed: Fail" not in diagnostic
                        or "rollback incomplete: OSError" not in diagnostic
                        or "SYNTHETIC_SECRET" in diagnostic
                        or not exc.__suppress_context__):
                    raise AssertionError("rollback failure leaked raw exception or lost incompleteness") from None
            else:
                raise AssertionError("reconciler accepted synthetic rollback failure")
            if "SYNTHETIC_SECRET" in captured_stdout.getvalue() + captured_stderr.getvalue():
                raise AssertionError("rollback validator emitted untrusted Python output")
        finally:
            reconciler.os.fsync = original_fsync

        if fsync_calls != 2:
            raise AssertionError(f"rollback failure injection was not exercised: {fsync_calls}")
        if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("rollback failure left atomic temporary authority")

        # Prove the reconciler's own prewrite guard, independently of validator policy.
        permissive_validator = chr(10).join((
            "def validate_contract(candidate): pass",
            "def validate_result(candidate, expected_sha): pass",
            "",
        ))
        reconciler.VALIDATOR_PATH.write_text(permissive_validator, encoding="utf-8")
        for key in ("productionDependenciesTested", "independentReviewCompleted", "productionReady"):
            for stronger in (True, None, 0, 1, "false", [], {}):
                candidate = json.loads(original_contract.decode("utf-8"))
                candidate["readiness"][key] = stronger
                payload = (json.dumps(candidate, indent=2) + chr(10)).encode("utf-8")
                reconciler.atomic_write_bytes(reconciler.CONTRACT_PATH, payload)
                before = reconciler.CONTRACT_PATH.read_bytes()
                try:
                    reconciler.main()
                except reconciler.Fail as exc:
                    if "local proof cannot downgrade readiness." + key not in str(exc):
                        raise AssertionError("unexpected stronger-readiness rejection: " + key) from None
                else:
                    raise AssertionError("reconciler downgraded stronger readiness: " + key)
                if reconciler.CONTRACT_PATH.read_bytes() != before:
                    raise AssertionError("stronger-readiness prewrite guard mutated contract: " + key)
                if list(reconciler.CONTRACT_PATH.parent.glob(f".{reconciler.CONTRACT_PATH.name}.*.tmp")):
                    raise AssertionError("stronger-readiness prewrite guard left temp authority")
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
        os.chmod(target, 0o640)
        reconciler.atomic_write_bytes(target, b"mode-check\n")
        if stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("atomic writer changed existing authority mode")
        target.write_bytes(b"before\n")

        canonical_replace = reconciler.os.replace
        failed = False

        def fail_replace(source_path, destination_path):
            nonlocal failed
            if Path(destination_path) == target and not failed:
                failed = True
                raise OSError("synthetic atomic replace failure")
            return canonical_replace(source_path, destination_path)

        try:
            reconciler.atomic_write_bytes(target, b"after\n", _replace=fail_replace)
        except OSError as exc:
            if "synthetic atomic replace failure" not in str(exc):
                raise AssertionError(f"unexpected atomic replacement failure: {exc}") from exc
        else:
            raise AssertionError("atomic writer accepted synthetic replacement failure")

        if not failed:
            raise AssertionError("synthetic atomic replacement failure was not exercised")
        if target.read_bytes() != b"before\n":
            raise AssertionError("atomic replacement failure mutated canonical target bytes")
        if stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("atomic replacement failure changed existing authority mode")
        if list(target.parent.glob(f".{target.name}.*.tmp")):
            raise AssertionError("atomic replacement failure left a temp file")

        target.write_bytes(b"before-binding\n")
        os.chmod(target, 0o640)
        mutable_replace_calls = 0

        def reject_mutable_replace(*_args, **_kwargs):
            nonlocal mutable_replace_calls
            mutable_replace_calls += 1
            raise OSError("mutable os.replace transport was invoked")

        reconciler.os.replace = reject_mutable_replace
        try:
            reconciler.atomic_write_bytes(target, b"after-binding\n")
        finally:
            reconciler.os.replace = canonical_replace

        if mutable_replace_calls != 0:
            raise AssertionError("bound atomic writer consulted mutable os.replace")
        if target.read_bytes() != b"after-binding\n":
            raise AssertionError("bound atomic writer failed to publish expected payload")
        if stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("bound atomic writer changed existing authority mode")
        if list(target.parent.glob(f".{target.name}.*.tmp")):
            raise AssertionError("bound atomic writer left a temp file")

        new_target = Path(tmp) / "new-authority.json"
        reconciler.atomic_write_bytes(new_target, b"new\\n")
        if new_target.read_bytes() != b"new\\n" or stat.S_IMODE(new_target.stat().st_mode) != 0o600:
            raise AssertionError("new atomic authority default mode/payload drift")

        outside = Path(tmp) / "outside"
        outside.mkdir()
        canary = outside / "canary.json"
        canary.write_bytes(b"SYNTHETIC_SECRET_CANARY")
        direct_link = Path(tmp) / "direct-symlink.json"
        direct_link.symlink_to(canary)
        linked_parent = Path(tmp) / "linked-parent"
        linked_parent.symlink_to(outside, target_is_directory=True)
        directory_target = Path(tmp) / "directory-target.json"
        directory_target.mkdir()
        cases = (
            ("symlink target", direct_link),
            ("symlink ancestor", linked_parent / "canary.json"),
            ("directory target", directory_target),
            ("missing parent", Path(tmp) / "missing" / "authority.json"),
        )
        for label, unsafe_target in cases:
            try:
                reconciler.atomic_write_bytes(unsafe_target, b"malicious\\n")
            except reconciler.Fail as exc:
                if "atomic " not in str(exc) or "SYNTHETIC_SECRET" in str(exc):
                    raise AssertionError("unsafe atomic path diagnostic drift: " + label) from None
            else:
                raise AssertionError("unsafe atomic writer path accepted: " + label)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("unsafe atomic writer mutated external canary: " + label)
            if list(Path(tmp).rglob(".*.tmp")):
                raise AssertionError("unsafe atomic writer left temp residue: " + label)

    print("PASS: deletion-worker saturation authority, secret-free validator output/import/rollback diagnostics, stronger-readiness prewrite, mode-preserving atomic publication, path rejection and rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
