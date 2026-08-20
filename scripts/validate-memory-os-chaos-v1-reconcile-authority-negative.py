#!/usr/bin/env python3
"""Reject repo-contained executable substitutions in the v1 chaos reconciler."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_chaos_v1_authority_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v1 chaos reconciler")
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
        raise RuntimeError(f"v1 chaos reconciler accepted substituted authority: {expected}")


def main() -> int:
    if not SUBSTITUTE.is_file():
        raise RuntimeError("substitute validator fixture missing")

    module = load_module()
    source_sha = "0" * 40

    original_v1 = module.V1_VALIDATOR
    try:
        module.V1_VALIDATOR = SUBSTITUTE
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            "v1 failure-drill validator authority drift",
        )
    finally:
        module.V1_VALIDATOR = original_v1

    original_operability = module.OPERABILITY_VALIDATOR
    try:
        module.OPERABILITY_VALIDATOR = SUBSTITUTE
        expect_rejection(
            lambda: module.validate_authority_chain(source_sha),
            "operability validator authority drift",
        )
    finally:
        module.OPERABILITY_VALIDATOR = original_operability

    original_reconciler = module.CANONICAL_RECONCILER
    try:
        module.CANONICAL_RECONCILER = SUBSTITUTE
        expect_rejection(
            module.load_canonical_normalizer,
            "chaos authority reconciler authority drift",
        )
    finally:
        module.CANONICAL_RECONCILER = original_reconciler

    print("PASS: v1 chaos reconcile executable substitutions are rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
