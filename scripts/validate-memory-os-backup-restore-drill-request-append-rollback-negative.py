#!/usr/bin/env python3
"""Prove backup/restore drill request registry append rollback is fail-closed."""

from __future__ import annotations

import importlib.util
import json
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
        registry.write_bytes(original)

        original_registry = writer.REGISTRY
        original_validate = writer.validate_registry_for_append
        writer.REGISTRY = registry

        def reject_after_write(_value):
            raise writer.Fail("synthetic post-append drill request registry validation failure")

        writer.validate_registry_for_append = reject_after_write
        try:
            try:
                writer.write_registry_transactionally({"sentinel": "after"})
            except writer.Fail as exc:
                require("synthetic post-append" in str(exc), "unexpected transactional drill request append failure")
            else:
                raise Fail("post-append drill request registry validation failure was accepted")
            require(registry.read_bytes() == original, "failed drill request append did not restore original registry bytes")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    print("Memory OS backup/restore drill request append rollback negative PASS")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte")
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
