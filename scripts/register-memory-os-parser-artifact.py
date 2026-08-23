#!/usr/bin/env python3
"""Register one reviewed parser artifact under an exclusive repository lock."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
CANONICAL_REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
CANONICAL_RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CANONICAL_RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
CANONICAL_LOCK_PATH = ROOT / "contracts/operations/.parser-artifact-registry.lock"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
REGISTRY_PATH = CANONICAL_REGISTRY_PATH
RELEASE_REGISTRY_PATH = CANONICAL_RELEASE_REGISTRY_PATH
RELEASE_WRITER_PATH = CANONICAL_RELEASE_WRITER_PATH
LOCK_PATH = CANONICAL_LOCK_PATH
CONFIRMATION = "REGISTER REVIEWED PARSER ARTIFACT"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_ID_RE = re.compile(r"^par_[a-z0-9][a-z0-9._-]{7,95}$")
ADAPTER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
APPROVER_RE = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
REQUIRED_ROLES = {"SECURITY_REVIEWER", "RUNTIME_REVIEWER", "RELEASE_OWNER"}
RETENTION_STATES = {"RETAINED", "RETENTION_PENDING", "RETIRED_BLOCKED_FROM_ROLLBACK"}
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "reviewedArtifactCount",
    "retainedRollbackArtifactCount",
    "replayProvenArtifactCount",
    "latestReviewedArtifactId",
    "evidenceDigestsByArtifactId",
    "artifacts",
    "limitations",
}
FORBIDDEN_RECORD_CONTENT = (
    "services/import-api/internal/parsersup/worker.go",
    "memory_os_parser_worker_mode",
    "go test",
    "postgres://",
    "postgresql://",
    "password=",
    "authorization: bearer",
    "minioadmin",
    "secretaccesskey",
    "account_id",
    "session_id",
    "job_id",
    "preview_id",
    "object_key",
    "apple_subject",
    "@",
)


class RegistrationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistrationFailure(message)


def require_actual_cli_authorities() -> None:
    for label, actual, canonical in (
        ("contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH),
        ("registry", REGISTRY_PATH, CANONICAL_REGISTRY_PATH),
        ("release registry", RELEASE_REGISTRY_PATH, CANONICAL_RELEASE_REGISTRY_PATH),
        ("release writer", RELEASE_WRITER_PATH, CANONICAL_RELEASE_WRITER_PATH),
    ):
        require(actual == canonical, f"parser artifact CLI {label} authority substitution rejected")
        require(not actual.is_symlink(), f"parser artifact CLI {label} authority must be symlink-free")
        require(actual.resolve(strict=True) == canonical.resolve(strict=True), f"parser artifact CLI {label} authority drift")
    require(LOCK_PATH == CANONICAL_LOCK_PATH, "parser artifact CLI lock authority substitution rejected")
    require(not LOCK_PATH.is_symlink(), "parser artifact CLI lock authority must be symlink-free")
    require(
        LOCK_PATH.parent.resolve(strict=True) == CANONICAL_LOCK_PATH.parent.resolve(strict=True),
        "parser artifact CLI lock parent authority drift",
    )


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrationFailure(f"invalid JSON: {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path}")
    return value


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(arguments)} failed without registration")
    return completed.stdout.strip()


def git_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(arguments)} failed without registration")
    return completed.stdout


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def parse_utc(value: Any) -> None:
    require(isinstance(value, str) and value.endswith("Z"),
            "registeredAt must be RFC3339 UTC ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RegistrationFailure("registeredAt must be valid RFC3339 UTC") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            "registeredAt must be UTC")


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    candidate = ROOT / path
    current = ROOT
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), f"{field} contains a symlink component: {value}")
    require(candidate.is_file(), f"{field} does not exist: {value}")
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RegistrationFailure(f"{field} escapes repository: {value}") from exc
    git("ls-files", "--error-unmatch", "--", value)
    require(candidate.read_bytes() == git_bytes("show", f"HEAD:{value}"),
            f"{field} must match committed HEAD bytes: {value}")
    return value


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def evidence_refs(record: dict[str, Any]) -> list[str]:
    refs = [
        record.get("buildProvenanceRef"),
        record.get("securityReviewRef"),
        record.get("retentionEvidenceRef"),
        *record.get("replayEvidenceRefs", []),
    ]
    retention = record.get("rollbackRetentionState")
    if isinstance(retention, dict) and retention.get("verificationEvidenceRef"):
        refs.append(retention["verificationEvidenceRef"])
    require(all(isinstance(ref, str) and ref for ref in refs),
            "parser artifact evidence refs are incomplete")
    require(len(refs) == len(set(refs)),
            "parser artifact evidence refs contain duplicates")
    return refs


def evidence_digests(record: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for ref in evidence_refs(record):
        safe_ref(ref, "artifact evidence ref")
        result[ref] = hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()
    return result


def load_release_writer() -> Any:
    require(RELEASE_WRITER_PATH.is_file(), "canonical release writer missing")
    spec = importlib.util.spec_from_file_location(
        "memory_os_release_baseline_writer_for_parser", RELEASE_WRITER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "cannot load canonical release writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.REGISTRY_PATH).resolve() == RELEASE_REGISTRY_PATH.resolve(),
            "canonical release registry authority drift")
    return module


def approved_release_ids() -> set[str]:
    release_writer = load_release_writer()
    release_registry = load(RELEASE_REGISTRY_PATH)
    release_contract = load(Path(release_writer.CONTRACT_PATH))
    try:
        release_writer.validate_registry_for_append(release_registry, release_contract)
    except Exception as exc:
        raise RegistrationFailure(f"approved release authority invalid: {exc}") from exc
    return {item["releaseId"] for item in release_registry["releases"]}


def validate_historical_record(
    record: dict[str, Any], required_fields: set[str], approved_release_ids_value: set[str]
) -> None:
    require(set(record) >= required_fields,
            f"record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-parser-artifact-record.v1",
            "record schemaVersion drift")
    require(isinstance(record.get("artifactId"), str) and
            ARTIFACT_ID_RE.fullmatch(record["artifactId"]) is not None,
            "artifactId format invalid")
    require(isinstance(record.get("adapterId"), str) and
            ADAPTER_RE.fullmatch(record["adapterId"]) is not None,
            "adapterId format invalid")
    require(isinstance(record.get("adapterVersion"), str) and
            VERSION_RE.fullmatch(record["adapterVersion"]) is not None,
            "adapterVersion format invalid")
    require(isinstance(record.get("artifactSha256"), str) and
            DIGEST_RE.fullmatch(record["artifactSha256"]) is not None,
            "artifact SHA-256 invalid")
    require(isinstance(record.get("artifactSizeBytes"), int) and
            not isinstance(record.get("artifactSizeBytes"), bool) and
            record["artifactSizeBytes"] > 0,
            "artifactSizeBytes invalid")
    require(record.get("reviewClass") == "REVIEWED_PARSER_ARTIFACT",
            "reviewClass must be REVIEWED_PARSER_ARTIFACT")
    parse_utc(record.get("registeredAt"))
    for field in ("artifactFormat", "targetOs", "targetArch", "protocolVersion"):
        require(isinstance(record.get(field), str) and record[field].strip(),
                f"{field} is required")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3,
            "exactly three artifact approvers are required")
    roles: set[str] = set()
    identities: set[str] = set()
    for approver in approvers:
        require(isinstance(approver, dict), "approver entry must be an object")
        role = approver.get("role")
        identity = approver.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles,
                f"approval role invalid or duplicated: {role}")
        require(isinstance(identity, str) and APPROVER_RE.fullmatch(identity) is not None,
                "approverRef must be an operational pseudonym")
        require(identity not in identities, "duplicate or self-approval detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, "required artifact approval roles incomplete")

    for field in ("buildProvenanceRef", "securityReviewRef", "retentionEvidenceRef"):
        safe_ref(record.get(field), field)
    for ref in strings(record.get("replayEvidenceRefs"), "replayEvidenceRefs", 1):
        safe_ref(ref, "replayEvidenceRefs")
    compatible = strings(record.get("compatibleReleaseIds"), "compatibleReleaseIds", 1)
    require(set(compatible) <= approved_release_ids_value,
            "compatibleReleaseIds contains an unapproved release")

    retention = record.get("rollbackRetentionState")
    require(isinstance(retention, dict) and retention.get("state") in RETENTION_STATES,
            "rollbackRetentionState invalid")
    if retention.get("state") == "RETAINED":
        require(retention.get("immutableLocationVerified") is True,
                "RETAINED artifact requires immutableLocationVerified=true")
        safe_ref(retention.get("verificationEvidenceRef"),
                 "rollbackRetentionState.verificationEvidenceRef")
    else:
        require(retention.get("immutableLocationVerified") is False,
                "non-retained artifact cannot claim immutable location verification")

    risks = record.get("openRisks")
    require(isinstance(risks, list), "openRisks must be a list")
    for risk in risks:
        require(isinstance(risk, dict) and risk.get("riskId") and
                risk.get("ownerRef") and risk.get("deadline") and risk.get("status"),
                "open risk entry is incomplete")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in FORBIDDEN_RECORD_CONTENT:
        require(forbidden not in serialized,
                f"record contains forbidden content: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any]) -> None:
    contract = load(CONTRACT_PATH)
    require(contract.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "parser artifact contract must require post-append revalidation and rollback")
    required_fields = set(strings(contract.get("requiredRecordFields"),
                                  "requiredRecordFields", 20))
    release_ids = approved_release_ids()
    require(set(registry) == REGISTRY_FIELDS, "parser artifact registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-parser-artifact-registry.v1",
            "parser artifact registry schema drift")
    require(registry.get("registryClass") == "REVIEWED_RETAINED_PARSER_ARTIFACTS",
            "parser artifact registry class drift")
    require(registry.get("appendOnly") is True,
            "parser artifact registry must remain append-only")
    require(registry.get("productionEvidence") is False,
            "parser artifact registry cannot claim production evidence")
    artifacts = registry.get("artifacts")
    require(isinstance(artifacts, list) and all(isinstance(item, dict) for item in artifacts),
            "parser artifact registry contains invalid artifacts")
    evidence_authority = registry.get("evidenceDigestsByArtifactId")
    require(isinstance(evidence_authority, dict),
            "parser artifact evidence digest authority missing")
    for field in ("reviewedArtifactCount", "retainedRollbackArtifactCount", "replayProvenArtifactCount"):
        value = registry.get(field)
        require(isinstance(value, int) and not isinstance(value, bool),
                f"{field} must be an integer")
    require(registry["reviewedArtifactCount"] == len(artifacts),
            "reviewedArtifactCount drift")
    retained = sum(
        1 for item in artifacts
        if item.get("rollbackRetentionState", {}).get("state") == "RETAINED"
    )
    replayed = sum(1 for item in artifacts if item.get("replayEvidenceRefs"))
    require(registry["retainedRollbackArtifactCount"] == retained,
            "retainedRollbackArtifactCount drift")
    require(registry["replayProvenArtifactCount"] == replayed,
            "replayProvenArtifactCount drift")
    ids: set[str] = set()
    digests: set[str] = set()
    adapter_versions: set[tuple[str, str]] = set()
    for item in artifacts:
        validate_historical_record(item, required_fields, release_ids)
        artifact_id = item.get("artifactId")
        digest = item.get("artifactSha256")
        adapter_id = item.get("adapterId")
        adapter_version = item.get("adapterVersion")
        pair = (adapter_id, adapter_version)
        require(artifact_id not in ids, f"duplicate registered artifactId: {artifact_id}")
        require(digest not in digests, f"duplicate registered artifact digest: {digest}")
        require(pair not in adapter_versions, f"duplicate registered adapter version: {pair}")
        ids.add(artifact_id)
        digests.add(digest)
        adapter_versions.add(pair)
        bound = evidence_authority.get(artifact_id)
        expected_refs = evidence_refs(item)
        require(isinstance(bound, dict) and set(bound) == set(expected_refs),
                f"artifact evidence digest refs drift: {artifact_id}")
        for ref in expected_refs:
            expected_digest = bound.get(ref)
            require(isinstance(expected_digest, str) and DIGEST_RE.fullmatch(expected_digest) is not None,
                    f"artifact evidence digest invalid: {artifact_id}:{ref}")
            safe_ref(ref, "historical artifact evidence ref")
            require(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest() == expected_digest,
                    f"artifact evidence bytes drift: {artifact_id}:{ref}")
    require(set(evidence_authority) == ids,
            "parser artifact evidence digest authority contains unknown or missing artifact IDs")
    expected_latest = artifacts[-1].get("artifactId") if artifacts else None
    require(registry.get("latestReviewedArtifactId") == expected_latest,
            "latestReviewedArtifactId drift")


def validate_record(record: dict[str, Any], required_fields: set[str],
                    artifact_path: Path, approved_release_ids_value: set[str]) -> None:
    validate_historical_record(record, required_fields, approved_release_ids_value)
    actual_digest, actual_size = sha256_file(artifact_path)
    require(record["artifactSha256"] == actual_digest,
            "artifact SHA-256 does not match exact bytes")
    require(record["artifactSizeBytes"] == actual_size,
            "artifactSizeBytes does not match exact bytes")


def acquire_lock() -> int:
    try:
        return os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RegistrationFailure("parser artifact registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".parser-artifact-registry.", suffix=".tmp",
        dir=REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def atomic_write_bytes(value: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".parser-artifact-registry.", suffix=".tmp",
        dir=REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def append_registry_transactionally(registry: dict[str, Any], original_bytes: bytes) -> None:
    atomic_write(registry)
    try:
        validate_registry_for_append(load(REGISTRY_PATH))
    except Exception:
        atomic_write_bytes(original_bytes)
        raise


def main() -> int:
    require_actual_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True,
                        help="JSON record outside the repository working tree")
    parser.add_argument("--artifact", required=True,
                        help="exact artifact bytes outside the repository working tree")
    parser.add_argument("--confirm", required=True)
    arguments = parser.parse_args()

    require(arguments.confirm == CONFIRMATION,
            f"confirmation must equal: {CONFIRMATION}")
    record_path = Path(arguments.record).resolve()
    artifact_path = Path(arguments.artifact).resolve()
    for path, label in ((record_path, "record"), (artifact_path, "artifact")):
        try:
            path.relative_to(ROOT)
        except ValueError:
            pass
        else:
            raise RegistrationFailure(f"input {label} must be outside the repository")
    require(artifact_path.is_file() and artifact_path.stat().st_size > 0,
            "artifact input must be a non-empty regular file")
    require(git("status", "--porcelain") == "",
            "working tree must be clean before artifact registration")

    contract = load(CONTRACT_PATH)
    require(contract.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "parser artifact contract must require post-append revalidation and rollback")
    required_fields = set(strings(contract.get("requiredRecordFields"),
                                  "requiredRecordFields", 20))
    releases = approved_release_ids()
    record = load(record_path)
    validate_record(record, required_fields, artifact_path, releases)
    record_evidence_digests = evidence_digests(record)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, f"{record['artifactId']}\n".encode("ascii"))
        os.fsync(lock_fd)
        original_registry_bytes = REGISTRY_PATH.read_bytes()
        registry = load(REGISTRY_PATH)
        validate_registry_for_append(registry)
        artifacts = registry["artifacts"]
        require(all(item.get("artifactId") != record["artifactId"] for item in artifacts),
                "artifactId is already registered")
        require(all(item.get("artifactSha256") != record["artifactSha256"]
                    for item in artifacts),
                "artifact digest is already registered")
        require(all(not (
            item.get("adapterId") == record["adapterId"] and
            item.get("adapterVersion") == record["adapterVersion"]
        ) for item in artifacts),
                "adapter ID and version are already registered")

        artifacts.append(record)
        registry["evidenceDigestsByArtifactId"][record["artifactId"]] = record_evidence_digests
        registry["reviewedArtifactCount"] = len(artifacts)
        registry["retainedRollbackArtifactCount"] = sum(
            1 for item in artifacts
            if item.get("rollbackRetentionState", {}).get("state") == "RETAINED"
        )
        registry["replayProvenArtifactCount"] = sum(
            1 for item in artifacts if item.get("replayEvidenceRefs")
        )
        registry["latestReviewedArtifactId"] = record["artifactId"]
        append_registry_transactionally(registry, original_registry_bytes)
    finally:
        os.close(lock_fd)
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered reviewed parser artifact: {record['artifactId']}")
    print("No release or production decision was changed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegistrationFailure as exc:
        print(f"PARSER ARTIFACT REGISTRATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
