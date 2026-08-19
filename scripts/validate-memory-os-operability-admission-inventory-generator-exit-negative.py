#!/usr/bin/env python3
"""Prove the operability inventory generator accepts only exact integer-zero validator exits."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_generator():
    spec = importlib.util.spec_from_file_location("memory_os_inventory_generator_exit_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load operability inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(generator: Any, value: Any, label: str) -> None:
    try:
        generator.exact_success(value, label)
    except SystemExit as exc:
        require(str(value) in str(exc), f"rejection lost validator result for {label}: {exc}")
        return
    raise Fail(f"non-exact validator success unexpectedly accepted: {label}={value!r}")


def main() -> int:
    require(GENERATOR.is_file(), "operability inventory generator missing")
    generator = load_generator()

    generator.exact_success(0, "integer zero")
    for value, label in (
        (False, "boolean false"),
        (True, "boolean true"),
        (1, "positive integer"),
        (-1, "negative integer"),
        ("0", "string zero"),
        (None, "null result"),
    ):
        expect_rejected(generator, value, label)

    print("Memory OS operability inventory generator exit-code negative PASS")
    print("exact integer zero accepted: true")
    print("boolean false accepted as success: false")
    print("boolean true accepted as success: false")
    print("nonzero/noninteger validator exits accepted: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY GENERATOR EXIT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
