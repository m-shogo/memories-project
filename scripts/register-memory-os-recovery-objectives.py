#!/usr/bin/env python3
"""Append one explicitly approved recovery-objectives record."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
LOCK = ROOT / "contracts/operations/.recovery-objectives.lock"
OBJECTIVE_ID = re.compile(r"^ro_[a-z0-9][a-z0-9_-]{7,63}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def evidence_refs(value: Any) -> list[str]:
    require(isinstance(value, list) and len(value) >= 2, "at least two approvalEvidenceRefs required")
    require(len(value) == len(set(value)), "approvalEvidenceRefs must be distinct")
    for ref in value:
        require(isinstance(ref, str) and ref and not Path(ref).is_absolute() and ".." not in Path(ref).parts, "approvalEvidenceRefs invalid")
        require((ROOT / ref).is_file(), f"approval evidence missing: {ref}")
    return value


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "schemaVersion drift")
    objective_id = record.get("objectiveId")
    require(isinstance(objective_id, str) and OBJECTIVE_ID.fullmatch(objective_id), "objectiveId invalid")
    require(record.get("scope") == "PRODUCTION_RECOVERY_OBJECTIVES", "scope invalid")
    for field in ("rpoSeconds", "rtoSeconds"):
        value = record.get(field)
        require(isinstance(value, int) and not isinstance(value, bool) and value > 0, f"{field} must be positive integer")
    skew = record.get("maximumObjectDatabaseSkewSeconds")
    require(isinstance(skew, int) and not isinstance(skew, bool) and skew >= 0, "maximumObjectDatabaseSkewSeconds invalid")
    for field in ("rpoMeasurementMethod", "rtoMeasurementMethod", "skewMeasurementMethod", "ownerRef"):
        value = record.get(field)
        require(isinstance(value, str) and 1 <= len(value) <= 240, f"{field} invalid")
    evidence_refs(record.get("approvalEvidenceRefs"))
    approved_at = record.get("approvedAt")
    require(isinstance(approved_at, str), "approvedAt required")
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fail("approvedAt must be ISO-8601 date-time") from exc
    supersedes = record.get("supersedesObjectiveId")
    require(supersedes is None or (isinstance(supersedes, str) and OBJECTIVE_ID.fullmatch(supersedes)), "supersedesObjectiveId invalid")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, "objective approval cannot promote production")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "password", "private_key", "access_key", "authorization: bearer", "account_id", "session_id", "@"):
        require(forbidden not in serialized, f"record contains forbidden material: {forbidden}")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".recovery-objectives.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    path = Path(args.record).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input objectives record must be outside repository")
    record = load(path)
    validate_record(record)
    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("recovery objectives registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["objectiveId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        rows = registry.get("records")
        require(registry.get("appendOnly") is True and isinstance(rows, list), "registry invalid")
        require(all(isinstance(row, dict) and row.get("objectiveId") != record["objectiveId"] for row in rows), "objectiveId already registered")
        expected_supersedes = rows[-1].get("objectiveId") if rows else None
        require(record.get("supersedesObjectiveId") == expected_supersedes, "supersedesObjectiveId must reference current approved objectives")
        rows.append(record)
        registry["approvedObjectiveCount"] = len(rows)
        registry["currentObjectiveId"] = record["objectiveId"]
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        registry["limitations"] = [
            "approved objectives are policy targets, not restore evidence",
            "measured recovery evidence must reference the exact current objectiveId",
            "objective approval does not establish production readiness"
        ]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered recovery objectives: {record['objectiveId']}")
    print("Production evidence: false")
    print("Production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
