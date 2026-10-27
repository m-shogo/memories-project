#!/usr/bin/env python3
"""Append one typed non-resurrection evidence record for backup/restore admission."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
CANONICAL_GEN_EVIDENCE_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
CONTRACT = CANONICAL_CONTRACT
REGISTRY = CANONICAL_REGISTRY
GEN_EVIDENCE_REGISTRY = CANONICAL_GEN_EVIDENCE_REGISTRY
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
LOCK = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECORD_ID = re.compile(r"^brnr_[a-z0-9][a-z0-9_-]{7,63}$")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
DOMAIN_EVIDENCE_FIELDS = {
    "schemaVersion", "generationEvidenceId", "sourceCommitSha", "domain", "result",
    "productionTraffic", "productionCredentials", "productionEvidence", "productionReady",
}
DOMAIN_EVIDENCE_SCHEMA = "memory-os-backup-restore-non-resurrection-domain-evidence.v1"
REVIEW_EVIDENCE_FIELDS = {
    "schemaVersion", "generationEvidenceId", "sourceCommitSha", "typedRecordId", "reviewType",
    "reviewerPseudonym", "reviewedDomainEvidenceRefs", "reviewedDomainEvidenceSha256", "result",
    "productionTraffic", "productionCredentials", "productionEvidence", "productionReady",
}
REVIEW_EVIDENCE_SCHEMA = "memory-os-backup-restore-non-resurrection-review-evidence.v1"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def domain_validation_failure(exc: BaseException) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RuntimeError) and current.__class__.__name__ == "Fail":
            return True
        current = current.__cause__ or current.__context__
    return False

MAX_JSON_BYTES = 1024 * 1024

def load(path: Path) -> dict[str, Any]:
    """Read external evidence and canonical registry JSON with bounded, strict semantics."""
    require(isinstance(path, Path) and path.is_absolute(), "typed writer JSON path invalid")
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "typed writer JSON safe open unavailable")
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        require(stat.S_ISREG(os.fstat(fd).st_mode), "typed writer JSON path unsafe")
        with os.fdopen(fd, "rb") as source:
            fd = -1
            raw = source.read(MAX_JSON_BYTES + 1)
    except OSError:
        raise Fail("typed writer JSON unreadable or invalid") from None
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                raise Fail("typed writer JSON descriptor cleanup failed") from None
    require(len(raw) <= MAX_JSON_BYTES, "typed writer JSON size limit exceeded")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "typed writer JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("typed writer JSON nonfinite number refused")

    def parse_finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "typed writer JSON nonfinite number refused")
        return number

    def parse_bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "typed writer JSON integer too large")
        return int(value)

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite,
            parse_float=parse_finite_float,
            parse_int=parse_bounded_int,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("typed writer JSON unreadable or invalid") from None
    require(isinstance(value, dict), "typed writer JSON root must be object")
    return value

def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to the canonical repository file")
    return path

def require_canonical_runtime_authority(path: Path, canonical: Path, field: str) -> None:
    if path == canonical:
        canonical_repo_file(path, field)

def require_cli_authorities() -> None:
    """Pin the actual typed-evidence append entrypoint to canonical authorities."""
    authorities = (
        (CONTRACT, CANONICAL_CONTRACT, "typed non-resurrection contract"),
        (REGISTRY, CANONICAL_REGISTRY, "typed non-resurrection registry"),
        (GEN_EVIDENCE_REGISTRY, CANONICAL_GEN_EVIDENCE_REGISTRY, "generation evidence registry"),
        (GEN_WRITER, ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py", "generation recovery writer"),
    )
    for actual, canonical, field in authorities:
        require(actual == canonical, f"{field} must use canonical authority")
        canonical_repo_file(actual, field)
    canonical_lock = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
    require(LOCK == canonical_lock, "typed non-resurrection lock must use canonical authority")
    require(LOCK.parent == CANONICAL_REGISTRY.parent, "typed non-resurrection lock must share canonical registry directory")

def payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be a canonical repository-relative path")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} evidence path missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value

MAX_SOURCE_BYTES = 1024 * 1024
SOURCE_GIT_TIMEOUT = 20

def require_ref_bound_to_source(source_commit: str, ref: str, field: str) -> None:
    """Compare a pinned, bounded local regular file with a bounded immutable Git blob."""
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit), f"{field} sourceCommitSha invalid")
    require(isinstance(ref, str) and ref and ":" not in ref, f"{field} invalid for immutable source binding")
    repo_ref(ref, field)
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            f"{field} safe source read unavailable")
    path = ROOT / ref
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        require(stat.S_ISREG(os.fstat(fd).st_mode), f"{field} evidence source is not a regular file")
        with os.fdopen(fd, "rb") as source:
            fd = -1
            current = source.read(MAX_SOURCE_BYTES + 1)
    except OSError:
        raise Fail(f"{field} cannot be read for immutable source binding") from None
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                raise Fail(f"{field} source descriptor cleanup failed") from None
    require(len(current) <= MAX_SOURCE_BYTES, f"{field} source file size limit exceeded")

    def git_blob(*args: str) -> bytes:
        try:
            completed = subprocess.run(
                ["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=SOURCE_GIT_TIMEOUT, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise Fail(f"{field} evidence missing from sourceCommitSha") from None
        require(type(completed.returncode) is int and completed.returncode == 0
                and isinstance(completed.stdout, bytes),
                f"{field} evidence missing from sourceCommitSha")
        return completed.stdout

    source_ref = f"{source_commit}:{ref}"
    size_bytes = git_blob("cat-file", "-s", source_ref)
    require(len(size_bytes) <= 32 and size_bytes.strip().isascii()
            and size_bytes.strip().isdigit(),
            f"{field} source blob size invalid")
    source_size = int(size_bytes.strip())
    require(source_size <= MAX_SOURCE_BYTES, f"{field} source blob size limit exceeded")
    historical = git_blob("show", source_ref)
    require(len(historical) == source_size, f"{field} source blob length mismatch")
    require(current == historical, f"{field} evidence changed since sourceCommitSha")

def load_generation_writer():
    writer = canonical_repo_file(GEN_WRITER, "generation recovery writer")
    spec = importlib.util.spec_from_file_location("memory_os_generation_recovery_writer", writer)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def generation_registry_rows() -> list[dict[str, Any]]:
    require_canonical_runtime_authority(GEN_EVIDENCE_REGISTRY, CANONICAL_GEN_EVIDENCE_REGISTRY, "generation evidence registry")
    registry = load(GEN_EVIDENCE_REGISTRY)
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    count = registry.get("registeredEvidenceCount")
    require(valid_count(count) and count == len(rows), "generation evidence registry registeredEvidenceCount drift")
    if GEN_EVIDENCE_REGISTRY == CANONICAL_GEN_EVIDENCE_REGISTRY:
        generation_writer = load_generation_writer()
        try:
            generation_writer.validate_upstream_authorities_for_append()
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail("generation evidence upstream authority invalid") from None
            raise
        if GEN_EVIDENCE_REGISTRY == ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json":
            for index, row in enumerate(rows):
                try:
                    generation_writer.validate_record(row, require_current_drill_request=False)
                except Exception as exc:
                    if domain_validation_failure(exc):
                        raise Fail(f"generation evidence registry records[{index}] historical authority invalid") from None
                    raise
        bound_count = registry.get("drillRequestBoundEvidenceCount")
        backup_count = registry.get("completeGenerationBoundBackupCount")
        restore_count = registry.get("completeGenerationBoundRestoreCount")
        candidate_count = registry.get("productionEquivalentRecoveryCandidateCount")
        require(
            all(valid_count(value) for value in (bound_count, backup_count, restore_count, candidate_count)),
            "generation evidence registry derived counts invalid",
        )
        derived_backup = sum(1 for row in rows if row.get("evidenceComplete") is True)
        derived_restore = sum(
            1
            for row in rows
            if row.get("evidenceComplete") is True
            and row.get("isolatedRestoreVerified") is True
            and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
        )
        require(bound_count == count, "generation evidence registry drillRequestBoundEvidenceCount drift")
        require(backup_count == derived_backup, "generation evidence registry completeGenerationBoundBackupCount drift")
        require(restore_count == derived_restore, "generation evidence registry completeGenerationBoundRestoreCount drift")
        require(0 <= candidate_count <= restore_count <= backup_count <= bound_count <= count, "generation evidence registry count ordering invalid")
    evidence_ids = [row.get("evidenceId") for row in rows]
    require(all(isinstance(value, str) and value for value in evidence_ids) and len(evidence_ids) == len(set(evidence_ids)), "generation evidence registry evidenceId authority invalid")
    return rows

def generation_record(evidence_id: Any) -> dict[str, Any]:
    require(isinstance(evidence_id, str) and evidence_id, "generationEvidenceId required")
    rows = generation_registry_rows()
    matches = [row for row in rows if row.get("evidenceId") == evidence_id]
    require(len(matches) == 1, "generationEvidenceId is not uniquely registered")
    return matches[0]

def domain_evidence(ref: str, *, domain: str, generation_evidence_id: str, source_commit_sha: str) -> dict[str, Any]:
    if GEN_EVIDENCE_REGISTRY == CANONICAL_GEN_EVIDENCE_REGISTRY:
        require_ref_bound_to_source(source_commit_sha, ref, f"domain {domain} evidence")
    payload = load(ROOT / ref)
    require(set(payload) == DOMAIN_EVIDENCE_FIELDS, f"domain {domain} evidence field set drift: {sorted(set(payload) ^ DOMAIN_EVIDENCE_FIELDS)}")
    require(payload.get("schemaVersion") == DOMAIN_EVIDENCE_SCHEMA, f"domain {domain} evidence schemaVersion drift")
    require(payload.get("generationEvidenceId") == generation_evidence_id, f"domain {domain} evidence generation binding mismatch")
    require(payload.get("sourceCommitSha") == source_commit_sha, f"domain {domain} evidence source commit binding mismatch")
    require(payload.get("domain") == domain, f"domain {domain} evidence domain binding mismatch")
    require(payload.get("result") in {"PASS", "FAIL", "NOT_RUN"}, f"domain {domain} evidence result invalid")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(payload.get(field) is False, f"domain {domain} evidence {field} must remain false")
    return payload

def review_evidence(ref: str, *, review_type: str, record_id: str, generation_evidence_id: str, source_commit_sha: str, domain_digests: dict[str, str]) -> dict[str, Any]:
    if GEN_EVIDENCE_REGISTRY == CANONICAL_GEN_EVIDENCE_REGISTRY:
        require_ref_bound_to_source(source_commit_sha, ref, f"{review_type} review evidence")
    payload = load(ROOT / ref)
    require(set(payload) == REVIEW_EVIDENCE_FIELDS, f"{review_type} review field set drift: {sorted(set(payload) ^ REVIEW_EVIDENCE_FIELDS)}")
    require(payload.get("schemaVersion") == REVIEW_EVIDENCE_SCHEMA, f"{review_type} review schemaVersion drift")
    require(payload.get("generationEvidenceId") == generation_evidence_id, f"{review_type} review generation binding mismatch")
    require(payload.get("sourceCommitSha") == source_commit_sha, f"{review_type} review source commit binding mismatch")
    require(payload.get("typedRecordId") == record_id, f"{review_type} review typed record binding mismatch")
    require(payload.get("reviewType") == review_type, f"{review_type} review type mismatch")
    reviewer = payload.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and REVIEWER_ID.fullmatch(reviewer), f"{review_type} reviewerPseudonym invalid")
    reviewed_refs = payload.get("reviewedDomainEvidenceRefs")
    require(isinstance(reviewed_refs, list) and len(reviewed_refs) == len(set(reviewed_refs)), f"{review_type} reviewedDomainEvidenceRefs invalid")
    require(set(reviewed_refs) == set(domain_digests), f"{review_type} review does not bind exact typed domain bundle")
    reviewed_digests = payload.get("reviewedDomainEvidenceSha256")
    require(isinstance(reviewed_digests, dict) and set(reviewed_digests) == set(domain_digests), f"{review_type} reviewedDomainEvidenceSha256 coverage mismatch")
    require(all(isinstance(value, str) and SHA256.fullmatch(value) for value in reviewed_digests.values()), f"{review_type} reviewedDomainEvidenceSha256 invalid")
    require(reviewed_digests == domain_digests, f"{review_type} review domain evidence digest binding mismatch")
    require(payload.get("result") == "APPROVED", f"{review_type} review must be APPROVED")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(payload.get(field) is False, f"{review_type} review {field} must remain false")
    return payload

def validate_record(record: dict[str, Any]) -> None:
    require_canonical_runtime_authority(CONTRACT, CANONICAL_CONTRACT, "typed non-resurrection contract")
    contract = load(CONTRACT)
    required_fields = set(contract.get("requiredRecordFields", []))
    required_domains = tuple(contract.get("requiredDomains", []))
    require(required_fields and required_domains, "non-resurrection contract incomplete")
    require(
        contract.get("recordRules", {}).get("typedRegistryMustRevalidateAfterAppendAndRollbackOnFailure") is True,
        "typed non-resurrection transactional append authority drift",
    )
    require(set(record) == required_fields, f"record field set drift: {sorted(set(record) ^ required_fields)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("recordId"), str) and RECORD_ID.fullmatch(record["recordId"]), "recordId invalid")
    generation = generation_record(record.get("generationEvidenceId"))
    source_sha = record.get("sourceCommitSha")
    require(isinstance(source_sha, str) and SHA40.fullmatch(source_sha), "sourceCommitSha invalid")
    require(source_sha == generation.get("sourceCommitSha"), "sourceCommitSha must match generation recovery evidence")

    prefixes = contract.get("domainEvidencePathPrefixes")
    require(isinstance(prefixes, dict) and set(prefixes) == set(required_domains), "domainEvidencePathPrefixes drift")
    domains = record.get("domains")
    require(isinstance(domains, dict) and set(domains) == set(required_domains), "domain coverage drift")
    refs_seen: set[str] = set()
    domain_digests: dict[str, str] = {}
    for name in required_domains:
        entry = domains.get(name)
        require(isinstance(entry, dict) and set(entry) == {"result", "evidenceRef"}, f"domain {name} field drift")
        require(entry.get("result") in {"PASS", "FAIL", "NOT_RUN"}, f"domain {name} result invalid")
        evidence_ref = repo_ref(entry.get("evidenceRef"), f"domains.{name}.evidenceRef")
        prefix = prefixes.get(name)
        require(isinstance(prefix, str) and evidence_ref.startswith(prefix) and evidence_ref.endswith(".json"), f"domain {name} evidence path is not typed")
        require(evidence_ref not in refs_seen, f"domain {name} evidenceRef must be distinct")
        refs_seen.add(evidence_ref)
        payload = domain_evidence(evidence_ref, domain=name, generation_evidence_id=record["generationEvidenceId"], source_commit_sha=source_sha)
        require(payload.get("result") == entry.get("result"), f"domain {name} evidence result binding mismatch")
        domain_digests[evidence_ref] = payload_sha256(payload)

    review_prefixes = contract.get("reviewEvidencePathPrefixes")
    require(isinstance(review_prefixes, dict) and set(review_prefixes) == {"SECURITY", "OPERABILITY"}, "reviewEvidencePathPrefixes drift")
    security = repo_ref(record.get("securityReviewRef"), "securityReviewRef")
    operability = repo_ref(record.get("operabilityReviewRef"), "operabilityReviewRef")
    require(security != operability, "security and operability reviews must be distinct")
    require(security.startswith(review_prefixes["SECURITY"]) and security.endswith(".json"), "security review path is not typed")
    require(operability.startswith(review_prefixes["OPERABILITY"]) and operability.endswith(".json"), "operability review path is not typed")
    security_payload = review_evidence(security, review_type="SECURITY", record_id=record["recordId"], generation_evidence_id=record["generationEvidenceId"], source_commit_sha=source_sha, domain_digests=domain_digests)
    operability_payload = review_evidence(operability, review_type="OPERABILITY", record_id=record["recordId"], generation_evidence_id=record["generationEvidenceId"], source_commit_sha=source_sha, domain_digests=domain_digests)
    require(security_payload["reviewerPseudonym"] != operability_payload["reviewerPseudonym"], "security and operability reviewers must be independent")
    if "securityReviewSha256" in required_fields or "operabilityReviewSha256" in required_fields:
        require({"securityReviewSha256", "operabilityReviewSha256"}.issubset(required_fields), "review digest field contract incomplete")
        security_digest = record.get("securityReviewSha256")
        operability_digest = record.get("operabilityReviewSha256")
        require(isinstance(security_digest, str) and SHA256.fullmatch(security_digest), "securityReviewSha256 invalid")
        require(isinstance(operability_digest, str) and SHA256.fullmatch(operability_digest), "operabilityReviewSha256 invalid")
        require(security_digest == payload_sha256(security_payload), "security review payload digest binding mismatch")
        require(operability_digest == payload_sha256(operability_payload), "operability review payload digest binding mismatch")

    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL findings block admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}] status invalid")
    require(isinstance(record.get("evidenceComplete"), bool), "evidenceComplete must be boolean")
    complete = all(domains[name]["result"] == "PASS" for name in required_domains) and not findings
    require(record.get("evidenceComplete") is complete, "evidenceComplete derivation drift")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@", "latest"):
        require(forbidden not in serialized, f"record contains forbidden recovery material: {forbidden}")

def candidate_complete(record: dict[str, Any]) -> bool:
    generation = generation_record(record.get("generationEvidenceId"))
    generation_writer = load_generation_writer()
    generation_writer.GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
    generation_writer.OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
    generation_writer.DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
    generation_writer.NON_RESURRECTION_REGISTRY = REGISTRY
    return record.get("evidenceComplete") is True and generation_writer.base_candidate(generation)

def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    generation_registry_rows()
    require(registry.get("schemaVersion") == "memory-os-backup-restore-non-resurrection-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry records invalid")
    registered_count = registry.get("registeredRecordCount")
    complete_count = registry.get("completeRecordCount")
    covered_count = registry.get("candidateCoveredCount")
    require(valid_count(registered_count) and registered_count == len(rows), "registeredRecordCount drift")
    for index, row in enumerate(rows):
        try:
            validate_record(row)
        except Fail as exc:
            raise Fail(f"registry records[{index}] authority invalid: {exc}") from exc
    derived_complete = sum(1 for row in rows if row.get("evidenceComplete") is True)
    require(valid_count(complete_count) and complete_count == derived_complete, "completeRecordCount drift")
    record_ids = [row.get("recordId") for row in rows]
    generation_ids = [row.get("generationEvidenceId") for row in rows]
    require(all(isinstance(value, str) and value for value in record_ids) and len(record_ids) == len(set(record_ids)), "recordId authority invalid")
    require(all(isinstance(value, str) and value for value in generation_ids) and len(generation_ids) == len(set(generation_ids)), "generationEvidenceId coverage authority invalid")
    derived_covered = sum(1 for row in rows if candidate_complete(row))
    require(valid_count(covered_count) and covered_count == derived_covered, "candidateCoveredCount drift")
    return rows

def atomic_write(value: dict[str, Any], mode: int) -> None:
    """Publish only a complete fsynced candidate; own and clean every temporary FD."""
    descriptor: int | None = None
    temp_name: str | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".backup-restore-non-resurrection.", suffix=".tmp", dir=REGISTRY.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            os.fchmod(handle.fileno(), mode)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
        temp_name = None
    except Exception:
        raise Fail("typed non-resurrection registry atomic write failed") from None
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
            raise Fail("typed non-resurrection registry temporary cleanup failed") from None


def atomic_restore(payload: bytes, mode: int) -> None:
    """Restore the exact prior registry bytes and mode after post-write rejection."""
    descriptor: int | None = None
    temp_name: str | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".backup-restore-non-resurrection-rollback.", suffix=".tmp", dir=REGISTRY.parent)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            os.fchmod(handle.fileno(), mode)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
        temp_name = None
    except Exception:
        raise Fail("typed non-resurrection registry atomic restore failed") from None
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
            raise Fail("typed non-resurrection registry temporary cleanup failed") from None


def snapshot_registry_for_append() -> tuple[bytes, int]:
    """Pin registry bytes and mode to the same bounded regular-file descriptor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "typed non-resurrection registry snapshot safe open unavailable")
    fd = -1
    try:
        fd = os.open(REGISTRY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(fd)
        require(stat.S_ISREG(metadata.st_mode),
                "typed non-resurrection registry snapshot path unsafe")
        with os.fdopen(fd, "rb") as source:
            fd = -1
            original = source.read(MAX_JSON_BYTES + 1)
    except OSError:
        raise Fail("cannot snapshot typed non-resurrection registry before append") from None
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                raise Fail("typed non-resurrection registry snapshot descriptor cleanup failed") from None
    require(len(original) <= MAX_JSON_BYTES,
            "typed non-resurrection registry snapshot size limit exceeded")
    return original, stat.S_IMODE(metadata.st_mode)


def write_registry_transactionally(value: dict[str, Any]) -> None:
    original, original_mode = snapshot_registry_for_append()
    atomic_write(value, original_mode)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        try:
            atomic_restore(original, original_mode)
        except Exception:
            raise Fail("typed non-resurrection append failed; rollback incomplete") from None
        raise Fail("typed non-resurrection append failed; rollback completed") from None

def main() -> int:
    require_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    input_path = Path(args.record).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input non-resurrection evidence must be outside repository")
    record = load(input_path)
    validate_record(record)
    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise Fail("non-resurrection admission registry lock already exists") from None
    except OSError:
        raise Fail("typed non-resurrection registry lock acquisition failed") from None
    try:
        lock_payload = (record["recordId"] + "\n").encode("ascii")
        try:
            written = os.write(lock_fd, lock_payload)
            require(type(written) is int and written == len(lock_payload),
                    "typed non-resurrection registry lock initialization failed")
            os.fsync(lock_fd)
        except OSError:
            raise Fail("typed non-resurrection registry lock initialization failed") from None
        registry = load(REGISTRY)
        rows = validate_registry_for_append(registry)
        require(all(row.get("recordId") != record["recordId"] for row in rows), "recordId already registered")
        require(all(row.get("generationEvidenceId") != record["generationEvidenceId"] for row in rows), "generationEvidenceId already has non-resurrection evidence")
        rows.append(record)
        registry["registeredRecordCount"] = len(rows)
        registry["completeRecordCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True)
        registry["candidateCoveredCount"] = sum(1 for row in rows if candidate_complete(row))
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        write_registry_transactionally(registry)
    finally:
        cleanup_failed = False
        try:
            os.close(lock_fd)
        except OSError:
            cleanup_failed = True
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            cleanup_failed = True
        if cleanup_failed:
            raise Fail("typed non-resurrection registry lock cleanup failed") from None
    print(f"Registered backup/restore non-resurrection evidence: {record['recordId']}")
    print(f"pre-overlay candidate covered: {str(candidate_complete(record)).lower()}")
    print("production evidence: false")
    print("production ready: false")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION REGISTRATION FAILED: {exc}")
        raise SystemExit(1)