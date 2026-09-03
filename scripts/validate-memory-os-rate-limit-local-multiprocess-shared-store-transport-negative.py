#!/usr/bin/env python3
"""Pin ancestry execution authority for local shared-store evidence validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_local_shared_store_transport_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load local shared-store validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action) -> None:
    try:
        action()
    except Exception as exc:
        require(exc.__class__.__name__ == "Fail", f"unexpected rejection for {label}: {type(exc).__name__}: {exc}")
        print(f"PASS reject: {label}")
        return
    raise NegativeFailure(f"negative unexpectedly accepted: {label}")


def main() -> int:
    validator = load_validator()
    require(validator.main() == 0, "canonical local shared-store validator baseline failed")

    real_run = validator.subprocess.run
    validator.subprocess.run = lambda *args, **kwargs: SimpleNamespace(returncode=0)
    try:
        expect_rejected("git ancestry subprocess transport substitution", validator.main)
    finally:
        validator.subprocess.run = real_run

    real_source_is_ancestor = validator.source_is_ancestor
    validator.source_is_ancestor = lambda _source: True
    try:
        expect_rejected("source ancestry helper substitution", validator.main)
    finally:
        validator.source_is_ancestor = real_source_is_ancestor

    require(validator.main() == 0, "canonical local shared-store validator failed after transport negatives")
    print("PASS: local shared-store ancestry execution authority is fail-closed")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
