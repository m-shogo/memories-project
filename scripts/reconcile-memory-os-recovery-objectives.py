#!/usr/bin/env python3
"""Reconcile explicitly approved recovery objectives without inventing values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
EVIDENCE_PREFIX = "recovery objectives approval is append-only:"
REFS = (
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/reconcile-memory-os-recovery-objectives.py",
    ".github/workflows/recovery-objectives-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    registry = load(REGISTRY)
    contract = load(CONTRACT)
    rows = registry.get("records")
    count = registry.get("approvedObjectiveCount")
    current_id = registry.get("currentObjectiveId")
    require(isinstance(rows, list) and isinstance(count, int) and len(rows) == count, "recovery objective registry count drift")
    require(current_id == (rows[-1].get("objectiveId") if rows else None), "current objective drift")
    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority missing")
    authority["approvedObjectiveCount"] = count
    authority["currentObjectiveId"] = current_id
    authority["rpoDefined"] = count > 0
    authority["rtoDefined"] = count > 0
    authority["objectDatabaseSkewDefined"] = count > 0
    authority["productionEvidence"] = False
    authority["productionReady"] = False
    authority["productionDecision"] = "NO_GO"
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-007 evidence arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    if count == 0:
        evidence = f"{EVIDENCE_PREFIX} approval registry exists but contains 0 records, so RPO/RTO/object-database skew remain intentionally undefined and restore evidence is forbidden from inventing targets"
    else:
        evidence = f"{EVIDENCE_PREFIX} {count} reviewed objective record(s) exist and current objectiveId={current_id}; measured restore evidence must bind this exact objective and satisfy its RPO/RTO/skew targets, while objective approval itself is not production evidence"
    append_once(existing, evidence)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"recovery objective authority ref missing: {ref}")
        append_once(refs, ref)
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Memory OS recovery objectives reconciliation PASS")
    print(f"approved objective records: {count}")
    print(f"current objective: {current_id or 'none'}")
    print("production evidence: false")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES RECONCILE FAILED: {exc}")
        raise SystemExit(1)
