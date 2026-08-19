#!/usr/bin/env python3
"""Negative proof for transactional load-readiness note reconciliation."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-load-readiness-note.py"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_load_readiness_note_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load load-readiness note reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    original = CANONICAL_LOAD.read_bytes()

    with tempfile.TemporaryDirectory(prefix="memory-os-load-readiness-note-") as temp_dir:
        fixture = Path(temp_dir) / "load-test-scenario-contract.v1.json"
        fixture.write_bytes(original)
        module.LOAD_PATH = fixture

        calls = 0

        def controlled_validator() -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                return
            raise SystemExit("synthetic post-write load authority rejection")

        module.validate_canonical_load = controlled_validator

        try:
            module.main()
        except SystemExit as exc:
            if "synthetic post-write load authority rejection" not in str(exc):
                raise RuntimeError(f"unexpected rejection: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted synthetic post-write validator failure")

        if calls != 2:
            raise RuntimeError(f"canonical validator call count drift: {calls}")
        if fixture.read_bytes() != original:
            raise RuntimeError("load authority was not restored byte-for-byte after post-write rejection")

    print("PASS: load readiness-note reconcile rolls back rejected post-write authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
