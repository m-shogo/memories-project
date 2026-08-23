#!/usr/bin/env python3
"""Fail closed if sustained-soak independent-review writer authorities are substituted."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-sustained-soak-independent-review.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
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

    print("PASS: sustained-soak independent-review writer rejects data/executable/lock authority substitution")
    print("PASS: paired contract/registry substitution cannot bypass canonical authority checks")
    print("PASS: imported validator remains bound to canonical contract and registry authorities")
    print("PASS: authority rejection preserves canonical append-only review authority")
    print("human review evidence generated: false")
    print("leak proof promoted: false")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
