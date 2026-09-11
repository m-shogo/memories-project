#!/usr/bin/env python3
"""Fail-closed negatives for deletion worker SIGKILL reconciliation authority and execution transport."""

from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-deletion-worker-sigkill-recovery.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
ALTERNATE_CONTRACT = ROOT / "contracts/operations/production-operability-status.json"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_deletion_worker_sigkill_reconciler", RECONCILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deletion worker SIGKILL reconciler")
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
    original = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: None
    try:
        try:
            module.validate_authority_identity()
        except module.ReconcileFailure as exc:
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
        except module.ReconcileFailure as exc:
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
        except module.ReconcileFailure as exc:
            if "atomic replacement transport is not canonical" not in str(exc):
                raise
        else:
            raise AssertionError("os.replace substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("atomic replacement transport rejection mutated canonical contract")
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
            raise AssertionError("atomic replacement changed canonical SIGKILL contract mode")
        if path.read_bytes() != original_contract:
            raise AssertionError("mode-preservation probe changed canonical SIGKILL contract bytes")
    finally:
        path.chmod(original_mode)


def changed_candidate(original_contract: bytes) -> dict:
    candidate = json.loads(original_contract.decode("utf-8"))
    readiness = candidate.setdefault("readiness", {})
    readiness["actualSIGKILLRecoveryProven"] = not bool(readiness.get("actualSIGKILLRecoveryProven", False))
    candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    if candidate_bytes == original_contract:
        raise AssertionError("rollback fixture did not change the candidate contract")
    return candidate


def expect_post_write_rollback(module: ModuleType, original_contract: bytes) -> None:
    candidate = changed_candidate(original_contract)
    original_run_validator = module.run_validator

    def reject_post_write(_expected_sha: str) -> None:
        raise RuntimeError("synthetic post-write SIGKILL validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, "0" * 40)
        except RuntimeError as exc:
            if "synthetic post-write SIGKILL validation failure" not in str(exc):
                raise
        else:
            raise AssertionError("post-write validator rejection was accepted")

        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("post-write validator rejection did not restore canonical contract bytes")
    finally:
        module.run_validator = original_run_validator
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            module.CANONICAL_ATOMIC_WRITE_BYTES(module.CANONICAL_CONTRACT_PATH, original_contract)


def expect_rollback_failure_diagnostic(module: ModuleType, original_contract: bytes) -> None:
    candidate = changed_candidate(original_contract)
    original_run_validator = module.run_validator
    original_restore = module.CANONICAL_ATOMIC_WRITE_BYTES

    def reject_post_write(_expected_sha: str) -> None:
        def fail_restore(_path: Path, _data: bytes) -> None:
            raise OSError("synthetic SIGKILL rollback failure")

        module.CANONICAL_ATOMIC_WRITE_BYTES = fail_restore
        raise RuntimeError("synthetic post-write SIGKILL validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, "0" * 40)
        except RuntimeError as exc:
            diagnostic = str(exc)
            if "synthetic post-write SIGKILL validation failure" not in diagnostic:
                raise AssertionError(f"primary validation diagnostic was lost: {diagnostic}") from exc
            if "rollback incomplete" not in diagnostic:
                raise AssertionError(f"rollback incompleteness was not diagnosed: {diagnostic}") from exc
            if "synthetic SIGKILL rollback failure" not in diagnostic:
                raise AssertionError(f"rollback failure diagnostic was lost: {diagnostic}") from exc
        else:
            raise AssertionError("rollback failure was accepted")
    finally:
        module.run_validator = original_run_validator
        module.CANONICAL_ATOMIC_WRITE_BYTES = original_restore
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            original_restore(module.CANONICAL_CONTRACT_PATH, original_contract)


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
    expect_rollback_failure_diagnostic(module, original_contract)

    print("PASS: deletion worker SIGKILL reconcile authority, execution transport, mode-preserving atomic writer, rollback, and primary diagnostics are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
