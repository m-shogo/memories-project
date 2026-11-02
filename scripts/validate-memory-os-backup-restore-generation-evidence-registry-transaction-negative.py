#!/usr/bin/env python3
"""Prove generation-evidence registry publication preserves authority bytes and mode."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
MAX_WRITER_SOURCE_BYTES = 1024 * 1024


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_writer_identity() -> None:
    require(WRITER == ROOT / WRITER_REL and WRITER.is_file()
            and not WRITER.is_symlink()
            and WRITER.resolve(strict=True) == WRITER,
            "generation evidence transaction writer source authority drift")


def pinned_writer_source() -> bytes:
    """Import only verified bytes from owned directory and source descriptors."""
    require_writer_identity()
    require(all(type(getattr(os, name, None)) is int and getattr(os, name) > 0
                for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")),
            "generation evidence transaction writer pinned import unavailable")
    owned: list[int] = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(ROOT, directory_flags)
        require(type(parent_fd) is int and parent_fd >= 0,
                "generation evidence transaction writer parent descriptor invalid")
        owned.append(parent_fd)
        for part in WRITER_REL.parts[:-1]:
            parent_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            require(type(parent_fd) is int and parent_fd >= 0,
                    "generation evidence transaction writer parent descriptor invalid")
            owned.append(parent_fd)
        parents_before = [os.fstat(fd) for fd in owned]
        parent_identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_ctime_ns
        )
        require(all(stat.S_ISDIR(item.st_mode) and not (item.st_mode & 0o022)
                    for item in parents_before),
                "generation evidence transaction writer parent unsafe")
        source_fd = os.open(
            WRITER_REL.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent_fd,
        )
        require(type(source_fd) is int and source_fd >= 0,
                "generation evidence transaction writer source descriptor invalid")
        owned.append(source_fd)
        before = os.fstat(source_fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and not (before.st_mode & 0o022)
                and 0 < before.st_size <= MAX_WRITER_SOURCE_BYTES,
                "generation evidence transaction writer source metadata unsafe")
        chunks: list[bytes] = []
        remaining = MAX_WRITER_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, remaining)
            require(type(chunk) is bytes,
                    "generation evidence transaction writer read type invalid")
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(source_fd)
        leaf = os.stat(WRITER_REL.name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_mode, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns
        )
        require(len(source) == before.st_size
                and len(source) <= MAX_WRITER_SOURCE_BYTES
                and identity(before) == identity(after) == identity(leaf),
                "generation evidence transaction writer source changed during read")
        for index, fd in enumerate(owned[:-1]):
            current = os.fstat(fd)
            lexical = ROOT if index == 0 else ROOT.joinpath(*WRITER_REL.parts[:index])
            visible = os.lstat(lexical)
            require(stat.S_ISDIR(visible.st_mode)
                    and parent_identity(parents_before[index])
                    == parent_identity(current) == parent_identity(visible),
                    "generation evidence transaction writer parent changed during read")
        require_writer_identity()
        require(identity(WRITER.stat()) == identity(after),
                "generation evidence transaction writer pathname changed during read")
        return source
    except OSError:
        raise Fail("generation evidence transaction writer pinned source unreadable") from None
    finally:
        primary = sys.exc_info()[0] is not None
        cleanup_failed = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except Exception:
                cleanup_failed = True
        if cleanup_failed and not primary:
            raise Fail("generation evidence transaction writer descriptor cleanup failed") from None


def load_writer() -> Any:
    source = pinned_writer_source()
    spec = importlib.util.spec_from_file_location(
        "memory_os_generation_evidence_registry_transaction_negative", WRITER,
    )
    require(spec is not None and spec.loader is not None,
            "cannot load generation evidence writer")
    module = importlib.util.module_from_spec(spec)
    # Do not let SourceFileLoader reopen a pathname after source verification.
    exec(compile(source, str(WRITER), "exec"), module.__dict__)
    return module


def prove_pinned_writer_import() -> None:
    """Prove an after-capture parent swap cannot execute redirected writer code."""
    global ROOT, WRITER
    original_root, original_writer = ROOT, WRITER
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-transaction-import-") as raw:
        fixture = Path(raw)
        parent = fixture / "scripts"
        parent.mkdir()
        source = parent / WRITER_REL.name
        source.write_text("SOURCE_MARKER = 'reviewed'\n", encoding="utf-8")
        redirected = fixture / "redirected"
        redirected.mkdir()
        canary = redirected / source.name
        canary_bytes = b"raise RuntimeError('PRIVATE_GENERATION_WRITER_IMPORT_CANARY')\n"
        canary.write_bytes(canary_bytes)
        parked = fixture / "parked-scripts"
        ROOT, WRITER = fixture, source
        try:
            require(load_writer().SOURCE_MARKER == "reviewed",
                    "generation transaction pinned writer positive control failed")
            # ROOT, scripts ancestor, and leaf are exactly three os.open calls.
            # Never derive an injection ordinal from absolute path depth.
            for ordinal in (1, 2, 3):
                for invalid in (None, True, -1, "7"):
                    original_open, original_close = os.open, os.close
                    acquired: list[int] = []
                    closed: list[int] = []
                    call_count = 0

                    def invalid_acquisition(path, flags, *args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        if call_count == ordinal:
                            return invalid
                        descriptor = original_open(path, flags, *args, **kwargs)
                        acquired.append(descriptor)
                        return descriptor

                    def observe_close(descriptor: int) -> None:
                        closed.append(descriptor)
                        original_close(descriptor)

                    os.open, os.close = invalid_acquisition, observe_close
                    try:
                        try:
                            load_writer()
                        except Fail as exc:
                            require("descriptor invalid" in str(exc),
                                    "generation transaction invalid acquired FD wrong rejection")
                        else:
                            raise Fail("generation transaction accepted invalid acquired FD")
                    finally:
                        os.open, os.close = original_open, original_close
                    require(call_count == ordinal,
                            "generation transaction invalid FD fixture acquisition order drift")
                    require(closed == list(reversed(acquired)),
                            "generation transaction invalid FD ownership/cleanup drift")
            for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
                original_flag = getattr(os, flag)
                setattr(os, flag, 0)
                try:
                    try:
                        load_writer()
                    except Fail as exc:
                        require(str(exc) == "generation evidence transaction writer pinned import unavailable",
                                "generation transaction zeroed " + flag + " rejected at wrong boundary")
                    else:
                        raise Fail("generation transaction accepted zeroed " + flag)
                finally:
                    setattr(os, flag, original_flag)
            source.chmod(0o666)
            try:
                load_writer()
            except Fail as exc:
                require(str(exc) == "generation evidence transaction writer source metadata unsafe",
                        "writable generation transaction writer rejected at wrong boundary")
            else:
                raise Fail("writable generation transaction writer accepted")
            source.chmod(0o644)
            alias = fixture / "hardlink-transaction-writer.py"
            os.link(source, alias)
            try:
                try:
                    load_writer()
                except Fail as exc:
                    require(str(exc) == "generation evidence transaction writer source metadata unsafe",
                            "hardlinked generation transaction writer wrong rejection")
                else:
                    raise Fail("hardlinked generation transaction writer accepted")
            finally:
                alias.unlink()

            def expect_mid_read_chmod(path: Path, unsafe_mode: int, safe_mode: int,
                                      expected: str, label: str) -> None:
                original_read = os.read
                mutated = False

                def read_then_chmod(fd: int, count: int) -> bytes:
                    nonlocal mutated
                    chunk = original_read(fd, count)
                    if not mutated:
                        path.chmod(unsafe_mode)
                        mutated = True
                    return chunk

                os.read = read_then_chmod
                try:
                    try:
                        load_writer()
                    except Fail as exc:
                        require(str(exc) == expected, label + " wrong rejection")
                    else:
                        raise Fail(label + " accepted")
                finally:
                    os.read = original_read
                    path.chmod(safe_mode)
                require(mutated, label + " fixture was inert")

            expect_mid_read_chmod(
                source, 0o666, 0o644,
                "generation evidence transaction writer source changed during read",
                "mid-read writable generation transaction writer",
            )
            expect_mid_read_chmod(
                parent, 0o777, 0o755,
                "generation evidence transaction writer parent changed during read",
                "mid-read writable generation transaction parent",
            )
            parent.rename(parked)
            parent.symlink_to(redirected, target_is_directory=True)
            try:
                load_writer()
            except Fail:
                pass
            else:
                raise Fail("symlinked generation transaction writer parent accepted")
            parent.unlink()
            parked.rename(parent)

            swapped = False

            def swap_after_capture(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == source:
                    swapped = True
                    parent.rename(parked)
                    parent.symlink_to(redirected, target_is_directory=True)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_after_capture
            loaded = load_writer()
            require(swapped and loaded.SOURCE_MARKER == "reviewed",
                    "generation transaction imported redirected writer source")
            require(canary.read_bytes() == canary_bytes,
                    "generation transaction redirected writer canary changed")
        finally:
            importlib.util.spec_from_file_location = original_spec
            ROOT, WRITER = original_root, original_writer
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
    print("PASS: generation transaction writer pinned source rejects hardlinks, mid-read chmod and swaps")



def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def residue(directory: Path) -> list[Path]:
    return sorted(
        list(directory.glob(".backup-restore-generation.*.tmp"))
        + list(directory.glob(".backup-restore-generation-rollback.*.tmp"))
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prove_close_failure_releases_lock(writer: Any) -> None:
    original_registry = writer.REGISTRY
    original_lock = writer.LOCK
    original_load = writer.load
    original_validate_record = writer.validate_record
    original_validate_registry = writer.validate_registry_for_append
    original_write = writer.write_registry_transactionally
    original_require_cli = writer.require_cli_authorities
    original_git = writer.git
    original_drill_current = writer.drill_request_current
    original_base_candidate = writer.base_candidate
    original_typed_covered = writer.typed_non_resurrection_covered
    original_candidate = writer.candidate
    original_close = writer.os.close
    original_open = writer.os.open
    original_write_fd = writer.os.write
    original_fsync = writer.os.fsync
    original_argv = sys.argv[:]

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-evidence-lock-") as raw_tmp:
        directory = Path(raw_tmp)
        registry = directory / "generation-evidence-registry.json"
        lock = directory / ".backup-restore-generation-evidence.lock"
        record_path = directory / "generation-evidence.json"
        record_path.write_text("{}\n", encoding="utf-8")
        record = {
            "evidenceId": "brge_fixture_close01",
            "drillRequestId": "brrq_fixture_close01",
            "evidenceComplete": False,
            "isolatedRestoreVerified": False,
            "restoredBackupArtifactSha256": "0" * 64,
            "backupArtifactSha256": "0" * 64,
        }
        registry_state: dict[str, Any] = {"records": []}

        def fixture_load(path: Path) -> dict[str, Any]:
            if Path(path) == record_path:
                return record
            if Path(path) == registry:
                return registry_state
            return original_load(path)

        try:
            writer.REGISTRY = registry
            writer.LOCK = lock
            writer.load = fixture_load
            writer.validate_record = lambda _record, require_current_drill_request=True: None
            writer.validate_registry_for_append = lambda value: value["records"]
            writer.write_registry_transactionally = lambda _value: None
            writer.require_cli_authorities = lambda: None
            writer.git = lambda *_args: ""
            writer.drill_request_current = lambda _record: False
            writer.base_candidate = lambda _record: False
            writer.typed_non_resurrection_covered = lambda _evidence_id: False
            writer.candidate = lambda _record: False
            sys.argv = [str(WRITER), "--record", str(record_path)]

            def close_then_fail(fd: int) -> None:
                original_close(fd)
                raise OSError("synthetic generation evidence lock close failure")

            writer.os.close = close_then_fail
            try:
                writer.main()
            except writer.Fail as exc:
                require(str(exc) == "generation evidence registry lock cleanup failed"
                        and exc.__suppress_context__,
                        "generation evidence close failure leaked private exception")
            else:
                raise Fail("generation evidence lock close failure was accepted")
            finally:
                writer.os.close = original_close

            require(not lock.exists(), "generation evidence close failure stranded its lock")
            registry_state["records"].clear()
            require(writer.main() == 0, "generation evidence retry did not complete after close failure cleanup")
            require(not lock.exists(), "generation evidence retry stranded its lock")
            registry_state["records"].clear()

            writer.os.write = lambda *_args: 0
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "generation evidence registry lock initialization failed",
                            "generation evidence short lock write rejected at wrong boundary")
                else:
                    raise Fail("generation evidence short lock write accepted")
            finally:
                writer.os.write = original_write_fd
            require(not lock.exists(), "generation evidence short lock write stranded lock")

            def reject_lock_fsync(*_args):
                raise OSError("PRIVATE_GENERATION_LOCK_CANARY fsync")
            writer.os.fsync = reject_lock_fsync
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "generation evidence registry lock initialization failed"
                            and exc.__suppress_context__,
                            "generation evidence fsync failure leaked private exception")
                else:
                    raise Fail("generation evidence lock fsync failure accepted")
            finally:
                writer.os.fsync = original_fsync
            require(not lock.exists(), "generation evidence lock fsync failure stranded lock")
            def reject_lock_open(path, flags, mode=0o600):
                if Path(path) == lock:
                    raise OSError("PRIVATE_GENERATION_LOCK_CANARY open")
                return original_open(path, flags, mode)
            writer.os.open = reject_lock_open
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "generation evidence registry lock acquisition failed"
                            and exc.__suppress_context__,
                            "generation evidence lock acquisition leaked private exception")
                else:
                    raise Fail("generation evidence lock acquisition failure accepted")
            finally:
                writer.os.open = original_open
            require(not lock.exists(), "generation evidence lock acquisition failure stranded lock")
            require(writer.main() == 0, "generation evidence lock retry failed after init errors")
            require(not lock.exists(), "generation evidence lock retry stranded lock")
            print("PASS reject: generation lock close, short-write and fsync failures preserve private classes and retry")
        finally:
            writer.REGISTRY = original_registry
            writer.LOCK = original_lock
            writer.load = original_load
            writer.validate_record = original_validate_record
            writer.validate_registry_for_append = original_validate_registry
            writer.write_registry_transactionally = original_write
            writer.require_cli_authorities = original_require_cli
            writer.git = original_git
            writer.drill_request_current = original_drill_current
            writer.base_candidate = original_base_candidate
            writer.typed_non_resurrection_covered = original_typed_covered
            writer.candidate = original_candidate
            writer.os.close = original_close
            writer.os.open = original_open
            writer.os.write = original_write_fd
            writer.os.fsync = original_fsync
            sys.argv = original_argv


def prove_pinned_registry_snapshot(writer: Any) -> None:
    """Exercise the actual writer snapshot against disposable regular and special files."""
    original_registry = writer.REGISTRY
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-snapshot-negative-") as raw:
        parent = Path(raw)
        registry = parent / "registry.json"
        registry.write_bytes(b'{"records": []}\n')
        registry.chmod(0o640)
        expected = registry.read_bytes()
        try:
            writer.REGISTRY = registry
            require(writer.snapshot_registry_for_append() == (expected, 0o640),
                    "generation registry descriptor snapshot positive control failed")
            registry.write_bytes(b"x" * (writer.MAX_JSON_BYTES + 1))
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "generation evidence registry snapshot size limit exceeded",
                        "oversized generation registry rejected at wrong boundary")
            else:
                raise Fail("oversized generation registry snapshot accepted")
            registry.write_bytes(expected)
            registry.chmod(0o640)

            canary = parent / "outside-canary.json"
            canary.write_bytes(b"PRIVATE_GENERATION_SNAPSHOT_CANARY")
            alias = parent / "registry-alias.json"
            alias.symlink_to(canary)
            writer.REGISTRY = alias
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "cannot snapshot generation evidence registry before append",
                        "generation registry symlink rejected at wrong boundary")
            else:
                raise Fail("generation registry symlink snapshot accepted")
            require(canary.read_bytes() == b"PRIVATE_GENERATION_SNAPSHOT_CANARY",
                    "generation registry symlink negative changed external canary")

            fifo = parent / "registry-fifo.json"
            os.mkfifo(fifo)
            writer.REGISTRY = fifo
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "generation evidence registry snapshot path unsafe",
                        "generation registry FIFO rejected at wrong boundary")
            else:
                raise Fail("generation registry FIFO snapshot accepted")

            writer.REGISTRY = parent
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) in {
                    "generation evidence registry snapshot path unsafe",
                    "cannot snapshot generation evidence registry before append",
                }, "generation registry directory rejected at wrong boundary")
            else:
                raise Fail("generation registry directory snapshot accepted")
            writer.REGISTRY = registry
            require(writer.snapshot_registry_for_append() == (expected, 0o640),
                    "generation registry snapshot changed after negative controls")
            require(registry.read_bytes() == expected and mode(registry) == 0o640,
                    "generation registry snapshot changed fixture bytes or mode")
            require(not residue(parent), "generation snapshot left temporary publication residue")
        finally:
            writer.REGISTRY = original_registry
    print("PASS reject: generation registry pinned bounded snapshot, symlink, FIFO and directory")


def main() -> int:
    require(WRITER.is_file(), "generation evidence writer missing")
    prove_pinned_writer_import()
    writer = load_writer()

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-evidence-registry-transaction-") as raw_tmp:
        directory = Path(raw_tmp)
        registry = directory / "generation-evidence-registry.json"
        original_value = {"sentinel": "original authority bytes"}
        candidate_value = {"sentinel": "candidate authority bytes"}
        write_json(registry, original_value)
        registry.chmod(0o640)
        original_bytes = registry.read_bytes()
        original_mode = mode(registry)
        require(original_mode == 0o640, "test fixture mode setup failed")

        original_registry = writer.REGISTRY
        original_validator = writer.validate_registry_for_append
        original_replace = writer.os.replace
        try:
            writer.REGISTRY = registry
            writer.validate_registry_for_append = lambda _value: []
            writer.write_registry_transactionally(candidate_value)
            require(mode(registry) == original_mode, "successful generation evidence append changed registry mode")
            require(not residue(directory), "successful generation evidence append left temp residue")
            print("PASS preserve: successful generation evidence append retained registry mode")

            registry.write_bytes(original_bytes)
            registry.chmod(original_mode)
            writer.validate_registry_for_append = lambda _value: (_ for _ in ()).throw(
                writer.Fail("synthetic post-append validation failure")
            )
            try:
                writer.write_registry_transactionally(candidate_value)
            except writer.Fail as exc:
                require(str(exc) == "generation evidence append failed; rollback completed"
                        and exc.__suppress_context__,
                        "generation evidence post-append rollback leaked primary diagnostic")
            else:
                raise Fail("post-append validation failure unexpectedly accepted")
            require(registry.read_bytes() == original_bytes, "post-append rejection changed generation evidence registry bytes")
            require(mode(registry) == original_mode, "post-append rejection changed generation evidence registry mode")
            require(not residue(directory), "post-append rollback left generation evidence temp residue")
            print("PASS preserve: post-append rejection restored generation evidence bytes and mode")

            registry.write_bytes(original_bytes)
            registry.chmod(original_mode)
            writer.validate_registry_for_append = lambda _value: []

            def reject_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
                if Path(destination) == registry and Path(source).name.startswith(".backup-restore-generation."):
                    raise OSError("synthetic generation evidence replace rejection")
                original_replace(source, destination)

            writer.os.replace = reject_replace
            try:
                writer.write_registry_transactionally(candidate_value)
            except writer.Fail as exc:
                require(str(exc) == "generation evidence registry atomic write failed"
                        and exc.__suppress_context__,
                        "generation evidence replace rejection leaked private details")
            else:
                raise Fail("generation evidence candidate replace rejection unexpectedly accepted")
            require(registry.read_bytes() == original_bytes, "replace rejection changed generation evidence registry bytes")
            require(mode(registry) == original_mode, "replace rejection changed generation evidence registry mode")
            require(not residue(directory), "replace rejection left generation evidence temp residue")
            print("PASS preserve: replace rejection left generation evidence bytes and mode unchanged")
            writer.os.replace = original_replace

            def expect_private(label: str, action, expected: str) -> None:
                try:
                    action()
                except writer.Fail as exc:
                    require(str(exc) == expected and exc.__suppress_context__,
                            f"{label} leaked raw error or wrong failure class")
                    require("PRIVATE_GENERATION_ATOMIC_CANARY" not in str(exc),
                            f"{label} leaked private canary")
                else:
                    raise Fail(f"{label} unexpectedly accepted")
                require(registry.read_bytes() == original_bytes and mode(registry) == original_mode,
                        f"{label} changed registry bytes or mode")
                require(not residue(directory), f"{label} left temporary file residue")
                print(f"PASS reject: {label}")

            original_mkstemp = writer.tempfile.mkstemp
            def reject_mkstemp(*_args, **_kwargs):
                raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY mkstemp")
            writer.tempfile.mkstemp = reject_mkstemp
            try:
                expect_private("generation atomic mkstemp failure",
                               lambda: writer.atomic_write(candidate_value, original_mode),
                               "generation evidence registry atomic write failed")
            finally:
                writer.tempfile.mkstemp = original_mkstemp

            original_fdopen = writer.os.fdopen
            captured_fd: int | None = None
            def capture_mkstemp(*args, **kwargs):
                nonlocal captured_fd
                captured_fd, name = original_mkstemp(*args, **kwargs)
                return captured_fd, name
            def reject_fdopen(*_args, **_kwargs):
                raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY fdopen")
            writer.tempfile.mkstemp = capture_mkstemp
            writer.os.fdopen = reject_fdopen
            try:
                expect_private("generation atomic fdopen failure",
                               lambda: writer.atomic_write(candidate_value, original_mode),
                               "generation evidence registry atomic write failed")
            finally:
                writer.os.fdopen = original_fdopen
                writer.tempfile.mkstemp = original_mkstemp
            require(captured_fd is not None, "generation fdopen negative did not create descriptor")
            try:
                os.fstat(captured_fd)
            except OSError:
                pass
            else:
                raise Fail("generation fdopen failure leaked descriptor")

            original_fchmod = writer.os.fchmod
            def reject_fchmod(*_args, **_kwargs):
                raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY fchmod")
            writer.os.fchmod = reject_fchmod
            try:
                expect_private("generation atomic fchmod failure",
                               lambda: writer.atomic_write(candidate_value, original_mode),
                               "generation evidence registry atomic write failed")
            finally:
                writer.os.fchmod = original_fchmod

            def reject_restore_replace(*_args, **_kwargs):
                raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY restore replace")
            writer.os.replace = reject_restore_replace
            try:
                expect_private("generation atomic restore replace failure",
                               lambda: writer.atomic_restore(original_bytes, original_mode),
                               "generation evidence registry atomic restore failed")
            finally:
                writer.os.replace = original_replace

            # A partial buffered rollback write cannot be reported as restored.
            original_restore_fdopen = writer.os.fdopen

            class ShortRestoreHandle:
                def __init__(self, descriptor: int):
                    self.source = original_restore_fdopen(descriptor, "wb")

                def __enter__(self):
                    self.source.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.source.__exit__(*args)

                def fileno(self):
                    return self.source.fileno()

                def write(self, payload: bytes) -> int:
                    short_count = max(1, len(payload) // 2)
                    self.source.write(payload[:short_count])
                    return short_count

                def flush(self) -> None:
                    self.source.flush()

            def short_restore_fdopen(descriptor, mode, *args, **kwargs):
                if mode == "wb":
                    return ShortRestoreHandle(descriptor)
                return original_restore_fdopen(descriptor, mode, *args, **kwargs)

            writer.os.fdopen = short_restore_fdopen
            try:
                expect_private("generation atomic short rollback write",
                               lambda: writer.atomic_restore(original_bytes, original_mode),
                               "generation evidence registry atomic restore failed")
            finally:
                writer.os.fdopen = original_restore_fdopen

            # Cleanup failure must be classified privately after removing its owned temp.
            original_unlink = writer.os.unlink
            def unlink_then_fail(path, *args, **kwargs):
                original_unlink(path, *args, **kwargs)
                raise OSError("PRIVATE_GENERATION_ATOMIC_CANARY unlink")
            writer.os.replace = reject_restore_replace
            writer.os.unlink = unlink_then_fail
            try:
                expect_private("generation atomic temporary cleanup failure",
                               lambda: writer.atomic_write(candidate_value, original_mode),
                               "generation evidence registry temporary cleanup failed")
            finally:
                writer.os.unlink = original_unlink
                writer.os.replace = original_replace
        finally:
            writer.os.replace = original_replace
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator

    prove_pinned_registry_snapshot(writer)
    prove_close_failure_releases_lock(writer)

    print("generation evidence registry transaction negative PASS")
    print("successful append registry mode preservation: enforced")
    print("post-append rollback: byte-for-byte and mode-preserving")
    print("replace rejection registry bytes/mode preservation: enforced")
    print("lock close failure stranded lock: false")
    print("lock close failure retry reacquisition: enforced")
    print("temporary registry residue: none")
    print("production evidence created: false")
    print("production readiness changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE REGISTRY TRANSACTION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
