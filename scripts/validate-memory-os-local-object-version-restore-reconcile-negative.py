#!/usr/bin/env python3
"""Negative checks for local object-version restore reconciliation authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-local-object-version-restore.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action) -> None:
    try:
        action()
    except Exception as exc:
        if exc.__class__.__name__ == "ReconcileFailure":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def authority_identity_negative(module) -> None:
    real_operability = module.OPERABILITY_VALIDATOR_PATH
    module.OPERABILITY_VALIDATOR_PATH = module.BACKUP_RESTORE_VALIDATOR_PATH
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR_PATH = real_operability


def data_authority_identity_negative(module) -> None:
    original_contract = module.CONTRACT_PATH
    original_result = module.RESULT_PATH
    original_status = module.STATUS_PATH
    try:
        module.CONTRACT_PATH = original_status
        expect_rejected(
            "repository-contained local object restore contract substitution",
            module.validate_runtime_authority,
        )
        module.CONTRACT_PATH = original_contract
        module.RESULT_PATH = original_contract
        expect_rejected(
            "repository-contained local object restore result substitution",
            module.validate_runtime_authority,
        )
        module.RESULT_PATH = original_result
        module.STATUS_PATH = original_contract
        expect_rejected(
            "repository-contained production status substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.CONTRACT_PATH = original_contract
        module.RESULT_PATH = original_result
        module.STATUS_PATH = original_status


def atomic_replace_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    original_mode = module.STATUS_PATH.stat().st_mode & 0o7777
    real_replace = module.os.replace

    def fail_replace(source, destination) -> None:
        raise OSError("synthetic local object restore atomic replace rejection")

    module.os.replace = fail_replace
    try:
        try:
            module.atomic_replace_bytes(module.STATUS_PATH, b'{"invalid":"must-not-persist"}\n')
        except OSError as exc:
            require("synthetic local object restore atomic replace rejection" in str(exc),
                    f"unexpected atomic replace rejection: {exc}")
        else:
            raise Fail("local object restore accepted synthetic atomic replace failure")
    finally:
        module.os.replace = real_replace

    require(module.STATUS_PATH.read_bytes() == original_status,
            "production status changed after object restore atomic replace failure")
    require(module.STATUS_PATH.stat().st_mode & 0o7777 == original_mode,
            "production status mode changed after object restore atomic replace failure")
    leftovers = list(module.STATUS_PATH.parent.glob(f".{module.STATUS_PATH.name}.*.tmp"))
    require(not leftovers, f"local object restore atomic replace left temporary files: {leftovers}")


def rollback_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    original_mode = module.STATUS_PATH.stat().st_mode & 0o7777
    real_load = module.load
    real_run_validator = module.run_validator
    result = json.loads(module.RESULT_PATH.read_text(encoding="utf-8"))
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40,
            "object restore fixture source SHA missing")
    previous_expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    calls: list[Path] = []

    def load_with_stale_projection(path: Path):
        value = real_load(path)
        if path != module.STATUS_PATH:
            return value
        candidate = copy.deepcopy(value)
        gate = next(
            row for row in candidate.get("areas", [])
            if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
        )
        existing = gate.get("existingEvidence")
        require(isinstance(existing, list), "OPS-P0-007 existing evidence missing")
        if module.NEW_EXISTING[0] in existing:
            existing.remove(module.NEW_EXISTING[0])
        return candidate

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        if len(calls) == 6 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.ReconcileFailure("synthetic aggregate operability rejection")

    module.load = load_with_stale_projection
    module.run_validator = fake_run_validator
    os.environ["EXPECTED_COMMIT_SHA"] = source_sha
    try:
        expect_rejected(
            "post-write operability rejection rolls back object restore status",
            module.main,
        )
        expected = [
            module.VALIDATOR_PATH,
            module.BACKUP_RESTORE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
            module.VALIDATOR_PATH,
            module.BACKUP_RESTORE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
        ]
        require(calls == expected, "object restore validator transaction order drift")
        require(module.STATUS_PATH.read_bytes() == original_status,
                "production status was not rolled back byte-for-byte")
        require(module.STATUS_PATH.stat().st_mode & 0o7777 == original_mode,
                "production status mode changed after object restore rollback")
    finally:
        module.load = real_load
        module.run_validator = real_run_validator
        if previous_expected_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_expected_sha
        if module.STATUS_PATH.read_bytes() != original_status:
            module.atomic_replace_bytes(module.STATUS_PATH, original_status)


def rollback_failure_diagnostic_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    original_mode = module.STATUS_PATH.stat().st_mode & 0o7777
    real_load = module.load
    real_run_validator = module.run_validator
    real_atomic_replace = module.atomic_replace_bytes
    result = json.loads(module.RESULT_PATH.read_text(encoding="utf-8"))
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40,
            "object restore fixture source SHA missing for rollback diagnostic")
    previous_expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    calls: list[Path] = []
    post_write_failure_seen = False
    rollback_injected = False

    def load_with_stale_projection(path: Path):
        value = real_load(path)
        if path != module.STATUS_PATH:
            return value
        candidate = copy.deepcopy(value)
        gate = next(
            row for row in candidate.get("areas", [])
            if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
        )
        existing = gate.get("existingEvidence")
        require(isinstance(existing, list), "OPS-P0-007 existing evidence missing")
        if module.NEW_EXISTING[0] in existing:
            existing.remove(module.NEW_EXISTING[0])
        return candidate

    def fake_run_validator(path: Path) -> None:
        nonlocal post_write_failure_seen
        calls.append(path)
        if len(calls) == 6 and path == module.OPERABILITY_VALIDATOR_PATH:
            post_write_failure_seen = True
            raise module.ReconcileFailure("synthetic aggregate operability rejection")

    def fail_restore_after_restoring(path: Path, payload: bytes) -> None:
        nonlocal rollback_injected
        if post_write_failure_seen and path == module.STATUS_PATH and payload == original_status:
            real_atomic_replace(path, payload)
            if not rollback_injected:
                rollback_injected = True
                raise OSError("synthetic local object restore rollback rejection")
            return
        real_atomic_replace(path, payload)

    module.load = load_with_stale_projection
    module.run_validator = fake_run_validator
    module.atomic_replace_bytes = fail_restore_after_restoring
    os.environ["EXPECTED_COMMIT_SHA"] = source_sha
    try:
        try:
            module.main()
        except module.ReconcileFailure as exc:
            text = str(exc)
            require("synthetic aggregate operability rejection" in text,
                    f"primary object restore failure was lost: {exc}")
            require("rollback incomplete" in text,
                    f"object restore rollback incompleteness was not reported: {exc}")
            require("synthetic local object restore rollback rejection" in text,
                    f"object restore rollback error was lost: {exc}")
        else:
            raise Fail("object restore reconciler accepted validator plus rollback failure")
        require(rollback_injected, "object restore rollback failure injection did not execute")
        require(module.STATUS_PATH.read_bytes() == original_status,
                "production status changed after object restore rollback diagnostic failure")
        require(module.STATUS_PATH.stat().st_mode & 0o7777 == original_mode,
                "production status mode changed after object restore rollback diagnostic failure")
    finally:
        module.load = real_load
        module.run_validator = real_run_validator
        module.atomic_replace_bytes = real_atomic_replace
        if previous_expected_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_expected_sha
        if module.STATUS_PATH.read_bytes() != original_status:
            real_atomic_replace(module.STATUS_PATH, original_status)


def main() -> int:
    reconciler = load_module(
        RECONCILER,
        "memory_os_local_object_restore_reconcile_negative_target",
    )
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    data_authority_identity_negative(reconciler)
    atomic_replace_negative(reconciler)
    rollback_negative(reconciler)
    rollback_failure_diagnostic_negative(reconciler)
    print("Memory OS local object-version restore reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("canonical contract/result/status identity: enforced")
    print("atomic publication and mode preservation: enforced")
    print("post-write aggregate rollback: enforced")
    print("primary plus rollback failure diagnostics: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL OBJECT RESTORE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
