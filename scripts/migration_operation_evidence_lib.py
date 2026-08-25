#!/usr/bin/env python3
"""Shared validation for Memory OS migration operation evidence."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

_CANONICAL_ROOT = Path(__file__).resolve().parents[1]
_CANONICAL_CONTRACT_PATH = _CANONICAL_ROOT / "contracts/operations/migration-operation-evidence-contract.v1.json"
_CANONICAL_LIFECYCLE_PATH = _CANONICAL_ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"

ROOT = _CANONICAL_ROOT
CONTRACT_PATH = _CANONICAL_CONTRACT_PATH
LIFECYCLE_PATH = _CANONICAL_LIFECYCLE_PATH


class EvidenceValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceValidationError(message)


def require_library_authorities(
    _canonical_root: Path = _CANONICAL_ROOT,
    _canonical_contract: Path = _CANONICAL_CONTRACT_PATH,
    _canonical_lifecycle: Path = _CANONICAL_LIFECYCLE_PATH,
) -> None:
    if ROOT != _canonical_root:
        raise EvidenceValidationError("migration operation validation repository authority substitution rejected")
    for current, canonical, label in (
        (CONTRACT_PATH, _canonical_contract, "contract"),
        (LIFECYCLE_PATH, _canonical_lifecycle, "lifecycle"),
    ):
        if current != canonical:
            raise EvidenceValidationError(f"migration operation validation {label} authority substitution rejected")
        if current.is_symlink():
            raise EvidenceValidationError(f"migration operation validation {label} authority must be symlink-free")
        try:
            resolved = current.resolve(strict=True)
            canonical_resolved = canonical.resolve(strict=True)
        except FileNotFoundError as exc:
            raise EvidenceValidationError(f"migration operation validation canonical {label} authority missing") from exc
        if resolved != canonical_resolved:
            raise EvidenceValidationError(f"migration operation validation {label} authority drift")


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    label = display_path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceValidationError(f"missing file: {label}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceValidationError(f"invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {label}")
    return value


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be a UTC timestamp ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceValidationError(f"{field} is not a valid timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")
    return parsed


def bounded_risks(value: Any) -> list[str]:
    require(isinstance(value, list), "openRisks must be a list")
    require(len(value) <= 20, "openRisks exceeds 20 entries")
    risks: list[str] = []
    for index, item in enumerate(value):
        require(isinstance(item, str) and item.strip(),
                f"openRisks[{index}] must be a non-empty string")
        require(len(item) <= 240, f"openRisks[{index}] exceeds 240 characters")
        require("\n" not in item and "\r" not in item,
                f"openRisks[{index}] must be single-line")
        risks.append(item)
    require(len(risks) == len(set(risks)), "openRisks contains duplicates")
    return risks


def validate_privacy(record: dict[str, Any]) -> None:
    serialized = json.dumps(record, ensure_ascii=False).lower()
    forbidden = (
        "postgres://", "postgresql://", "jdbc:", "password=", "passwd=",
        "secret=", "token=", "authorization:", "bearer ", "access_key",
        "secret_key", "private_key", "database_url", "dsn=", "hostname=",
        "account_id", "apple_subject", "owner_account", "user content",
        "select ", "insert ", "update ", "delete ", "alter table",
        "create table", "drop table", "sqlparams", "sql_params",
    )
    for marker in forbidden:
        require(marker not in serialized,
                f"migration evidence contains forbidden value: {marker}")
    for value in record.get("openRisks", []):
        require("@" not in value and "://" not in value,
                "openRisks cannot contain email addresses or URLs")


def validate_record(
    record: dict[str, Any],
    *,
    now: dt.datetime | None = None,
    _canonical_guard=require_library_authorities,
) -> None:
    if require_library_authorities is not _canonical_guard:
        raise EvidenceValidationError("migration operation validation authority guard substitution rejected")
    _canonical_guard()
    contract = load_json(_CANONICAL_CONTRACT_PATH)
    lifecycle = load_json(_CANONICAL_LIFECYCLE_PATH)
    required_fields = set(contract["requiredFields"])
    optional_fields = {"productionConfirmation"}
    require(set(record) >= required_fields,
            f"record missing required fields: {sorted(required_fields - set(record))}")
    require(set(record) <= required_fields | optional_fields,
            f"record contains undeclared fields: {sorted(set(record) - required_fields - optional_fields)}")
    require(record.get("schemaVersion") == contract["recordSchemaVersion"],
            "record schemaVersion drift")

    identifier = contract["identifierPolicy"]
    for field, pattern_field in (
        ("migrationRunId", "migrationRunIdPattern"),
        ("operator", "operatorPattern"),
        ("reviewer", "reviewerPattern"),
        ("databaseIdentityDigest", "databaseIdentityDigestPattern"),
        ("sourceCommitSha", "sourceCommitShaPattern"),
        ("recoveryPointReference", "recoveryPointReferencePattern"),
    ):
        value = record.get(field)
        require(isinstance(value, str) and
                re.fullmatch(identifier[pattern_field], value) is not None,
                f"{field} violates identifier policy")
    require(record["operator"] != record["reviewer"],
            "operator and reviewer must differ")

    enums = contract["enums"]
    require(record.get("environment") in enums["environment"],
            "environment enum drift")
    for field in ("preflightResult", "applyResult", "verificationResult"):
        require(record.get(field) in enums["stepResult"],
                f"{field} enum drift")
    require(record.get("recoveryDecision") in enums["recoveryDecision"],
            "recoveryDecision enum drift")
    require(record.get("containsSecrets") is False,
            "containsSecrets must be false")
    require(record.get("productionEvidence") is False,
            "operation record cannot claim production readiness evidence")

    canonical = lifecycle.get("migrationSequence")
    require(isinstance(canonical, list) and canonical,
            "canonical migration sequence missing")
    for field in ("migrationSequenceBefore", "migrationSequenceAfter"):
        sequence = record.get(field)
        require(isinstance(sequence, list), f"{field} must be a list")
        require(all(isinstance(item, str) and item for item in sequence),
                f"{field} contains invalid filenames")
        require(len(sequence) == len(set(sequence)), f"{field} contains duplicates")
        require(sequence == canonical[:len(sequence)],
                f"{field} must be a canonical migration prefix")
    require(len(record["migrationSequenceAfter"]) >=
            len(record["migrationSequenceBefore"]),
            "migrationSequenceAfter cannot be shorter than before")

    started = parse_utc(record.get("startedAt"), "startedAt")
    completed = parse_utc(record.get("completedAt"), "completedAt")
    require(completed >= started, "completedAt cannot precede startedAt")
    require(completed - started <= dt.timedelta(hours=24),
            "migration evidence duration exceeds 24 hours")
    reference_now = now or dt.datetime.now(dt.timezone.utc)
    require(started <= reference_now + dt.timedelta(minutes=10) and
            completed <= reference_now + dt.timedelta(minutes=10),
            "migration evidence timestamp exceeds allowed future skew")

    risks = bounded_risks(record.get("openRisks"))
    preflight = record["preflightResult"]
    apply = record["applyResult"]
    verification = record["verificationResult"]
    decision = record["recoveryDecision"]
    if preflight == "FAIL":
        require(apply == "NOT_RUN",
                "preflight FAIL requires applyResult NOT_RUN")
    if apply == "FAIL":
        require(verification != "PASS",
                "apply FAIL forbids verification PASS")
    if verification == "PASS":
        require(apply == "PASS", "verification PASS requires apply PASS")
    if decision == "NO_RECOVERY_NEEDED":
        require(preflight == apply == verification == "PASS",
                "NO_RECOVERY_NEEDED requires all steps PASS")
    incomplete = any(value != "PASS" for value in (preflight, apply, verification))
    if incomplete:
        require(risks, "failed or incomplete migration run requires openRisks")

    if record["environment"] == "PRODUCTION":
        require(record.get("productionConfirmation") ==
                contract["resultPolicy"]["productionRecordRequiresConfirmationPhrase"],
                "production record confirmation phrase missing")
    else:
        require("productionConfirmation" not in record,
                "non-production record cannot include production confirmation")

    validate_privacy(record)


def expected_filename(record: dict[str, Any]) -> str:
    return f"{record['migrationRunId']}.json"
