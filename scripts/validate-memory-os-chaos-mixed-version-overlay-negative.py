#!/usr/bin/env python3
"""Fail-closed negatives for mixed-version chaos overlay reconciliation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-mixed-version-overlay.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Failure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def load_reconciler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mixed_version_overlay_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load mixed-version overlay reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_failure(fn: Callable[[], object], needle: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - negative boundary intentionally catches the domain error.
        require(needle in str(exc), f"unexpected rejection: {exc}")
        return
    raise Failure(f"expected failure containing: {needle}")


def main() -> int:
    module = load_reconciler()
    original_status = STATUS.read_bytes()

    original_mixed_validator = module.MIXED_VERSION_VALIDATOR
    try:
        module.MIXED_VERSION_VALIDATOR = module.OPERABILITY_VALIDATOR
        expect_failure(module.require_canonical_authorities, "mixed-version validator authority substitution")
        require(STATUS.read_bytes() == original_status, "authority substitution mutated production status")
    finally:
        module.MIXED_VERSION_VALIDATOR = original_mixed_validator

    original_runner = module.run_validator
    calls: list[Path] = []
    try:
        module.run_validator = lambda path: calls.append(path)
        module.validate_source_authority()
        require(
            calls == [module.MIXED_VERSION_VALIDATOR, module.EXECUTION_VALIDATOR],
            "source validator chain drift",
        )
        calls.clear()
        module.validate_post_write_authority()
        require(
            calls == [
                module.MIXED_VERSION_VALIDATOR,
                module.EXECUTION_VALIDATOR,
                module.CHAOS_VALIDATOR,
                module.OPERABILITY_VALIDATOR,
            ],
            "post-write validator chain drift",
        )
    finally:
        module.run_validator = original_runner

    original_source_validation = module.validate_source_authority
    original_post_validation = module.validate_post_write_authority
    try:
        module.validate_source_authority = lambda: None

        def reject_after_write() -> None:
            raise module.Fail("synthetic post-write aggregate rejection")

        module.validate_post_write_authority = reject_after_write
        expect_failure(module.main, "synthetic post-write aggregate rejection")
        require(STATUS.read_bytes() == original_status, "post-write rejection did not roll back production status")
    finally:
        module.validate_source_authority = original_source_validation
        module.validate_post_write_authority = original_post_validation
        if STATUS.read_bytes() != original_status:
            STATUS.write_bytes(original_status)

    print("PASS: mixed-version overlay authority identity and transaction are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Failure as exc:
        print(f"MIXED-VERSION OVERLAY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
