#!/usr/bin/env python3
"""Validate deterministic P0 admission inventory against canonical registries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    inventory = load(INVENTORY)
    status = load(STATUS)
    require(inventory.get("schemaVersion") == "memory-os-operability-admission-inventory.v1", "inventory schema drift")
    require(inventory.get("deterministic") is True, "inventory must remain deterministic")
    require(inventory.get("productionEvidence") is False and inventory.get("productionReady") is False, "inventory cannot promote production")
    require(inventory.get("productionDecision") == "NO_GO" and status.get("productionDecision") == "NO_GO", "production decision drift")
    rows = inventory.get("areas")
    require(isinstance(rows, list) and len(rows) == 9, "inventory must contain P0-001 through P0-009")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    require(ids == [f"OPS-P0-{number:03d}" for number in range(1, 10)], f"inventory area order/set drift: {ids}")
    status_rows = {row.get("id"): row for row in status.get("areas", []) if isinstance(row, dict)}
    for row in rows:
        area_id = row["id"]
        require(row.get("productionEvidence") is False and row.get("productionReady") is False, f"{area_id} inventory cannot promote production")
        require(isinstance(row.get("foundationImplemented"), bool), f"{area_id}.foundationImplemented invalid")
        require(isinstance(row.get("admittedEvidenceCount"), int) and row["admittedEvidenceCount"] >= 0, f"{area_id}.admittedEvidenceCount invalid")
        require(isinstance(row.get("nextGate"), str) and row["nextGate"], f"{area_id}.nextGate missing")
        source = status_rows.get(area_id)
        require(isinstance(source, dict), f"status row missing: {area_id}")
        require(row.get("status") == source.get("status"), f"{area_id}.status drift")
        require(row.get("blocking") == source.get("blocking"), f"{area_id}.blocking drift")
        missing = source.get("missingEvidence")
        require(isinstance(missing, list), f"{area_id}.missingEvidence invalid")
        require(row.get("missingEvidenceCount") == len(missing), f"{area_id}.missingEvidenceCount drift")
    generations = load(ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    require(inventory.get("productionEquivalentEnvironmentGenerationCount") == generations.get("registeredGenerationCount"), "environment generation count drift")
    print("Memory OS operability admission inventory validation PASS")
    print("P0 areas: 9")
    print(f"production-equivalent generations: {inventory.get('productionEquivalentEnvironmentGenerationCount')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY ADMISSION INVENTORY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
