#!/usr/bin/env python3
"""Prove container-kill authority identity, atomic publication, and reconcile rollback remain fail-closed."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-container-kill-authority.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def load_module():
    spec = importlib.util.spec_from_file_location("container_kill_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load container-kill reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(fn, needle: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - negative authority boundary.
        if needle not in str(exc):
            raise SystemExit(f"unexpected rejection: {exc}") from exc
        return
    raise SystemExit(f"expected rejection containing: {needle}")


def expect_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-container-kill-atomic-") as tmp:
        root = Path(tmp)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic container-kill atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                if "synthetic container-kill atomic replacement failure" not in str(exc):
                    raise
            else:
                raise SystemExit("atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise SystemExit("atomic replacement failure mutated target bytes")
        if list(root.glob(f".{authority.name}.*.tmp")):
            raise SystemExit("atomic replacement failure left temp residue")


def main() -> int:
    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    module = load_module()

    source = RECONCILER.read_text(encoding="utf-8")
    for forbidden in ("LOAD_CONTRACT.write_text(", "STATUS.write_text(", "LOAD_CONTRACT.write_bytes(", "STATUS.write_bytes("):
        if forbidden in source:
            raise SystemExit(f"container-kill authority regressed to direct publication/rollback: {forbidden}")

    original_proof_validator = module.PROOF_VALIDATOR
    try:
        module.PROOF_VALIDATOR = module.LOAD_VALIDATOR
        expect_rejection(module.require_canonical_authorities, "proof validator authority substitution")
        if LOAD_CONTRACT.read_bytes() != original_load or STATUS.read_bytes() != original_status:
            raise SystemExit("authority substitution mutated canonical data")
    finally:
        module.PROOF_VALIDATOR = original_proof_validator

    expect_atomic_replace_failure(module)

    original_normalize = module.normalize_and_validate_authority
    try:
        def reject_after_write() -> None:
            raise module.ReconcileFailure("synthetic post-write aggregate failure")

        module.normalize_and_validate_authority = reject_after_write
        expect_rejection(module.main, "synthetic post-write aggregate failure")
        load_after = LOAD_CONTRACT.read_bytes()
        status_after = STATUS.read_bytes()
        if load_after != original_load:
            raise SystemExit("container-kill reconcile failed to roll back load authority")
        if status_after != original_status:
            raise SystemExit("container-kill reconcile failed to roll back production status")
    finally:
        module.normalize_and_validate_authority = original_normalize
        if LOAD_CONTRACT.read_bytes() != original_load:
            module.atomic_write_bytes(LOAD_CONTRACT, original_load)
        if STATUS.read_bytes() != original_status:
            module.atomic_write_bytes(STATUS, original_status)

    print("PASS: container-kill authority identity, atomic publication, and post-write rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
