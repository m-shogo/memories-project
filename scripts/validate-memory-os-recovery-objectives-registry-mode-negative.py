#!/usr/bin/env python3
"""Prove recovery-objective registry publication preserves bytes/mode on failure."""

from __future__ import annotations

import copy
import importlib.util
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_registry_mode_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def temp_residue(directory: Path) -> list[Path]:
    return [
        *directory.glob(".recovery-objectives.*.tmp"),
        *directory.glob(".recovery-objectives-rollback.*.tmp"),
    ]


def prove_close_failure_releases_lock(writer) -> None:
    original_registry = writer.REGISTRY
    original_lock = writer.LOCK
    original_load = writer.load
    original_validate_record = writer.validate_record
    original_validate_registry = writer.validate_registry_for_append
    original_write = writer.write_registry_transactionally
    original_approval_sha256 = writer.approval_sha256
    original_require_actual = writer.require_actual_cli_authorities
    original_require_canonical = writer.require_canonical_runtime_authorities
    original_close = writer.os.close
    original_open = writer.os.open
    original_write = writer.os.write
    original_fsync = writer.os.fsync
    original_argv = sys.argv[:]

    with tempfile.TemporaryDirectory(prefix="memory-os-objective-lock-") as tmpdir:
        tmp = Path(tmpdir)
        registry_copy = tmp / REGISTRY.name
        shutil.copyfile(REGISTRY, registry_copy)
        lock = tmp / ".recovery-objectives.lock"
        record_path = tmp / "objective.json"
        record = {
            "objectiveId": "ro_fixture_close01",
            "approvalEvidenceRefs": ["approval-owner", "approval-operability"],
            "supersedesObjectiveId": None,
        }
        record_path.write_text("{}\n", encoding="utf-8")
        baseline = original_load(registry_copy)

        def fixture_load(path: Path):
            if Path(path) == record_path:
                return copy.deepcopy(record)
            if Path(path) == registry_copy:
                return copy.deepcopy(baseline)
            return original_load(path)

        try:
            writer.REGISTRY = registry_copy
            writer.LOCK = lock
            writer.load = fixture_load
            writer.validate_record = lambda _record: None
            writer.validate_registry_for_append = lambda registry: registry["records"]
            writer.write_registry_transactionally = lambda _registry: None
            writer.approval_sha256 = lambda _ref: "0" * 64
            writer.require_actual_cli_authorities = lambda: None
            writer.require_canonical_runtime_authorities = lambda: None
            sys.argv = [str(WRITER), "--record", str(record_path)]

            def close_then_fail(fd: int) -> None:
                original_close(fd)
                raise OSError("synthetic recovery objective lock close failure")

            writer.os.close = close_then_fail
            try:
                writer.main()
            except writer.Fail as exc:
                require(
                    str(exc) == "recovery objectives registry lock cleanup failed",
                    "recovery objective lock close failure class drift",
                )
                require(
                    exc.__suppress_context__ and "synthetic recovery objective lock close failure" not in str(exc),
                    "recovery objective lock close failure leaked private OS diagnostics",
                )
            else:
                raise Fail("recovery objective close failure was accepted")
            finally:
                writer.os.close = original_close

            require(not lock.exists(), "recovery objective close failure stranded its lock")
            require(writer.main() == 0, "recovery objective retry did not complete after close failure cleanup")
            require(not lock.exists(), "recovery objective retry stranded its lock")

            # A failed lock open must be private and must not claim an acquired lock.
            def reject_lock_open(path, flags, mode=0o777):
                if Path(path) == lock:
                    raise OSError("PRIVATE_OBJECTIVE_LOCK_OPEN_CANARY")
                return original_open(path, flags, mode)

            writer.os.open = reject_lock_open
            try:
                writer.main()
            except writer.Fail as exc:
                require(
                    str(exc) == "recovery objectives registry lock acquisition failed",
                    "recovery objective lock open failure class drift",
                )
                require(
                    exc.__suppress_context__ and "PRIVATE_OBJECTIVE_LOCK_OPEN_CANARY" not in str(exc),
                    "recovery objective lock open failure leaked private OS diagnostics",
                )
            else:
                raise Fail("recovery objective failed lock open was accepted")
            finally:
                writer.os.open = original_open
            require(not lock.exists(), "failed objective lock acquisition left a lock")
            require(writer.main() == 0, "recovery objective retry after lock open fault failed")
            require(not lock.exists(), "recovery objective lock open retry stranded lock")

            # Lock payload writes must be complete, private and durable before append.
            for fault in ("write-error", "write-short", "write-boolean", "fsync-error"):
                def synthetic_write(fd, payload):
                    if fault == "write-error":
                        raise OSError("PRIVATE_OBJECTIVE_LOCK_INIT_CANARY")
                    if fault == "write-short":
                        return len(payload) - 1
                    if fault == "write-boolean":
                        return True
                    return original_write(fd, payload)

                def synthetic_fsync(fd):
                    if fault == "fsync-error":
                        raise OSError("PRIVATE_OBJECTIVE_LOCK_INIT_CANARY")
                    return original_fsync(fd)

                writer.os.write = synthetic_write
                writer.os.fsync = synthetic_fsync
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(
                        str(exc) == "recovery objectives registry lock initialization failed",
                        "recovery objective lock initialization failure class drift",
                    )
                    require(
                        "PRIVATE_OBJECTIVE_LOCK_INIT_CANARY" not in str(exc),
                        "recovery objective lock initialization leaked private OS diagnostics",
                    )
                    if fault.endswith("error"):
                        require(exc.__suppress_context__,
                                "recovery objective lock OS fault retained private exception context")
                else:
                    raise Fail("recovery objective incomplete lock initialization was accepted")
                finally:
                    writer.os.write = original_write
                    writer.os.fsync = original_fsync
                require(not lock.exists(), "failed objective lock initialization stranded lock")
                require(writer.main() == 0, "recovery objective retry after lock initialization fault failed")
                require(not lock.exists(), "recovery objective lock initialization retry stranded lock")

            # Never unlink a different lock inode or a symlink substituted during append.
            fixture_write = writer.write_registry_transactionally
            for replacement in ("regular", "symlink"):
                def substitute_lock(_registry):
                    lock.unlink()
                    if replacement == "regular":
                        lock.write_text("FOREIGN_OBJECTIVE_LOCK_CANARY\n", encoding="utf-8")
                    else:
                        lock.symlink_to(record_path)

                writer.write_registry_transactionally = substitute_lock
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(
                        str(exc) == "recovery objectives registry lock cleanup failed",
                        "recovery objective foreign lock replacement failure class drift",
                    )
                    require(exc.__suppress_context__,
                            "recovery objective foreign lock replacement exposed exception context")
                else:
                    raise Fail("recovery objective foreign lock replacement was accepted")
                finally:
                    writer.write_registry_transactionally = fixture_write

                if replacement == "regular":
                    require(lock.is_file() and not lock.is_symlink(),
                            "foreign objective regular lock was removed")
                    require(lock.read_text(encoding="utf-8") == "FOREIGN_OBJECTIVE_LOCK_CANARY\n",
                            "foreign objective lock contents changed")
                else:
                    require(lock.is_symlink() and record_path.read_text(encoding="utf-8") == "{}\n",
                            "foreign objective symlink or target was modified")
                lock.unlink()
                require(writer.main() == 0, "recovery objective retry after foreign lock replacement failed")
                require(not lock.exists(), "recovery objective foreign lock retry stranded lock")
        finally:
            writer.REGISTRY = original_registry
            writer.LOCK = original_lock
            writer.load = original_load
            writer.validate_record = original_validate_record
            writer.validate_registry_for_append = original_validate_registry
            writer.write_registry_transactionally = original_write
            writer.approval_sha256 = original_approval_sha256
            writer.require_actual_cli_authorities = original_require_actual
            writer.require_canonical_runtime_authorities = original_require_canonical
            writer.os.close = original_close
            writer.os.open = original_open
            writer.os.write = original_write
            writer.os.fsync = original_fsync
            sys.argv = original_argv


def main() -> int:
    require(WRITER.is_file() and REGISTRY.is_file(), "recovery objective registry foundation missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_writer()
    original_registry = writer.REGISTRY
    original_validator = writer.validate_registry_for_append
    original_replace = writer.os.replace

    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-registry-mode-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            registry_copy = tmp / REGISTRY.name
            shutil.copyfile(REGISTRY, registry_copy)
            os.chmod(registry_copy, 0o640)
            writer.REGISTRY = registry_copy

            baseline = writer.load(registry_copy)
            baseline_bytes = registry_copy.read_bytes()
            baseline_mode = stat.S_IMODE(registry_copy.stat().st_mode)

            # A successful byte-current publication must not relax the canonical mode.
            writer.write_registry_transactionally(copy.deepcopy(baseline))
            require(registry_copy.read_bytes() == baseline_bytes, "byte-current objective publication changed canonical bytes")
            require(stat.S_IMODE(registry_copy.stat().st_mode) == baseline_mode, "successful objective publication changed canonical mode")
            require(not temp_residue(tmp), "successful objective publication left temporary residue")

            # Force the post-publication validator to fail only after candidate bytes exist.
            candidate = copy.deepcopy(baseline)
            candidate["productionReady"] = True
            observed_candidate = False

            def reject_after_publication(value):
                nonlocal observed_candidate
                observed_candidate = registry_copy.read_bytes() != baseline_bytes
                require(observed_candidate, "objective validator failed before candidate publication")
                raise writer.Fail("synthetic objective post-publication rejection")

            writer.validate_registry_for_append = reject_after_publication
            try:
                writer.write_registry_transactionally(candidate)
            except writer.Fail as exc:
                require(
                    str(exc) == "recovery objectives append failed; rollback completed",
                    "objective post-publication rejection did not report completed rollback",
                )
                require(
                    exc.__suppress_context__ and "synthetic objective post-publication rejection" not in str(exc),
                    "objective rollback exposed private validator diagnostics",
                )
            else:
                raise Fail("forced objective post-publication rejection unexpectedly accepted")
            finally:
                writer.validate_registry_for_append = original_validator

            require(observed_candidate, "objective transaction did not publish candidate before validation")
            require(registry_copy.read_bytes() == baseline_bytes, "objective validator failure left registry mutation behind")
            require(stat.S_IMODE(registry_copy.stat().st_mode) == baseline_mode, "objective validator failure changed registry mode")
            require(not temp_residue(tmp), "objective rollback left temporary residue")

            # A failed atomic replace must leave the existing authority untouched and clean its temp file.
            def reject_replace(src, dst) -> None:
                if Path(dst) == registry_copy:
                    raise OSError("synthetic objective replace rejection")
                original_replace(src, dst)

            writer.os.replace = reject_replace
            try:
                writer.write_registry_transactionally(copy.deepcopy(baseline))
            except writer.Fail as exc:
                require(
                    str(exc) == "recovery objective registry atomic write failed",
                    "objective replace rejection did not report private atomic failure",
                )
                require(
                    exc.__suppress_context__ and "synthetic objective replace rejection" not in str(exc),
                    "objective atomic replace exposed private OS diagnostics",
                )
            else:
                raise Fail("forced objective replace rejection unexpectedly accepted")
            finally:
                writer.os.replace = original_replace

            require(registry_copy.read_bytes() == baseline_bytes, "objective replace rejection changed canonical bytes")
            require(stat.S_IMODE(registry_copy.stat().st_mode) == baseline_mode, "objective replace rejection changed canonical mode")
            require(not temp_residue(tmp), "objective replace rejection left temporary residue")
    finally:
        writer.REGISTRY = original_registry
        writer.validate_registry_for_append = original_validator
        writer.os.replace = original_replace

    prove_close_failure_releases_lock(writer)

    print("Recovery objective registry mode negative PASS")
    print("successful publication mode preserved: true")
    print("post-publication validator rollback exact bytes/mode: true")
    print("atomic replace rejection preserves bytes/mode: true")
    print("lock close failure stranded lock: false")
    print("lock close failure retry reacquisition: enforced")
    print("temporary residue: false")
    print("production recovery objective created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE REGISTRY MODE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
