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


def assert_unchanged(protected, before, label: str) -> None:
    for path in protected:
        if path.read_bytes() != before[path]:
            raise RuntimeError(f"partial authority write after {label}: {path.relative_to(ROOT)}")


def run_prewrite_failure(module) -> None:
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

    assert_unchanged(protected, before, "rejected pre-write reconcile")


def run_postwrite_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    contract = module.load(module.CONTRACT)
    load_contract = module.load(module.LOAD)
    status = module.load(module.STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True
    original_validators = module.run_post_write_validators

    def fail_after_write() -> None:
        raise RuntimeError("synthetic post-write repeatability validation failure")

    module.run_post_write_validators = fail_after_write
    try:
        try:
            module.write_transactionally(contract, load_contract, status)
        except RuntimeError as exc:
            if str(exc) != "synthetic post-write repeatability validation failure":
                raise
        else:
            raise RuntimeError("reconciler unexpectedly accepted post-write validation failure")
    finally:
        module.run_post_write_validators = original_validators

    assert_unchanged(protected, before, "post-write validation rollback")


def main() -> int:
    module = load_module()
    run_prewrite_failure(module)
    run_postwrite_failure(module)
    print("Memory OS controlled saturation repeatability reconcile negative PASS")
    print("pre-write and post-write failures leave CONTRACT/LOAD/STATUS byte-for-byte unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
