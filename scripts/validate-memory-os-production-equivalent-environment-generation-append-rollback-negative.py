#!/usr/bin/env python3
"""Prove environment-generation registry append rollback is fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
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
                require("synthetic post-append" in str(exc), "unexpected transactional generation append failure")
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

    prove_successful_atomic_write_preserves_mode(writer)
    prove_atomic_replace_rejection_preserves_registry(writer)
    prove_post_append_validation_rollback(writer)

    print("Memory OS environment generation append rollback negative PASS")
    print("successful atomic append registry mode preservation: enforced")
    print("atomic append replace rejection preserves registry: byte-for-byte and mode-for-mode")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte and mode-for-mode")
    print("failed append temporary registry residue: false")
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
