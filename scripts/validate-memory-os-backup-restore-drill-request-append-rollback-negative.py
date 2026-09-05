#!/usr/bin/env python3
"""Prove backup/restore drill request registry append rollback is fail-closed."""

from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_drill_request_append_rollback_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load backup/restore drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def require_no_temp_residue(path: Path) -> None:
    residue = list(path.parent.glob(".backup-restore-drill-request*.tmp"))
    require(not residue, f"drill request registry temp residue remained: {[item.name for item in residue]}")


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "drill request append authority missing")
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
        finally:
            writer.os.replace = original_replace
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    print("Memory OS backup/restore drill request append rollback negative PASS")
    print("successful append registry mode preservation: enforced")
    print("replace rejection registry bytes/mode preservation: enforced")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte and mode-preserving")
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
        print(f"BACKUP RESTORE DRILL REQUEST APPEND ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
