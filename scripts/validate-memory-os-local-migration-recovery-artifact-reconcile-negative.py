#!/usr/bin/env python3
"""Negative checks for local migration recovery-artifact reconciliation authority."""

from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"


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
        if exc.__class__.__name__ == "Fail":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def select_local_run(module) -> str:
    registry = module.load(module.REGISTRY_PATH)
    records = registry.get("records")
    require(isinstance(records, list), "migration registry records missing")
    for row in reversed(records):
        if not isinstance(row, dict):
            continue
        if row.get("environmentClass") != "LOCAL_POSTGRES_REHEARSAL":
            continue
        run_id = row.get("migrationRunId")
        evidence_ref = row.get("recoveryPointRestoreEvidenceRef")
        if not isinstance(run_id, str) or not isinstance(evidence_ref, str):
            continue
        if evidence_ref == f"docs/evidence/migrations/recovery/{run_id}.json" and (module.ROOT / evidence_ref).is_file():
            return run_id
    raise Fail("no canonical local migration recovery-artifact record available for negative fixture")


def authority_identity_negative(module) -> None:
    real_operability = module.OPERABILITY_VALIDATOR_PATH
    module.OPERABILITY_VALIDATOR_PATH = module.LIFECYCLE_VALIDATOR_PATH
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR_PATH = real_operability


def rollback_negative(module) -> None:
    run_id = select_local_run(module)
    original_contract = module.CONTRACT_PATH.read_bytes()
    real_load = module.load
    real_parse_args = module.parse_args
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def stale_contract_load(path: Path):
        value = real_load(path)
        if path != module.CONTRACT_PATH:
            return value
        candidate = copy.deepcopy(value)
        readiness = candidate.get("readiness")
        require(isinstance(readiness, dict), "local recovery readiness missing in fixture")
        readiness["localActualRecoveryArtifactRestoreProven"] = False
        return candidate

    def fake_run_validator(path: Path, *args: str) -> None:
        calls.append(path)
        if len(calls) == 8 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.Fail("synthetic aggregate operability rejection")

    module.load = stale_contract_load
    module.parse_args = lambda: argparse.Namespace(run_id=run_id)
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "post-write operability rejection rolls back local recovery-artifact contract",
            module.main,
        )
        expected = [
            module.VALIDATOR_PATH,
            module.REGISTRY_VALIDATOR_PATH,
            module.LIFECYCLE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
            module.VALIDATOR_PATH,
            module.REGISTRY_VALIDATOR_PATH,
            module.LIFECYCLE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
        ]
        require(calls == expected, "local recovery validator transaction order drift")
        require(module.CONTRACT_PATH.read_bytes() == original_contract,
                "local recovery-artifact contract was not rolled back byte-for-byte")
    finally:
        module.load = real_load
        module.parse_args = real_parse_args
        module.run_validator = real_run_validator
        if module.CONTRACT_PATH.read_bytes() != original_contract:
            module.CONTRACT_PATH.write_bytes(original_contract)


def main() -> int:
    reconciler = load_module(
        RECONCILER,
        "memory_os_local_migration_recovery_reconcile_negative_target",
    )
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    rollback_negative(reconciler)
    print("Memory OS local migration recovery-artifact reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("post-write aggregate rollback: enforced")
    print("production-equivalent recovery artifact restore: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL MIGRATION RECOVERY RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
