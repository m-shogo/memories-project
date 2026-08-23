#!/usr/bin/env python3
"""Fail-closed authority and rollback negatives for generation-binding status reconcile."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
ALTERNATE_FILE = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler(name: str):
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation status reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_substitution_rejected(attribute: str) -> None:
    reconciler = load_reconciler(f"memory_os_generation_status_authority_{attribute.lower()}")
    original_status = CANONICAL_STATUS.read_bytes()
    original_contract = CANONICAL_CONTRACT.read_bytes()
    setattr(reconciler, attribute, ALTERNATE_FILE)
    try:
        reconciler.main()
    except reconciler.Fail:
        pass
    else:
        raise Fail(f"{attribute} substitution unexpectedly accepted")
    require(CANONICAL_STATUS.read_bytes() == original_status, f"{attribute} rejection mutated canonical status")
    require(CANONICAL_CONTRACT.read_bytes() == original_contract, f"{attribute} rejection mutated canonical generation binding contract")
    print(f"PASS reject: {attribute} substitution fails closed without canonical mutation")


def prove_post_write_aggregate_rollback() -> None:
    reconciler = load_reconciler("memory_os_generation_status_aggregate_rollback")
    original_status = CANONICAL_STATUS.read_bytes()
    original_run_validator = reconciler.run_validator

    def fail_operability(path: Path, expected_relative: Path, label: str) -> None:
        if label == "operability validator":
            raise reconciler.Fail("synthetic aggregate operability rejection")
        original_run_validator(path, expected_relative, label)

    reconciler.run_validator = fail_operability
    try:
        reconciler.main()
    except reconciler.Fail as exc:
        require("synthetic aggregate operability rejection" in str(exc), "unexpected aggregate rejection")
    else:
        raise Fail("synthetic aggregate operability rejection unexpectedly accepted")
    require(CANONICAL_STATUS.read_bytes() == original_status, "aggregate rejection did not byte-restore canonical status")
    print("PASS rollback: post-write aggregate rejection restores canonical status byte-for-byte")


def main() -> int:
    require(ALTERNATE_FILE.is_file(), "alternate repository fixture missing")
    for attribute in ("CONTRACT", "VALIDATOR", "BACKUP_VALIDATOR", "OPERABILITY_VALIDATOR", "STATUS"):
        prove_substitution_rejected(attribute)
    prove_post_write_aggregate_rollback()
    print("Memory OS backup/restore generation status reconcile negative suite PASS")
    print("generation created: false")
    print("recovery objective created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION STATUS RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
