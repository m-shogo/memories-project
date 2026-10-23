#!/usr/bin/env python3
"""Negative proof for OPS-P0-007 strict snapshot atomic replacement."""

from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("ops_p0_007_snapshot_atomic_negative", GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_generator()
    atomic_write = getattr(module, "atomic_write_text", None)
    if not callable(atomic_write):
        raise SystemExit("strict snapshot atomic writer missing")

    target = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
    before = target.read_bytes()
    before_mode = stat.S_IMODE(target.stat().st_mode)
    temp_prefix = f".{target.name}."
    before_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}

    real_replace = os.replace
    target_replace_attempts = 0

    def reject_replace(src, dst):
        nonlocal target_replace_attempts
        if Path(dst) == target:
            target_replace_attempts += 1
            raise OSError("injected atomic replacement failure")
        return real_replace(src, dst)

    try:
        with mock.patch.object(module.os, "replace", side_effect=reject_replace):
            atomic_write(target, before.decode("utf-8") + "\n")
    except SystemExit as exc:
        if "cannot atomically write" not in str(exc) or "injected atomic replacement failure" not in str(exc):
            raise SystemExit(f"unexpected atomic-write failure: {exc}") from exc
    else:
        raise SystemExit("injected atomic replacement failure was accepted")

    if target_replace_attempts != 1:
        raise SystemExit(f"expected exactly one injected canonical replacement attempt, got {target_replace_attempts}")
    if target.read_bytes() != before:
        raise SystemExit("failed atomic replacement mutated canonical snapshot bytes")
    if stat.S_IMODE(target.stat().st_mode) != before_mode:
        raise SystemExit("failed atomic replacement mutated canonical snapshot mode")
    after_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}
    if after_temps != before_temps:
        raise SystemExit("failed atomic replacement left temporary residue")

    print("OPS-P0-007 strict snapshot atomic replacement negative proof: PASS")
    print("exact injected replacement failure and one canonical target attempt verified: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
