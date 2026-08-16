#!/usr/bin/env python3
"""Focused negatives for sustained-soak human evidence repository containment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
AUTHORITY_DIR = "contracts/operations"
TRACKED = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
UNTRACKED = ROOT / "contracts/operations/.sustained-soak-human-evidence-untracked.json"
SYMLINK = ROOT / "contracts/operations/.sustained-soak-human-evidence-symlink.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("sustained_soak_review_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import sustained-soak validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reject(validator, ref: str, label: str) -> None:
    try:
        validator.dedicated_ref(ref, AUTHORITY_DIR, label)
    except validator.Fail:
        print(f"PASS reject: {label}")
        return
    raise RuntimeError(f"sustained-soak human evidence unexpectedly accepted: {label}")


def main() -> int:
    validator = load_validator()
    original = TRACKED.read_bytes()
    try:
        UNTRACKED.write_text("{}\n", encoding="utf-8")
        expect_reject(validator, str(UNTRACKED.relative_to(ROOT)), "untracked human evidence")
        UNTRACKED.unlink(missing_ok=True)

        SYMLINK.symlink_to(TRACKED.name)
        expect_reject(validator, str(SYMLINK.relative_to(ROOT)), "symlinked human evidence")
        SYMLINK.unlink(missing_ok=True)

        TRACKED.write_bytes(original + b"\n")
        expect_reject(validator, str(TRACKED.relative_to(ROOT)), "post-commit human evidence mutation")
        TRACKED.write_bytes(original)
    finally:
        UNTRACKED.unlink(missing_ok=True)
        SYMLINK.unlink(missing_ok=True)
        TRACKED.write_bytes(original)

    print("Memory OS sustained-soak human evidence path negative suite PASS")
    print("untracked human evidence accepted: false")
    print("symlinked human evidence accepted: false")
    print("post-commit human evidence mutation accepted: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
