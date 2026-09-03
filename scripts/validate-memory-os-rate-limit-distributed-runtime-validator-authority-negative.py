#!/usr/bin/env python3
"""Prove distributed runtime validator execution authorities cannot be substituted."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-distributed-runtime.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_runtime_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load distributed runtime validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {label}")
        return
    except Exception as exc:
        raise Fail(f"{label} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {label}")


def main() -> int:
    validator = load_validator()
    validator.require_runtime_authorities()
    canonical_registry_before = validator.REGISTRY.read_bytes()

    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-runtime-validator-") as temp_dir:
        outside = Path(temp_dir) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        path_attributes = (
            "CONTRACT",
            "REGISTRY",
            "POLICY",
            "GEN_REGISTRY",
            "GEN_WRITER",
            "WRITER",
            "VALIDATOR",
            "RECONCILER",
            "WORKFLOW",
            "STATUS",
            "LOCK",
        )
        for attribute in path_attributes:
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, outside)
                expect_rejected(
                    f"distributed runtime validator {attribute} substitution",
                    validator.require_runtime_authorities,
                    validator.Fail,
                )
            finally:
                setattr(validator, attribute, original)

        helper_attributes = (
            "require",
            "require_count",
            "load",
            "load_module",
            "load_writer",
            "validate_writer_authority",
            "validate_reconciler_authority",
            "validate_generation_authority",
            "validate_registry_for_append",
        )
        for attribute in helper_attributes:
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, lambda *args, **kwargs: [] if attribute.startswith("validate_") else {})
                expect_rejected(
                    f"distributed runtime validator {attribute} execution substitution",
                    validator.require_runtime_authorities,
                    validator.Fail,
                )
            finally:
                setattr(validator, attribute, original)

        real_guard = validator.require_runtime_authorities
        validator.require_runtime_authorities = lambda: None
        try:
            expect_rejected(
                "distributed runtime validator main guard substitution",
                validator.main,
                validator.Fail,
            )
        finally:
            validator.require_runtime_authorities = real_guard

        guard_defaults = real_guard.__defaults__
        require(guard_defaults is not None, "distributed runtime guard defaults missing")
        real_guard.__defaults__ = (ROOT / "contracts", guard_defaults[1], guard_defaults[2])
        try:
            expect_rejected(
                "distributed runtime validator guard default mutation",
                validator.main,
                validator.Fail,
            )
        finally:
            real_guard.__defaults__ = guard_defaults

        validator.require_runtime_authorities = lambda: None
        real_guard.__defaults__ = (ROOT / "contracts", guard_defaults[1], guard_defaults[2])
        try:
            expect_rejected(
                "paired distributed runtime guard and default substitution",
                validator.main,
                validator.Fail,
            )
        finally:
            validator.require_runtime_authorities = real_guard
            real_guard.__defaults__ = guard_defaults

    validator.require_runtime_authorities()
    require(validator.main() == 0, "canonical distributed runtime validator failed after authority negatives")
    require(validator.REGISTRY.read_bytes() == canonical_registry_before,
            "distributed runtime validator authority negative mutated canonical registry")
    print("Memory OS distributed rate-limit runtime validator authority negative suite PASS")
    print("validator data/executable/helper substitution accepted: false")
    print("runtime guard paired substitution accepted: false")
    print("distributed runtime evidence generated: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME VALIDATOR AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
