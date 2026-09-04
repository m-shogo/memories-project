#!/usr/bin/env python3
"""Prove the real incident-contact routing writer cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-incident-contact-routing.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_incident_contact_routing_writer_authority_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load contact routing writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {label}")
        return
    except Exception as exc:
        raise Fail(f"{label} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {label}")


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(".incident-contact-routing.*.tmp"))


def prove_atomic_writer_transaction(writer) -> None:
    original_registry_path = writer.REGISTRY
    original_replace = writer.os.replace
    original_validate = writer.validate_registry_for_append
    try:
        with tempfile.TemporaryDirectory(prefix="memory-os-contact-routing-writer-") as temp_dir:
            registry = Path(temp_dir) / "registry.json"
            original_value = {
                "schemaVersion": "test-registry.v1",
                "appendOnly": True,
                "routings": [],
                "admittedRoutingCount": 0,
                "productionEquivalentRoutingCount": 0,
                "productionRoutingCount": 0,
                "productionReady": False,
            }
            replacement_value = {**original_value, "testMarker": "replacement"}
            original_bytes = (json.dumps(original_value, indent=2) + "\n").encode("utf-8")
            registry.write_bytes(original_bytes)
            os.chmod(registry, 0o640)
            writer.REGISTRY = registry

            writer.atomic_write(replacement_value)
            require(mode(registry) == 0o640,
                    "contact routing atomic writer changed registry permission mode on success")
            require(json.loads(registry.read_text(encoding="utf-8")) == replacement_value,
                    "contact routing atomic writer did not publish replacement value")
            require(not temp_residue(registry),
                    "contact routing atomic writer left temp residue after success")

            registry.write_bytes(original_bytes)
            os.chmod(registry, 0o640)

            def reject_replace(_src, _dst):
                raise OSError("synthetic replace rejection")

            writer.os.replace = reject_replace
            expect_rejected(
                "contact routing registry replace rejection",
                lambda: writer.atomic_write(replacement_value),
                OSError,
            )
            require(registry.read_bytes() == original_bytes,
                    "replace rejection mutated contact routing registry bytes")
            require(mode(registry) == 0o640,
                    "replace rejection changed contact routing registry permission mode")
            require(not temp_residue(registry),
                    "replace rejection left contact routing temp residue")
            writer.os.replace = original_replace

            registry.write_bytes(original_bytes)
            os.chmod(registry, 0o640)
            calls = 0

            def reject_post_write(_value, *, validate_rows=True):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise writer.Fail("synthetic post-write validation rejection")

            writer.validate_registry_for_append = reject_post_write
            expect_rejected(
                "contact routing post-write validation rollback",
                lambda: writer.commit_registry_candidate(original_value, replacement_value),
                writer.Fail,
            )
            require(registry.read_bytes() == original_bytes,
                    "post-write validation rejection did not restore contact routing registry bytes")
            require(mode(registry) == 0o640,
                    "post-write validation rejection did not restore contact routing registry mode")
            require(not temp_residue(registry),
                    "post-write validation rollback left contact routing temp residue")
    finally:
        writer.REGISTRY = original_registry_path
        writer.os.replace = original_replace
        writer.validate_registry_for_append = original_validate


def main() -> int:
    require(WRITER.is_file(), "incident contact routing writer missing")
    writer = load_writer()
    require(callable(getattr(writer, "require_actual_cli_authorities", None)),
            "contact routing writer CLI authority guard missing")
    main_source = inspect.getsource(writer.main)
    require("require_actual_cli_authorities()" in main_source,
            "contact routing writer main does not enforce CLI authority guard")
    atomic_source = inspect.getsource(writer.atomic_write)
    require("existing_mode" in atomic_source and "os.fchmod" in atomic_source,
            "contact routing registry writer must preserve existing permission mode")
    writer.require_actual_cli_authorities()

    canonical_registry_before = writer.CANONICAL_REGISTRY.read_bytes()
    canonical_registry_mode = mode(writer.CANONICAL_REGISTRY)
    with tempfile.TemporaryDirectory(prefix="memory-os-contact-routing-authority-") as temp_dir:
        outside = Path(temp_dir) / "outside-authority.json"
        outside.write_text("{}\n", encoding="utf-8")
        substitutions = (
            ("CONTRACT", writer.CANONICAL_CONTRACT),
            ("REGISTRY", writer.CANONICAL_REGISTRY),
            ("OBS_REGISTRY", writer.CANONICAL_OBS_REGISTRY),
            ("OBS_WRITER", writer.CANONICAL_OBS_WRITER),
            ("GEN_REGISTRY", writer.CANONICAL_GEN_REGISTRY),
            ("LOCK", writer.CANONICAL_LOCK),
        )
        for attribute, canonical in substitutions:
            original = getattr(writer, attribute)
            try:
                setattr(writer, attribute, outside)
                expect_rejected(
                    f"contact routing writer CLI {attribute} substitution",
                    writer.require_actual_cli_authorities,
                    writer.Fail,
                )
            finally:
                setattr(writer, attribute, original)
            require(getattr(writer, attribute) == canonical,
                    f"contact routing writer CLI {attribute} canonical authority not restored")

    prove_atomic_writer_transaction(writer)
    writer.require_actual_cli_authorities()
    require(writer.CANONICAL_REGISTRY.read_bytes() == canonical_registry_before,
            "contact routing writer authority negative mutated canonical registry")
    require(mode(writer.CANONICAL_REGISTRY) == canonical_registry_mode,
            "contact routing writer authority negative changed canonical registry mode")
    print("Memory OS incident contact routing writer authority negative suite PASS")
    print("writer CLI data/executable/lock substitution accepted: false")
    print("registry mode drift on atomic replacement accepted: false")
    print("contact routing evidence generated: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"INCIDENT CONTACT ROUTING WRITER AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
