#!/usr/bin/env python3
"""Prove client-baseline multi-authority reconcile rolls back on post-write validation failure."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_client_baseline_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load client baseline reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_reconciler()
    paths = (module.CONTRACT, module.SUPPORT, module.STATUS)
    original = {path: path.read_bytes() for path in paths}
    observed_post_write_failure = False

    def controlled_validator(path: Path, label: str) -> None:
        nonlocal observed_post_write_failure
        if label == "post-write operability validator":
            observed_post_write_failure = True
            raise module.Fail("synthetic post-write operability validation failure")

    module.run_validator = controlled_validator
    try:
        try:
            module.main()
        except module.Fail as exc:
            if "synthetic post-write operability validation failure" not in str(exc):
                raise AssertionError(f"unexpected reconcile failure: {exc}") from exc
        else:
            raise AssertionError("reconcile unexpectedly succeeded after synthetic post-write failure")

        if not observed_post_write_failure:
            raise AssertionError("synthetic post-write validator was not reached")
        for path in paths:
            if path.read_bytes() != original[path]:
                raise AssertionError(f"reconcile rollback changed canonical authority: {path.relative_to(ROOT)}")
    finally:
        for path in paths:
            if path.read_bytes() != original[path]:
                path.write_bytes(original[path])

    print("PASS: client baseline reconcile rolls back all canonical authority after post-write validation failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
