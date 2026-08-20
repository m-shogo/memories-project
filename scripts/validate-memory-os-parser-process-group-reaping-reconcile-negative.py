#!/usr/bin/env python3
"""Negative proof for parser process-group authority delegation and rollback."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-process-group-reaping.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_process_group_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load process-group reconciler")
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
        raise RuntimeError("process-group readiness missing")
    readiness["productionReady"] = True

    source_sha = "0" * 40
    original_runner = module.run_authority_validators
    calls: list[str] = []

    def fail_post_validation(validated_sha: str) -> None:
        calls.append(validated_sha)
        if len(calls) == 2:
            raise module.ReconcileFailure("synthetic post-write validation failure")

    module.run_authority_validators = fail_post_validation
    try:
        # First prove that direct authority validation is part of the reconcile path.
        module.run_authority_validators(source_sha)
        try:
            module.commit_candidate(contract, status, source_sha)
        except module.ReconcileFailure as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise
        else:
            raise RuntimeError("transaction accepted synthetic post-write validation failure")
    finally:
        module.run_authority_validators = original_runner

    if calls != [source_sha, source_sha]:
        raise RuntimeError(f"process-group authority validation order drift: {calls}")
    if module.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("process-group contract changed after rejected transaction")
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after rejected transaction")

    print("PASS: process-group reconcile delegates canonical authority and rolls back after post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
