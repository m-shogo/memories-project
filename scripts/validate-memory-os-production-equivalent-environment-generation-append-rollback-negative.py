#!/usr/bin/env python3
"""Prove environment-generation registry append rollback is fail-closed."""

from __future__ import annotations

import importlib.util
import json
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


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_append_rollback_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment-generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "environment-generation append authority missing")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("bindingRules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "transactional generation append contract guard missing",
    )

    writer = load_writer()
    require(callable(getattr(writer, "write_registry_transactionally", None)), "transactional generation registry writer missing")

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-rollback-") as tmp:
        registry = Path(tmp) / "generation-registry.v1.json"
        original = b'{"sentinel":"before"}\n'
        registry.write_bytes(original)

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
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate

    print("Memory OS environment generation append rollback negative PASS")
    print("post-append canonical registry revalidation: enforced")
    print("failed append registry rollback: byte-for-byte")
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
