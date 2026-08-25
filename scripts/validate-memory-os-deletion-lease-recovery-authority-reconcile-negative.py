#!/usr/bin/env python3
"""Prove lease-recovery authority reconcile is canonical, atomic and rollback-safe."""

from __future__ import annotations

import importlib.util
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-lease-recovery-authority.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def load_module():
    spec = importlib.util.spec_from_file_location("lease_recovery_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load lease-recovery reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.require_canonical_authorities()
        except SystemExit:
            pass
        else:
            raise AssertionError(f"lease authority substitution accepted: {attr}")
    finally:
        setattr(module, attr, original)


def expect_atomic_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-lease-authority-atomic-") as temp_dir:
        root = Path(temp_dir)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        authority.chmod(0o640)
        original_mode = stat.S_IMODE(authority.stat().st_mode)
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic lease authority replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.CANONICAL_ATOMIC_WRITE_BYTES(authority, b"after\n")
            except OSError as exc:
                if "synthetic lease authority replacement failure" not in str(exc):
                    raise
            else:
                raise AssertionError("lease authority atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise AssertionError("failed lease atomic replacement changed authority bytes")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise AssertionError("failed lease atomic replacement changed authority mode")
        if list(root.glob(f".{authority.name}.*.tmp")):
            raise AssertionError("failed lease atomic replacement left temp residue")

        module.CANONICAL_ATOMIC_WRITE_BYTES(authority, b"after\n")
        if authority.read_bytes() != b"after\n":
            raise AssertionError("successful lease atomic replacement did not update authority")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise AssertionError("successful lease atomic replacement changed authority mode")


def expect_post_write_rollback(module) -> None:
    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    original_load_mode = stat.S_IMODE(LOAD_CONTRACT.stat().st_mode)
    original_status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    original_operability_bytes = module.OPERABILITY_VALIDATOR.read_bytes()
    original_operability_mode = stat.S_IMODE(module.OPERABILITY_VALIDATOR.stat().st_mode)
    failing_bytes = b"raise SystemExit('synthetic post-write operability failure')\n"

    try:
        module.CANONICAL_ATOMIC_WRITE_BYTES(module.OPERABILITY_VALIDATOR, failing_bytes)
        rejected = False
        try:
            module.main()
        except BaseException:
            rejected = True
        if not rejected:
            raise AssertionError("lease-recovery reconcile accepted synthetic post-write validation failure")
        if LOAD_CONTRACT.read_bytes() != original_load:
            raise AssertionError("lease-recovery reconcile failed to roll back load authority")
        if STATUS.read_bytes() != original_status:
            raise AssertionError("lease-recovery reconcile failed to roll back production status")
        if stat.S_IMODE(LOAD_CONTRACT.stat().st_mode) != original_load_mode:
            raise AssertionError("lease-recovery reconcile changed load authority mode")
        if stat.S_IMODE(STATUS.stat().st_mode) != original_status_mode:
            raise AssertionError("lease-recovery reconcile changed production status mode")
    finally:
        module.CANONICAL_ATOMIC_WRITE_BYTES(module.OPERABILITY_VALIDATOR, original_operability_bytes)
        module.OPERABILITY_VALIDATOR.chmod(original_operability_mode)
        module.CANONICAL_ATOMIC_WRITE_BYTES(LOAD_CONTRACT, original_load)
        module.CANONICAL_ATOMIC_WRITE_BYTES(STATUS, original_status)

    residue = list(LOAD_CONTRACT.parent.glob(f".{LOAD_CONTRACT.name}.*.tmp"))
    residue += list(STATUS.parent.glob(f".{STATUS.name}.*.tmp"))
    if residue:
        raise AssertionError(f"lease authority rollback left temp residue: {residue!r}")


def main() -> int:
    module = load_module()
    substitutions = {
        "PROOF_CONTRACT": module.LOAD_CONTRACT,
        "PROOF_RESULT": module.PROOF_CONTRACT,
        "PROOF_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_CONTRACT": module.PROOF_CONTRACT,
        "STATUS": module.LOAD_CONTRACT,
        "READINESS_NORMALIZER": module.LOAD_VALIDATOR,
        "MISSING_EVIDENCE_NORMALIZER": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.PROOF_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_authority_rejection(module, attr, replacement)
    module.require_canonical_authorities()

    original_run = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: None
    try:
        try:
            module.require_canonical_authorities()
        except SystemExit:
            pass
        else:
            raise AssertionError("lease authority accepted substituted subprocess transport")
    finally:
        module.subprocess.run = original_run

    original_writer = module.atomic_write_bytes
    module.atomic_write_bytes = lambda _path, _data: None
    try:
        try:
            module.require_canonical_authorities()
        except SystemExit:
            pass
        else:
            raise AssertionError("lease authority accepted substituted atomic writer")
    finally:
        module.atomic_write_bytes = original_writer

    expect_atomic_failure(module)
    module.require_canonical_authorities()
    expect_post_write_rollback(module)
    module.require_canonical_authorities()

    print("PASS: lease-recovery authority pins canonical data/execution paths, atomic publication, mode and rollback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
