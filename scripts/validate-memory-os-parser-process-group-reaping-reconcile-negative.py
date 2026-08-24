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


def expect_rejection(callback, expected: str) -> None:
    try:
        callback()
    except Exception as exc:
        if expected not in str(exc):
            raise RuntimeError(f"unexpected process-group authority rejection: {exc}") from exc
    else:
        raise RuntimeError(f"process-group reconciler accepted invalid authority: {expected}")


def main() -> int:
    module = load_module()

    for attr, substitute, expected in (
        ("CONTRACT_PATH", ROOT / "README.md", "process-group contract authority drift"),
        ("RESULT_PATH", ROOT / "README.md", "process-group result authority drift"),
        ("STATUS_PATH", ROOT / "SECURITY.md", "production operability status authority drift"),
    ):
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            expect_rejection(module.enforce_data_authorities, expected)
        finally:
            setattr(module, attr, original)

    source_sha = "0" * 40
    for attr, substitute, expected in (
        ("PROCESS_GROUP_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py", "process-group validator authority drift"),
        ("OPERABILITY_VALIDATOR", ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py", "operability validator authority drift"),
    ):
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            expect_rejection(lambda: module.run_authority_validators(source_sha), expected)
        finally:
            setattr(module, attr, original)

    original_contract = module.CONTRACT_PATH.read_bytes()
    original_status = module.STATUS_PATH.read_bytes()
    contract = copy.deepcopy(module.load(module.CONTRACT_PATH))
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise RuntimeError("process-group readiness missing")
    readiness["productionReady"] = True

    original_runner = module.run_authority_validators
    original_atomic_writer = module.atomic_write_bytes
    calls: list[str] = []
    atomic_calls: list[tuple[Path, bytes]] = []

    def tracked_atomic_write(path: Path, payload: bytes) -> None:
        atomic_calls.append((path, bytes(payload)))
        original_atomic_writer(path, payload)

    def fail_post_validation(validated_sha: str) -> None:
        calls.append(validated_sha)
        if len(calls) == 2:
            raise module.ReconcileFailure("synthetic post-write validation failure")

    module.atomic_write_bytes = tracked_atomic_write
    module.run_authority_validators = fail_post_validation
    try:
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
        module.atomic_write_bytes = original_atomic_writer

    if calls != [source_sha, source_sha]:
        raise RuntimeError(f"process-group authority validation order drift: {calls}")
    expected_paths = [
        module.CONTRACT_PATH,
        module.STATUS_PATH,
        module.CONTRACT_PATH,
        module.STATUS_PATH,
    ]
    if [path for path, _payload in atomic_calls] != expected_paths:
        raise RuntimeError(f"process-group atomic transaction order drift: {atomic_calls}")
    if atomic_calls[-2][1] != original_contract or atomic_calls[-1][1] != original_status:
        raise RuntimeError("process-group atomic rollback payload drift")
    if module.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("process-group contract changed after rejected transaction")
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after rejected transaction")

    contract = copy.deepcopy(module.load(module.CONTRACT_PATH))
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    canonical_replace = module.os.replace

    def reject_replace(_source, _target) -> None:
        raise OSError("synthetic atomic replacement rejection")

    try:
        module.os.replace = reject_replace
        expect_rejection(
            lambda: module.commit_candidate(contract, status, source_sha),
            "cannot atomically write authority",
        )
    finally:
        module.os.replace = canonical_replace
    if module.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("atomic replacement failure mutated process-group contract")
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("atomic replacement failure mutated Production Status")
    residues = [
        *module.CONTRACT_PATH.parent.glob(f".{module.CONTRACT_PATH.name}.*.tmp"),
        *module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp"),
    ]
    if residues:
        raise RuntimeError(f"atomic replacement failure left process-group temp authority residue: {residues}")

    print("PASS: process-group reconcile pins data/executable authority, publishes atomically, and rolls back after post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
