#!/usr/bin/env python3
"""Pin fail-closed compatibility admission count and authority semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/update-memory-os-compatibility-admission-gaps.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_generator():
    spec = importlib.util.spec_from_file_location("compatibility_admission_gap_generator", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load compatibility gap generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_count_rejection(module, value, field: str) -> None:
    rejected = False
    try:
        module.non_negative_count(value, field)
    except SystemExit as exc:
        require(field in str(exc), f"unexpected count rejection for {field}: {exc}")
        rejected = True
    require(rejected, f"invalid compatibility count accepted for {field}: {value!r}")


def main() -> int:
    module = load_generator()
    for field in (
        "approvedReleaseCount",
        "approvedClientBaselineCount",
        "reviewedArtifactCount",
        "approvedRollbackPairCount",
    ):
        expect_count_rejection(module, True, field)
        expect_count_rejection(module, False, field)
        expect_count_rejection(module, -1, field)
    require(module.non_negative_count(0, "validZero") == 0, "zero count should remain valid")
    print("PASS: compatibility admission counts reject booleans and negative values")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
