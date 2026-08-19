#!/usr/bin/env python3
"""Prove inventory validator exit/result semantics remain fail-closed."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
SOURCE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory-source-authorities.py"
SOURCE_REGISTRY = "contracts/operations/migration-production-shaped-admission-registry.v1.json"
SOURCE_WRITER = "scripts/register-memory-os-migration-production-shaped-admission.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(generator: Any, value: Any, label: str) -> None:
    try:
        generator.exact_success(value, label)
    except SystemExit as exc:
        require(str(value) in str(exc), f"rejection lost validator result for {label}: {exc}")
        return
    raise Fail(f"non-exact validator success unexpectedly accepted: {label}={value!r}")


def expect_boolean_registry_result_rejected(source_validator: Any, value: bool) -> None:
    try:
        source_validator.reject_boolean_registry_result(value, f"boolean registry result {value!r}")
    except source_validator.Fail as exc:
        require("registry validator returned boolean" in str(exc), f"unexpected registry result rejection: {exc}")
        return
    raise Fail(f"boolean registry validator result unexpectedly accepted: {value!r}")


def expect_validate_source_result_semantics(source_validator: Any) -> None:
    original = source_validator.load_validator

    def run_with(result: Any) -> None:
        def patched_load_validator(relative: str, module_name: str, function_name: str):
            require(relative == SOURCE_WRITER, f"unexpected source writer under result test: {relative}")
            require(function_name == "validate_registry_for_append", f"unexpected source function under result test: {function_name}")

            def synthetic_registry_validator(registry: dict[str, Any]) -> Any:
                return result

            return synthetic_registry_validator

        source_validator.load_validator = patched_load_validator
        source_validator.validate_source(
            SOURCE_REGISTRY,
            SOURCE_WRITER,
            "memory_os_inventory_source_result_negative_runtime",
            "validate_registry_for_append",
            f"synthetic registry result {result!r}",
        )

    try:
        run_with(None)
        run_with([])
        for result in (False, True):
            try:
                run_with(result)
            except source_validator.Fail as exc:
                require("registry validator returned boolean" in str(exc), f"unexpected validate_source rejection: {exc}")
            else:
                raise Fail(f"validate_source accepted boolean registry validator result: {result!r}")
    finally:
        source_validator.load_validator = original
    print("PASS source validator: validate_source rejects boolean registry results while preserving legitimate return contracts")


def main() -> int:
    require(GENERATOR.is_file(), "operability inventory generator missing")
    require(SOURCE_VALIDATOR.is_file(), "operability inventory source-authority validator missing")
    generator = load_module(GENERATOR, "memory_os_inventory_generator_exit_negative")
    source_validator = load_module(SOURCE_VALIDATOR, "memory_os_inventory_source_result_negative")

    generator.exact_success(0, "integer zero")
    for value, label in (
        (False, "boolean false"),
        (True, "boolean true"),
        (1, "positive integer"),
        (-1, "negative integer"),
        ("0", "string zero"),
        (None, "null result"),
    ):
        expect_rejected(generator, value, label)

    source_validator.reject_boolean_registry_result(None, "none-return registry validator")
    source_validator.reject_boolean_registry_result([], "normalized-list registry validator")
    for value in (False, True):
        expect_boolean_registry_result_rejected(source_validator, value)
    expect_validate_source_result_semantics(source_validator)

    print("Memory OS operability inventory validator result negative PASS")
    print("exact integer zero command-validator success accepted: true")
    print("boolean command-validator result accepted as success: false")
    print("nonzero/noninteger command-validator exits accepted: false")
    print("none-return registry validator accepted: true")
    print("normalized-list registry validator accepted: true")
    print("boolean registry validator result accepted: false")
    print("validate_source boolean-result bypass: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY VALIDATOR RESULT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
