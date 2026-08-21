#!/usr/bin/env python3
"""Prove short stability direct reconcile pins canonical source authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-short-stability-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("short_stability_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load short stability reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def main() -> int:
    module = load_module()
    substitutions = {
        "CONTRACT_PATH": module.LOAD_PATH,
        "LOAD_PATH": module.CONTRACT_PATH,
        "STATUS_PATH": module.LOAD_PATH,
        "RESULT_PATH": module.CONTRACT_PATH,
        "SHORT_VALIDATOR": module.LOAD_VALIDATOR,
        "SOAK_RECONCILER": module.SHORT_VALIDATOR,
        "LOAD_VALIDATOR": module.SHORT_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    print("PASS: short stability direct reconcile source authorities are canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
