#!/usr/bin/env python3
"""Negative proof for the canonical OPS-P0-007 admission-chain full runner.

This test mutates only the imported in-memory runner. It never changes repository
files or creates operational evidence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-full.py"


class Fail(RuntimeError):
    pass


def load_target():
    spec = importlib.util.spec_from_file_location("admission_chain_full_negative_target", TARGET)
    if spec is None or spec.loader is None:
        raise Fail("cannot load canonical admission-chain full runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(label: str, mutation, invoke, expected: str) -> None:
    module = load_target()
    mutation(module)
    try:
        invoke(module)
    except module.Fail as exc:
        if expected not in str(exc):
            raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
        print(f"PASS negative: {label}")
        return
    raise Fail(f"{label}: weakened runner was accepted")


def main() -> int:
    expect_fail(
        "validation sequence removal",
        lambda m: setattr(m, "STEPS", m.STEPS[:-1]),
        lambda m: m.enforce_runtime_authority(),
        "validation sequence drift",
    )
    expect_fail(
        "subprocess transport substitution",
        lambda m: setattr(m.subprocess, "run", lambda *args, **kwargs: None),
        lambda m: m.enforce_execution_transport(),
        "subprocess transport drift",
    )
    expect_fail(
        "transport guard substitution",
        lambda m: setattr(m, "enforce_execution_transport", lambda: None),
        lambda m: m.enforce_runtime_authority(),
        "transport guard drift",
    )
    expect_fail(
        "execution function substitution",
        lambda m: setattr(m, "run_step", lambda *args, **kwargs: None),
        lambda m: m.main(),
        "execution function drift",
    )
    print("Admission-chain full runner negative validation PASS")
    print("repository mutation: false")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN FULL RUNNER NEGATIVE VALIDATION FAILED: {exc}")
        raise SystemExit(1)
