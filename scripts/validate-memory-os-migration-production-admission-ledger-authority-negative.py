#!/usr/bin/env python3
"""Reject migration admission ledger writer/validator/lock authority substitution."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/memory_os_migration_production_admission_ledger.py"
ALTERNATE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-release-baseline-registry.py"
ALTERNATE_LOCK = ROOT / "contracts/operations/.migration-production-admission-ledger-negative.lock"


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_migration_production_admission_ledger_negative", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load migration production admission ledger helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(label: str, mutate) -> None:
    helper = load_helper()
    mutate(helper)
    try:
        helper.load_writer()
    except helper.LedgerBindingFailure:
        return
    raise RuntimeError(f"migration admission ledger helper accepted authority substitution: {label}")


def expect_ledger_rejected(label: str, mutate) -> None:
    helper = load_helper()
    mutate(helper)
    try:
        helper.validate_canonical_ledger()
    except helper.LedgerBindingFailure:
        return
    raise RuntimeError(f"migration admission ledger helper accepted authority substitution: {label}")


def main() -> int:
    expect_writer_rejected("writer executable", lambda helper: setattr(helper, "LEDGER_WRITER", ALTERNATE_WRITER))
    expect_ledger_rejected("validator executable", lambda helper: setattr(helper, "LEDGER_VALIDATOR", ALTERNATE_VALIDATOR))
    expect_writer_rejected("append lock", lambda helper: setattr(helper, "LEDGER_LOCK", ALTERNATE_LOCK))
    print("PASS: migration production admission ledger writer, validator and append-lock substitutions are rejected")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
