#!/usr/bin/env python3
"""Focused negatives for rate-limit operation writer CLI authority identity."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/create-memory-os-rate-limit-operation-evidence.py"


def load_writer():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_writer_authority_negative", WRITER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load rate-limit operation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(writer, mutate, expected: str) -> None:
    originals = {
        "ROOT": writer.ROOT,
        "VALIDATOR_PATH": writer.VALIDATOR_PATH,
        "DEFAULT_LEDGER": writer.DEFAULT_LEDGER,
        "load_validator": writer.load_validator,
        "require_cli_execution_authority": writer.require_cli_execution_authority,
    }
    try:
        mutate(writer)
        try:
            writer.require_cli_execution_authority()
        except writer.WriterFailure as exc:
            if expected not in str(exc):
                raise AssertionError(f"unexpected authority rejection: {exc}") from exc
        else:
            raise AssertionError("substituted writer authority was incorrectly accepted")
    finally:
        for name, value in originals.items():
            setattr(writer, name, value)


def main() -> int:
    writer = load_writer()
    writer.require_cli_execution_authority()

    expect_rejection(
        writer,
        lambda module: setattr(module, "ROOT", ROOT / "docs"),
        "ROOT authority must remain canonical",
    )
    expect_rejection(
        writer,
        lambda module: setattr(
            module,
            "VALIDATOR_PATH",
            ROOT / "scripts/validate-memory-os-rate-limit.py",
        ),
        "VALIDATOR_PATH authority must remain canonical",
    )
    expect_rejection(
        writer,
        lambda module: setattr(module, "DEFAULT_LEDGER", ROOT / "docs/evidence"),
        "DEFAULT_LEDGER authority must remain canonical",
    )
    expect_rejection(
        writer,
        lambda module: setattr(module, "load_validator", lambda: None),
        "validator loader authority drift",
    )

    original_guard = writer.require_cli_execution_authority
    try:
        writer.require_cli_execution_authority = lambda: None
        try:
            writer.main()
        except writer.WriterFailure as exc:
            if "CLI guard authority drift" not in str(exc):
                raise AssertionError(f"unexpected CLI guard rejection: {exc}") from exc
        else:
            raise AssertionError("substituted CLI guard reached argument parsing")
    finally:
        writer.require_cli_execution_authority = original_guard

    if writer.ROOT != ROOT:
        raise AssertionError("canonical ROOT authority was not restored")
    if writer.VALIDATOR_PATH != ROOT / "scripts/validate-memory-os-rate-limit-operation-evidence.py":
        raise AssertionError("canonical validator authority was not restored")
    if writer.DEFAULT_LEDGER != ROOT / "docs/evidence/rate-limit-operations":
        raise AssertionError("canonical ledger authority was not restored")

    print("PASS: rate-limit operation writer CLI data authorities are immutable")
    print("PASS: rate-limit operation writer validator loader is immutable")
    print("PASS: rate-limit operation writer CLI guard cannot be bypassed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
