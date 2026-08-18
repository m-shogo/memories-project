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
VALIDATOR = ROOT / "scripts/validate-memory-os-client-baseline-registry.py"
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
EVIDENCE_FIELDS = (
    "buildProvenanceEvidenceRefs",
    "securityEvidenceRefs",
    "compatibilityEvidenceRefs",
    "artifactRetentionEvidenceRefs",
)
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "approvedClientBaselineCount",
    "latestApprovedClientByClass",
    "clients",
    "limitations",
}
FORBIDDEN_RECORD_CONTENT = (
    "postgres://", "postgresql://", "authorization: bearer", "password=", "minioadmin",
    "secretaccesskey", "apple developer", "account_id", "session_id", "job_id", "preview_id", "object_key", "@",
)


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


def validate_contract_authority() -> dict[str, Any]:
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-client-baseline-registry-contract.v1", "client contract schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "client registryPath authority drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "client append lock authority drift")
    require(contract.get("writer") == str(Path(__file__).resolve().relative_to(ROOT)), "client writer authority drift")
    require(contract.get("validator") == str(VALIDATOR.relative_to(ROOT)), "client validator authority drift")
    require(contract.get("recordSchemaVersion") == "memory-os-client-baseline-record.v1", "client record schema authority drift")
    require(contract.get("appendOnly") is True and contract.get("productionDecision") == "NO_GO", "client production boundary drift")
    require(set(contract.get("allowedClientClasses", [])) == CLIENT_CLASSES, "client class authority drift")
    policy = contract.get("approvalPolicy")
    require(isinstance(policy, dict), "client approval policy missing")
    require(policy.get("approvalClass") == "REVIEWED_CLIENT_BASELINE", "client approval class drift")
    require(policy.get("minimumDistinctApprovers") == 3, "client approver minimum drift")
    require(set(policy.get("requiredRoles", [])) == REQUIRED_ROLES, "client approval roles drift")
    for key in (
        "selfApprovalForbidden", "sourceCommitIsInsufficient", "ciPassIsInsufficient",
        "marketingVersionIsInsufficient", "artifactDigestWithoutBytesIsInsufficient",
        "productionTrafficForbiddenForRegistration",
    ):
        require(policy.get(key) is True, f"client approval policy weakened: {key}")
    guards = strings(contract.get("registrationGuards"), "registrationGuards", 12)
    require(any("ancestor of current HEAD" in guard for guard in guards), "client source lineage guard missing")
    require(any("sourceCommitSha" in guard and "current bytes" in guard for guard in guards), "client source-bound evidence guard missing")
    require(any("historical registered evidence" in guard for guard in guards), "client historical evidence guard missing")
    require(any("canonical exclusive append lock" in guard for guard in guards), "client canonical append lock guard missing")
    return contract


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


def validate_evidence_ref_at_source(ref: str, source_commit_sha: str, field: str) -> None:
    relative = Path(ref)
    require(not relative.is_absolute() and ".." not in relative.parts,
            f"unsafe evidence ref: {ref}")
    current = ROOT / relative
    require(current.is_file(), f"evidence ref missing: {ref}")
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"evidence ref must be symlink-free: {ref}")
    try:
        current.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Failure(f"evidence ref escapes repository: {ref}") from exc
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", ref],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    require(tracked.returncode == 0, f"evidence ref must be tracked: {ref}")
    source = subprocess.run(
        ["git", "show", f"{source_commit_sha}:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    require(source.returncode == 0,
            f"{field} evidence did not exist at source commit: {ref}")
    require(source.stdout == current.read_bytes(),
            f"{field} evidence changed after source commit: {ref}")


def validate_record_evidence(record: dict[str, Any], prefix: str = "record") -> None:
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None,
            f"{prefix}.sourceCommitSha invalid")
    for field in EVIDENCE_FIELDS:
        for ref in strings(record.get(field), f"{prefix}.{field}"):
            validate_evidence_ref_at_source(ref, source, f"{prefix}.{field}")


def validate_historical_record(record: dict[str, Any], required_fields: set[str], prefix: str = "record") -> None:
    require(set(record) >= required_fields, f"{prefix} missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-client-baseline-record.v1", f"{prefix} schema drift")
    require(isinstance(record.get("clientBaselineId"), str) and BASELINE_ID.fullmatch(record["clientBaselineId"]) is not None,
            f"{prefix}.clientBaselineId invalid")
    client_class = record.get("clientClass")
    require(client_class in CLIENT_CLASSES, f"{prefix}.clientClass invalid")
    require(isinstance(record.get("marketingVersion"), str) and VERSION.fullmatch(record["marketingVersion"]) is not None,
            f"{prefix}.marketingVersion invalid")
    require(isinstance(record.get("buildNumber"), str) and BUILD.fullmatch(record["buildNumber"]) is not None,
            f"{prefix}.buildNumber invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None, f"{prefix}.sourceCommitSha invalid")
    validate_source_commit_lineage(source)
    artifact_kind = record.get("artifactKind")
    require(artifact_kind in ARTIFACT_KINDS, f"{prefix}.artifactKind invalid")
    if client_class == "IOS_APP":
        require(artifact_kind in {"IOS_IPA", "IOS_XCARCHIVE_EXPORT"}, f"{prefix} iOS artifact kind mismatch")
    if client_class == "PORTAL":
        require(artifact_kind == "PORTAL_BUNDLE", f"{prefix} Portal artifact kind mismatch")
    utc_timestamp(record.get("approvedAt"), f"{prefix}.approvedAt")
    require(record.get("approvalClass") == "REVIEWED_CLIENT_BASELINE", f"{prefix}.approvalClass invalid")
    require(record.get("apiMajor") == "v1", f"{prefix}.apiMajor drift")
    require(record.get("signedUploadContract") == "memory-os-signed-upload.v1", f"{prefix}.signedUploadContract drift")
    for field in ("artifactSha256", "apiContractSha256", "clientBehaviorContractSha256"):
        require(isinstance(record.get(field), str) and SHA256.fullmatch(record[field]) is not None,
                f"{prefix}.{field} must be SHA-256")
    require(isinstance(record.get("artifactByteLength"), int) and not isinstance(record.get("artifactByteLength"), bool) and
            record["artifactByteLength"] > 0, f"{prefix}.artifactByteLength invalid")
    require(record.get("evidenceComplete") is True and record.get("approvedForPairing") is True,
            f"{prefix} requires complete pairing approval")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False,
            f"{prefix} cannot be production evidence/readiness")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3,
            f"{prefix} requires exactly three approvers")
    roles: set[str] = set()
    identities: set[str] = set()
    for item in approvers:
        require(isinstance(item, dict), f"{prefix} approver entry invalid")
        role = item.get("role")
        identity = item.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles, f"{prefix} approval role invalid/duplicate: {role}")
        require(isinstance(identity, str) and APPROVER.fullmatch(identity) is not None, f"{prefix} approverRef invalid")
        require(identity not in identities, f"{prefix} duplicate/self approval detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, f"{prefix} required approval roles incomplete")

    validate_record_evidence(record, prefix)
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in FORBIDDEN_RECORD_CONTENT:
        require(forbidden not in serialized, f"{prefix} contains forbidden content: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any]) -> None:
    contract = validate_contract_authority()
    required_fields = set(strings(contract.get("requiredRecordFields"), "requiredRecordFields", 23))
    require(set(registry) == REGISTRY_FIELDS, "client registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-client-baseline-registry.v1",
            "client registry schema drift")
    require(registry.get("registryClass") == "APPROVED_CLIENT_BASELINES",
            "client registry class drift")
    require(registry.get("appendOnly") is True, "client registry must remain append-only")
    require(registry.get("productionEvidence") is False,
            "client registry cannot claim production evidence")
    clients = registry.get("clients")
    require(isinstance(clients, list) and all(isinstance(item, dict) for item in clients),
            "client registry contains invalid clients")
    count = registry.get("approvedClientBaselineCount")
    require(isinstance(count, int) and not isinstance(count, bool),
            "approvedClientBaselineCount must be an integer")
    require(count == len(clients), "approvedClientBaselineCount drift")
    latest = registry.get("latestApprovedClientByClass")
    require(isinstance(latest, dict) and set(latest) == CLIENT_CLASSES,
            "latestApprovedClientByClass drift")
    ids: set[str] = set()
    digests: set[str] = set()
    expected_latest: dict[str, str | None] = {"IOS_APP": None, "PORTAL": None}
    for index, item in enumerate(clients):
        validate_historical_record(item, required_fields, f"clients[{index}]")
        baseline_id = item.get("clientBaselineId")
        client_class = item.get("clientClass")
        artifact_digest = item.get("artifactSha256")
        require(baseline_id not in ids, f"duplicate registered clientBaselineId: {baseline_id}")
        require(artifact_digest not in digests, f"duplicate registered artifactSha256: {artifact_digest}")
        ids.add(baseline_id)
        digests.add(artifact_digest)
        expected_latest[client_class] = baseline_id
    require(latest == expected_latest,
            f"latestApprovedClientByClass drift: expected {expected_latest}, got {latest}")


def validate_record(record: dict[str, Any], required_fields: set[str], artifact: Path) -> None:
    validate_historical_record(record, required_fields)
    hasher = hashlib.sha256()
    size = 0
    with artifact.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            hasher.update(chunk)
    require(size == record["artifactByteLength"], "artifact byte length mismatch")
    require(hasher.hexdigest() == record["artifactSha256"], "artifact SHA-256 mismatch")


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

    contract = validate_contract_authority()
    required = set(strings(contract.get("requiredRecordFields"), "requiredRecordFields", 23))
    record = load(record_path)
    validate_record(record, required, artifact_path)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, (record["clientBaselineId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        clients = registry["clients"]
        require(all(item.get("clientBaselineId") != record["clientBaselineId"] for item in clients), "clientBaselineId already registered")
        require(all(item.get("artifactSha256") != record["artifactSha256"] for item in clients), "artifact digest already registered")
        clients.append(record)
        registry["approvedClientBaselineCount"] = len(clients)
        latest = registry["latestApprovedClientByClass"]
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
