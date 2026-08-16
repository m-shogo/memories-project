#!/usr/bin/env python3
"""Prove repeatability reconciliation cannot leave partial derived authority writes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-repeatability.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repeatability_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repeatability reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    original_load = module.load

    def fail_on_status(path: Path):
        if path == module.STATUS:
            raise module.Fail("synthetic status read failure")
        return original_load(path)

    module.load = fail_on_status
    try:
        module.main()
    except module.Fail as exc:
        if str(exc) != "synthetic status read failure":
            raise
    else:
        raise RuntimeError("reconciler unexpectedly succeeded after synthetic status read failure")
    finally:
        module.load = original_load

    for path in protected:
        if path.read_bytes() != before[path]:
            raise RuntimeError(f"partial authority write after rejected reconcile: {path.relative_to(ROOT)}")

    print("Memory OS controlled saturation repeatability reconcile negative PASS")
    print("synthetic status read failure left CONTRACT/LOAD/STATUS byte-for-byte unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
