#!/usr/bin/env python3
"""Prove metrics scrape authority publication is atomic and transport-bound."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile-memory-os-metrics-scrape-status.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("metrics_scrape_atomic_negative_target", SCRIPT)
    require(spec is not None and spec.loader is not None, "cannot load metrics scrape reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(callback, expected: str, label: str) -> None:
    try:
        callback()
    except Exception as exc:
        require(expected in str(exc), f"{label}: unexpected rejection: {exc}")
    else:
        raise NegativeFailure(f"{label}: substitution was incorrectly accepted")


def main() -> int:
    module = load_module()
    original_bytes = STATUS.read_bytes()
    original_mode = STATUS.stat().st_mode & 0o7777

    original_replace = module.os.replace
    original_canonical_replace = module.CANONICAL_OS_REPLACE
    fake_replace = lambda _src, _dst: None
    try:
        module.os.replace = fake_replace
        module.CANONICAL_OS_REPLACE = fake_replace
        expect_rejection(
            module.enforce_runtime_authorities,
            "canonical os.replace transport authority drift",
            "paired os.replace",
        )
    finally:
        module.os.replace = original_replace
        module.CANONICAL_OS_REPLACE = original_canonical_replace

    original_writer = module.atomic_write_bytes
    original_canonical_writer = module.CANONICAL_ATOMIC_WRITE_BYTES
    fake_writer = lambda _path, _payload: None
    try:
        module.atomic_write_bytes = fake_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = fake_writer
        expect_rejection(
            module.enforce_runtime_authorities,
            "canonical atomic writer authority drift",
            "paired atomic writer",
        )
    finally:
        module.atomic_write_bytes = original_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = original_canonical_writer

    original_validator = module.validate_written_authority
    def fail_after_write() -> None:
        raise module.ReconcileFailure("controlled post-write failure")
    module.validate_written_authority = fail_after_write
    try:
        status = module.load(STATUS)
        status["asOf"] = "2099-01-01"
        try:
            module.write_transactionally(status)
        except module.ReconcileFailure as exc:
            require("controlled post-write failure" in str(exc), f"unexpected rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled post-write failure was accepted")
    finally:
        module.validate_written_authority = original_validator

    require(STATUS.read_bytes() == original_bytes, "status bytes changed after rollback")
    require((STATUS.stat().st_mode & 0o7777) == original_mode, "status mode changed after rollback")
    temp_pattern = f".{STATUS.name}.*.tmp"
    require(not list(STATUS.parent.glob(temp_pattern)), "temporary atomic authority file leaked")

    source = SCRIPT.read_text(encoding="utf-8")
    require("STATUS_PATH.write_text(" not in source, "direct status write_text regression")
    require("STATUS_PATH.write_bytes(" not in source, "direct status write_bytes rollback regression")

    print("PASS: metrics scrape authority uses immutable atomic transport and rollback")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"METRICS SCRAPE ATOMIC NEGATIVE FAILED: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
