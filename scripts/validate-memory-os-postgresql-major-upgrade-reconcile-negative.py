#!/usr/bin/env python3
"""Negative proof for PostgreSQL major-upgrade authority transaction."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-postgresql-major-upgrade.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_postgresql_major_upgrade_reconcile_negative", RECONCILER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PostgreSQL major-upgrade reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_status = module.STATUS_PATH.read_bytes()
    contract = copy.deepcopy(module.load(module.CONTRACT_PATH))
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise RuntimeError("PostgreSQL upgrade readiness missing")
    readiness["exactSourcePassResultCommitted"] = True
    readiness["postgresql17LogicalForwardUpgradeExecuted"] = True

    source_sha = "0" * 40
    original_validator = module.validate_authority_chain
    calls: list[tuple[str, bool]] = []

    def reject_aggregate(commit_sha: str, *, require_reconciled: bool) -> None:
        calls.append((commit_sha, require_reconciled))
        if require_reconciled:
            raise module.ReconcileFailure("synthetic post-write aggregate rejection")

    module.validate_authority_chain = reject_aggregate
    try:
        try:
            module.commit_candidate(contract, status, source_sha)
        except module.ReconcileFailure as exc:
            if "synthetic post-write aggregate rejection" not in str(exc):
                raise
        else:
            raise RuntimeError("major-upgrade transaction accepted post-write aggregate rejection")
    finally:
        module.validate_authority_chain = original_validator

    if calls != [(source_sha, True)]:
        raise RuntimeError(f"major-upgrade validator call drift: {calls}")
    if module.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("PostgreSQL upgrade contract changed after rejected transaction")
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after rejected transaction")

    print("PASS: PostgreSQL major-upgrade reconcile rolls back after aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
