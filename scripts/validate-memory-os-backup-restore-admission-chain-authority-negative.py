#!/usr/bin/env python3
"""Prove direct admission-chain validation cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
ALTERNATE_DATA = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
ALTERNATE_SCRIPT = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
ALTERNATE_WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "admission-chain validator missing or symlinked")
    resolved = VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve())
    require(resolved == Path("scripts/validate-memory-os-backup-restore-admission-chain.py"), "validator authority drift")
    spec = importlib.util.spec_from_file_location("memory_os_admission_chain_authority_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_guard_rejected(module: Any, field: str, replacement: Path) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        rejected = False
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            rejected = True
        require(rejected, f"admission-chain authority substitution accepted: {field}")
    finally:
        setattr(module, field, original)


def main() -> int:
    module = load_validator()
    module.enforce_runtime_authorities()
    status_before = module.STATUS.read_bytes()
    inventory_before = module.INVENTORY.read_bytes()
    contract_before = module.CONTRACT.read_bytes()

    data_fields = (
        "CONTRACT",
        "PREFLIGHT_CONTRACT",
        "DRILL_CONTRACT",
        "DRILL_REGISTRY",
        "GEN_CONTRACT",
        "GEN_REGISTRY",
        "BINDING_CONTRACT",
        "TYPED_CONTRACT",
        "TYPED_REGISTRY",
        "INVENTORY",
        "STATUS",
    )
    script_fields = (
        "DRILL_WRITER",
        "GEN_WRITER",
        "TYPED_WRITER",
        "BLOCKER_AUTHORITY",
        "SELF",
    )
    for field in data_fields:
        expect_guard_rejected(module, field, ALTERNATE_DATA)
    for field in script_fields:
        expect_guard_rejected(module, field, ALTERNATE_SCRIPT)
    expect_guard_rejected(module, "WORKFLOW", ALTERNATE_WORKFLOW)

    original_contract = module.CONTRACT
    module.CONTRACT = ALTERNATE_DATA
    try:
        rejected = False
        try:
            module.main()
        except module.Fail:
            rejected = True
        require(rejected, "main did not enforce admission-chain authority identity before validation")
    finally:
        module.CONTRACT = original_contract

    require(module.STATUS.read_bytes() == status_before, "authority substitution probe mutated Production Status")
    require(module.INVENTORY.read_bytes() == inventory_before, "authority substitution probe mutated Operability Inventory")
    require(module.CONTRACT.read_bytes() == contract_before, "authority substitution probe mutated admission-chain contract")

    print("Memory OS backup/restore admission-chain authority negative PASS")
    print("canonical data authority substitution accepted: false")
    print("canonical writer/blocker/validator/workflow substitution accepted: false")
    print("main bypasses runtime authority guard: false")
    print("rejected probe mutated admission-chain authorities: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
