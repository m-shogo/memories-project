#!/usr/bin/env python3
"""Fail-closed negatives for deletion lease-recovery reconciliation authority."""

from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-deletion-lease-recovery.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
ALTERNATE_CONTRACT = ROOT / "contracts/operations/production-operability-status.json"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_deletion_lease_recovery_reconciler", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deletion lease recovery reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_identity_rejection(module: ModuleType, attribute: str, replacement: Path, original_contract: bytes) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        try:
            module.validate_authority_identity()
        except module.ReconcileFailure:
            pass
        else:
            raise AssertionError(f"{attribute} substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError(f"{attribute} rejection mutated canonical contract")
    finally:
        setattr(module, attribute, original)


def expect_transport_rejection(module: ModuleType, original_contract: bytes) -> None:
    original_run = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: None
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure as exc:
            if "subprocess transport is not canonical" not in str(exc):
                raise AssertionError(f"unexpected transport rejection: {exc}") from exc
        else:
            raise AssertionError("subprocess transport substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("transport rejection mutated canonical contract")
    finally:
        module.subprocess.run = original_run


def expect_atomic_writer_rejection(module: ModuleType, original_contract: bytes) -> None:
    original = module.atomic_write_bytes
    module.atomic_write_bytes = lambda _path, _data: None
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure as exc:
            if "atomic writer authority is not canonical" not in str(exc):
                raise AssertionError(f"unexpected atomic writer rejection: {exc}") from exc
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
            module.enforce_runtime_authorities()
        except module.ReconcileFailure as exc:
            if "atomic replacement transport is not canonical" not in str(exc):
                raise AssertionError(f"unexpected atomic replacement rejection: {exc}") from exc
        else:
            raise AssertionError("os.replace substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("atomic replacement rejection mutated canonical contract")
    finally:
        module.os.replace = original


def expect_mode_preservation(module: ModuleType, original_contract: bytes) -> None:
    path = module.CANONICAL_CONTRACT_PATH
    original_mode = stat.S_IMODE(path.stat().st_mode)
    probe_mode = 0o640 if original_mode != 0o640 else 0o644
    path.chmod(probe_mode)
    try:
        module.CANONICAL_ATOMIC_WRITE_BYTES(path, original_contract)
        if stat.S_IMODE(path.stat().st_mode) != probe_mode:
            raise AssertionError("atomic replacement changed canonical lease recovery contract mode")
        if path.read_bytes() != original_contract:
            raise AssertionError("mode-preservation probe changed canonical lease recovery contract bytes")
    finally:
        path.chmod(original_mode)


def expect_post_write_rollback(module: ModuleType, original_contract: bytes) -> None:
    candidate = json.loads(original_contract.decode("utf-8"))
    readiness = candidate.setdefault("readiness", {})
    readiness["leaseExpiryReclaimProven"] = not bool(readiness.get("leaseExpiryReclaimProven", False))
    candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    if candidate_bytes == original_contract:
        raise AssertionError("rollback fixture did not change the candidate contract")

    original_run_validator = module.run_validator

    def reject_post_write(_expected_sha: str) -> None:
        raise RuntimeError("synthetic post-write lease recovery validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, "0" * 40)
        except RuntimeError as exc:
            if "synthetic post-write lease recovery validation failure" not in str(exc):
                raise
        else:
            raise AssertionError("post-write validator rejection was accepted")

        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("post-write validator rejection did not restore canonical contract bytes")
        if list(module.CANONICAL_CONTRACT_PATH.parent.glob(f".{module.CANONICAL_CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("post-write rollback left an atomic temp file")
    finally:
        module.run_validator = original_run_validator
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            module.CANONICAL_ATOMIC_WRITE_BYTES(module.CANONICAL_CONTRACT_PATH, original_contract)


def main() -> int:
    module = load_module()
    original_contract = module.CANONICAL_CONTRACT_PATH.read_bytes()

    module.validate_authority_identity()
    expect_identity_rejection(module, "VALIDATOR", ALTERNATE_VALIDATOR, original_contract)
    expect_identity_rejection(module, "CONTRACT_PATH", ALTERNATE_CONTRACT, original_contract)
    expect_transport_rejection(module, original_contract)
    expect_atomic_writer_rejection(module, original_contract)
    expect_atomic_replace_rejection(module, original_contract)
    expect_mode_preservation(module, original_contract)
    expect_post_write_rollback(module, original_contract)

    print("PASS: deletion lease recovery reconcile authority, execution transport, mode-preserving atomic writer and rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
