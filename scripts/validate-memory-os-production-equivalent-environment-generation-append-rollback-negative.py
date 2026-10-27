#!/usr/bin/env python3
"""Prove environment-generation registry append rollback is fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def file_mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_append_rollback_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment-generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generation_temp_files(path: Path) -> list[Path]:
    return list(path.parent.glob(".environment-generation*.tmp"))


def prove_strict_generation_json_reader(writer) -> None:
    """Use the real reader to reject ambiguous and unsafe JSON authorities."""
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-json-reader-") as tmp:
        parent = Path(tmp)
        source = parent / "source.json"
        source.write_bytes(json.dumps({"sentinel": "safe"}).encode("utf-8"))
        require(writer.load(source) == {"sentinel": "safe"},
                "environment generation JSON reader positive control failed")

        cases = (
            ("duplicate", b'{"a":1,"a":2}', "environment generation JSON duplicate key refused"),
            ("nonfinite", b'{"a":NaN}', "environment generation JSON nonfinite number refused"),
            ("huge-integer", b'{"a":' + b"9" * 129 + b"}",
             "environment generation JSON integer too large"),
            ("invalid-utf8", bytes([255]), "environment generation JSON unreadable or invalid"),
            ("oversized", b"x" * (writer.MAX_JSON_BYTES + 1),
             "environment generation JSON size limit exceeded"),
            ("array-root", b"[]", "environment generation JSON root must be object"),
        )
        for label, payload, expected in cases:
            source.write_bytes(payload)
            try:
                writer.load(source)
            except writer.Fail as exc:
                require(str(exc) == expected, f"generation JSON {label} wrong rejection class")
            else:
                raise Fail(f"generation JSON {label} unexpectedly accepted")

        canary = parent / "external-canary.json"
        canary.write_bytes(b"PRIVATE_GENERATION_JSON_CANARY")
        alias = parent / "source-alias.json"
        alias.symlink_to(canary)
        try:
            writer.load(alias)
        except writer.Fail as exc:
            require(str(exc) == "environment generation JSON unreadable or invalid"
                    and exc.__suppress_context__,
                    "environment generation JSON symlink failure leaked path diagnostics")
        else:
            raise Fail("environment generation JSON symlink unexpectedly accepted")
        require(canary.read_bytes() == b"PRIVATE_GENERATION_JSON_CANARY",
                "environment generation JSON symlink mutated external canary")

        fifo = parent / "source-fifo.json"
        os.mkfifo(fifo)
        try:
            writer.load(fifo)
        except writer.Fail as exc:
            require(str(exc) == "environment generation JSON path unsafe",
                    "environment generation JSON FIFO wrong rejection class")
        else:
            raise Fail("environment generation JSON FIFO unexpectedly accepted")
    print("PASS reject: strict bounded generation JSON, symlink and FIFO controls")


def prove_bounded_registry_snapshot(writer) -> None:
    """Reject oversized and unsafe registry nodes before any atomic candidate write."""
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-snapshot-") as tmp:
        parent = Path(tmp)
        registry = parent / "generation-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)
        original_registry = writer.REGISTRY
        try:
            writer.REGISTRY = registry
            require(writer.snapshot_registry_for_append() == (original, 0o640),
                    "environment generation pinned snapshot positive control failed")
            registry.write_bytes(b"x" * (writer.MAX_JSON_BYTES + 1))
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "environment generation registry snapshot size limit exceeded",
                        "environment generation oversized snapshot wrong failure class")
            else:
                raise Fail("environment generation oversized snapshot accepted")
            registry.write_bytes(original)

            external = parent / "external-canary.json"
            external.write_bytes(b"PRIVATE_GENERATION_SNAPSHOT_CANARY")
            alias = parent / "registry-alias.json"
            alias.symlink_to(external)
            writer.REGISTRY = alias
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail:
                pass
            else:
                raise Fail("environment generation symlinked snapshot accepted")
            require(external.read_bytes() == b"PRIVATE_GENERATION_SNAPSHOT_CANARY",
                    "environment generation symlink snapshot changed canary")

            fifo = parent / "registry-fifo.json"
            os.mkfifo(fifo)
            writer.REGISTRY = fifo
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "environment generation registry snapshot path unsafe",
                        "environment generation FIFO snapshot wrong failure class")
            else:
                raise Fail("environment generation FIFO snapshot accepted")

            writer.REGISTRY = parent
            try:
                writer.snapshot_registry_for_append()
            except writer.Fail as exc:
                require(str(exc) == "environment generation registry snapshot path unsafe",
                        "environment generation directory snapshot wrong failure class")
            else:
                raise Fail("environment generation directory snapshot accepted")
            writer.REGISTRY = registry
            require(writer.snapshot_registry_for_append() == (original, 0o640),
                    "environment generation snapshot positive control changed")
        finally:
            writer.REGISTRY = original_registry
    print("PASS reject: bounded pinned generation snapshot rejects oversized, symlink, FIFO and directory")


def prove_successful_atomic_write_preserves_mode(writer) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-mode-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        registry.write_bytes(b'{"sentinel":"before"}\n')
        registry.chmod(0o640)
        original_mode = file_mode(registry)
        original_registry = writer.REGISTRY
        writer.REGISTRY = registry
        try:
            writer.atomic_write({"sentinel": "after"}, original_mode)
            require(json.loads(registry.read_text(encoding="utf-8")) == {"sentinel": "after"}, "successful atomic generation append payload drift")
            require(file_mode(registry) == original_mode == 0o640, "successful atomic generation append changed registry mode")
            require(not generation_temp_files(registry), "successful atomic generation append left temporary registry files")
        finally:
            writer.REGISTRY = original_registry
    print("PASS boundary: successful atomic generation append preserves registry mode and leaves no temporary residue")


def prove_atomic_replace_rejection_preserves_registry(writer) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-replace-rejection-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)
        original_mode = file_mode(registry)
        original_registry = writer.REGISTRY
        original_replace = writer.os.replace
        writer.REGISTRY = registry

        def reject_replace(_source, _destination):
            raise OSError("synthetic environment generation append replace rejection")

        writer.os.replace = reject_replace
        try:
            try:
                writer.atomic_write({"sentinel": "after"}, original_mode)
            except OSError as exc:
                require("synthetic environment generation append replace rejection" in str(exc), "unexpected atomic generation append replace failure")
            else:
                raise Fail("atomic generation append replace rejection was accepted")
            require(registry.read_bytes() == original, "failed atomic generation append replace changed registry bytes")
            require(file_mode(registry) == original_mode == 0o640, "failed atomic generation append replace changed registry mode")
            require(not generation_temp_files(registry), "failed atomic generation append replace left temporary registry files")
        finally:
            writer.os.replace = original_replace
            writer.REGISTRY = original_registry
    print("PASS boundary: rejected atomic generation append preserves registry bytes/mode and leaves no temporary residue")


def prove_short_restore_write_rejected(writer) -> None:
    """Exercise the real rollback writer through the canonical CI-reached suite."""
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-short-restore-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)
        original_mode = file_mode(registry)
        original_registry = writer.REGISTRY
        original_fdopen = writer.os.fdopen

        class ShortRestoreHandle:
            def __init__(self, descriptor: int):
                self.source = original_fdopen(descriptor, "wb")

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

        def short_fdopen(descriptor, mode, *args, **kwargs):
            if mode == "wb":
                return ShortRestoreHandle(descriptor)
            return original_fdopen(descriptor, mode, *args, **kwargs)

        writer.REGISTRY = registry
        writer.os.fdopen = short_fdopen
        try:
            try:
                writer.atomic_restore(original, original_mode)
            except writer.Fail as exc:
                require(str(exc) == "environment generation registry atomic restore failed"
                        and exc.__suppress_context__,
                        "environment generation short restore error class or privacy drift")
            else:
                raise Fail("environment generation short restore unexpectedly accepted")
        finally:
            writer.os.fdopen = original_fdopen
            writer.REGISTRY = original_registry
        require(registry.read_bytes() == original,
                "environment generation short restore published truncated bytes")
        require(file_mode(registry) == original_mode == 0o640,
                "environment generation short restore changed registry mode")
        require(not generation_temp_files(registry),
                "environment generation short restore left temporary residue")
    print("PASS reject: short environment-generation rollback write cannot publish")


def prove_post_append_validation_rollback(writer) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-rollback-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)
        registry.chmod(0o640)
        original_mode = file_mode(registry)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        writer.REGISTRY = registry

        def reject_after_write(_value):
            raise writer.Fail("synthetic post-append generation registry validation failure")

        writer.validate_registry_for_append = reject_after_write
        try:
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require(str(exc) == "environment generation append failed; rollback completed"
                        and exc.__suppress_context__,
                        "generation append rollback completed class or privacy drift")
            else:
                raise Fail("post-append generation registry validation failure was accepted")
            require(registry.read_bytes() == original, "failed generation append did not restore original registry bytes")
            require(file_mode(registry) == original_mode == 0o640, "failed generation append did not restore original registry mode")
            leftovers = generation_temp_files(registry)
            require(not leftovers, f"failed generation append left temporary registry files: {leftovers}")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate
    print("PASS rollback: post-append validation failure restores registry byte-for-byte and mode-for-mode")


def prove_post_append_rollback_failure_preserves_diagnostics(writer) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-rollback-diagnostics-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        registry.write_bytes(b'{"sentinel":"before"}\n')
        registry.chmod(0o640)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        original_restore = writer.atomic_restore
        writer.REGISTRY = registry

        def reject_after_write(_value):
            raise writer.Fail("synthetic post-append generation registry validation failure")

        def reject_restore(_payload: bytes, _mode: int) -> None:
            raise OSError("synthetic environment generation rollback restore rejection")

        writer.validate_registry_for_append = reject_after_write
        writer.atomic_restore = reject_restore
        try:
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require(str(exc) == "environment generation append failed; rollback incomplete"
                        and exc.__suppress_context__,
                        "generation append rollback incomplete class or privacy drift")
                require("synthetic" not in str(exc),
                        "generation append rollback leaked private primary or restore details")
            else:
                raise Fail("generation append validation plus rollback failure was accepted")
            require(not generation_temp_files(registry), "rollback diagnostic negative left temporary registry files")
        finally:
            writer.atomic_restore = original_restore
            writer.validate_registry_for_append = original_validate
            writer.REGISTRY = original_registry
    print("PASS diagnostics: generation append rollback uses private fixed completed/incomplete classes")


def prove_failed_registration_releases_lock_for_retry(writer) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-lock-retry-") as tmp:
        temp_root = Path(tmp)
        lock = temp_root / "generation.lock"
        input_record = temp_root / "candidate.json"
        input_record.write_text("{}\n", encoding="utf-8")
        record = {
            "environmentId": "fixture-env-a",
            "generationId": "fixture-gen-a",
        }

        original_lock = writer.LOCK
        original_git = writer.git
        original_require_actual = writer.require_actual_cli_authorities
        original_require_canonical = writer.require_canonical_runtime_authorities
        original_load = writer.load
        original_validate_record = writer.validate_record
        original_validate_registry = writer.validate_registry_for_append
        original_write = writer.write_registry_transactionally
        original_close = writer.os.close
        original_argv = sys.argv[:]

        def fixture_load(path: Path):
            if Path(path) == input_record.resolve():
                return dict(record)
            return {"generations": []}

        def reject_append(_registry):
            raise writer.Fail("synthetic transactional generation append failure")

        writer.LOCK = lock
        writer.git = lambda *_args: ""
        writer.require_actual_cli_authorities = lambda: None
        writer.require_canonical_runtime_authorities = lambda: None
        writer.load = fixture_load
        writer.validate_record = lambda _record: False
        writer.validate_registry_for_append = lambda _registry: []
        writer.write_registry_transactionally = reject_append
        sys.argv = [str(WRITER), "--record", str(input_record)]
        try:
            try:
                writer.main()
            except writer.Fail as exc:
                require("synthetic transactional generation append failure" in str(exc), "unexpected failed registration error")
            else:
                raise Fail("synthetic transactional generation append failure was accepted")
            require(not lock.exists(), "failed generation registration stranded its lock")

            writer.write_registry_transactionally = lambda _registry: None
            require(writer.main() == 0, "generation registration retry did not complete after lock release")
            require(not lock.exists(), "successful generation registration retry stranded its lock")

            def close_then_fail(fd: int) -> None:
                original_close(fd)
                raise OSError("synthetic generation lock close failure")

            writer.os.close = close_then_fail
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "environment generation registry lock cleanup failed"
                            and exc.__suppress_context__,
                            "generation lock close failure leaked private details")
                else:
                    raise Fail("generation lock close failure was accepted")
            finally:
                writer.os.close = original_close
            require(not lock.exists(), "generation lock close failure stranded its lock")
            require(writer.main() == 0, "generation registration retry did not complete after close failure cleanup")
            require(not lock.exists(), "generation registration retry after close failure stranded its lock")

            original_write = writer.os.write
            writer.os.write = lambda *_args: 0
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "environment generation registry lock initialization failed",
                            "environment generation short lock write wrong rejection class")
                else:
                    raise Fail("environment generation short lock write unexpectedly accepted")
            finally:
                writer.os.write = original_write
            require(not lock.exists(), "environment generation short lock write stranded lock")

            original_fsync = writer.os.fsync
            def reject_lock_fsync(*_args):
                raise OSError("PRIVATE_GENERATION_LOCK_FSYNC_CANARY")
            writer.os.fsync = reject_lock_fsync
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "environment generation registry lock initialization failed"
                            and exc.__suppress_context__,
                            "environment generation lock fsync leaked private details")
                else:
                    raise Fail("environment generation lock fsync failure unexpectedly accepted")
            finally:
                writer.os.fsync = original_fsync
            require(not lock.exists(), "environment generation lock fsync stranded lock")

            original_open = writer.os.open
            def reject_lock_open(path, *args, **kwargs):
                if Path(path) == lock:
                    raise OSError("PRIVATE_GENERATION_LOCK_OPEN_CANARY")
                return original_open(path, *args, **kwargs)
            writer.os.open = reject_lock_open
            try:
                try:
                    writer.main()
                except writer.Fail as exc:
                    require(str(exc) == "environment generation registry lock acquisition failed"
                            and exc.__suppress_context__,
                            "environment generation lock acquisition leaked private details")
                else:
                    raise Fail("environment generation lock acquisition failure unexpectedly accepted")
            finally:
                writer.os.open = original_open
            require(not lock.exists(), "environment generation lock acquisition stranded lock")

            lock.write_bytes(b"existing-owner\n")
            lock.chmod(0o600)
            existing = lock.read_bytes()
            existing_mode = file_mode(lock)
            try:
                writer.main()
            except writer.Fail as exc:
                require("registry lock already exists" in str(exc), "unexpected existing-lock rejection")
            else:
                raise Fail("existing generation registry lock was accepted")
            require(lock.read_bytes() == existing, "existing generation registry lock bytes were changed")
            require(file_mode(lock) == existing_mode == 0o600, "existing generation registry lock mode was changed")
        finally:
            writer.os.close = original_close
            writer.LOCK = original_lock
            writer.git = original_git
            writer.require_actual_cli_authorities = original_require_actual
            writer.require_canonical_runtime_authorities = original_require_canonical
            writer.load = original_load
            writer.validate_record = original_validate_record
            writer.validate_registry_for_append = original_validate_registry
            writer.write_registry_transactionally = original_write
            sys.argv = original_argv
    print("PASS lock: failed registration and close failures release the lock, retries can reacquire it, and foreign locks remain untouched")


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "environment-generation append authority missing")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("bindingRules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "transactional generation append contract guard missing",
    )

    writer = load_writer()
    require(callable(getattr(writer, "write_registry_transactionally", None)), "transactional generation registry writer missing")
    require(callable(getattr(writer, "atomic_write", None)), "atomic generation registry writer missing")

    prove_strict_generation_json_reader(writer)
    prove_bounded_registry_snapshot(writer)
    prove_successful_atomic_write_preserves_mode(writer)
    prove_atomic_replace_rejection_preserves_registry(writer)
    prove_short_restore_write_rejected(writer)
    prove_post_append_validation_rollback(writer)
    prove_post_append_rollback_failure_preserves_diagnostics(writer)
    prove_failed_registration_releases_lock_for_retry(writer)

    print("Memory OS environment generation append rollback negative PASS")
    print("successful atomic append registry mode preservation: enforced")
    print("atomic append replace rejection preserves registry: byte-for-byte and mode-for-mode")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte and mode-for-mode")
    print("failed append primary validation diagnostic preservation: enforced")
    print("failed append rollback diagnostic preservation: enforced")
    print("failed append temporary registry residue: false")
    print("failed registration lock stranded: false")
    print("failed registration close-failure lock stranded: false")
    print("failed registration retry lock reacquisition: enforced")
    print("foreign generation registry lock preservation: enforced")
    print("generation created: false")
    print("production evidence: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION APPEND ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
