#!/usr/bin/env python3
"""Focused negatives for shared migration operation validation authority."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts/migration_operation_evidence_lib.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_lib():
    spec = importlib.util.spec_from_file_location(
        "memory_os_migration_operation_library_authority_negative", LIB
    )
    require(spec is not None and spec.loader is not None, "cannot load migration operation library")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(call, error_type, expected: str) -> None:
    try:
        call()
    except error_type as exc:
        require(expected in str(exc), f"unexpected authority rejection: {exc}")
    else:
        raise NegativeFailure(f"expected rejection containing: {expected}")


def main() -> int:
    lib = load_lib()
    lib.require_library_authorities()

    cases = (
        ("ROOT", ROOT / "docs", "repository authority substitution rejected"),
        (
            "CONTRACT_PATH",
            ROOT / "contracts/operations/migration-lifecycle-contract.v1.json",
            "contract authority substitution rejected",
        ),
        (
            "LIFECYCLE_PATH",
            ROOT / "contracts/operations/migration-operation-evidence-contract.v1.json",
            "lifecycle authority substitution rejected",
        ),
    )
    originals = {name: getattr(lib, name) for name, _, _ in cases}
    try:
        for name, substitute, expected in cases:
            setattr(lib, name, substitute)
            try:
                expect_rejection(
                    lib.require_library_authorities,
                    lib.EvidenceValidationError,
                    expected,
                )
                expect_rejection(
                    lambda: lib.validate_record({}),
                    lib.EvidenceValidationError,
                    expected,
                )
            finally:
                setattr(lib, name, originals[name])

        original_guard = lib.require_library_authorities
        lib.require_library_authorities = lambda: None
        try:
            expect_rejection(
                lambda: lib.validate_record({}),
                lib.EvidenceValidationError,
                "authority guard substitution rejected",
            )
        finally:
            lib.require_library_authorities = original_guard
    finally:
        for name, value in originals.items():
            setattr(lib, name, value)

    lib.require_library_authorities()
    print("PASS: migration operation shared validation paths remain canonical")
    print("PASS: migration operation shared validation guard cannot be bypassed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
