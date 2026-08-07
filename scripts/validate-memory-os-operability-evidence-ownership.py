#!/usr/bin/env python3
"""Validate high-impact operability evidence is attached only to its owning P0 areas."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/operability-evidence-ownership-contract.v1.json"
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
    contract = load(CONTRACT)
    status = load(STATUS)
    require(contract.get("schemaVersion") == "memory-os-operability-evidence-ownership.v1", "contract schema drift")
    require(contract.get("statusPath") == str(STATUS.relative_to(ROOT)), "status path drift")
    require(contract.get("productionDecision") == "NO_GO", "ownership contract production decision drift")
    require(status.get("productionDecision") == "NO_GO", "status production decision must remain NO_GO")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "ownership rules must remain true")

    areas = status.get("areas")
    require(isinstance(areas, list), "status areas missing")
    by_id: dict[str, set[str]] = {}
    for area in areas:
        require(isinstance(area, dict) and isinstance(area.get("id"), str), "invalid status area")
        area_id = area["id"]
        if not area_id.startswith("OPS-P0-"):
            continue
        refs = area.get("evidenceRefs")
        require(isinstance(refs, list), f"{area_id} evidenceRefs missing")
        require(all(isinstance(ref, str) for ref in refs), f"{area_id} evidenceRefs invalid")
        by_id[area_id] = set(refs)
    require(by_id, "no P0 operability areas found")

    entries = contract.get("ownership")
    require(isinstance(entries, list) and entries, "ownership entries missing")
    seen_refs: set[str] = set()
    for index, entry in enumerate(entries):
        require(isinstance(entry, dict), f"ownership[{index}] invalid")
        ref = entry.get("ref")
        allowed = entry.get("allowedOwners")
        required = entry.get("requiredOwners")
        require(isinstance(ref, str) and ref and ref not in seen_refs, f"ownership[{index}].ref invalid/duplicate")
        seen_refs.add(ref)
        require((ROOT / ref).is_file(), f"owned authority path missing: {ref}")
        require(isinstance(allowed, list) and allowed and len(allowed) == len(set(allowed)), f"ownership[{index}].allowedOwners invalid")
        require(isinstance(required, list) and required and len(required) == len(set(required)), f"ownership[{index}].requiredOwners invalid")
        require(set(required) <= set(allowed), f"ownership[{index}] required owners must be allowed")
        for owner in allowed:
            require(owner in by_id, f"ownership[{index}] unknown allowed P0 owner: {owner}")
        for owner in required:
            require(ref in by_id[owner], f"{ref} missing from required owner {owner}")
        allowed_set = set(allowed)
        for area_id, area_refs in by_id.items():
            if ref in area_refs:
                require(area_id in allowed_set, f"{ref} is misclassified under {area_id}; allowed={allowed}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    require(readiness.get("productionReady") is False, "ownership validator cannot make productionReady")
    print("Memory OS operability evidence ownership validation PASS")
    print(f"P0 areas checked: {len(by_id)}")
    print(f"owned authorities: {len(entries)}")
    print("cross-area misclassification: none")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY EVIDENCE OWNERSHIP FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
