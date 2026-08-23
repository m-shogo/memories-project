#!/usr/bin/env python3
"""Fail-closed authority and rollback negatives for typed non-resurrection reconcile."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
CANONICAL_GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
ALTERNATE_FILE = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler(name: str):
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_bytes() -> dict[Path, bytes]:
    return {
        CANONICAL_CONTRACT: CANONICAL_CONTRACT.read_bytes(),
        CANONICAL_REGISTRY: CANONICAL_REGISTRY.read_bytes(),
        CANONICAL_GEN_REGISTRY: CANONICAL_GEN_REGISTRY.read_bytes(),
        CANONICAL_STATUS: CANONICAL_STATUS.read_bytes(),
    }


def require_unchanged(before: dict[Path, bytes], label: str) -> None:
    for path, value in before.items():
        require(path.read_bytes() == value, f"{label} mutated canonical {path.name}")


def prove_substitution_rejected(attribute: str) -> None:
    reconciler = load_reconciler(f"memory_os_typed_non_resurrection_authority_{attribute.lower()}")
    before = canonical_bytes()
    setattr(reconciler, attribute, ALTERNATE_FILE)
    try:
        reconciler.main()
    except reconciler.Fail:
        pass
    else:
        raise Fail(f"{attribute} substitution unexpectedly accepted")
    require_unchanged(before, attribute)
    print(f"PASS reject: {attribute} substitution fails closed without canonical mutation")


def expect_shared_registry_rejection(module, registry: dict, label: str) -> None:
    validator = getattr(module, "validate_registry_for_append", None)
    require(callable(validator), f"{label} shared registry validator missing")
    try:
        validator(registry)
    except Exception as exc:
        fail_type = getattr(module, "Fail", None)
        require(isinstance(fail_type, type) and isinstance(exc, fail_type), f"{label} leaked non-domain exception: {type(exc).__name__}")
        return
    raise Fail(f"corrupt {label} registry unexpectedly accepted")


def prove_corrupt_append_only_authority_rejected() -> None:
    reconciler = load_reconciler("memory_os_typed_non_resurrection_corrupt_registry")
    before = canonical_bytes()
    typed_writer = reconciler.load_module(reconciler.TYPED_WRITER, "memory_os_typed_writer_negative")
    generation_writer = reconciler.load_module(reconciler.GEN_WRITER, "memory_os_generation_writer_negative")
    typed_registry = json.loads(CANONICAL_REGISTRY.read_text(encoding="utf-8"))
    generation_registry = json.loads(CANONICAL_GEN_REGISTRY.read_text(encoding="utf-8"))

    typed_cases = (
        ("registeredRecordCount", 1),
        ("completeRecordCount", True),
        ("productionEvidence", True),
    )
    for field, value in typed_cases:
        corrupt = copy.deepcopy(typed_registry)
        corrupt[field] = value
        expect_shared_registry_rejection(typed_writer, corrupt, f"typed {field}")

    generation_cases = (
        ("registeredEvidenceCount", 1),
        ("productionEquivalentRecoveryCandidateCount", True),
        ("productionReady", True),
    )
    for field, value in generation_cases:
        corrupt = copy.deepcopy(generation_registry)
        corrupt[field] = value
        expect_shared_registry_rejection(generation_writer, corrupt, f"generation {field}")

    require_unchanged(before, "corrupt registry rejection")
    print("PASS reject: corrupt append-only typed/generation authority is rejected without auto-heal")


def prove_post_write_aggregate_rollback() -> None:
    reconciler = load_reconciler("memory_os_typed_non_resurrection_aggregate_rollback")
    before = canonical_bytes()
    original_post_validator = reconciler.run_post_validator

    def fail_operability(path: Path, expected_relative: Path, label: str) -> None:
        if label == "operability validator":
            raise reconciler.Fail("synthetic aggregate operability rejection")
        original_post_validator(path, expected_relative, label)

    reconciler.run_post_validator = fail_operability
    try:
        reconciler.main()
    except reconciler.Fail as exc:
        require("synthetic aggregate operability rejection" in str(exc), "unexpected aggregate rejection")
    else:
        raise Fail("synthetic aggregate operability rejection unexpectedly accepted")
    require_unchanged(before, "aggregate rejection")
    print("PASS rollback: aggregate rejection byte-restores typed, generation and status authorities")


def main() -> int:
    require(ALTERNATE_FILE.is_file(), "alternate repository fixture missing")
    for attribute in (
        "CONTRACT",
        "REGISTRY",
        "GEN_REGISTRY",
        "TYPED_WRITER",
        "GEN_WRITER",
        "VALIDATOR",
        "OPERABILITY_VALIDATOR",
        "STATUS",
    ):
        prove_substitution_rejected(attribute)
    prove_corrupt_append_only_authority_rejected()
    prove_post_write_aggregate_rollback()
    print("Memory OS typed non-resurrection reconcile negative suite PASS")
    print("generic non-resurrection PASS promoted to typed coverage: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP NON-RESURRECTION RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
