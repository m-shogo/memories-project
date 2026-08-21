#!/usr/bin/env python3
"""Negative checks for local logical restore reconciliation authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-local-logical-restore.py"


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
    module.OPERABILITY_VALIDATOR_PATH = module.VALIDATOR_PATH
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
            "repository-contained local logical restore contract substitution",
            module.validate_runtime_authority,
        )
        module.CONTRACT_PATH = original_contract
        module.RESULT_PATH = original_contract
        expect_rejected(
            "repository-contained local logical restore result substitution",
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


def rollback_negative(module) -> None:
    original_status = module.STATUS_PATH.read_bytes()
    real_load = module.load
    real_run_validator = module.run_validator
    result = json.loads(module.RESULT_PATH.read_text(encoding="utf-8"))
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40,
            "logical restore fixture source SHA missing")
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
        if len(calls) == 4 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.ReconcileFailure("synthetic aggregate operability rejection")

    module.load = load_with_stale_projection
    module.run_validator = fake_run_validator
    os.environ["EXPECTED_COMMIT_SHA"] = source_sha
    try:
        expect_rejected(
            "post-write operability rejection rolls back logical restore status",
            module.main,
        )
        require(
            calls == [
                module.VALIDATOR_PATH,
                module.OPERABILITY_VALIDATOR_PATH,
                module.VALIDATOR_PATH,
                module.OPERABILITY_VALIDATOR_PATH,
            ],
            "logical restore validator transaction order drift",
        )
        require(module.STATUS_PATH.read_bytes() == original_status,
                "production status was not rolled back byte-for-byte")
    finally:
        module.load = real_load
        module.run_validator = real_run_validator
        if previous_expected_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_expected_sha
        if module.STATUS_PATH.read_bytes() != original_status:
            module.STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_module(
        RECONCILER,
        "memory_os_local_logical_restore_reconcile_negative_target",
    )
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    data_authority_identity_negative(reconciler)
    rollback_negative(reconciler)
    print("Memory OS local logical restore reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("canonical contract/result/status identity: enforced")
    print("post-write aggregate rollback: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL LOGICAL RESTORE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
