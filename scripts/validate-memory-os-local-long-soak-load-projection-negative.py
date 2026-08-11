#!/usr/bin/env python3
"""Negative checks for fail-closed LOCAL_LONG_SOAK load projection boundaries."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/reconcile-memory-os-local-long-soak-load-projection.py"
SPEC = importlib.util.spec_from_file_location("local_long_soak_projection", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("LOCAL LONG SOAK LOAD PROJECTION NEGATIVE FAILED: cannot load projection module")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def expect_reject(label: str, mutate) -> None:
    row = module.derived_row()
    mutate(row)
    try:
        module.assert_local_only_boundary(row)
    except module.Fail:
        print(f"PASS reject: {label}")
        return
    raise AssertionError(f"corruption accepted: {label}")


def main() -> int:
    valid = copy.deepcopy(module.derived_row())
    module.assert_local_only_boundary(valid)

    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityApproved",
        "thresholdsApproved",
    ):
        expect_reject(f"{key} manufactured", lambda row, key=key: row.__setitem__(key, True))

    for key in (
        "productionEquivalent",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
    ):
        expect_reject(
            f"runMetadata.{key} manufactured",
            lambda row, key=key: row["runMetadata"].__setitem__(key, True),
        )

    expect_reject(
        "approval authority manufactured",
        lambda row: row["runMetadata"].__setitem__("approvalAuthority", "HUMAN_APPROVED"),
    )
    expect_reject("run metadata removed", lambda row: row.pop("runMetadata"))

    print("Memory OS LOCAL_LONG_SOAK load projection negative suite PASS")
    print("production evidence promotion accepted: false")
    print("production traffic promotion accepted: false")
    print("production credentials promotion accepted: false")
    print("automatic approval authority accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
