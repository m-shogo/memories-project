#!/usr/bin/env python3
"""Validate OPS-P0-007 semantic blocker authority without rewriting it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


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


def validate_runtime_authority() -> None:
    canonical = ROOT / "contracts/operations/production-operability-status.json"
    require(STATUS_PATH == canonical, "canonical production status identity drift")
    require(STATUS_PATH.is_file(), "canonical production status missing")
    require(not STATUS_PATH.is_symlink(), "canonical production status must not be a symlink")
    try:
        require(STATUS_PATH.resolve(strict=True) == canonical,
                "canonical production status path drift")
    except OSError as exc:
        raise ReconcileFailure("cannot resolve canonical production status") from exc


def validate(status: dict[str, Any]) -> None:
    require(status.get("productionDecision") == "NO_GO",
            "backup semantic authority requires productionDecision NO_GO")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY",
            "backup semantic authority requires PARTIAL_FOUNDATIONS_ONLY")
    require_canonical_gaps(gate.get("missingEvidence"), ReconcileFailure)
    require(gate.get("status") != "READY",
            "semantic validation cannot make OPS-P0-007 READY")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.parse_args()

    validate_runtime_authority()
    status = load(STATUS_PATH)
    validate(status)
    print("Memory OS backup semantic authority PASS; canonical blockers unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"BACKUP SEMANTIC AUTHORITY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
