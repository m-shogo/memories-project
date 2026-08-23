#!/usr/bin/env python3
"""Negative checks for atomic operability admission inventory publication."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
CANONICAL_OUTPUT = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_generator():
    spec = importlib.util.spec_from_file_location("memory_os_operability_inventory_atomic_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load operability inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    require(GENERATOR.is_file(), "canonical operability inventory generator missing")
    require(CANONICAL_OUTPUT.is_file(), "canonical operability inventory missing")
    require(CANONICAL_STATUS.is_file(), "canonical production status missing")

    generator = load_generator()
    output_before = CANONICAL_OUTPUT.read_bytes()
    status_before = CANONICAL_STATUS.read_bytes()
    original_replace = generator.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    generator.os.replace = reject_replace
    try:
        try:
            generator.atomic_write_text(CANONICAL_OUTPUT, output_before.decode("utf-8") + " ")
        except SystemExit as exc:
            require(
                "cannot atomically write contracts/operations/operability-admission-inventory.v1.json" in str(exc),
                f"atomic inventory write rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("synthetic operability inventory atomic replace failure unexpectedly accepted")
    finally:
        generator.os.replace = original_replace

    require(CANONICAL_OUTPUT.read_bytes() == output_before, "atomic replace rejection mutated canonical operability inventory")
    require(CANONICAL_STATUS.read_bytes() == status_before, "atomic replace rejection mutated canonical production status")
    leftovers = list(CANONICAL_OUTPUT.parent.glob(f".{CANONICAL_OUTPUT.name}.*.tmp"))
    require(not leftovers, f"atomic replace rejection left temporary operability inventory authority files: {leftovers}")

    print("Memory OS operability admission inventory atomic replacement negative PASS")
    print("non-atomic inventory authority write accepted: false")
    print("canonical inventory mutated on failed atomic replace: false")
    print("production evidence: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
