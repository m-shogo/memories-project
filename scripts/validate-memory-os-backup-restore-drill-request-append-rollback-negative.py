#!/usr/bin/env python3
"""Prove backup/restore drill request registry and reconcile rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer():
    return load_module(WRITER, "memory_os_backup_restore_drill_request_append_rollback_negative")


def load_reconciler():
    return load_module(RECONCILER, "memory_os_backup_restore_drill_request_reconcile_transaction_negative")


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def require_no_temp_residue(path: Path) -> None:
    residue = list(path.parent.glob(".backup-restore-drill-request*.tmp"))
    require(not residue, f"drill request registry temp residue remained: {[item.name for item in residue]}")


def prove_close_failure_releases_lock(writer) -> None:
    original_registry = writer.REGISTRY
    original_lock = writer.LOCK
    original_load = writer.load
    original_validate_request = writer.validate_request
    original_validate_registry = writer.validate_registry_for_append
    original_write = writer.write_registry_transactionally
    original_approval_sha256 = writer.approval_sha256
    original_currently_executable = writer.request_currently_executable
    original_require_cli = writer.require_cli_authorities
    original_git = writer.git
    original_close = writer.os.close
    original_argv = sys.argv[:]

    with tempfile.TemporaryDirectory(prefix="memory-os-drill-request-lock-") as tmpdir:
        tmp = Path(tmpdir)
        registry = tmp / REGISTRY.name
        lock = tmp / ".backup-restore-drill-request.lock"
        record_path = tmp / "request.json"
        record_path.write_text("{}\n", encoding="utf-8")
        record = {
            "requestId": "brrq_fixture_close01",
            "sourceEnvironmentGenerationId": "peg_fixture_source",
            "restoreTargetEnvironmentGenerationId": "peg_fixture_target",
            "recoveryObjectivesId": "ro_fixture_current",
            "approvalRefs": {
                "recoveryOwner": "approval-owner",
                "securityReview": "approval-security",
                "operabilityReview": "approval-operability",
            },
        }
        registry_state = {
            "requests": [],
            "approvalEvidenceDigestsByRequestId": {},
        }

        def fixture_load(path: Path):
            if Path(path) == record_path:
                return record
            if Path(path) == registry:
                return registry_state
            return original_load(path)

        try:
            writer.REGISTRY = registry
            writer.LOCK = lock
            writer.load = fixture_load
            writer.validate_request = lambda _record, require_current=True: None
            writer.validate_registry_for_append = lambda value: value["requests"]
            writer.write_registry_transactionally = lambda _value: None
            writer.approval_sha256 = lambda _ref: "0" * 64
            writer.request_currently_executable = lambda _record: False
            writer.require_cli_authorities = lambda: None
            writer.git = lambda *_args: ""
            sys.argv = [str(WRITER), "--request", str(record_path)]

            def close_then_fail(fd: int) -> None:
                original_close(fd)
                raise OSError("synthetic drill request lock close failure")

            writer.os.close = close_then_fail
            try:
                writer.main()
            except OSError as exc:
                require(
                    "synthetic drill request lock close failure" in str(exc),
                    f"unexpected drill request close failure: {exc}",
                )
            else:
                raise Fail("drill request lock close failure was accepted")
            finally:
                writer.os.close = original_close

            require(not lock.exists(), "drill request close failure stranded its lock")
            registry_state["requests"].clear()
            registry_state["approvalEvidenceDigestsByRequestId"].clear()
            require(writer.main() == 0, "drill request retry did not complete after close failure cleanup")
            require(not lock.exists(), "drill request retry stranded its lock")
        finally:
            writer.REGISTRY = original_registry
            writer.LOCK = original_lock
            writer.load = original_load
            writer.validate_request = original_validate_request
            writer.validate_registry_for_append = original_validate_registry
            writer.write_registry_transactionally = original_write
            writer.approval_sha256 = original_approval_sha256
            writer.request_currently_executable = original_currently_executable
            writer.require_cli_authorities = original_require_cli
            writer.git = original_git
            writer.os.close = original_close
            sys.argv = original_argv


def prove_reconciler_transaction_rollback() -> None:
    reconciler = load_reconciler()
    output_names = ("REGISTRY", "CONTRACT", "STATUS")

    for fail_index in (2, 3):
        with tempfile.TemporaryDirectory(prefix=f".memory-os-drill-request-reconcile-transaction-{fail_index}-", dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            originals = {name: getattr(reconciler, name) for name in output_names}
            copies: dict[str, Path] = {}
            expected: dict[str, bytes] = {}
            for name, source in originals.items():
                target = tmp_path / source.name
                shutil.copy2(source, target)
                target.chmod(0o640)
                copies[name] = target
                expected[name] = target.read_bytes()

            original_enforcer = reconciler.enforce_runtime_authorities
            original_replace = reconciler.os.replace
            replace_calls = 0

            def fail_nth_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == fail_index:
                    raise OSError(f"synthetic drill-request reconcile replace failure #{fail_index}")
                original_replace(source, destination)

            for name, target in copies.items():
                setattr(reconciler, name, target)
            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.os.replace = fail_nth_replace
            try:
                try:
                    reconciler.main()
                except reconciler.Fail:
                    pass
                else:
                    raise Fail(f"drill-request reconcile replace failure #{fail_index} was accepted")
            finally:
                reconciler.os.replace = original_replace
                reconciler.enforce_runtime_authorities = original_enforcer
                for name, source in originals.items():
                    setattr(reconciler, name, source)

            require(
                replace_calls >= fail_index + len(output_names),
                f"drill-request reconcile rollback did not restore all authorities after replace #{fail_index}: {replace_calls}",
            )
            for name, target in copies.items():
                require(
                    target.read_bytes() == expected[name],
                    f"drill-request reconcile {name} bytes changed after replace #{fail_index} rollback",
                )
                require(
                    file_mode(target) == 0o640,
                    f"drill-request reconcile {name} mode changed after replace #{fail_index} rollback",
                )
            residue = list(tmp_path.glob(".*.tmp"))
            require(not residue, f"drill-request reconcile replace #{fail_index} left temporary files: {residue}")

    print("PASS rollback: drill-request 3-authority reconcile restores exact bytes+mode after second/third replace failures")


def main() -> int:
    require(WRITER.is_file() and RECONCILER.is_file() and CONTRACT.is_file(), "drill request append authority missing")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("admissionRules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "transactional drill request append contract guard missing",
    )

    writer = load_writer()
    require(callable(getattr(writer, "write_registry_transactionally", None)), "transactional drill request registry writer missing")

    with tempfile.TemporaryDirectory(prefix="memory-os-drill-request-append-rollback-") as tmp:
        registry = Path(tmp) / "backup-restore-drill-request-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        expected_mode = 0o640
        registry.write_bytes(original)
        registry.chmod(expected_mode)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        original_replace = writer.os.replace
        original_atomic_restore = writer.atomic_restore
        writer.REGISTRY = registry

        def accept_after_write(_value):
            return []

        def reject_after_write(_value):
            raise writer.Fail("synthetic post-append drill request registry validation failure")

        def reject_replace(_source, _destination):
            raise OSError("synthetic drill request registry replace rejection")

        try:
            writer.validate_registry_for_append = accept_after_write
            writer.write_registry_transactionally({"sentinel": "after"})
            require(file_mode(registry) == expected_mode, "successful drill request append changed registry mode")
            require_no_temp_residue(registry)

            registry.write_bytes(original)
            registry.chmod(expected_mode)
            writer.os.replace = reject_replace
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except OSError as exc:
                require("synthetic drill request registry replace rejection" in str(exc), "unexpected drill request replace failure")
            else:
                raise Fail("drill request registry replace rejection was accepted")
            require(registry.read_bytes() == original, "rejected drill request append changed registry bytes")
            require(file_mode(registry) == expected_mode, "rejected drill request append changed registry mode")
            require_no_temp_residue(registry)

            writer.os.replace = original_replace
            writer.validate_registry_for_append = reject_after_write
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require("synthetic post-append" in str(exc), "unexpected transactional drill request append failure")
            else:
                raise Fail("post-append drill request registry validation failure was accepted")
            require(registry.read_bytes() == original, "failed drill request append did not restore original registry bytes")
            require(file_mode(registry) == expected_mode, "failed drill request append did not restore original registry mode")
            require_no_temp_residue(registry)

            def reject_rollback_restore(_payload, _mode=None):
                raise writer.Fail("synthetic drill request rollback restore failure")

            writer.atomic_restore = reject_rollback_restore
            try:
                writer.write_registry_transactionally({"sentinel": "rollback-failure"})
            except writer.Fail as exc:
                text = str(exc)
                require("primary failure" in text, "drill request rollback failure lost primary failure marker")
                require(
                    "synthetic post-append drill request registry validation failure" in text,
                    "drill request rollback failure lost primary validator diagnostic",
                )
                require("rollback incomplete" in text, "drill request rollback failure missing incomplete rollback marker")
                require(
                    "synthetic drill request rollback restore failure" in text,
                    "drill request rollback failure diagnostic missing restore cause",
                )
            else:
                raise Fail("drill request rollback restore failure was accepted")
            finally:
                writer.atomic_restore = original_atomic_restore
                registry.write_bytes(original)
                registry.chmod(expected_mode)
            require_no_temp_residue(registry)
        finally:
            writer.os.replace = original_replace
            writer.atomic_restore = original_atomic_restore
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    prove_close_failure_releases_lock(writer)
    prove_reconciler_transaction_rollback()

    print("Memory OS backup/restore drill request append/reconcile rollback negative PASS")
    print("successful append registry mode preservation: enforced")
    print("replace rejection registry bytes/mode preservation: enforced")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte and mode-preserving")
    print("append rollback failure preserves primary and rollback diagnostics: enforced")
    print("lock close failure stranded lock: false")
    print("lock close failure retry reacquisition: enforced")
    print("reconcile second/third replace partial transaction accepted: false")
    print("reconcile transaction rollback: exact bytes+mode and no temp residue")
    print("temporary registry residue: none")
    print("request created: false")
    print("planning authority only: true")
    print("production evidence: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST APPEND/RECONCILE ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
