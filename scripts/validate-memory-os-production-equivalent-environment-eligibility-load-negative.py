#!/usr/bin/env python3
"""Prove semantic environment-generation eligibility authority fails closed on unreadable inputs."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-eligibility.py"
HELPER_SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_environment_eligibility_load_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load environment eligibility validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(VALIDATOR.is_file(), "environment eligibility validator missing")
    require(HELPER_SUBSTITUTE.is_file(), "repo-contained helper substitute missing")
    validator = load_validator()

    with tempfile.TemporaryDirectory(prefix="memory-os-environment-eligibility-load-negative-") as tmp:
        root = Path(tmp)
        malformed = root / "invalid-utf8.json"
        malformed.write_bytes(b"{\xff}")
        expect_rejected("invalid UTF-8 eligibility authority", lambda: validator.load(malformed), validator.Fail)
        expect_rejected("missing eligibility authority", lambda: validator.load(root / "missing.json"), validator.Fail)

    original_helper = validator.HELPER
    try:
        validator.HELPER = HELPER_SUBSTITUTE
        expect_rejected("repo-contained eligibility helper substitution", validator.load_helper, validator.Fail)
    finally:
        validator.HELPER = original_helper

    print("Memory OS production-equivalent environment eligibility load negative PASS")
    print("invalid UTF-8 authority accepted: false")
    print("missing authority accepted: false")
    print("repo-contained helper substitution accepted: false")
    print("canonical authority mutated: false")
    print("production evidence: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT ELIGIBILITY LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
