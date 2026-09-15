#!/usr/bin/env python3
"""Prove observability writer rollback without mutating canonical registry authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"


def load_writer():
    spec = importlib.util.spec_from_file_location("observability_stack_writer_rollback_isolation", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observability stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def main() -> int:
    canonical_bytes = REGISTRY.read_bytes()
    canonical_mode = mode(REGISTRY)
    registry = json.loads(canonical_bytes.decode("utf-8"))
    writer = load_writer()

    with tempfile.TemporaryDirectory(prefix="memory-os-observability-writer-negative-") as tmp:
        fixture = Path(tmp) / REGISTRY.name
        fixture.write_bytes(canonical_bytes)
        fixture.chmod(canonical_mode)
        original_registry = writer.REGISTRY
        original_validator = writer.validate_registry_for_append
        calls = 0

        def injected_validator(value, *, validate_rows=True):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            raise writer.Fail("injected post-append registry validation failure")

        candidate = copy.deepcopy(registry)
        candidate["appendOnly"] = False
        try:
            writer.REGISTRY = fixture
            writer.validate_registry_for_append = injected_validator
            try:
                writer.commit_registry_candidate(registry, candidate)
            except writer.Fail as exc:
                if "injected post-append registry validation failure" not in str(exc):
                    raise RuntimeError(f"rollback rejected at wrong boundary: {exc}") from exc
            else:
                raise RuntimeError("writer accepted injected post-append registry validation failure")

            if fixture.read_bytes() != canonical_bytes:
                raise RuntimeError("isolated writer rollback did not restore registry bytes")
            if mode(fixture) != canonical_mode:
                raise RuntimeError("isolated writer rollback did not preserve registry mode")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator

    if REGISTRY.read_bytes() != canonical_bytes:
        raise RuntimeError("writer rollback negative mutated canonical registry bytes")
    if mode(REGISTRY) != canonical_mode:
        raise RuntimeError("writer rollback negative mutated canonical registry mode")

    print("PASS: observability writer rollback is proven in a run-local registry fixture")
    print("PASS: canonical observability registry bytes and mode remain unchanged")
    print("production evidence created: false")
    print("automatic production promotion authorized: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
