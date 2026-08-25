#!/usr/bin/env python3
"""Fail-closed negatives for local deletion container-kill reconciliation authority and rollback."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-worker-container-kill-recovery.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
ALTERNATE_CONTRACT = ROOT / "contracts/operations/production-operability-status.json"
ALTERNATE_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("container_kill_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load container-kill reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_identity_rejection(module: ModuleType, attribute: str, replacement: Path, original_contract: bytes) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        try:
            module.validate_authority_identity()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attribute} substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError(f"{attribute} rejection mutated canonical contract")
    finally:
        setattr(module, attribute, original)


def expect_transport_rejection(module: ModuleType, original_contract: bytes) -> None:
    original = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: None
    try:
        try:
            module.validate_authority_identity()
        except module.Fail as exc:
            if "validator execution transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("subprocess.run substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("execution transport rejection mutated canonical contract")
    finally:
        module.subprocess.run = original


def expect_atomic_writer_rejection(module: ModuleType, original_contract: bytes) -> None:
    original = module.atomic_write_bytes
    module.atomic_write_bytes = lambda _path, _data: None
    try:
        try:
            module.validate_authority_identity()
        except module.Fail as exc:
            if "atomic writer authority is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("atomic writer substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("atomic writer rejection mutated canonical contract")
    finally:
        module.atomic_write_bytes = original


def expect_atomic_replace_rejection(module: ModuleType, original_contract: bytes) -> None:
    original = module.os.replace
    module.os.replace = lambda _source, _target: None
    try:
        try:
            module.validate_authority_identity()
        except module.Fail as exc:
            if "atomic replacement transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("os.replace substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("atomic replacement rejection mutated canonical contract")
    finally:
        module.os.replace = original


def expect_post_write_rollback(module: ModuleType, original_contract: bytes) -> None:
    candidate = json.loads(original_contract.decode("utf-8"))
    readiness = candidate.setdefault("readiness", {})
    readiness["actualContainerKillRecoveryProven"] = not bool(readiness.get("actualContainerKillRecoveryProven", False))
    if (json.dumps(candidate, indent=2) + "\n").encode("utf-8") == original_contract:
        raise AssertionError("rollback fixture did not change candidate contract")

    original_run_validator = module.run_validator

    def reject_post_write(_expected_sha: str) -> None:
        raise RuntimeError("synthetic post-write container-kill validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, "0" * 40)
        except RuntimeError as exc:
            if "synthetic post-write container-kill validation failure" not in str(exc):
                raise
        else:
            raise AssertionError("post-write validator rejection was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("post-write validator rejection did not restore canonical contract bytes")
        if list(module.CANONICAL_CONTRACT_PATH.parent.glob(f".{module.CANONICAL_CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("container-kill rollback left atomic temp residue")
    finally:
        module.run_validator = original_run_validator
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            module.CANONICAL_ATOMIC_WRITE_BYTES(module.CANONICAL_CONTRACT_PATH, original_contract)


def main() -> int:
    module = load_module()
    original_contract = module.CANONICAL_CONTRACT_PATH.read_bytes()

    module.validate_authority_identity()
    expect_identity_rejection(module, "CONTRACT_PATH", ALTERNATE_CONTRACT, original_contract)
    expect_identity_rejection(module, "RESULT_PATH", ALTERNATE_RESULT, original_contract)
    expect_identity_rejection(module, "VALIDATOR", ALTERNATE_VALIDATOR, original_contract)
    expect_transport_rejection(module, original_contract)
    expect_atomic_writer_rejection(module, original_contract)
    expect_atomic_replace_rejection(module, original_contract)
    expect_post_write_rollback(module, original_contract)

    print("PASS: container-kill reconcile authority, execution transport, atomic writer, and rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
