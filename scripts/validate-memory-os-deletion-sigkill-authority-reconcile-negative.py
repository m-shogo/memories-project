#!/usr/bin/env python3
"""Prove SIGKILL authority reconcile publishes atomically and rolls back every canonical write."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-sigkill-authority.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def load_module():
    spec = importlib.util.spec_from_file_location("sigkill_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load SIGKILL reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-sigkill-atomic-") as temp_dir:
        root = Path(temp_dir)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                if "synthetic atomic replacement failure" not in str(exc):
                    raise
            else:
                raise AssertionError("atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise AssertionError("failed atomic replacement changed authority bytes")
        residue = list(root.glob(f".{authority.name}.*.tmp"))
        if residue:
            raise AssertionError(f"failed atomic replacement left temp residue: {residue!r}")


def main() -> int:
    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    module = load_module()
    expect_atomic_replace_failure(module)

    with tempfile.TemporaryDirectory(prefix="memory-os-sigkill-rollback-") as temp_dir:
        failing_validator = Path(temp_dir) / "fail-operability.py"
        failing_validator.write_text("raise SystemExit('synthetic post-write operability failure')\n", encoding="utf-8")
        module.OPERABILITY_VALIDATOR = failing_validator

        rejected = False
        try:
            module.main()
        except (subprocess.CalledProcessError, SystemExit):
            rejected = True

        load_after = LOAD_CONTRACT.read_bytes()
        status_after = STATUS.read_bytes()
        module.atomic_write_bytes(LOAD_CONTRACT, original_load)
        module.atomic_write_bytes(STATUS, original_status)

        if not rejected:
            raise SystemExit("SIGKILL reconcile unexpectedly accepted synthetic post-write validation failure")
        if load_after != original_load:
            raise SystemExit("SIGKILL reconcile failed to roll back load authority")
        if status_after != original_status:
            raise SystemExit("SIGKILL reconcile failed to roll back production status")
        residue = list(LOAD_CONTRACT.parent.glob(f".{LOAD_CONTRACT.name}.*.tmp"))
        residue += list(STATUS.parent.glob(f".{STATUS.name}.*.tmp"))
        if residue:
            raise SystemExit(f"SIGKILL reconcile left atomic temp residue: {residue!r}")

    print("PASS: SIGKILL reconcile atomic publication and post-write rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
