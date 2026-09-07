#!/usr/bin/env python3
"""Fail closed if sustained-soak independent-review writer authorities are substituted."""

from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-sustained-soak-independent-review.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
CANONICAL_RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-result.py"
CANONICAL_LOCK = ROOT / "contracts/operations/.sustained-soak-independent-review.lock"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_sustained_soak_review_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load sustained-soak review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reject(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attr} substitution unexpectedly accepted")
    finally:
        setattr(module, attr, original)


def main() -> int:
    module = load_module()
    module.enforce_runtime_authorities()
    original_registry = CANONICAL_REGISTRY.read_bytes()
    original_registry_mode = stat.S_IMODE(CANONICAL_REGISTRY.stat().st_mode)
    original_contract = CANONICAL_CONTRACT.read_bytes()

    expect_reject(module, "CONTRACT_PATH", CANONICAL_REGISTRY)
    expect_reject(module, "REGISTRY", CANONICAL_CONTRACT)
    expect_reject(module, "VALIDATOR_PATH", WRITER)
    expect_reject(module, "LOCK_PATH", ROOT / "contracts/operations/.sustained-soak-independent-review.alternate.lock")

    paired = (
        ("CONTRACT_PATH", CANONICAL_REGISTRY),
        ("REGISTRY", CANONICAL_CONTRACT),
    )
    originals = {attr: getattr(module, attr) for attr, _ in paired}
    for attr, replacement in paired:
        setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.Fail:
            pass
        else:
            raise AssertionError("paired contract/registry substitution unexpectedly accepted")
    finally:
        for attr, original in originals.items():
            setattr(module, attr, original)

    if CANONICAL_REGISTRY.read_bytes() != original_registry:
        raise AssertionError("writer authority rejection mutated canonical review registry")
    if CANONICAL_CONTRACT.read_bytes() != original_contract:
        raise AssertionError("writer authority rejection mutated canonical review contract")

    module.enforce_runtime_authorities()
    validator = module.load_validator()
    if validator.CONTRACT.resolve() != CANONICAL_CONTRACT.resolve():
        raise AssertionError("writer imported validator with non-canonical contract authority")
    if validator.REGISTRY.resolve() != CANONICAL_REGISTRY.resolve():
        raise AssertionError("writer imported validator with non-canonical registry authority")
    if validator.RESULT_VALIDATOR.resolve() != CANONICAL_RESULT_VALIDATOR.resolve():
        raise AssertionError("writer imported validator with non-canonical per-run result validator authority")

    candidate_path = module.validate_candidate(module.load(CANONICAL_REGISTRY))
    try:
        if stat.S_IMODE(candidate_path.stat().st_mode) != original_registry_mode:
            raise AssertionError("validated candidate did not preserve canonical registry mode")
    finally:
        candidate_path.unlink(missing_ok=True)

    candidate_path = module.validate_candidate(module.load(CANONICAL_REGISTRY))
    forced_candidate_mode = 0o600 if original_registry_mode != 0o600 else 0o644
    os.chmod(candidate_path, forced_candidate_mode)
    original_validate_registry_for_append = module.validate_registry_for_append

    def reject_post_append(_registry):
        raise module.Fail("forced post-append validation failure")

    module.validate_registry_for_append = reject_post_append
    try:
        try:
            module.replace_registry_transactionally(candidate_path)
        except module.Fail:
            pass
        else:
            raise AssertionError("forced post-append validation failure unexpectedly accepted")
    finally:
        module.validate_registry_for_append = original_validate_registry_for_append
        candidate_path.unlink(missing_ok=True)

    if CANONICAL_REGISTRY.read_bytes() != original_registry:
        raise AssertionError("post-append failure did not restore exact canonical registry bytes")
    if stat.S_IMODE(CANONICAL_REGISTRY.stat().st_mode) != original_registry_mode:
        raise AssertionError("post-append failure did not restore exact canonical registry mode")
    residue = list(CANONICAL_REGISTRY.parent.glob(".sustained-soak-independent-review-rollback-*.tmp"))
    residue += list(CANONICAL_REGISTRY.parent.glob(".sustained-soak-independent-review-registry-candidate-*.json"))
    if residue:
        raise AssertionError(f"transactional review writer left temporary residue: {residue}")

    print("PASS: sustained-soak independent-review writer rejects data/executable/lock authority substitution")
    print("PASS: paired contract/registry substitution cannot bypass canonical authority checks")
    print("PASS: imported validator remains bound to canonical contract, registry and per-run result authorities")
    print("PASS: validated candidate preserves canonical registry permission mode")
    print("PASS: post-append failure restores exact canonical registry bytes and mode without temporary residue")
    print("PASS: authority rejection preserves canonical append-only review authority")
    print("human review evidence generated: false")
    print("leak proof promoted: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
