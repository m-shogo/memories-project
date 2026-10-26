#!/usr/bin/env python3
"""Prove pre-fence proof reconcile authority identity, execution transport, and rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-prefence-linearization.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
ALTERNATE_CONTRACT = ROOT / "contracts/operations/production-operability-status.json"
SOURCE_SHA = "3" * 40


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prefence_proof_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pre-fence proof reconciler")
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
            raise AssertionError("atomic replacement changed canonical pre-fence contract mode")
        if path.read_bytes() != original_contract:
            raise AssertionError("mode-preservation probe changed canonical pre-fence contract bytes")
    finally:
        path.chmod(original_mode)


def changed_candidate(original_contract: bytes) -> dict:
    candidate = json.loads(original_contract.decode("utf-8"))
    readiness = candidate.setdefault("readiness", {})
    readiness["preFenceInFlightLinearizationProven"] = not bool(
        readiness.get("preFenceInFlightLinearizationProven", False)
    )
    candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    if candidate_bytes == original_contract:
        raise AssertionError("rollback fixture did not change candidate contract")
    return candidate


def expect_post_write_rollback(module: ModuleType, original_contract: bytes) -> None:
    candidate = changed_candidate(original_contract)
    original_run_validator = module.run_validator

    def reject_post_write(_expected: str) -> None:
        raise RuntimeError("synthetic post-write pre-fence validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, SOURCE_SHA)
        except RuntimeError as exc:
            if (str(exc) != "pre-fence post-write validation failed: RuntimeError"
                    or not exc.__suppress_context__):
                raise AssertionError("pre-fence post-write failure leaked raw validator details") from exc
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

    def reject_post_write(_expected: str) -> None:
        def fail_restore(_path: Path, _data: bytes) -> None:
            raise OSError("synthetic pre-fence rollback failure")

        module.CANONICAL_ATOMIC_WRITE_BYTES = fail_restore
        raise RuntimeError("synthetic post-write pre-fence validation failure")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, SOURCE_SHA)
        except RuntimeError as exc:
            diagnostic = str(exc)
            if (diagnostic != "pre-fence post-write validation failed: RuntimeError; rollback incomplete: OSError"
                    or not exc.__suppress_context__):
                raise AssertionError("pre-fence rollback failure leaked raw exception details") from exc
        else:
            raise AssertionError("rollback failure was accepted")
    finally:
        module.run_validator = original_run_validator
        module.CANONICAL_ATOMIC_WRITE_BYTES = original_restore
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            original_restore(module.CANONICAL_CONTRACT_PATH, original_contract)



def expect_atomic_path_guard(module: ModuleType) -> None:
    """Exercise the real atomic helper with disposable paths and an outside canary."""
    with tempfile.TemporaryDirectory(prefix="prefence-atomic-path-") as temp:
        root = Path(temp)
        parent = root / "inside"
        parent.mkdir()
        outside = root / "outside"
        outside.mkdir()
        canary = outside / "canary"
        canary.write_bytes(b"SYNTHETIC_SECRET_CANARY")
        target = parent / "contract.json"

        def reject(path: Path, label: str) -> None:
            try:
                module.CANONICAL_ATOMIC_WRITE_BYTES(path, b"changed")
            except module.Fail:
                pass
            else:
                raise AssertionError("pre-fence atomic writer accepted " + label)
            if canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY":
                raise AssertionError("pre-fence atomic writer changed outside canary")
            if list(parent.glob(".*.tmp")):
                raise AssertionError("pre-fence atomic writer left temporary residue")

        target.symlink_to(canary)
        reject(target, "symlink target")
        target.unlink()

        parent.rmdir()
        parent.symlink_to(outside, target_is_directory=True)
        reject(target, "symlink ancestor")
        parent.unlink()
        parent.mkdir()

        target.mkdir()
        reject(target, "directory target")
        target.rmdir()
        reject(root / "missing" / "contract.json", "missing parent")

        target.write_bytes(b"before")
        target.chmod(0o640)
        module.CANONICAL_ATOMIC_WRITE_BYTES(target, b"after")
        if target.read_bytes() != b"after" or stat.S_IMODE(target.stat().st_mode) != 0o640:
            raise AssertionError("pre-fence atomic writer did not preserve bytes/mode")

        original_replace = module.os.replace
        def deny_replace(*_args):
            raise OSError("synthetic replace failure")
        module.os.replace = deny_replace
        try:
            try:
                module.CANONICAL_ATOMIC_WRITE_BYTES(target, b"wrong")
            except OSError:
                pass
            else:
                raise AssertionError("pre-fence atomic writer accepted replace failure")
        finally:
            module.os.replace = original_replace

        original_fsync = module.os.fsync
        def deny_fsync(*_args):
            raise OSError("synthetic fsync failure")
        module.os.fsync = deny_fsync
        try:
            try:
                module.CANONICAL_ATOMIC_WRITE_BYTES(target, b"wrong")
            except OSError:
                pass
            else:
                raise AssertionError("pre-fence atomic writer accepted fsync failure")
        finally:
            module.os.fsync = original_fsync

        if (target.read_bytes() != b"after" or stat.S_IMODE(target.stat().st_mode) != 0o640
                or canary.read_bytes() != b"SYNTHETIC_SECRET_CANARY"
                or list(parent.glob(".*.tmp"))):
            raise AssertionError("pre-fence atomic rollback/mode/canary drift")
    print("PASS: pre-fence reconcile atomic symlink/path/rollback runtime (7 cases)")


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
    expect_atomic_path_guard(module)
    expect_post_write_rollback(module, original_contract)
    expect_rollback_failure_diagnostic(module, original_contract)

    print("PASS: pre-fence proof reconcile preserves authority identity, atomic mode, rollback, and primary diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
