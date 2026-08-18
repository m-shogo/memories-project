#!/usr/bin/env python3
"""Pin fail-closed numeric and source-authority boundaries for compatibility foundation status reconcile."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-foundation-status.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("compatibility_foundation_status_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load compatibility foundation reconciler")
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


def expect_source_authority_rejection(module) -> None:
    path = module.RELEASE_REGISTRY_PATH
    original = path.read_bytes()
    try:
        registry = json.loads(original.decode("utf-8"))
        registry["registryClass"] = "CORRUPTED_RELEASE_AUTHORITY"
        path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        rejected = False
        try:
            module.validate_source_registries()
        except module.ReconcileFailure as exc:
            require("compatibility source authority invalid" in str(exc),
                    f"unexpected source-authority rejection: {exc}")
            rejected = True
        require(rejected, "corrupt canonical release authority was accepted before reconcile")
    finally:
        path.write_bytes(original)
    require(path.read_bytes() == original,
            "canonical release authority changed after source-authority rejection")


def main() -> int:
    module = load_reconciler()
    for field in module.ZERO_COUNT_FIELDS:
        expect_rejection(module, False, field)
        expect_rejection(module, True, field)
        expect_rejection(module, -1, field)
        module.require_zero_count({field: 0}, field)

    for _path, count_field, items_field, label in module.EMPTY_AUTHORITIES:
        expect_registry_rejection(module, False, count_field, items_field, label)
        expect_registry_rejection(module, True, count_field, items_field, label)
        expect_registry_rejection(module, -1, count_field, items_field, label)
        expect_registry_rejection(module, 1, count_field, items_field, label)
        expect_registry_rejection(module, 0, count_field, items_field, label, items=[{"forged": True}])
        module.require_empty_registry({count_field: 0, items_field: []},
                                      count_field, items_field, label)

    expect_source_authority_rejection(module)

    print("PASS: compatibility foundation counts and canonical source authorities fail closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
