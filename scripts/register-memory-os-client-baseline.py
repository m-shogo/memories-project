#!/usr/bin/env python3
"""Register one reviewed immutable client artifact baseline.

The record and artifact must both live outside the repository. The writer
recomputes exact artifact identity, verifies review/evidence metadata and then
performs one append-only atomic registry update. It cannot create approvals,
client/server support or production readiness.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/client-baseline-registry.v1.json"
LOCK = ROOT / "contracts/operations/.client-baseline-registry.lock"
CONFIRMATION = "REGISTER REVIEWED CLIENT BASELINE"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BASELINE_ID = re.compile(r"^clb_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
APPROVER = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$")
BUILD = re.compile(r"^[0-9A-Za-z._-]{1,64}$")
CLIENT_CLASSES = {"IOS_APP", "PORTAL"}
ARTIFACT_KINDS = {"IOS_IPA", "IOS_XCARCHIVE_EXPORT", "PORTAL_BUNDLE"}
REQUIRED_ROLES = {"CLIENT_OWNER", "SECURITY_REVIEWER", "COMPATIBILITY_REVIEWER"}


class Failure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Failure(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value), f"{field} contains invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def outside_repo(path: Path, field: str) -> None:
    try:
        path.relative_to(ROOT)
    except ValueError:
        return
    raise Failure(f"{field} must be outside repository")


def utc_timestamp(value: Any, field: str) -> None:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be RFC3339 UTC")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise Failure(f"{field} invalid timestamp") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")


def validate_source_commit_lineage(commit_sha: str) -> None:
    head = git("rev-parse", "HEAD")
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_sha, head],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0,
            f"source commit is not an ancestor of current HEAD: {commit_sha}")


def validate_record(record: dict[str, Any], required_fields: set[str], artifact: Path) -> None:
    require(set(record) >= required_fields, f"record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-client-baseline-record.v1", "record schema drift")
    require(isinstance(record.get("clientBaselineId"), str) and BASELINE_ID.fullmatch(record["clientBaselineId"]) is not None, "clientBaselineId invalid")
    require(record.get("clientClass") in CLIENT_CLASSES, "clientClass invalid")
    require(isinstance(record.get("marketingVersion"), str) and VERSION.fullmatch(record["marketingVersion"]) is not None, "marketingVersion invalid")
    require(isinstance(record.get("buildNumber"), str) and BUILD.fullmatch(record["buildNumber"]) is not None, "buildNumber invalid")
    require(isinstance(record.get("sourceCommitSha"), str) and SHA40.fullmatch(record["sourceCommitSha"]) is not None, "sourceCommitSha invalid")
    validate_source_commit_lineage(record["sourceCommitSha"])
    require(record.get("artifactKind") in ARTIFACT_KINDS, "artifactKind invalid")
    if record["clientClass"] == "IOS_APP":
        require(record["artifactKind"] in {"IOS_IPA", "IOS_XCARCHIVE_EXPORT"}, "iOS baseline requires iOS artifact kind")
    if record["clientClass"] == "PORTAL":
        require(record["artifactKind"] == "PORTAL_BUNDLE", "Portal baseline requires portal artifact kind")
    utc_timestamp(record.get("approvedAt"), "approvedAt")
    require(record.get("approvalClass") == "REVIEWED_CLIENT_BASELINE", "approvalClass invalid")
    require(record.get("apiMajor") == "v1", "apiMajor must remain v1")
    require(record.get("signedUploadContract") == "memory-os-signed-upload.v1", "signed upload contract drift")
    for field in ("artifactSha256", "apiContractSha256", "clientBehaviorContractSha256"):
        require(isinstance(record.get(field), str) and SHA256.fullmatch(record[field]) is not None, f"{field} must be SHA-256")
    require(isinstance(record.get("artifactByteLength"), int) and record["artifactByteLength"] > 0, "artifactByteLength invalid")
    require(record.get("evidenceComplete") is True and record.get("approvedForPairing") is True, "baseline requires complete pairing approval")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, "client baseline cannot be production evidence/readiness")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3, "exactly three approvers required")
    roles: set[str] = set()
    identities: set[str] = set()
    for item in approvers:
        require(isinstance(item, dict), "approver entry invalid")
        role = item.get("role")
        identity = item.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles, f"approval role invalid/duplicate: {role}")
        require(isinstance(identity, str) and APPROVER.fullmatch(identity) is not None, "approverRef invalid")
        require(identity not in identities, "duplicate/self approval detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, "required approval roles incomplete")

    for field in ("buildProvenanceEvidenceRefs", "securityEvidenceRefs", "compatibilityEvidenceRefs", "artifactRetentionEvidenceRefs"):
        for ref in strings(record.get(field), field):
            relative = Path(ref)
            require(not relative.is_absolute() and ".." not in relative.parts, f"unsafe evidence ref: {ref}")
            require((ROOT / relative).is_file(), f"evidence ref missing: {ref}")

    hasher = hashlib.sha256()
    size = 0
    with artifact.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            hasher.update(chunk)
    require(size == record["artifactByteLength"], "artifact byte length mismatch")
    require(hasher.hexdigest() == record["artifactSha256"], "artifact SHA-256 mismatch")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "authorization: bearer", "password=", "minioadmin",
        "secretaccesskey", "apple developer", "account_id", "session_id", "job_id", "preview_id", "object_key", "@",
    ):
        require(forbidden not in serialized, f"record contains forbidden content: {forbidden}")


def acquire_lock() -> int:
    try:
        return os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Failure("client baseline registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    fd, name = tempfile.mkstemp(prefix=".client-baseline-registry.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, REGISTRY)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    require(args.confirm == CONFIRMATION, f"confirmation must equal: {CONFIRMATION}")
    record_path = Path(args.record).resolve()
    artifact_path = Path(args.artifact).resolve()
    outside_repo(record_path, "record")
    outside_repo(artifact_path, "artifact")
    require(artifact_path.is_file(), "artifact file missing")
    require(git("status", "--porcelain") == "", "working tree must be clean before client baseline registration")

    contract = load(CONTRACT)
    required = set(strings(contract.get("requiredRecordFields"), "requiredRecordFields", 23))
    record = load(record_path)
    validate_record(record, required, artifact_path)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, (record["clientBaselineId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        clients = registry.get("clients")
        require(isinstance(clients, list) and all(isinstance(item, dict) for item in clients), "client registry invalid")
        require(all(item.get("clientBaselineId") != record["clientBaselineId"] for item in clients), "clientBaselineId already registered")
        require(all(item.get("artifactSha256") != record["artifactSha256"] for item in clients), "artifact digest already registered")
        clients.append(record)
        registry["approvedClientBaselineCount"] = len(clients)
        latest = registry.get("latestApprovedClientByClass")
        require(isinstance(latest, dict), "latestApprovedClientByClass invalid")
        latest[record["clientClass"]] = record["clientBaselineId"]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered reviewed client baseline: {record['clientBaselineId']}")
    print("This baseline is eligible for future skew-pair review only; production readiness remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Failure as exc:
        print(f"CLIENT BASELINE REGISTRATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
