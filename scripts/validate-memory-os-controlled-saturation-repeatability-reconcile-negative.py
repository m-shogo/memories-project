#!/usr/bin/env python3
"""Prove repeatability reconciliation pins authorities and cannot leave partial writes."""

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


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def run_authority_substitutions(module) -> None:
    substitutions = {
        "CONTRACT": module.LOAD,
        "RESULT": module.CONTRACT,
        "VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD": module.CONTRACT,
        "STATUS": module.LOAD,
        "WORKFLOW": module.VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()


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


def run_atomic_replace_failure(module) -> None:
    protected = (module.CONTRACT, module.LOAD, module.STATUS)
    before = {path: path.read_bytes() for path in protected}
    residues_before = set(path for authority in protected for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic repeatability atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTRACT),
                module.load(module.LOAD),
                module.load(module.STATUS),
            )
        except BaseException as exc:
            rejected = True
            if "synthetic repeatability atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("repeatability reconciler accepted synthetic atomic replacement failure")
        assert_unchanged(protected, before, "atomic replacement failure")
        residues_after = set(path for authority in protected for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("repeatability atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in before.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)


def main() -> int:
    module = load_module()
    run_authority_substitutions(module)
    run_prewrite_failure(module)
    run_postwrite_failure(module)
    run_atomic_replace_failure(module)
    print("Memory OS controlled saturation repeatability reconcile negative PASS")
    print("authority substitution plus pre-write/post-write/atomic failures are fail-closed")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
