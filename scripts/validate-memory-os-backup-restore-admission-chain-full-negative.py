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
    original_subprocess_run = module.subprocess.run
    original_sys_executable = module.sys.executable
    try:
        mutation(module)
        try:
            invoke(module)
        except module.Fail as exc:
            if expected not in str(exc):
                raise Fail(f"{label}: wrong fail-closed diagnostic: {exc}") from exc
            print(f"PASS negative: {label}")
            return
        raise Fail(f"{label}: weakened runner was accepted")
    finally:
        # subprocess and sys are shared imported modules; never leak transport or
        # interpreter mutations into a later case or its freshly imported target.
        module.subprocess.run = original_subprocess_run
        module.sys.executable = original_sys_executable


def main() -> int:
    expect_fail(
        "repository root substitution",
        lambda m: setattr(m, "ROOT", ROOT / "scripts"),
        lambda m: m.enforce_runtime_authority(),
        "repository root drift",
    )
    expect_fail(
        "self path substitution",
        lambda m: setattr(m, "SELF_REL", Path("scripts/validate-memory-os-backup-restore-admission-chain.py")),
        lambda m: m.enforce_runtime_authority(),
        "self path drift",
    )
    expect_fail(
        "script repository escape",
        lambda m: None,
        lambda m: m.canonical_script("../outside-validator.py"),
        "validation authority missing or escapes repository",
    )
    expect_fail(
        "script lexical alias",
        lambda m: None,
        lambda m: m.canonical_script("scripts/../scripts/validate-memory-os-backup-restore-admission-chain-full.py"),
        "validation authority drift",
    )
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
        "Python executable substitution",
        lambda m: setattr(m.sys, "executable", str(ROOT)),
        lambda m: m.enforce_execution_transport(),
        "Python executable drift",
    )
    expect_fail(
        "transport guard substitution",
        lambda m: setattr(m, "enforce_execution_transport", lambda: None),
        lambda m: m.enforce_runtime_authority(),
        "transport guard drift",
    )
    expect_fail(
        "script resolver substitution",
        lambda m: setattr(m, "canonical_script", lambda relative: ROOT / relative),
        lambda m: m.run_step(m.STEPS[0][0], m.STEPS[0][1]),
        "script resolver drift",
    )
    expect_fail(
        "authority guard substitution",
        lambda m: setattr(m, "enforce_runtime_authority", lambda: None),
        lambda m: m.main(),
        "authority guard drift",
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
