#!/usr/bin/env python3
"""Validate append-only explicitly approved recovery objectives."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objectives writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    writer = load_writer()
    require(contract.get("schemaVersion") == "memory-os-recovery-objectives-admission.v1", "contract schema drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "registry ref drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)) and WRITER.is_file(), "writer ref drift")
    for field in ("validator", "workflow"):
        ref = contract.get(field)
        require(isinstance(ref, str) and ref and (ROOT / ref).is_file(), f"contract artifact missing: {field}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "recovery-objective rules must remain fail-closed")

    require(registry.get("schemaVersion") == "memory-os-recovery-objectives-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "objectives registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "objectives registry cannot promote production")
    rows = registry.get("records")
    count = registry.get("approvedObjectiveCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "objectives records invalid")
    require(isinstance(count, int) and count == len(rows), "approvedObjectiveCount drift")
    ids: set[str] = set()
    previous: str | None = None
    for row in rows:
        writer.validate_record(row)
        objective_id = row.get("objectiveId")
        require(isinstance(objective_id, str) and objective_id not in ids, f"duplicate objectiveId: {objective_id}")
        ids.add(objective_id)
        require(row.get("supersedesObjectiveId") == previous, "recovery objective supersession chain drift")
        previous = objective_id
    current_id = registry.get("currentObjectiveId")
    require(current_id == previous, "currentObjectiveId must equal latest append-only record")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority required")
    require(authority.get("approvedObjectiveCount") == count, "contract objective count drift")
    require(authority.get("currentObjectiveId") == current_id, "contract currentObjectiveId drift")
    defined = count > 0
    require(authority.get("rpoDefined") is defined, "rpoDefined drift")
    require(authority.get("rtoDefined") is defined, "rtoDefined drift")
    require(authority.get("objectDatabaseSkewDefined") is defined, "objectDatabaseSkewDefined drift")
    require(authority.get("productionEvidence") is False and authority.get("productionReady") is False, "objective authority cannot promote production")
    require(authority.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    print("Memory OS recovery objectives validation PASS")
    print(f"approved objective records: {count}")
    print(f"current objective: {current_id or 'none'}")
    print(f"RPO/RTO defined: {str(defined).lower()}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
