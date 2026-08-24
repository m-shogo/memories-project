#!/usr/bin/env python3
"""Prove typed non-resurrection validator execution transport cannot be substituted."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_typed_transport_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical typed validator missing or symlinked")
    validator = load_validator()

    original_subprocess_run = validator.subprocess.run
    original_spec_from_file_location = validator.importlib.util.spec_from_file_location
    original_module_from_spec = validator.importlib.util.module_from_spec
    original_guard = validator.enforce_execution_transport

    try:
        validator.subprocess.run = lambda *args, **kwargs: None
        expect_rejected("typed subprocess transport substitution", validator.main, validator.Fail)
    finally:
        validator.subprocess.run = original_subprocess_run

    try:
        validator.importlib.util.spec_from_file_location = lambda *args, **kwargs: None
        expect_rejected("typed import spec transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.spec_from_file_location = original_spec_from_file_location

    try:
        validator.importlib.util.module_from_spec = lambda *args, **kwargs: None
        expect_rejected("typed module loader transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.module_from_spec = original_module_from_spec

    try:
        validator.enforce_execution_transport = lambda: None
        expect_rejected("typed execution guard substitution", validator.main, validator.Fail)
    finally:
        validator.enforce_execution_transport = original_guard

    print("Typed non-resurrection execution transport negative suite PASS")
    print("subprocess/import loader/guard substitution accepted: false")
    print("typed evidence created: false")
    print("production evidence: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
