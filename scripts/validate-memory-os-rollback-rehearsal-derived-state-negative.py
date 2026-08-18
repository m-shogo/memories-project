#!/usr/bin/env python3
"""Reject boolean/negative rollback admission-state counts without mutating authority."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-rollback-rehearsal-gate.py"
COUNT_FIELDS = (
    "approvedReleaseCount",
    "rollbackEligibleReleaseCount",
    "admissibleReleasePairCount",
    "rehearsalRequestCount",
)


def main() -> int:
    original = CONTRACT.read_bytes()
    base = json.loads(original.decode("utf-8"))
    try:
        for field in COUNT_FIELDS:
            for bad in (False, -1):
                candidate = copy.deepcopy(base)
                candidate["currentAdmissionState"][field] = bad
                CONTRACT.write_text(
                    json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                completed = subprocess.run(
                    [sys.executable, str(VALIDATOR)],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if completed.returncode == 0:
                    raise RuntimeError(
                        f"standalone rollback validator accepted invalid {field}={bad!r}"
                    )
    finally:
        CONTRACT.write_bytes(original)

    if CONTRACT.read_bytes() != original:
        raise RuntimeError("rollback contract bytes changed after state-count negative suite")
    print("PASS: rollback admission-state counts reject booleans and negative integers")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL DERIVED STATE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
