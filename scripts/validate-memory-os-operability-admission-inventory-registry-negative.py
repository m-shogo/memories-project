#!/usr/bin/env python3
"""Prove operability inventory validation/generation rejects corrupt append-only authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory.py"
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"
AUTHORITIES = {
    "environment generation": ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "recovery objective": ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    "drill request": ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "generation recovery evidence": ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "typed non-resurrection": ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "human promotion review": ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_validator_rejected(
    validator: Any,
    path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(load(path))
    mutate(bad)
    original_load = validator.load

    def patched_load(candidate: Path) -> dict[str, Any]:
        if candidate == path:
            return copy.deepcopy(bad)
        return original_load(candidate)

    validator.load = patched_load
    try:
        validator.main()
    except validator.Fail:
        print(f"PASS validator reject: {name}")
        return
    finally:
        validator.load = original_load
    raise Fail(f"corrupt append-only authority unexpectedly accepted by validator: {name}")


def expect_generator_rejected(
    generator: Any,
    path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(load(path))
    mutate(bad)
    original_load = generator.load
    relative = path.relative_to(ROOT).as_posix()
    output_before = generator.OUTPUT.read_bytes()

    def patched_load(candidate: str) -> dict[str, Any]:
        if candidate == relative:
            return copy.deepcopy(bad)
        return original_load(candidate)

    generator.load = patched_load
    rejected = False
    try:
        generator.main()
    except SystemExit:
        rejected = True
        print(f"PASS generator reject: {name}")
    finally:
        generator.load = original_load
    require(rejected, f"corrupt append-only authority unexpectedly accepted by generator: {name}")
    require(generator.OUTPUT.read_bytes() == output_before, f"generator mutated inventory after rejecting corrupt authority: {name}")


def main() -> int:
    require(VALIDATOR.is_file(), "inventory validator missing")
    require(GENERATOR.is_file(), "inventory generator missing")
    require(all(path.is_file() for path in AUTHORITIES.values()), "canonical append-only authority missing")
    validator = load_module(VALIDATOR, "memory_os_inventory_registry_negative_validator")
    generator = load_module(GENERATOR, "memory_os_inventory_registry_negative_generator")
    before = {path: path.read_bytes() for path in AUTHORITIES.values()}
    inventory_before = generator.OUTPUT.read_bytes()

    validator.main()
    generator.main()
    require(generator.OUTPUT.read_bytes() == inventory_before, "canonical inventory generator is not byte-deterministic")
    print("PASS baseline: canonical append-only authorities accepted without inventory drift")

    cases: list[tuple[Path, str, Callable[[dict[str, Any]], None]]] = [
        (
            AUTHORITIES["environment generation"],
            "environment generation registryClass drift",
            lambda value: value.__setitem__("registryClass", "NOT_PRODUCTION_EQUIVALENT_GENERATIONS"),
        ),
        (
            AUTHORITIES["recovery objective"],
            "recovery objective schema drift",
            lambda value: value.__setitem__("schemaVersion", "invalid"),
        ),
        (
            AUTHORITIES["drill request"],
            "drill request append-only disabled",
            lambda value: value.__setitem__("appendOnly", False),
        ),
        (
            AUTHORITIES["generation recovery evidence"],
            "generation recovery evidence schema drift",
            lambda value: value.__setitem__("schemaVersion", "invalid"),
        ),
        (
            AUTHORITIES["typed non-resurrection"],
            "typed non-resurrection production readiness manufactured",
            lambda value: value.__setitem__("productionReady", True),
        ),
        (
            AUTHORITIES["human promotion review"],
            "human promotion latest decision manufactured",
            lambda value: value.__setitem__("latestDecisionId", "brpr_manufactured_authority"),
        ),
    ]
    for path, name, mutate in cases:
        expect_validator_rejected(validator, path, name, mutate)
        expect_generator_rejected(generator, path, name, mutate)

    after = {path: path.read_bytes() for path in AUTHORITIES.values()}
    require(after == before, "negative suite mutated canonical append-only authority")
    require(generator.OUTPUT.read_bytes() == inventory_before, "negative suite mutated canonical inventory")
    print("Memory OS operability inventory append-only authority negative suite PASS")
    print("canonical registry corruption accepted by standalone inventory validator: false")
    print("canonical registry corruption accepted by inventory generator: false")
    print("rejected generator run mutated inventory: false")
    print("canonical append-only authority mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY REGISTRY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)