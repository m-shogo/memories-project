#!/usr/bin/env python3
"""Prove inventory validator exit/result semantics remain fail-closed."""

from __future__ import annotations

import copy
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


def expect_registry_result_rejected(source_validator: Any, value: Any) -> None:
    try:
        source_validator.validate_registry_result(value, f"registry result {value!r}")
    except source_validator.Fail as exc:
        if isinstance(value, bool):
            require("registry validator returned boolean" in str(exc), f"unexpected boolean registry result rejection: {exc}")
        else:
            require("unsupported registry validator result" in str(exc), f"unexpected scalar registry result rejection: {exc}")
        return
    raise Fail(f"scalar registry validator result unexpectedly accepted: {value!r}")


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
        for result in (None, [], {}, (), set()):
            run_with(result)
        for result in (False, True, 1, -1, 0, "FAIL", b"FAIL", 1.5):
            try:
                run_with(result)
            except source_validator.Fail as exc:
                expected = "registry validator returned boolean" if isinstance(result, bool) else "unsupported registry validator result"
                require(expected in str(exc), f"unexpected validate_source rejection for {result!r}: {exc}")
            else:
                raise Fail(f"validate_source accepted scalar registry validator result: {result!r}")
    finally:
        source_validator.load_validator = original
    print("PASS source validator: validate_source rejects scalar registry results while preserving legitimate return contracts")


def expect_inventory_request_authority(source_validator: Any) -> None:
    canonical = source_validator.load(source_validator.REQUEST)
    original_load = source_validator.load

    def run_case(name: str, mutate) -> None:
        bad = copy.deepcopy(canonical)
        mutate(bad)

        def patched_load(relative: str):
            if relative == source_validator.REQUEST:
                return copy.deepcopy(bad)
            return original_load(relative)

        source_validator.load = patched_load
        try:
            source_validator.validate_inventory_request()
        except source_validator.Fail:
            print(f"PASS request authority reject: {name}")
            return
        finally:
            source_validator.load = original_load
        raise Fail(f"invalid operability inventory request unexpectedly accepted: {name}")

    run_case("production traffic enabled", lambda value: value.__setitem__("productionTraffic", True))
    run_case(
        "human-approved recovery objective constraint disabled",
        lambda value: value["constraints"].__setitem__("approvedRecoveryObjectiveCountMustDeriveFromTypedHumanApprovalAuthority", False),
    )
    run_case(
        "unknown request constraint",
        lambda value: value["constraints"].__setitem__("automaticProductionPromotionAllowed", True),
    )
    run_case(
        "required request constraint removed",
        lambda value: value["constraints"].pop("humanProductionPromotionAuthorityMustRemainSeparate"),
    )
    source_validator.validate_inventory_request()
    print("PASS request authority: canonical inventory generation request remains fail-closed")


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

    for value, label in (
        (None, "none-return registry validator"),
        ([], "normalized-list registry validator"),
        ({}, "normalized-object registry validator"),
        ((), "normalized-tuple registry validator"),
        (set(), "normalized-set registry validator"),
    ):
        source_validator.validate_registry_result(value, label)
    for value in (False, True, 0, 1, -1, "FAIL", b"FAIL", 1.5):
        expect_registry_result_rejected(source_validator, value)
    expect_validate_source_result_semantics(source_validator)
    expect_inventory_request_authority(source_validator)

    print("Memory OS operability inventory validator result negative PASS")
    print("exact integer zero command-validator success accepted: true")
    print("boolean command-validator result accepted as success: false")
    print("nonzero/noninteger command-validator exits accepted: false")
    print("none-return registry validator accepted: true")
    print("normalized-collection registry validator accepted: true")
    print("boolean registry validator result accepted: false")
    print("scalar registry validator result accepted: false")
    print("validate_source scalar-result bypass: false")
    print("inventory request production boundary drift accepted: false")
    print("inventory request human-approved objective constraint drift accepted: false")
    print("inventory request unknown/missing constraints accepted: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY VALIDATOR RESULT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)