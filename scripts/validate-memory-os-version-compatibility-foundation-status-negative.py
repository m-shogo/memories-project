#!/usr/bin/env python3
"""Pin fail-closed numeric and source-authority boundaries for compatibility foundations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-foundation-status.py"
FOUNDATION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, value, field: str) -> None:
    rejected = False
    try:
        module.require_zero_count({field: value}, field)
    except module.ReconcileFailure as exc:
        require(field in str(exc), f"unexpected rejection for {field}: {exc}")
        rejected = True
    require(rejected, f"invalid zero-count authority accepted for {field}: {value!r}")


def expect_registry_rejection(module, count, count_field: str,
                              items_field: str, label: str, items=None) -> None:
    registry = {count_field: count, items_field: [] if items is None else items}
    rejected = False
    try:
        module.require_empty_registry(registry, count_field, items_field, label)
    except module.ReconcileFailure as exc:
        require(label in str(exc), f"unexpected registry rejection for {label}: {exc}")
        rejected = True
    require(rejected, f"invalid empty authority accepted for {label}: {registry!r}")


def expect_source_authority_rejection(reconciler, validator, path: Path, field: str,
                                      replacement, label: str) -> None:
    original = path.read_bytes()
    try:
        registry = json.loads(original.decode("utf-8"))
        registry[field] = replacement
        path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            reconciler.validate_source_registries()
        except reconciler.ReconcileFailure as exc:
            require("compatibility source authority invalid" in str(exc),
                    f"unexpected reconciler rejection for {label}: {exc}")
            rejected = True
        require(rejected, f"corrupt canonical {label} authority was accepted before reconcile")

        rejected = False
        try:
            validator.validate_empty_authorities()
        except validator.ValidationFailure as exc:
            require("compatibility source authority invalid" in str(exc),
                    f"unexpected standalone validator rejection for {label}: {exc}")
            rejected = True
        require(rejected, f"corrupt canonical {label} authority was accepted by standalone validator")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            f"canonical {label} authority changed after source-authority rejection")


def expect_foundation_boolean_count_rejection(validator, field: str) -> None:
    path = validator.FOUNDATION_PATH
    original = path.read_bytes()
    try:
        contract = json.loads(original.decode("utf-8"))
        contract["aggregateBoundaries"][field] = False
        path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            validator.validate_foundation_contract()
        except validator.ValidationFailure as exc:
            require(field in str(exc), f"unexpected foundation count rejection for {field}: {exc}")
            rejected = True
        require(rejected, f"boolean foundation count accepted for {field}")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            f"foundation contract changed after boolean-count rejection for {field}")


def main() -> int:
    reconciler = load_module(RECONCILER, "compatibility_foundation_status_reconciler")
    validator = load_module(FOUNDATION_VALIDATOR, "compatibility_foundation_validator")
    for field in reconciler.ZERO_COUNT_FIELDS:
        expect_rejection(reconciler, False, field)
        expect_rejection(reconciler, True, field)
        expect_rejection(reconciler, -1, field)
        reconciler.require_zero_count({field: 0}, field)
        expect_foundation_boolean_count_rejection(validator, field)

    for _path, count_field, items_field, label in reconciler.EMPTY_AUTHORITIES:
        expect_registry_rejection(reconciler, False, count_field, items_field, label)
        expect_registry_rejection(reconciler, True, count_field, items_field, label)
        expect_registry_rejection(reconciler, -1, count_field, items_field, label)
        expect_registry_rejection(reconciler, 1, count_field, items_field, label)
        expect_registry_rejection(reconciler, 0, count_field, items_field, label, items=[{"forged": True}])
        reconciler.require_empty_registry({count_field: 0, items_field: []},
                                          count_field, items_field, label)

    expect_source_authority_rejection(
        reconciler, validator, reconciler.RELEASE_REGISTRY_PATH, "registryClass",
        "CORRUPTED_RELEASE_AUTHORITY", "release",
    )
    expect_source_authority_rejection(
        reconciler, validator, reconciler.ROLLBACK_REGISTRY_PATH, "appendOnly",
        False, "rollback rehearsal",
    )
    expect_source_authority_rejection(
        reconciler, validator, reconciler.PARSER_REGISTRY_PATH, "productionEvidence",
        True, "parser artifact",
    )

    print("PASS: compatibility foundation reconciler and validator fail closed on source authority drift")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
