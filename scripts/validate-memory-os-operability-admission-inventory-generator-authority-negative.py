#!/usr/bin/env python3
"""Prove direct inventory generation rejects substituted canonical authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
INVENTORY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory.py"
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


def load_inventory_validator():
    return load_module(INVENTORY_VALIDATOR, "memory_os_inventory_validator_execution_authority_negative")


def load_source_authority():
    return load_module(SOURCE_AUTHORITY, "memory_os_inventory_source_authority_order_negative")


def expect_source_authority_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    rejected = False
    try:
        module.enforce_runtime_authority()
    except module.Fail:
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"inventory source-authority validator accepted substituted {field}")


def expect_source_execution_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    rejected = False
    try:
        module.main()
    except module.Fail:
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"inventory source-authority validator accepted substituted execution helper {field}")


def expect_inventory_execution_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    rejected = False
    try:
        module.main()
    except module.Fail:
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"inventory validator accepted substituted runtime authority {field}")


def restore_input(input_before: bytes) -> None:
    INPUT.unlink(missing_ok=True)
    INPUT.write_bytes(input_before)
    ALIAS_TARGET.unlink(missing_ok=True)


def main() -> int:
    generator = load_generator()
    inventory_validator = load_inventory_validator()
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

    expect_source_authority_rejected(source_authority, "ROOT", ROOT / "contracts")
    expect_source_authority_rejected(source_authority, "SELF_REL", Path("scripts/validate-memory-os-operability.py"))
    expect_source_authority_rejected(source_authority, "REQUEST", "contracts/operations/production-operability-status.json")
    expect_source_authority_rejected(source_authority, "REQUEST_FIELDS", tuple())
    expect_source_authority_rejected(source_authority, "REQUEST_CONSTRAINTS", tuple())
    expect_source_authority_rejected(source_authority, "SOURCES", tuple(reversed(source_authority.SOURCES)))
    expect_source_authority_rejected(source_authority, "COMMAND_SOURCES", tuple(reversed(source_authority.COMMAND_SOURCES)))
    source_authority.enforce_runtime_authority()

    expect_source_execution_rejected(source_authority, "enforce_execution_authority", lambda: None)
    expect_source_execution_rejected(source_authority, "require", lambda *_args: None)
    expect_source_execution_rejected(source_authority, "load", lambda _relative: {})
    expect_source_execution_rejected(source_authority, "load_validator", lambda *_args: (lambda *_inner: 0))
    expect_source_execution_rejected(source_authority, "validate_inventory_request", lambda: None)
    expect_source_execution_rejected(source_authority, "validate_human_tabletop_source", lambda: 6)
    expect_source_execution_rejected(source_authority, "validate_load_source", lambda: None)
    expect_source_execution_rejected(source_authority, "validate_command_source", lambda *_args: None)
    expect_source_execution_rejected(source_authority, "validate_source", lambda *_args: None)
    expect_source_execution_rejected(source_authority, "exact_success", lambda *_args: None)
    expect_source_execution_rejected(source_authority, "validate_registry_result", lambda *_args: None)

    expect_inventory_execution_rejected(inventory_validator, "enforce_runtime_authority", lambda: None)
    expect_inventory_execution_rejected(inventory_validator, "require", lambda *_args: None)
    expect_inventory_execution_rejected(inventory_validator, "valid_count", lambda _value: True)
    expect_inventory_execution_rejected(inventory_validator, "require_count_match", lambda *_args: None)
    expect_inventory_execution_rejected(inventory_validator, "repo_relative", lambda _path: Path("contracts/operations/production-operability-status.json"))
    expect_inventory_execution_rejected(inventory_validator, "load", lambda _path: {})
    expect_inventory_execution_rejected(inventory_validator, "canonical_registry_validator", lambda *_args: (lambda _registry: None))
    expect_inventory_execution_rejected(inventory_validator, "require_canonical_registry", lambda *_args: None)
    expect_inventory_execution_rejected(inventory_validator, "validate_source_authorities", lambda: None)
    expect_inventory_execution_rejected(inventory_validator, "INVENTORY", inventory_validator.STATUS)
    expect_inventory_execution_rejected(inventory_validator, "STATUS", inventory_validator.INVENTORY)
    expect_inventory_execution_rejected(inventory_validator, "SOURCE_AUTHORITY_VALIDATOR", INVENTORY_VALIDATOR)
    inventory_validator.enforce_runtime_authority()

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
    print("inventory source-authority self/request shape substitution accepted: false")
    print("inventory source registry/command sequence substitution accepted: false")
    print("inventory source execution helper substitution accepted: false")
    print("inventory validator execution helper substitution accepted: false")
    print("inventory validator canonical data authority substitution accepted: false")
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
