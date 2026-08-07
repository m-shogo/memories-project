#!/usr/bin/env python3
"""Validate structural hygiene of the canonical operability status ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_SCHEMA = "memory-os-operability-status.0.1"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def unique_strings(value: Any, field: str) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(all(isinstance(item, str) and item.strip() for item in value), f"{field} contains empty/non-string value")
    require(len(value) == len(set(value)), f"{field} contains exact duplicates")
    return value


def main() -> int:
    status = load(STATUS)
    require(status.get("schemaVersion") == CANONICAL_SCHEMA, "status schema drift")
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list) and areas, "areas missing")
    ids: set[str] = set()
    p0_count = 0
    for index, area in enumerate(areas):
        require(isinstance(area, dict), f"areas[{index}] invalid")
        area_id = area.get("id")
        require(isinstance(area_id, str) and area_id and area_id not in ids, f"areas[{index}].id invalid/duplicate")
        ids.add(area_id)
        if not area_id.startswith("OPS-P0-"):
            continue
        p0_count += 1
        existing = unique_strings(area.get("existingEvidence"), f"{area_id}.existingEvidence")
        missing = unique_strings(area.get("missingEvidence"), f"{area_id}.missingEvidence")
        refs = unique_strings(area.get("evidenceRefs"), f"{area_id}.evidenceRefs")
        require(not (set(existing) & set(missing)), f"{area_id} has the same statement in existingEvidence and missingEvidence")
        for ref in refs:
            relative = Path(ref)
            require(not relative.is_absolute() and ".." not in relative.parts, f"{area_id} unsafe evidence ref: {ref}")
            require((ROOT / relative).is_file(), f"{area_id} evidence ref missing: {ref}")
            require("diagnostic.last.json" not in ref, f"{area_id} failure diagnostic cannot be canonical proof: {ref}")
        area_status = area.get("status")
        blocking = area.get("blocking")
        require(blocking is True, f"{area_id} is a P0 gate and must remain classified as blocking")
        if area_status == "READY":
            require(not missing, f"{area_id} READY cannot retain missingEvidence")
            require(existing and refs, f"{area_id} READY requires named evidence")
        else:
            require(missing, f"{area_id} incomplete status requires missingEvidence")
    require(p0_count >= 9, "unexpected P0 area count")
    print("Memory OS operability status hygiene validation PASS")
    print(f"status schema: {CANONICAL_SCHEMA}")
    print(f"P0 areas checked: {p0_count}")
    print("exact duplicate authority entries: none")
    print("failure diagnostics referenced as proof: none")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY STATUS HYGIENE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
