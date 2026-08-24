#!/usr/bin/env python3
"""Prove direct inventory generation rejects symlinked canonical input authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
SOURCE_AUTHORITY = ROOT / "scripts/validate-memory-os-operability-admission-inventory-source-authorities.py"
INPUT_REL = Path("contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json")
INPUT = ROOT / INPUT_REL
ALIAS_TARGET = INPUT.parent / ".inventory-generator-input-authority-target.json"
ENV_GENERATION_VALIDATOR = "scripts/validate-memory-os-production-equivalent-environment-generation.py"
ADMISSION_CHAIN_VALIDATOR = "scripts/validate-memory-os-backup-restore-admission-chain.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, module_name: str):
    require(path.is_file() and not path.is_symlink(), f"authority missing or symlinked: {path.relative_to(ROOT)}")
    resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    require(resolved == path.relative_to(ROOT), f"authority path drift: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator():
    return load_module(GENERATOR, "memory_os_inventory_generator_input_authority_negative")


def load_source_authority():
    return load_module(SOURCE_AUTHORITY, "memory_os_inventory_source_authority_order_negative")


def restore_input(input_before: bytes) -> None:
    INPUT.unlink(missing_ok=True)
    INPUT.write_bytes(input_before)
    ALIAS_TARGET.unlink(missing_ok=True)


def main() -> int:
    generator = load_generator()
    source_authority = load_source_authority()
    command_paths = [row[0] for row in source_authority.COMMAND_SOURCES]
    require(
        command_paths.count(ENV_GENERATION_VALIDATOR) == 1,
        "inventory source authority must validate the full environment-generation admission authority exactly once",
    )
    require(
        ADMISSION_CHAIN_VALIDATOR not in command_paths,
        "pre-generation source authority must not validate the inventory-dependent end-to-end admission chain",
    )

    source_root_before = source_authority.ROOT
    source_authority.ROOT = ROOT / "contracts"
    root_rejected = False
    try:
        source_authority.enforce_runtime_authority()
    except source_authority.Fail:
        root_rejected = True
    finally:
        source_authority.ROOT = source_root_before
    require(root_rejected, "inventory source-authority validator accepted substituted repository root")
    source_authority.enforce_runtime_authority()

    require(INPUT.is_file() and not INPUT.is_symlink(), "canonical inventory input missing or already symlinked")
    require(not ALIAS_TARGET.exists() and not ALIAS_TARGET.is_symlink(), "inventory input alias fixture already exists")
    input_before = INPUT.read_bytes()
    output_before = generator.OUTPUT.read_bytes()

    try:
        ALIAS_TARGET.write_bytes(input_before)
        INPUT.unlink()
        INPUT.symlink_to(ALIAS_TARGET.name)
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
        restore_input(input_before)

    require(INPUT.is_file() and not INPUT.is_symlink(), "canonical inventory input was not restored")
    require(INPUT.read_bytes() == input_before, "canonical inventory input bytes changed after negative probe")
    require(not ALIAS_TARGET.exists() and not ALIAS_TARGET.is_symlink(), "inventory input alias fixture cleanup failed")
    require(generator.OUTPUT.read_bytes() == output_before, "negative probe mutated canonical inventory")

    print("Memory OS operability inventory generator authority negative PASS")
    print("full environment-generation admission authority validated before inventory generation: true")
    print("inventory-dependent end-to-end admission chain validated before inventory generation: false")
    print("inventory source-authority repository root substitution accepted: false")
    print("symlinked canonical input accepted by direct generator: false")
    print("symlinked foundation path counted as canonical foundation: false")
    print("fixture setup failure can strand canonical input authority: false")
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
