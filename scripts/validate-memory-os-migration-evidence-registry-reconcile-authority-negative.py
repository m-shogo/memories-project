#!/usr/bin/env python3
"""Prove migration evidence reconciliation cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-evidence-registry.py"
ORPHAN_RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-recovery-result-orphans.py"
CANONICAL_REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
CANONICAL_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
CANONICAL_LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
CANONICAL_LOCAL_CONTRACT = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_canonical_bytes_unchanged(before: dict[Path, bytes], label: str) -> None:
    for path, payload in before.items():
        require(path.read_bytes() == payload, f"{label} substitution mutated {path.relative_to(ROOT)}")


def expect_path_substitution_rejected(
    module: Any,
    attribute: str,
    replacement: Path,
    label: str,
    before: dict[Path, bytes],
) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        rejected = False
        try:
            module.main()
        except module.Fail as exc:
            require("authority drift" in str(exc) or "missing or escapes repository" in str(exc),
                    f"unexpected {label} rejection: {exc}")
            rejected = True
        require(rejected, f"reconciler accepted non-canonical {label}")
    finally:
        setattr(module, attribute, original)
    require_canonical_bytes_unchanged(before, label)


def expect_validator_chain_substitution_rejected(module: Any, before: dict[Path, bytes]) -> None:
    original = module.POST_WRITE_VALIDATORS
    module.POST_WRITE_VALIDATORS = ()
    try:
        rejected = False
        try:
            module.main()
        except module.Fail as exc:
            require("validator chain authority drift" in str(exc),
                    f"unexpected validator-chain rejection: {exc}")
            rejected = True
        require(rejected, "migration evidence reconciler accepted validator-chain substitution")
    finally:
        module.POST_WRITE_VALIDATORS = original
    require_canonical_bytes_unchanged(before, "validator-chain")


def expect_atomic_replace_failure_rolls_back(module: Any, before: dict[Path, bytes]) -> None:
    paths = (CANONICAL_CONTRACT, CANONICAL_LIFECYCLE, CANONICAL_STATUS)
    outputs = {path: module.load(path) for path in paths}
    for value in outputs.values():
        value["atomicRollbackProbe"] = "must-not-persist"

    original_replace = module.os.replace
    calls = 0

    def fail_second_replace(source, destination) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic migration evidence atomic replace failure")
        original_replace(source, destination)

    module.os.replace = fail_second_replace
    try:
        rejected = False
        try:
            module.commit_outputs_transactionally(outputs)
        except module.Fail as exc:
            require("restored prior authority" in str(exc), f"unexpected atomic rollback rejection: {exc}")
            rejected = True
        require(rejected, "migration evidence reconciler accepted synthetic atomic replace failure")
    finally:
        module.os.replace = original_replace

    require(calls >= 5, "migration evidence rollback did not atomically restore all canonical authorities")
    for path in paths:
        require(path.read_bytes() == before[path], f"atomic replace failure mutated {path.relative_to(ROOT)}")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary migration evidence authority remained after replace failure: {leftovers}")


def prove_registry_reconcile_authorities(before: dict[Path, bytes]) -> None:
    module = load_module(RECONCILER, "migration_evidence_registry_reconcile_authority_negative")
    replacement_file = ROOT / "README.md"
    replacement_directory = ROOT / "scripts"
    cases = (
        ("REGISTRY_CONTRACT", replacement_file, "registry contract"),
        ("REGISTRY", replacement_file, "registry"),
        ("WRITER", replacement_file, "writer"),
        ("REGISTRY_VALIDATOR", replacement_file, "registry validator"),
        ("RECOVERY_VALIDATOR", replacement_file, "recovery-point validator"),
        ("ARTIFACT_CONTRACT", replacement_file, "artifact contract"),
        ("ARTIFACT_RUNNER", replacement_file, "artifact runner"),
        ("ARTIFACT_VALIDATOR", replacement_file, "artifact validator"),
        ("ARTIFACT_EVIDENCE_ROOT", replacement_directory, "artifact evidence root"),
        ("LOCAL_RESTORE", replacement_file, "local restore result"),
        ("WORKFLOW", replacement_file, "workflow"),
        ("LIFECYCLE", replacement_file, "lifecycle contract"),
        ("LIFECYCLE_VALIDATOR", replacement_file, "lifecycle validator"),
        ("OPERABILITY_VALIDATOR", replacement_file, "operability validator"),
        ("STATUS", replacement_file, "production status"),
    )
    for attribute, replacement, label in cases:
        expect_path_substitution_rejected(module, attribute, replacement, f"registry {label}", before)
        print(f"PASS authority reject: registry {label}")
    expect_validator_chain_substitution_rejected(module, before)
    print("PASS authority reject: registry post-write validator chain")
    expect_atomic_replace_failure_rolls_back(module, before)
    print("PASS atomic rollback: registry derived authority")


def prove_orphan_rescue_authorities(before: dict[Path, bytes]) -> None:
    module = load_module(ORPHAN_RECONCILER, "migration_recovery_orphan_reconcile_authority_negative")
    replacement_file = ROOT / "README.md"
    replacement_directory = ROOT / "scripts"
    cases = (
        ("RESULT_ROOT", replacement_directory, "orphan result root"),
        ("REGISTRY", replacement_file, "orphan registry"),
        ("REGISTRY_CONTRACT", replacement_file, "orphan registry contract"),
        ("LIFECYCLE", replacement_file, "orphan lifecycle contract"),
        ("STATUS", replacement_file, "orphan production status"),
        ("LOCAL_CONTRACT", replacement_file, "orphan local recovery contract"),
        ("WRITER", replacement_file, "orphan writer"),
        ("RESULT_VALIDATOR", replacement_file, "orphan result validator"),
        ("LOCAL_RECONCILER", replacement_file, "orphan local reconciler"),
        ("GLOBAL_RECONCILER", replacement_file, "orphan global reconciler"),
    )
    for attribute, replacement, label in cases:
        expect_path_substitution_rejected(module, attribute, replacement, label, before)
        print(f"PASS authority reject: {label}")


def main() -> int:
    before = {
        CANONICAL_REGISTRY: CANONICAL_REGISTRY.read_bytes(),
        CANONICAL_CONTRACT: CANONICAL_CONTRACT.read_bytes(),
        CANONICAL_LIFECYCLE: CANONICAL_LIFECYCLE.read_bytes(),
        CANONICAL_LOCAL_CONTRACT: CANONICAL_LOCAL_CONTRACT.read_bytes(),
        CANONICAL_STATUS: CANONICAL_STATUS.read_bytes(),
    }
    prove_registry_reconcile_authorities(before)
    prove_orphan_rescue_authorities(before)
    print("Memory OS migration evidence reconcile authority negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"MIGRATION EVIDENCE RECONCILE AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
