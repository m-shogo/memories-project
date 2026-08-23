#!/usr/bin/env python3
"""Prove production-equivalent foundation authority is exact and rollback is fail-closed."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-foundation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("production_foundation_reconcile", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load production-equivalent foundation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def prove_authority_identity(module) -> None:
    module.enforce_runtime_authorities()
    original_load = module.CANONICAL_LOAD_PATH.read_bytes()
    original_status = module.CANONICAL_STATUS_PATH.read_bytes()
    substitutions = (
        ("CONTRACT_PATH", module.LOAD_PATH, "dependency contract"),
        ("LOAD_PATH", module.STATUS_PATH, "load contract"),
        ("STATUS_PATH", module.LOAD_PATH, "production status"),
        ("DEPENDENCY_VALIDATOR", module.LOAD_INDEX_VALIDATOR, "dependency validator"),
        ("LOAD_INDEX_VALIDATOR", module.LOAD_VALIDATOR, "load index validator"),
        ("LOAD_VALIDATOR", module.OPERABILITY_VALIDATOR, "load validator"),
        ("OPERABILITY_VALIDATOR", module.LOAD_VALIDATOR, "operability validator"),
        (
            "WORKFLOW_PATH",
            ROOT / ".github/workflows/operability-contracts.yml",
            "foundation workflow",
        ),
    )
    for attribute, substitute, label in substitutions:
        original = getattr(module, attribute)
        try:
            setattr(module, attribute, substitute)
            try:
                module.enforce_runtime_authorities()
            except module.Fail as exc:
                require("authority drift" in str(exc) or "authority missing" in str(exc), f"{label} rejected for unrelated reason: {exc}")
            else:
                raise Fail(f"reconciler accepted authority substitution: {label}")
        finally:
            setattr(module, attribute, original)

    require(module.CANONICAL_LOAD_PATH.read_bytes() == original_load, "load authority changed after substitution rejection")
    require(module.CANONICAL_STATUS_PATH.read_bytes() == original_status, "status authority changed after substitution rejection")
    module.enforce_runtime_authorities()


def prove_validator_chain(module) -> None:
    observed: list[Path] = []
    original_run = module.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        module.run_validator = capture
        module.validate_current_authority()
    finally:
        module.run_validator = original_run

    expected = [
        module.DEPENDENCY_VALIDATOR.resolve(),
        module.LOAD_INDEX_VALIDATOR.resolve(),
        module.LOAD_VALIDATOR.resolve(),
        module.OPERABILITY_VALIDATOR.resolve(),
    ]
    require(observed == expected, f"foundation validator chain drift: {observed!r} != {expected!r}")


def prove_transaction_rollback(module) -> None:
    originals = {
        module.CANONICAL_LOAD_PATH: module.CANONICAL_LOAD_PATH.read_bytes(),
        module.CANONICAL_STATUS_PATH: module.CANONICAL_STATUS_PATH.read_bytes(),
    }
    load_contract = copy.deepcopy(load_json(module.CANONICAL_LOAD_PATH))
    status = copy.deepcopy(load_json(module.CANONICAL_STATUS_PATH))
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True

    original_validator = module.validate_current_authority

    def controlled_validator() -> None:
        raise module.Fail("controlled post-write production foundation validation failure")

    module.validate_current_authority = controlled_validator
    try:
        try:
            module.write_and_validate_transactionally(load_contract, status)
        except module.Fail as exc:
            require(
                "controlled post-write production foundation validation failure" in str(exc),
                f"unexpected rollback failure: {exc}",
            )
        else:
            raise Fail("controlled production foundation post-write failure was accepted")

        for path, original in originals.items():
            require(path.read_bytes() == original, f"authority was not rolled back byte-for-byte: {path.relative_to(ROOT)}")
    finally:
        module.validate_current_authority = original_validator
        for path, original in originals.items():
            if path.read_bytes() != original:
                path.write_bytes(original)


def main() -> int:
    module = load_module()
    prove_authority_identity(module)
    prove_validator_chain(module)
    prove_transaction_rollback(module)

    print("PASS: production-equivalent foundation exact data/executable authorities reject substitution")
    print("PASS: foundation validation includes dependency, load index, load and aggregate operability")
    print("PASS: post-write failure restores load authority and production status byte-for-byte")
    print("environment provisioned: false")
    print("production-equivalent dependencies: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"PRODUCTION FOUNDATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
