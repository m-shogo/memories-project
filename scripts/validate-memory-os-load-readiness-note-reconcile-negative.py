#!/usr/bin/env python3
"""Negative proof for canonical load-readiness note reconciliation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-load-readiness-note.py"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_load_readiness_note_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load load-readiness note reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority_substitution_rejected(module) -> None:
    original = CANONICAL_LOAD.read_bytes()
    substitutions = (
        ("LOAD_PATH", RECONCILER, "load contract authority drift"),
        ("LOAD_VALIDATOR", RECONCILER, "load validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        current = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            try:
                module.validate_authorities()
            except RuntimeError as exc:
                if expected not in str(exc):
                    raise RuntimeError(f"unexpected {attr} authority rejection: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted substituted authority: {attr}")
            if CANONICAL_LOAD.read_bytes() != original:
                raise RuntimeError(f"canonical load authority changed after rejected substitution: {attr}")
        finally:
            setattr(module, attr, current)


def main() -> int:
    module = load_module()
    original = CANONICAL_LOAD.read_bytes()
    authority_substitution_rejected(module)

    calls = 0
    original_validate = module.validate_canonical_load

    def controlled_validator() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            return
        raise SystemExit("synthetic post-write load authority rejection")

    module.validate_canonical_load = controlled_validator
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "synthetic post-write load authority rejection" not in str(exc):
                raise RuntimeError(f"unexpected rejection: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted synthetic post-write validator failure")

        if calls != 2:
            raise RuntimeError(f"canonical validator call count drift: {calls}")
        if CANONICAL_LOAD.read_bytes() != original:
            raise RuntimeError("load authority was not restored byte-for-byte after post-write rejection")
    finally:
        module.validate_canonical_load = original_validate
        CANONICAL_LOAD.write_bytes(original)

    if CANONICAL_LOAD.read_bytes() != original:
        raise RuntimeError("canonical load authority was not restored")
    print("PASS: load readiness-note reconcile pins canonical authority identity and rolls back rejected post-write authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
