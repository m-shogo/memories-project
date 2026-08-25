#!/usr/bin/env python3
"""Prove capacity ramp direct reconcile pins canonical authorities and atomic rollback."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-capacity-ramp-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("capacity_ramp_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load capacity ramp reconciler")
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


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure(module) -> None:
    module.enforce_runtime_authorities()
    paths = (module.CONTRACT_PATH, module.LOAD_PATH, module.STATUS_PATH)
    originals = {path: path.read_bytes() for path in paths}
    residues_before = set(path for authority in paths for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic capacity atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_and_validate_transactionally(
                module.load(module.CONTRACT_PATH),
                module.load(module.LOAD_PATH),
                module.load(module.STATUS_PATH),
            )
        except BaseException as exc:
            rejected = True
            if "synthetic capacity atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("capacity ramp accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                raise RuntimeError(f"atomic replacement failure mutated {path.relative_to(ROOT)}")
        residues_after = set(path for authority in paths for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("capacity ramp atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)


def main() -> int:
    module = load_module()
    substitutions = {
        "CONTRACT_PATH": module.LOAD_PATH,
        "LOAD_PATH": module.CONTRACT_PATH,
        "STATUS_PATH": module.LOAD_PATH,
        "RESULT_PATH": module.CONTRACT_PATH,
        "CAPACITY_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.CAPACITY_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    verify_atomic_replace_failure(module)
    print("PASS: capacity ramp direct reconcile authorities are canonical and atomic")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
