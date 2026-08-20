#!/usr/bin/env python3
"""Reject repo-contained executable substitutions in chaos scenario reconcilers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py"
V2_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py"
PARSER_RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py"
V1_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills.py"
V2_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"
PARSER_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-restart-matrix.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load chaos reconciler: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(callback, expected: str) -> None:
    try:
        callback()
    except Exception as exc:
        if expected not in str(exc):
            raise RuntimeError(f"unexpected authority rejection: {exc}") from exc
    else:
        raise RuntimeError(f"chaos reconciler accepted substituted authority: {expected}")


def validate_module(
    module,
    *,
    validator_attr: str,
    validator_substitute: Path,
    validator_error: str,
    reconciler_substitute: Path,
) -> None:
    source_sha = "0" * 40

    original_validator = getattr(module, validator_attr)
    try:
        setattr(module, validator_attr, validator_substitute)
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            validator_error,
        )
    finally:
        setattr(module, validator_attr, original_validator)

    original_operability = module.OPERABILITY_VALIDATOR
    try:
        module.OPERABILITY_VALIDATOR = validator_substitute
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            "operability validator authority drift",
        )
    finally:
        module.OPERABILITY_VALIDATOR = original_operability

    original_reconciler = module.CANONICAL_RECONCILER
    try:
        module.CANONICAL_RECONCILER = reconciler_substitute
        expect_rejection(
            module.load_canonical_normalizer,
            "chaos authority reconciler authority drift",
        )
    finally:
        module.CANONICAL_RECONCILER = original_reconciler


def main() -> int:
    for path in (
        V1_RECONCILER,
        V2_RECONCILER,
        PARSER_RECONCILER,
        V1_VALIDATOR,
        V2_VALIDATOR,
        PARSER_VALIDATOR,
    ):
        if not path.is_file():
            raise RuntimeError(f"authority fixture missing: {path.name}")

    validate_module(
        load_module(V1_RECONCILER, "memory_os_chaos_v1_authority_negative"),
        validator_attr="V1_VALIDATOR",
        validator_substitute=V2_VALIDATOR,
        validator_error="v1 failure-drill validator authority drift",
        reconciler_substitute=V2_VALIDATOR,
    )
    validate_module(
        load_module(V2_RECONCILER, "memory_os_chaos_v2_authority_negative"),
        validator_attr="V2_VALIDATOR",
        validator_substitute=V1_VALIDATOR,
        validator_error="v2 failure-drill validator authority drift",
        reconciler_substitute=V1_VALIDATOR,
    )
    validate_module(
        load_module(PARSER_RECONCILER, "memory_os_parser_restart_authority_negative"),
        validator_attr="PARSER_VALIDATOR",
        validator_substitute=V1_VALIDATOR,
        validator_error="parser restart validator authority drift",
        reconciler_substitute=V1_VALIDATOR,
    )

    print("PASS: v1/v2/parser-restart reconcile executable substitutions are rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
