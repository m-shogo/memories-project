#!/usr/bin/env python3
"""Negative proof for parser process-group authority delegation and rollback."""

from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
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


def prove_atomic_transport_binding(module) -> None:
    canonical_replace = module.os.replace

    def reject_mutable_replace(*_args, **_kwargs) -> None:
        raise RuntimeError("mutable os.replace transport was invoked")

    with tempfile.TemporaryDirectory(prefix="process-group-atomic-negative-") as temp_dir:
        target = Path(temp_dir) / "authority.json"
        target.write_bytes(b"before\n")
        os.chmod(target, 0o640)
        expected_mode = target.stat().st_mode & 0o7777
        module.os.replace = reject_mutable_replace
        try:
            module.atomic_write_bytes(target, b"after\n")
        finally:
            module.os.replace = canonical_replace

        if target.read_bytes() != b"after\n":
            raise RuntimeError("bound process-group atomic writer did not replace payload")
        if target.stat().st_mode & 0o7777 != expected_mode:
            raise RuntimeError("bound process-group atomic writer did not preserve mode")
        residues = list(target.parent.glob(f".{target.name}.*.tmp"))
        if residues:
            raise RuntimeError(f"bound process-group atomic writer left temp residue: {residues}")


def prove_bound_transaction_rollback(module, source_sha: str) -> None:
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_status = module.STATUS_PATH.read_bytes()
    contract_mode = module.CONTRACT_PATH.stat().st_mode & 0o7777
    status_mode = module.STATUS_PATH.stat().st_mode & 0o7777
    contract = copy.deepcopy(module.load(module.CONTRACT_PATH))
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise RuntimeError("process-group readiness missing")
    readiness["productionReady"] = True

    original_writer = module.write_json
    original_atomic_writer = module.atomic_write_bytes
    original_runner = module.run_authority_validators

    class SyntheticPostWriteFailure(RuntimeError):
        pass

    def reject_mutable_helper(*_args, **_kwargs) -> None:
        raise RuntimeError("mutable process-group transaction helper was invoked")

    def fail_post_validation(validated_sha: str) -> None:
        if validated_sha != source_sha:
            raise RuntimeError("process-group source SHA changed during synthetic rollback")
        raise SyntheticPostWriteFailure("synthetic post-write validation failure")

    module.write_json = reject_mutable_helper
    module.atomic_write_bytes = reject_mutable_helper
    module.run_authority_validators = reject_mutable_helper
    try:
        try:
            module.commit_candidate(
                contract,
                status,
                source_sha,
                validator_runner=fail_post_validation,
            )
        except SyntheticPostWriteFailure:
            pass
        else:
            raise RuntimeError("transaction accepted synthetic post-write validation failure")
    finally:
        module.write_json = original_writer
        module.atomic_write_bytes = original_atomic_writer
        module.run_authority_validators = original_runner

    if module.CONTRACT_PATH.read_bytes() != original_contract:
        raise RuntimeError("process-group contract changed after bound rollback")
    if module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after bound rollback")
    if module.CONTRACT_PATH.stat().st_mode & 0o7777 != contract_mode:
        raise RuntimeError("process-group contract mode changed after bound rollback")
    if module.STATUS_PATH.stat().st_mode & 0o7777 != status_mode:
        raise RuntimeError("production status mode changed after bound rollback")
    residues = [
        *module.CONTRACT_PATH.parent.glob(f".{module.CONTRACT_PATH.name}.*.tmp"),
        *module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp"),
    ]
    if residues:
        raise RuntimeError(f"bound process-group rollback left temp authority residue: {residues}")


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

    prove_atomic_transport_binding(module)
    prove_bound_transaction_rollback(module, source_sha)

    if module.CONTRACT_PATH.read_bytes() != module.CONTRACT_PATH.read_bytes():
        raise RuntimeError("unreachable process-group authority consistency guard")

    print(
        "PASS: process-group reconcile pins data/executable authority, atomic transport, mode preservation, and rollback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
