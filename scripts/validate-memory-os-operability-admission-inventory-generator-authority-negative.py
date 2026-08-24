#!/usr/bin/env python3
"""Prove direct inventory generation rejects symlinked canonical input authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
INPUT_REL = Path("contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json")
INPUT = ROOT / INPUT_REL
ALIAS_TARGET = INPUT.parent / ".inventory-generator-input-authority-target.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_generator():
    require(GENERATOR.is_file() and not GENERATOR.is_symlink(), "inventory generator missing or symlinked")
    resolved = GENERATOR.resolve(strict=True).relative_to(ROOT.resolve())
    require(resolved == Path("scripts/generate-memory-os-operability-admission-inventory.py"), "inventory generator authority drift")
    spec = importlib.util.spec_from_file_location("memory_os_inventory_generator_input_authority_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    generator = load_generator()
    require(INPUT.is_file() and not INPUT.is_symlink(), "canonical inventory input missing or already symlinked")
    require(not ALIAS_TARGET.exists() and not ALIAS_TARGET.is_symlink(), "inventory input alias fixture already exists")
    input_before = INPUT.read_bytes()
    output_before = generator.OUTPUT.read_bytes()

    ALIAS_TARGET.write_bytes(input_before)
    INPUT.unlink()
    INPUT.symlink_to(ALIAS_TARGET.name)
    try:
        rejected = False
        try:
            generator.load(INPUT_REL.as_posix())
        except SystemExit as exc:
            require(exc.code not in (None, 0), "symlinked canonical input produced successful SystemExit")
            rejected = True
        require(rejected, "direct inventory generator accepted symlinked canonical input authority")
        require(generator.exists(INPUT_REL.as_posix()) is False, "symlinked foundation path counted as canonical foundation")
        require(generator.OUTPUT.read_bytes() == output_before, "input authority rejection mutated canonical inventory")
    finally:
        INPUT.unlink(missing_ok=True)
        INPUT.write_bytes(input_before)
        ALIAS_TARGET.unlink(missing_ok=True)

    require(INPUT.is_file() and not INPUT.is_symlink(), "canonical inventory input was not restored")
    require(INPUT.read_bytes() == input_before, "canonical inventory input bytes changed after negative probe")
    require(not ALIAS_TARGET.exists() and not ALIAS_TARGET.is_symlink(), "inventory input alias fixture cleanup failed")
    require(generator.OUTPUT.read_bytes() == output_before, "negative probe mutated canonical inventory")

    print("Memory OS operability inventory generator authority negative PASS")
    print("symlinked canonical input accepted by direct generator: false")
    print("symlinked foundation path counted as canonical foundation: false")
    print("rejected probe mutated canonical input authority: false")
    print("rejected probe mutated canonical inventory: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY GENERATOR AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
