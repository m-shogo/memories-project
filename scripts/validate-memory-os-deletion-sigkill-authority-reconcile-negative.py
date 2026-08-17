#!/usr/bin/env python3
"""Prove SIGKILL authority reconcile rolls back every canonical write on post-write validation failure."""

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


def main() -> int:
    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    module = load_module()

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
        LOAD_CONTRACT.write_bytes(original_load)
        STATUS.write_bytes(original_status)

        if not rejected:
            raise SystemExit("SIGKILL reconcile unexpectedly accepted synthetic post-write validation failure")
        if load_after != original_load:
            raise SystemExit("SIGKILL reconcile failed to roll back load authority")
        if status_after != original_status:
            raise SystemExit("SIGKILL reconcile failed to roll back production status")

    print("PASS: SIGKILL reconcile post-write failure rolls back all canonical authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
