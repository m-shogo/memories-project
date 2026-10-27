#!/usr/bin/env python3
"""Append one explicitly approved recovery-objectives record."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT
CANONICAL_CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
CONTRACT = CANONICAL_CONTRACT
REGISTRY = CANONICAL_REGISTRY
CANONICAL_LOCK = ROOT / "contracts/operations/.recovery-objectives.lock"
LOCK = CANONICAL_LOCK
CANONICAL_APPROVAL_DIR = ROOT / "docs/evidence/recovery-objectives/approvals"
APPROVAL_DIR = CANONICAL_APPROVAL_DIR
OBJECTIVE_ID = re.compile(r"^ro_[a-z0-9][a-z0-9_-]{7,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
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


MAX_JSON_BYTES = 1024 * 1024


def load(path: Path) -> dict[str, Any]:
    """Read bounded, unambiguous objective JSON without exposing private paths."""
    require(isinstance(path, Path) and path.is_absolute(),
            "recovery objective writer JSON path invalid")

    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "recovery objective writer JSON duplicate key refused")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise Fail("recovery objective writer JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "recovery objective writer JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128,
                "recovery objective writer JSON integer too large")
        return int(value)

    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "recovery objective writer JSON platform unsafe")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode),
                "recovery objective writer JSON unreadable or invalid")
        require(metadata.st_size <= MAX_JSON_BYTES,
                "recovery objective writer JSON size limit exceeded")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES,
                "recovery objective writer JSON size limit exceeded")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys,
                           parse_constant=reject_constant, parse_float=finite_float,
                           parse_int=bounded_int)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError,
            OverflowError, RecursionError):
        raise Fail("recovery objective writer JSON unreadable or invalid") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                raise Fail("recovery objective writer JSON descriptor cleanup failed") from None
    require(isinstance(value, dict), "recovery objective writer JSON root must be object")
    return value


def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to its canonical repository file")
    return path


def canonical_repo_directory(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_dir(), f"{field} must resolve to its canonical repository directory")
    return path


def require_canonical_runtime_authorities() -> None:
    if ROOT != CANONICAL_ROOT:
        return
    require(LOCK == CANONICAL_LOCK, "recovery objective lock authority drift")
    require(LOCK.parent == CANONICAL_REGISTRY.parent, "recovery objective lock must share registry authority directory")
    if CONTRACT == CANONICAL_CONTRACT:
        canonical_repo_file(CONTRACT, "recovery objective contract")
        contract = load(CONTRACT)
        require(
            contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "recovery objective transactional append authority drift",
        )
    if REGISTRY == CANONICAL_REGISTRY:
        canonical_repo_file(REGISTRY, "recovery objective registry")
    if APPROVAL_DIR == CANONICAL_APPROVAL_DIR:
        canonical_repo_directory(APPROVAL_DIR, "recovery objective approval authority directory")


def require_actual_cli_authorities() -> None:
    """Pin the real approval append entrypoint while preserving isolated helper fixtures."""
    require(ROOT == CANONICAL_ROOT, "recovery objective writer root authority must remain canonical")
    require(CONTRACT == CANONICAL_CONTRACT, "recovery objective contract must remain canonical for CLI registration")
    require(REGISTRY == CANONICAL_REGISTRY, "recovery objective registry must remain canonical for CLI registration")
    require(APPROVAL_DIR == CANONICAL_APPROVAL_DIR, "recovery objective approval directory must remain canonical for CLI registration")
    require(LOCK == CANONICAL_LOCK, "recovery objective lock authority must remain canonical for CLI registration")
    canonical_repo_file(CONTRACT, "recovery objective contract")
    canonical_repo_file(REGISTRY, "recovery objective registry")
    canonical_repo_directory(APPROVAL_DIR, "recovery objective approval authority directory")
    try:
        relative_parent = LOCK.parent.relative_to(ROOT)
        resolved_parent = LOCK.parent.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail("recovery objective lock parent missing or escapes repository") from None
    require(
        relative_parent == resolved_parent and LOCK.parent.is_dir(),
        "recovery objective lock parent must resolve to the canonical repository directory",
    )


def parse_utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]+)?Z", value) is not None,
            f"{field} must be UTC RFC3339 date-time")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Fail(f"{field} must be UTC RFC3339 date-time") from None
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field} must be UTC")
    return parsed


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.as_posix() == value,
        f"{field} must be a canonical repository-relative path",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} evidence missing or escapes repository") from None
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def approval_ref(value: Any) -> str:
    require_canonical_runtime_authorities()
    ref = repo_ref(value, "approvalEvidenceRefs")
    try:
        path = (ROOT / ref).resolve(strict=True)
        approval_root = APPROVAL_DIR.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        raise Fail("approval authority directory or evidence cannot be resolved") from None
    require(path.is_relative_to(approval_root), "approvalEvidenceRefs must use the dedicated recovery-objective approval authority directory")
    return ref


def approval_sha256(ref: str) -> str:
    """Hash only bounded canonical approval files, never aliases or private paths."""
    require(isinstance(ref, str) and bool(ref),
            "approval evidence digest reference invalid")
    relative = Path(ref)
    require(not relative.is_absolute() and ".." not in relative.parts
            and relative.as_posix() == ref,
            "approval evidence digest reference invalid")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
        approval_root = APPROVAL_DIR.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail("approval evidence digest path unsafe") from None
    require(relative == resolved and path.is_file() and not path.is_symlink()
            and path.is_relative_to(approval_root),
            "approval evidence digest path unsafe")
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "approval evidence digest platform unsafe")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode), "approval evidence digest path unsafe")
        require(metadata.st_size <= MAX_JSON_BYTES,
                "approval evidence digest size limit exceeded")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            payload = source.read(MAX_JSON_BYTES + 1)
    except (OSError, ValueError, TypeError):
        raise Fail("approval evidence digest unreadable") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                raise Fail("approval evidence digest descriptor cleanup failed") from None
    require(len(payload) <= MAX_JSON_BYTES,
            "approval evidence digest size limit exceeded")
    return hashlib.sha256(payload).hexdigest()


def approval_document(ref: str, record: dict[str, Any], approved_at: datetime) -> dict[str, Any]:
    document = load(ROOT / ref)
    require(set(document) == APPROVAL_FIELDS, "approval evidence field drift")
    require(document.get("schemaVersion") == APPROVAL_SCHEMA, "approval evidence schemaVersion drift")
    require(document.get("decision") == "APPROVED", "approval evidence decision must be APPROVED")
    role = document.get("reviewRole")
    require(isinstance(role, str) and role in APPROVAL_ROLES, "approval evidence reviewRole invalid")
    reviewer = document.get("reviewerPseudonym")
    require(isinstance(reviewer, str), "approval evidence reviewerPseudonym required")
    canonical_reviewer = reviewer.strip()
    require(1 <= len(canonical_reviewer) <= 128 and reviewer == canonical_reviewer, "approval evidence reviewerPseudonym must be canonical non-empty text")
    reviewed_at = parse_utc_timestamp(document.get("reviewedAt"), "approval evidence reviewedAt")
    require(reviewed_at <= approved_at, "approval evidence cannot post-date objective approval")
    for field in ("objectiveId", "scope", "rpoSeconds", "rtoSeconds", "maximumObjectDatabaseSkewSeconds"):
        require(type(document.get(field)) is type(record.get(field))
                and document.get(field) == record.get(field),
                f"approval evidence {field} binding mismatch")
    for field in ("productionTraffic", "productionCredentials", "automaticPromotion"):
        require(document.get(field) is False, f"approval evidence {field} must remain false")
    return document


def evidence_refs(value: Any, record: dict[str, Any], approved_at: datetime) -> list[str]:
    require(isinstance(value, list) and len(value) == 2, "exactly two typed approvalEvidenceRefs required")
    require(all(isinstance(ref, str) and ref for ref in value), "approvalEvidenceRefs must be non-empty strings")
    require(len(value) == len(set(value)), "approvalEvidenceRefs must be distinct")
    refs = [approval_ref(ref) for ref in value]
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
    require_canonical_runtime_authorities()
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, "record field set drift")
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


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject corrupt append-only objective authority before adding human-reviewed policy."""
    require(registry.get("schemaVersion") == "memory-os-recovery-objectives-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "objectives registry must remain append-only")
    require(registry.get("productionEvidence") is False, "objectives registry productionEvidence must remain false")
    require(registry.get("productionReady") is False, "objectives registry productionReady must remain false")
    rows = registry.get("records")
    count = registry.get("approvedObjectiveCount")
    digest_map = registry.get("approvalEvidenceDigestsByObjectiveId")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "objectives records invalid")
    require(isinstance(count, int) and not isinstance(count, bool), "approvedObjectiveCount must be a non-boolean integer")
    require(count == len(rows), "approvedObjectiveCount drift")
    require(isinstance(digest_map, dict), "approval evidence digest map invalid")
    ids: set[str] = set()
    previous: str | None = None
    for row in rows:
        validate_record(row)
        objective_id = row.get("objectiveId")
        require(isinstance(objective_id, str) and objective_id not in ids, f"duplicate objectiveId: {objective_id}")
        ids.add(objective_id)
        require(row.get("supersedesObjectiveId") == previous, "recovery objective supersession chain drift")
        refs = row.get("approvalEvidenceRefs")
        digests = digest_map.get(objective_id)
        require(isinstance(refs, list) and isinstance(digests, dict), f"approval evidence digest authority missing: {objective_id}")
        require(set(digests) == set(refs), f"approval evidence digest refs drift: {objective_id}")
        for ref in refs:
            digest = digests.get(ref)
            require(isinstance(digest, str) and SHA256.fullmatch(digest), f"approval evidence digest invalid: {objective_id}")
            require(digest == approval_sha256(ref), f"approval evidence content drift: {objective_id}: {ref}")
        previous = objective_id
    require(set(digest_map) == ids, "approval evidence digest objective set drift")
    require(registry.get("currentObjectiveId") == previous, "currentObjectiveId must equal latest append-only record")
    limitations = registry.get("limitations")
    require(
        isinstance(limitations, list)
        and limitations
        and all(isinstance(item, str) and item.strip() for item in limitations)
        and len(limitations) == len(set(limitations)),
        "objectives registry limitations invalid",
    )
    return rows


def atomic_write(value: dict[str, Any], mode: int) -> None:
    descriptor: int | None = None
    temp_name: str | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".recovery-objectives.", suffix=".tmp", dir=REGISTRY.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            os.fchmod(handle.fileno(), mode)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
        temp_name = None
    except (OSError, ValueError, TypeError, UnicodeError):
        raise Fail("recovery objective registry atomic write failed") from None
    finally:
        cleanup_failed = False
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise Fail("recovery objective registry temporary cleanup failed") from None


def atomic_restore(payload: bytes, mode: int) -> None:
    descriptor: int | None = None
    temp_name: str | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".recovery-objectives-rollback.", suffix=".tmp", dir=REGISTRY.parent)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            os.fchmod(handle.fileno(), mode)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
        temp_name = None
    except (OSError, ValueError, TypeError):
        raise Fail("recovery objective registry atomic restore failed") from None
    finally:
        cleanup_failed = False
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise Fail("recovery objective registry temporary cleanup failed") from None


def snapshot_registry_for_append() -> tuple[bytes, int]:
    """Pin a bounded regular registry snapshot before any candidate write."""
    require(isinstance(REGISTRY, Path) and REGISTRY.is_absolute(),
            "recovery objective registry snapshot path invalid")
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "recovery objective registry snapshot platform unsafe")
    descriptor: int | None = None
    try:
        descriptor = os.open(REGISTRY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode),
                "recovery objective registry snapshot unsafe file type")
        require(metadata.st_size <= MAX_JSON_BYTES,
                "recovery objective registry snapshot size limit exceeded")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            original = source.read(MAX_JSON_BYTES + 1)
        require(len(original) <= MAX_JSON_BYTES,
                "recovery objective registry snapshot size limit exceeded")
        return original, stat.S_IMODE(metadata.st_mode)
    except (OSError, ValueError, TypeError):
        raise Fail("recovery objective registry snapshot unreadable or unsafe") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                raise Fail("recovery objective registry snapshot cleanup failed") from None


def write_registry_transactionally(value: dict[str, Any]) -> None:
    original, original_mode = snapshot_registry_for_append()
    atomic_write(value, original_mode)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        try:
            atomic_restore(original, original_mode)
        except Exception:
            raise Fail("recovery objectives append failed; rollback incomplete") from None
        raise Fail("recovery objectives append failed; rollback completed") from None


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
    require_actual_cli_authorities()
    require_canonical_runtime_authorities()
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
        rows = validate_registry_for_append(registry)
        require(all(row.get("objectiveId") != record["objectiveId"] for row in rows), "objectiveId already registered")
        expected_supersedes = rows[-1].get("objectiveId") if rows else None
        require(record.get("supersedesObjectiveId") == expected_supersedes, "supersedesObjectiveId must reference current approved objectives")
        objective_id = record["objectiveId"]
        refs = record["approvalEvidenceRefs"]
        digest_map = registry["approvalEvidenceDigestsByObjectiveId"]
        require(objective_id not in digest_map, "objective approval digest authority already registered")
        digest_map[objective_id] = {ref: approval_sha256(ref) for ref in refs}
        rows.append(record)
        registry["approvedObjectiveCount"] = len(rows)
        registry["currentObjectiveId"] = objective_id
        registry["limitations"] = [
            "approved objectives are policy targets, not restore evidence",
            "objective values are supplied by reviewed human authority and are never chosen or defaulted by this writer",
            "the current objective requires distinct typed Recovery Owner and Operability approvals bound to the exact objectiveId and RPO/RTO/skew values",
            "production approval evidence is accepted only from the dedicated recovery-objective approval authority directory; arbitrary repository files are forbidden",
            "typed approval evidence bytes are SHA-256 bound into the append-only objective registry and later mutation is rejected",
            "measurement methods must be concrete non-placeholder descriptions and owner evidence must remain distinct from approval evidence",
            "measured recovery evidence must reference the exact current objectiveId",
            "objective approval does not establish production readiness"
        ]
        write_registry_transactionally(registry)
    finally:
        try:
            os.close(lock_fd)
        finally:
            try:
                LOCK.unlink()
            except FileNotFoundError:
                pass
    print(f"Registered recovery objectives: {record['objectiveId']}")
    print("Typed Recovery Owner/Operability approvals bound to objective: true")
    print("Approval evidence content SHA-256 bound: true")
    print("Arbitrary repository approval files accepted: false")
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
