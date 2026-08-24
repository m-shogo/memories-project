#!/usr/bin/env python3
"""Prove direct admission-chain validation cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
FULL_RUNNER = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-full.py"
ALTERNATE_DATA = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
ALTERNATE_SCRIPT = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
ALTERNATE_WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, module_name: str):
    require(path.is_file() and not path.is_symlink(), f"authority missing or symlinked: {path.relative_to(ROOT)}")
    resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    require(resolved == path.relative_to(ROOT), f"authority path drift: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator():
    return load_module(VALIDATOR, "memory_os_admission_chain_authority_negative")


def load_full_runner():
    return load_module(FULL_RUNNER, "memory_os_admission_chain_full_authority_negative")


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


def validate_full_runner_authority() -> None:
    runner = load_full_runner()
    runner.enforce_runtime_authority()

    root_before = runner.ROOT
    runner.ROOT = ROOT / "contracts"
    try:
        rejected = False
        try:
            runner.enforce_runtime_authority()
        except runner.Fail:
            rejected = True
        require(rejected, "full admission-chain runner accepted substituted repository root")
    finally:
        runner.ROOT = root_before

    self_before = runner.SELF_REL
    runner.SELF_REL = Path("scripts/validate-memory-os-backup-restore-generation-binding.py")
    try:
        rejected = False
        try:
            runner.enforce_runtime_authority()
        except runner.Fail:
            rejected = True
        require(rejected, "full admission-chain runner accepted substituted self path")
    finally:
        runner.SELF_REL = self_before

    steps_before = runner.STEPS
    runner.STEPS = ()
    try:
        rejected = False
        try:
            runner.enforce_runtime_authority()
        except runner.Fail:
            rejected = True
        require(rejected, "full admission-chain runner accepted empty validation sequence")
    finally:
        runner.STEPS = steps_before

    run_step_before = runner.run_step
    runner.run_step = lambda _relative, _label: None
    try:
        rejected = False
        try:
            runner.main()
        except runner.Fail:
            rejected = True
        require(rejected, "full admission-chain runner accepted substituted execution function")
    finally:
        runner.run_step = run_step_before

    runner.enforce_runtime_authority()


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

    validate_full_runner_authority()

    require(module.STATUS.read_bytes() == status_before, "authority substitution probe mutated Production Status")
    require(module.INVENTORY.read_bytes() == inventory_before, "authority substitution probe mutated Operability Inventory")
    require(module.CONTRACT.read_bytes() == contract_before, "authority substitution probe mutated admission-chain contract")

    print("Memory OS backup/restore admission-chain authority negative PASS")
    print("canonical data authority substitution accepted: false")
    print("canonical writer/blocker/validator/workflow substitution accepted: false")
    print("main bypasses runtime authority guard: false")
    print("full validation runner root substitution accepted: false")
    print("full validation runner self path substitution accepted: false")
    print("full validation sequence substitution accepted: false")
    print("full validation execution function substitution accepted: false")
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
