#!/usr/bin/env python3
"""Prove controlled saturation direct reconcile pins canonical source authorities and atomic rollback."""

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


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure(module) -> None:
    module.enforce_runtime_authorities()
    paths = module.TRANSACTION_PATHS
    originals = {path: path.read_bytes() for path in paths}
    residues_before = set(path for authority in paths for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic controlled saturation atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTROLLED_CONTRACT),
                module.load(module.LOAD_CONTRACT),
                module.load(module.STATUS_PATH),
                module.load(module.RESULT_PATH)["commitSha"],
            )
        except BaseException as exc:
            rejected = True
            if "synthetic controlled saturation atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("controlled saturation accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                raise RuntimeError(f"atomic replacement failure mutated {path.relative_to(ROOT)}")
        residues_after = set(path for authority in paths for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("controlled saturation atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)


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
    verify_atomic_replace_failure(module)
    print("PASS: controlled saturation direct reconcile source authorities are canonical and atomic")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
