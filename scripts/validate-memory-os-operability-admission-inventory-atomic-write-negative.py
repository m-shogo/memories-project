#!/usr/bin/env python3
"""Negative proof for operability admission inventory atomic replacement."""

from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("operability_inventory_atomic_negative", GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load operability admission inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_generator()
    atomic_write = getattr(module, "atomic_write_text", None)
    if not callable(atomic_write):
        raise SystemExit("operability admission inventory atomic writer missing")

    target = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
    before = target.read_bytes()
    before_mode = stat.S_IMODE(target.stat().st_mode)
    temp_prefix = f".{target.name}."
    before_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}

    real_replace = os.replace

    def reject_replace(src, dst):
        if Path(dst) == target:
            raise OSError("injected atomic replacement failure")
        return real_replace(src, dst)

    try:
        with mock.patch.object(module.os, "replace", side_effect=reject_replace):
            atomic_write(target, before.decode("utf-8") + "\n")
    except SystemExit as exc:
        if "cannot atomically write" not in str(exc):
            raise SystemExit(f"unexpected atomic-write failure: {exc}") from exc
    else:
        raise SystemExit("injected atomic replacement failure was accepted")

    if target.read_bytes() != before:
        raise SystemExit("failed atomic replacement mutated canonical inventory bytes")
    if stat.S_IMODE(target.stat().st_mode) != before_mode:
        raise SystemExit("failed atomic replacement mutated canonical inventory mode")
    after_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}
    if after_temps != before_temps:
        raise SystemExit("failed atomic replacement left temporary residue")

    print("operability admission inventory atomic replacement negative proof: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
