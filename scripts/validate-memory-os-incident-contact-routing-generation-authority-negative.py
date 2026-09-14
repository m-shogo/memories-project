#!/usr/bin/env python3
"""Reject corrupt environment-generation authority without mutating canonical registry."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-contact-routing.py"


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "memory_os_contact_routing_generation_authority_negative",
        VALIDATOR,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load contact-routing validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(validator, candidate: dict, label: str) -> None:
    original_load = validator.load

    def overlay_load(path: Path):
        if path == validator.GEN_REGISTRY:
            return copy.deepcopy(candidate)
        return original_load(path)

    validator.load = overlay_load
    try:
        try:
            validator.main()
        except validator.Fail:
            return
        raise RuntimeError(f"contact-routing validator accepted corrupt generation authority: {label}")
    finally:
        validator.load = original_load


def main() -> int:
    original_bytes = GEN_REGISTRY.read_bytes()
    original_mode = mode(GEN_REGISTRY)
    registry = json.loads(original_bytes.decode("utf-8"))
    validator = load_validator()
    validator.enforce_runtime_authorities()

    cases: list[tuple[str, dict]] = []

    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))

    candidate = copy.deepcopy(registry)
    candidate["registeredGenerationCount"] = True
    cases.append(("boolean generation count", candidate))

    candidate = copy.deepcopy(registry)
    candidate["productionEvidence"] = True
    cases.append(("production evidence escalation", candidate))

    for label, candidate in cases:
        expect_rejected(validator, candidate, label)
        if GEN_REGISTRY.read_bytes() != original_bytes:
            raise RuntimeError(f"{label} mutated canonical environment-generation registry bytes")
        if mode(GEN_REGISTRY) != original_mode:
            raise RuntimeError(f"{label} changed canonical environment-generation registry mode")

    validator.enforce_runtime_authorities()
    if GEN_REGISTRY.read_bytes() != original_bytes:
        raise RuntimeError("generation authority negative mutated canonical registry")
    if mode(GEN_REGISTRY) != original_mode:
        raise RuntimeError("generation authority negative changed canonical registry mode")

    print("PASS: contact routing rejects corrupt environment-generation authority through read-only overlay")
    print("canonical environment-generation registry mutated by negative suite: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
