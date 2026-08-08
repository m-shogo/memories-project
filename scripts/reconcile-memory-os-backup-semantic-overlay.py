#!/usr/bin/env python3
"""Validate semantic wording for OPS-P0-007 without creating duplicate gaps."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
LEGACY_GAPS = {
    "production object backup with independently owned retention, deletion protection, immutability and lifecycle verification",
    "production independent object backup retention, deletion protection, immutability and lifecycle verification",
    "production-shaped cross-cluster isolated restore with approved recovery owner and promotion decision",
    "production-shaped cross-cluster isolated restore drill with approved recovery owner and promotion decision",
}


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def normalize(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO",
            "backup semantic overlay requires productionDecision NO_GO")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY",
            "backup semantic overlay requires PARTIAL_FOUNDATIONS_ONLY")
    missing = gate.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence must be a list")

    # These historical semantic overlays predate the generation-bound canonical
    # blocker set. They must be removed, not rewritten into a second equivalent
    # blocker. The canonical six are owned by reconcile-memory-os-backup-authority.py.
    gate["missingEvidence"] = unique([
        item for item in missing
        if item not in LEGACY_GAPS
    ])

    lowered = [item.lower() for item in gate["missingEvidence"]]
    require(any("production independent object backup retention" in item and
                "tls" in item and "lifecycle" in item for item in lowered),
            "canonical independent object production gap missing")
    require(any("production-shaped cross-cluster isolated restore drill" in item and
                "promotion decision" in item for item in lowered),
            "canonical isolated restore drill production gap missing")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = load(STATUS_PATH)
    candidate = normalize(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    left = copy.deepcopy(current)
    right = copy.deepcopy(candidate)
    left.pop("asOf", None)
    right.pop("asOf", None)
    changed = left != right

    if args.check:
        require(not changed, "backup semantic overlay is not normalized")
        print("Memory OS backup semantic overlay check PASS")
        return 0
    if not changed:
        print("Memory OS backup semantic overlay already normalized")
        return 0
    STATUS_PATH.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Removed redundant OPS-P0-007 semantic blocker overlays")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"BACKUP SEMANTIC OVERLAY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
