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


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_registry_transaction_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            except OSError as exc:
                require(
                    "synthetic generation evidence lock close failure" in str(exc),
                    f"unexpected generation evidence close failure: {exc}",
                )
            else:
                raise Fail("generation evidence lock close failure was accepted")
            finally:
                writer.os.close = original_close

            require(not lock.exists(), "generation evidence close failure stranded its lock")
            registry_state["records"].clear()
            require(writer.main() == 0, "generation evidence retry did not complete after close failure cleanup")
            require(not lock.exists(), "generation evidence retry stranded its lock")
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
            sys.argv = original_argv


def main() -> int:
    require(WRITER.is_file(), "generation evidence writer missing")
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
            except writer.Fail:
                pass
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
            except OSError as exc:
                require("synthetic generation evidence replace rejection" in str(exc), "replace rejection failed at wrong boundary")
            else:
                raise Fail("generation evidence candidate replace rejection unexpectedly accepted")
            require(registry.read_bytes() == original_bytes, "replace rejection changed generation evidence registry bytes")
            require(mode(registry) == original_mode, "replace rejection changed generation evidence registry mode")
            require(not residue(directory), "replace rejection left generation evidence temp residue")
            print("PASS preserve: replace rejection left generation evidence bytes and mode unchanged")
        finally:
            writer.os.replace = original_replace
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator

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
