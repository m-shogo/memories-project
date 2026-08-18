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
            validator.validate_source_authorities()
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


def expect_nonempty_source_inventory_allowed(module, validator_mode: bool) -> None:
    releases = {"approvedReleaseCount": 2, "releases": [{"id": "rel_a"}, {"id": "rel_b"}]}
    rollback = {"rehearsalRequestCount": 1, "requests": [{"id": "rr_a"}]}
    parsers = {"reviewedArtifactCount": 1, "artifacts": [{"id": "pa_a"}]}
    release_contract = {"contract": "release"}
    rollback_contract = {"contract": "rollback"}
    values = {
        module.RELEASE_REGISTRY_PATH: releases,
        module.ROLLBACK_REGISTRY_PATH: rollback,
        module.PARSER_REGISTRY_PATH: parsers,
        module.RELEASE_CONTRACT_PATH: release_contract,
        module.ROLLBACK_CONTRACT_PATH: rollback_contract,
    }

    class ReleaseWriter:
        @staticmethod
        def validate_registry_for_append(registry, contract):
            require(registry is releases and contract is release_contract,
                    "release shared validator did not receive synthetic authority")

    class RollbackWriter:
        @staticmethod
        def validate_registry_for_append(registry, contract, release_registry):
            require(registry is rollback and contract is rollback_contract and release_registry is releases,
                    "rollback shared validator did not receive synthetic authority")

    class ParserWriter:
        @staticmethod
        def validate_registry_for_append(registry):
            require(registry is parsers,
                    "parser shared validator did not receive synthetic authority")

    writers = {
        module.RELEASE_WRITER_PATH: ReleaseWriter,
        module.ROLLBACK_WRITER_PATH: RollbackWriter,
        module.PARSER_WRITER_PATH: ParserWriter,
    }
    original_load = module.load
    original_load_module = module.load_module
    try:
        module.load = lambda path: values[path]
        module.load_module = lambda path, _name: writers[path]
        if validator_mode:
            module.validate_source_authorities()
        else:
            module.validate_source_registries()
    finally:
        module.load = original_load
        module.load_module = original_load_module


def main() -> int:
    reconciler = load_module(RECONCILER, "compatibility_foundation_status_reconciler")
    validator = load_module(FOUNDATION_VALIDATOR, "compatibility_foundation_validator")
    for field in reconciler.ZERO_COUNT_FIELDS:
        expect_rejection(reconciler, False, field)
        expect_rejection(reconciler, True, field)
        expect_rejection(reconciler, -1, field)
        reconciler.require_zero_count({field: 0}, field)
        expect_foundation_boolean_count_rejection(validator, field)

    expect_nonempty_source_inventory_allowed(reconciler, validator_mode=False)
    expect_nonempty_source_inventory_allowed(validator, validator_mode=True)

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

    print("PASS: compatibility foundations accept canonical non-empty source inventory while rejecting authority drift")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
