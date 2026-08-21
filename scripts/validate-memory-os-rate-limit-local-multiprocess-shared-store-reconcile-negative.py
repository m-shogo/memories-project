#!/usr/bin/env python3
"""Negative checks for local multi-process shared-store reconciliation authority."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-rate-limit-local-multiprocess-shared-store.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_local_shared_store_reconcile_negative_target",
        RECONCILER,
    )
    require(spec is not None and spec.loader is not None, "cannot load local shared-store reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action) -> None:
    try:
        action()
    except Exception as exc:
        if exc.__class__.__module__.startswith("memory_os_rate_limit_local_shared_store_") and exc.__class__.__name__ == "Fail":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def authority_identity_negative(module) -> None:
    real_operability = module.OPERABILITY_VALIDATOR
    module.OPERABILITY_VALIDATOR = module.RATE_LIMIT_VALIDATOR
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR = real_operability


def rollback_negative(module) -> None:
    original_contract = module.CONTRACT.read_bytes()
    original_status = module.STATUS.read_bytes()
    real_normalized_contract = module.normalized_contract
    real_normalized_status = module.normalized_status
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def fake_contract(current, result_present):
        candidate = copy.deepcopy(current)
        readiness = candidate.get("readiness")
        require(isinstance(readiness, dict), "readiness missing in rollback fixture")
        readiness["localCrossProcessStoreSemanticsProven"] = not bool(
            readiness.get("localCrossProcessStoreSemanticsProven")
        )
        return candidate

    def fake_status(current, result_present):
        candidate = copy.deepcopy(current)
        gate = next(
            row for row in candidate.get("areas", [])
            if isinstance(row, dict) and row.get("id") == "OPS-P0-005"
        )
        evidence = gate.get("existingEvidence")
        require(isinstance(evidence, list), "OPS-P0-005 existingEvidence missing in rollback fixture")
        evidence.append("synthetic local shared-store rollback sentinel")
        return candidate

    def fake_run_validator(path: Path) -> None:
        calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise module.Fail("synthetic aggregate operability rejection")

    module.normalized_contract = fake_contract
    module.normalized_status = fake_status
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "post-write operability rejection rolls back local shared-store authority",
            module.main,
        )
        require(
            calls == [
                module.VALIDATOR,
                module.RATE_LIMIT_OPERATIONS_VALIDATOR,
                module.RATE_LIMIT_VALIDATOR,
                module.OPERABILITY_VALIDATOR,
            ],
            "local shared-store validator transaction order drift",
        )
        require(module.CONTRACT.read_bytes() == original_contract,
                "local shared-store contract was not rolled back byte-for-byte")
        require(module.STATUS.read_bytes() == original_status,
                "production status was not rolled back byte-for-byte")
    finally:
        module.normalized_contract = real_normalized_contract
        module.normalized_status = real_normalized_status
        module.run_validator = real_run_validator
        if module.CONTRACT.read_bytes() != original_contract:
            module.CONTRACT.write_bytes(original_contract)
        if module.STATUS.read_bytes() != original_status:
            module.STATUS.write_bytes(original_status)


def main() -> int:
    module = load_module()
    module.validate_runtime_authority()
    authority_identity_negative(module)
    rollback_negative(module)
    print("Memory OS local multi-process shared-store reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("post-write aggregate rollback: enforced")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL SHARED-STORE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
