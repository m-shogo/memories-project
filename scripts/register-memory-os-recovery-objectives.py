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
PLACEHOLDER_METHODS = {
    "tbd", "todo", "unknown", "default", "n/a", "na", "later", "pending",
    "none", "not defined", "not_defined",
}
APPROVAL_SCHEMA = "memory-os-recovery-objectives-approval.v1"
APPROVAL_ROLES = {"RECOVERY_OWNER", "OPERABILITY"}
APPROVAL_FIELDS = {
    "schemaVersion",
    "objectiveId",
    "reviewRole",
    "decision",
    "scope",
    "rpoSeconds",
    "rtoSeconds",
    "maximumObjectDatabaseSkewSeconds",
    "reviewedAt",
    "reviewerPseudonym",
    "productionTraffic",
    "productionCredentials",
    "automaticPromotion",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def parse_utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} must be UTC RFC3339 date-time") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field} must be UTC")
    return parsed


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value and not Path(value).is_absolute(), f"{field} invalid")
    path = Path(value)
    require(".." not in path.parts, f"{field} invalid")
    require((ROOT / path).is_file(), f"{field} evidence missing: {value}")
    return value


def approval_document(ref: str, record: dict[str, Any], approved_at: datetime) -> dict[str, Any]:
    document = load(ROOT / ref)
    require(set(document) == APPROVAL_FIELDS, "approval evidence field drift")
    require(document.get("schemaVersion") == APPROVAL_SCHEMA, "approval evidence schemaVersion drift")
    require(document.get("decision") == "APPROVED", "approval evidence decision must be APPROVED")
    role = document.get("reviewRole")
    require(role in APPROVAL_ROLES, "approval evidence reviewRole invalid")
    reviewer = document.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and reviewer.strip(), "approval evidence reviewerPseudonym required")
    reviewed_at = parse_utc_timestamp(document.get("reviewedAt"), "approval evidence reviewedAt")
    require(reviewed_at <= approved_at, "approval evidence cannot post-date objective approval")
    for field in ("objectiveId", "scope", "rpoSeconds", "rtoSeconds", "maximumObjectDatabaseSkewSeconds"):
        require(document.get(field) == record.get(field), f"approval evidence {field} binding mismatch")
    for field in ("productionTraffic", "productionCredentials", "automaticPromotion"):
        require(document.get(field) is False, f"approval evidence {field} must remain false")
    return document


def evidence_refs(value: Any, record: dict[str, Any], approved_at: datetime) -> list[str]:
    require(isinstance(value, list) and len(value) == 2, "exactly two typed approvalEvidenceRefs required")
    require(len(value) == len(set(value)), "approvalEvidenceRefs must be distinct")
    refs = [repo_ref(ref, "approvalEvidenceRefs") for ref in value]
    approvals = [approval_document(ref, record, approved_at) for ref in refs]
    roles = [approval.get("reviewRole") for approval in approvals]
    require(set(roles) == APPROVAL_ROLES, "Recovery Owner and Operability approvals are both required")
    reviewers = [approval.get("reviewerPseudonym") for approval in approvals]
    require(len(set(reviewers)) == 2, "Recovery Owner and Operability reviewers must be distinct")
    return refs


def measurement_method(value: Any, field: str) -> str:
    require(isinstance(value, str), f"{field} invalid")
    normalized = " ".join(value.strip().split())
    require(1 <= len(normalized) <= 240, f"{field} invalid")
    require(normalized.casefold() not in PLACEHOLDER_METHODS, f"{field} cannot be placeholder text")
    return normalized


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

    for field in ("rpoMeasurementMethod", "rtoMeasurementMethod", "skewMeasurementMethod"):
        measurement_method(record.get(field), field)

    approved_at = parse_utc_timestamp(record.get("approvedAt"), "approvedAt")
    owner_ref = repo_ref(record.get("ownerRef"), "ownerRef")
    approvals = evidence_refs(record.get("approvalEvidenceRefs"), record, approved_at)
    require(owner_ref not in approvals, "ownerRef must be distinct from approvalEvidenceRefs")

    supersedes = record.get("supersedesObjectiveId")
    require(supersedes is None or (isinstance(supersedes, str) and OBJECTIVE_ID.fullmatch(supersedes)), "supersedesObjectiveId invalid")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, "objective approval cannot promote production")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "password", "private_key", "access_key", "authorization: bearer",
        "account_id", "session_id", "@", "latest",
    ):
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
            "objective values are supplied by reviewed human authority and are never chosen or defaulted by this writer",
            "the current objective requires distinct typed Recovery Owner and Operability approvals bound to the exact objectiveId and RPO/RTO/skew values",
            "measurement methods must be concrete non-placeholder descriptions and approval/owner evidence must resolve to distinct repository artifacts",
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
    print("Typed Recovery Owner/Operability approvals bound to objective: true")
    print("Objective values chosen by writer: false")
    print("Production evidence: false")
    print("Production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
