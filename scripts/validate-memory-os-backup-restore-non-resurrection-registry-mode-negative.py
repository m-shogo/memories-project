#!/usr/bin/env python3
"""Verify typed non-resurrection registry publication preserves mode and lock cleanup."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_registry_mode_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def prove_close_failure_releases_lock(writer) -> None:
    original_lock = writer.LOCK
    original_require_cli_authorities = writer.require_cli_authorities
    original_load = writer.load
    original_validate_record = writer.validate_record
    original_write = writer.os.write
    original_close = writer.os.close
    original_argv = sys.argv[:]

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-lock-") as tmp:
        lock = Path(tmp) / ".backup-restore-non-resurrection-admission.lock"
        input_path = Path(tempfile.gettempdir()) / "memory-os-non-resurrection-lock-close-failure.json"
        writer.LOCK = lock
        writer.require_cli_authorities = lambda: None
        writer.load = lambda _: {"recordId": "brnr_lock_cleanup_negative"}
        writer.validate_record = lambda _: None

        def reject_body_write(*_args) -> int:
            raise RuntimeError("synthetic non-resurrection body failure")

        def close_then_fail(fd: int) -> None:
            original_close(fd)
            raise OSError("synthetic non-resurrection lock close failure")

        writer.os.write = reject_body_write
        writer.os.close = close_then_fail
        sys.argv = [str(WRITER), "--record", str(input_path)]
        try:
            try:
                writer.main()
            except OSError as exc:
                require("synthetic non-resurrection lock close failure" in str(exc), f"unexpected close failure: {exc}")
            else:
                raise Fail("synthetic non-resurrection lock close failure unexpectedly accepted")
            require(not lock.exists(), "typed non-resurrection lock stranded after close failure")

            writer.os.close = original_close
            retry_fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(retry_fd)
            lock.unlink()
            require(not lock.exists(), "typed non-resurrection lock retry cleanup failed")
            print("PASS cleanup: close failure still unlinks typed non-resurrection lock and permits immediate reacquisition")
        finally:
            writer.LOCK = original_lock
            writer.require_cli_authorities = original_require_cli_authorities
            writer.load = original_load
            writer.validate_record = original_validate_record
            writer.os.write = original_write
            writer.os.close = original_close
            sys.argv = original_argv


def main() -> int:
    writer = load_writer()
    original_registry = writer.REGISTRY
    original_validate = writer.validate_registry_for_append

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-mode-") as tmp:
        registry = Path(tmp) / "typed-registry.json"
        initial = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 0,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        }
        registry.write_text(json.dumps(initial, indent=2) + "\n", encoding="utf-8")
        registry.chmod(0o640)
        writer.REGISTRY = registry

        try:
            writer.validate_registry_for_append = lambda value: []
            success_candidate = dict(initial)
            writer.write_registry_transactionally(success_candidate)
            require(mode(registry) == 0o640, "successful typed registry publication changed permission mode")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection.*.tmp")), "successful publication left temporary files")
            print("PASS preserve: successful typed registry publication preserves 0640 mode and leaves no temp files")

            before = registry.read_bytes()
            before_mode = mode(registry)

            def reject_after_write(value):
                raise writer.Fail("synthetic typed post-write validator failure")

            writer.validate_registry_for_append = reject_after_write
            failed_candidate = dict(initial)
            failed_candidate["productionReady"] = True
            try:
                writer.write_registry_transactionally(failed_candidate)
            except writer.Fail:
                pass
            else:
                raise Fail("synthetic post-write validator failure unexpectedly accepted")

            require(registry.read_bytes() == before, "typed registry rollback did not restore exact bytes")
            require(mode(registry) == before_mode == 0o640, "typed registry rollback did not restore original permission mode")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection.*.tmp")), "rollback left temporary publication files")
            require(not list(registry.parent.glob(".backup-restore-non-resurrection-rollback.*.tmp")), "rollback left temporary restore files")
            print("PASS preserve: rejected typed registry publication restores exact bytes and 0640 mode")
            print("PASS cleanup: typed registry publication and rollback leave no temporary residue")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    prove_close_failure_releases_lock(writer)
    print("canonical registries mutated: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
