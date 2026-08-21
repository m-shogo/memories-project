#!/usr/bin/env python3
"""Prove controlled saturation direct reconcile pins canonical source authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-ramp-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("controlled_saturation_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load controlled saturation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except SystemExit:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def main() -> int:
    module = load_module()
    substitutions = {
        "CONTROLLED_CONTRACT": module.LOAD_CONTRACT,
        "LOAD_CONTRACT": module.CONTROLLED_CONTRACT,
        "STATUS_PATH": module.LOAD_CONTRACT,
        "RESULT_PATH": module.CONTROLLED_CONTRACT,
        "CONTROLLED_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.CONTROLLED_VALIDATOR,
        "LOAD_INDEX_VALIDATOR": module.LOAD_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "WORKFLOW": module.CONTROLLED_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    print("PASS: controlled saturation direct reconcile source authorities are canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
