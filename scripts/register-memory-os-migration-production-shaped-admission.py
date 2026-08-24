#!/usr/bin/env python3
"""Register one production-equivalent migration rehearsal admission.

The underlying migration evidence remains canonical and append-only. This tool
only binds that record to an immutable environment generation, approved release
pair, mixed-version observation, generation-bound recovery evidence and review.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from memory_os_migration_production_admission_ledger import (
    LedgerBindingFailure,
    require_registered_production_equivalent_rehearsal,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
CANONICAL_RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CANONICAL_RELEASE_CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
CANONICAL_RELEASE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
CANONICAL_RELEASE_PAIRS = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
CANONICAL_RELEASE_PAIR_WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
CANONICAL_GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
CANONICAL_GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
CANONICAL_REVIEW_ROOT = ROOT / "docs/evidence/migration-production-shaped-admission/independent-reviews"
CANONICAL_LOCK = ROOT / "contracts/operations/.migration-production-shaped-admission.lock"
CONTRACT = CANONICAL_CONTRACT
REGISTRY = CANONICAL_REGISTRY
RELEASES = CANONICAL_RELEASES
RELEASE_CONTRACT = CANONICAL_RELEASE_CONTRACT
RELEASE_WRITER = CANONICAL_RELEASE_WRITER
RELEASE_PAIRS = CANONICAL_RELEASE_PAIRS
RELEASE_PAIR_WRITER = CANONICAL_RELEASE_PAIR_WRITER
GENERATIONS = CANONICAL_GENERATIONS
GENERATION_WRITER = CANONICAL_GENERATION_WRITER
REVIEW_ROOT = CANONICAL_REVIEW_ROOT
LOCK = CANONICAL_LOCK
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ADMISSION_ID = re.compile(r"^mpa_[a-z0-9][a-z0-9_-]{7,63}$")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
REVIEW_SCHEMA = "memory-os-migration-production-shaped-independent-review.v1"
EXTERNAL_EVIDENCE_FIELDS = (
    "compatibilityEvidenceRefs",
    "mixedVersionObservationRefs",
    "recoveryEvidenceRefs",
    "backfillEvidenceRefs",
)
REVIEW_FIELDS = {
    "schemaVersion",
    "admissionId",
    "migrationRunId",
    "environmentGenerationId",
    "sourceCommitSha",
    "predecessorReleaseId",
    "successorReleaseId",
    "reviewRole",
    "reviewerId",
    "decision",
    "reviewedAt",
    "productionTrafficChanged",
    "productionCredentialsUsed",
    "automaticPromotionAuthorized",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_actual_cli_authorities() -> None:
    for label, actual, canonical in (
        ("contract", CONTRACT, CANONICAL_CONTRACT),
        ("registry", REGISTRY, CANONICAL_REGISTRY),
        ("release registry", RELEASES, CANONICAL_RELEASES),
        ("release contract", RELEASE_CONTRACT, CANONICAL_RELEASE_CONTRACT),
        ("release writer", RELEASE_WRITER, CANONICAL_RELEASE_WRITER),
        ("release pair registry", RELEASE_PAIRS, CANONICAL_RELEASE_PAIRS),
        ("release pair writer", RELEASE_PAIR_WRITER, CANONICAL_RELEASE_PAIR_WRITER),
        ("generation registry", GENERATIONS, CANONICAL_GENERATIONS),
        ("generation writer", GENERATION_WRITER, CANONICAL_GENERATION_WRITER),
    ):
        require(actual == canonical, f"migration production admission CLI {label} authority substitution rejected")
        require(not actual.is_symlink(), f"migration production admission CLI {label} authority must be symlink-free")
        require(
            actual.resolve(strict=True) == canonical.resolve(strict=True),
            f"migration production admission CLI {label} authority drift",
        )
    require(REVIEW_ROOT == CANONICAL_REVIEW_ROOT, "migration production admission CLI independent-review namespace substitution rejected")
    require(not REVIEW_ROOT.is_symlink(), "migration production admission CLI independent-review namespace must be symlink-free")
    require(
        REVIEW_ROOT.resolve(strict=True) == CANONICAL_REVIEW_ROOT.resolve(strict=True),
        "migration production admission CLI independent-review namespace drift",
    )
    require(LOCK == CANONICAL_LOCK, "migration production admission CLI lock authority substitution rejected")
    require(not LOCK.is_symlink(), "migration production admission CLI lock authority must be symlink-free")
    require(
        LOCK.parent.resolve(strict=True) == CANONICAL_LOCK.parent.resolve(strict=True),
        "migration production admission CLI lock parent authority drift",
    )


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def load_module(path: Path, name: str, label: str) -> ModuleType:
    require(path.is_file(), f"canonical {label} missing")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical {label}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generation_writer() -> ModuleType:
    return load_module(GENERATION_WRITER, "memory_os_environment_generation_writer", "environment generation writer")


def load_release_writer() -> ModuleType:
    return load_module(RELEASE_WRITER, "memory_os_release_baseline_writer", "release baseline writer")


def load_release_pair_writer() -> ModuleType:
    return load_module(RELEASE_PAIR_WRITER, "memory_os_release_pair_writer_for_migration", "release compatibility pair writer")


def evidence_refs(value: Any, field: str, *, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} reference(s)")
    require(all(isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        path = ROOT / item
        require(path.is_file(), f"{field} path missing: {item}")
        try:
            resolved = path.resolve(strict=True)
            relative = resolved.relative_to(ROOT.resolve())
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise Fail(f"{field} must resolve inside repository: {item}") from exc
        require(relative == Path(item), f"{field} must use canonical repository path: {item}")
        current = ROOT
        for part in Path(item).parts:
            current = current / part
            require(not current.is_symlink(), f"{field} must not traverse symlinks: {item}")
        require(git("ls-files", "--error-unmatch", "--", item) == item, f"{field} must be tracked at HEAD: {item}")
        current_bytes = path.read_bytes()
        head_bytes = subprocess.run(
            ["git", "show", f"HEAD:{item}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(head_bytes.returncode == 0 and head_bytes.stdout == current_bytes, f"{field} bytes must match current HEAD: {item}")
    return value


def external_evidence_digests(record: dict[str, Any]) -> dict[str, str]:
    refs: set[str] = set()
    for field in EXTERNAL_EVIDENCE_FIELDS:
        value = record.get(field)
        if isinstance(value, list):
            refs.update(item for item in value if isinstance(item, str))
    return {ref: hashlib.sha256((ROOT / ref).read_bytes()).hexdigest() for ref in sorted(refs)}


def json_contains_generation(value: Any, generation_id: str) -> bool:
    if isinstance(value, dict):
        return any(json_contains_generation(item, generation_id) for item in value.values())
    if isinstance(value, list):
        return any(json_contains_generation(item, generation_id) for item in value)
    return value == generation_id


def registered_generation(generation_id: str) -> dict[str, Any]:
    registry = load(GENERATIONS)
    generation_writer = load_generation_writer()
    try:
        generation_writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"environment generation registry invalid: {exc}") from exc
    rows = registry.get("generations")
    require(isinstance(rows, list), "environment generation registry missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("generationId") == generation_id]
    require(len(matches) == 1, "environmentGenerationId is not registered exactly once")
    return matches[0]


def approved_release(release_id: str) -> dict[str, Any]:
    registry = load(RELEASES)
    contract = load(RELEASE_CONTRACT)
    release_writer = load_release_writer()
    try:
        release_writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise Fail(f"release baseline registry invalid: {exc}") from exc
    rows = registry.get("releases")
    require(isinstance(rows, list), "release registry missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("releaseId") == release_id]
    require(len(matches) == 1, f"approved release not found exactly once: {release_id}")
    require(matches[0].get("approvalClass") == "PRODUCTION_RELEASE_BASELINE", f"release is not an approved baseline: {release_id}")
    require(matches[0].get("evidenceComplete") is True and matches[0].get("productionReady") is True, f"approved release evidence incomplete: {release_id}")
    return matches[0]


def approved_release_pair(predecessor: str, successor: str) -> dict[str, Any]:
    registry = load(RELEASE_PAIRS)
    pair_writer = load_release_pair_writer()
    try:
        pair_writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"release compatibility pair registry invalid: {exc}") from exc
    rows = registry.get("pairs")
    require(isinstance(rows, list), "release compatibility pair registry missing")
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("predecessorReleaseId") == predecessor
        and row.get("successorReleaseId") == successor
    ]
    require(len(matches) == 1, "predecessor/successor relation is not an approved release compatibility pair")
    require(matches[0].get("pairEvidenceComplete") is True, "approved release compatibility pair evidence incomplete")
    require(matches[0].get("productionEvidence") is False and matches[0].get("productionReady") is False, "release pair cannot already claim production")
    return matches[0]


def canonical_review_path(ref: Any, field: str) -> Path:
    require(isinstance(ref, str) and ref and not Path(ref).is_absolute() and ".." not in Path(ref).parts, f"{field} invalid")
    path = ROOT / ref
    require(path.is_file(), f"{field} path missing: {ref}")
    try:
        path.resolve(strict=True).relative_to(REVIEW_ROOT.resolve(strict=False))
    except (OSError, ValueError) as exc:
        raise Fail(f"{field} must remain inside monitored migration independent-review namespace") from exc
    current = ROOT
    for part in Path(ref).parts:
        current = current / part
        require(not current.is_symlink(), f"{field} must not traverse symlinks: {ref}")
    require(git("ls-files", "--error-unmatch", "--", ref) == ref, f"{field} must be tracked at HEAD: {ref}")
    current_bytes = path.read_bytes()
    head_bytes = subprocess.run(
        ["git", "show", f"HEAD:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(head_bytes.returncode == 0 and head_bytes.stdout == current_bytes, f"{field} bytes must match current HEAD: {ref}")
    creation_commits = [item for item in git("log", "--diff-filter=A", "--format=%H", "--", ref).splitlines() if item]
    require(len(creation_commits) == 1, f"{field} must have exactly one immutable creation authority: {ref}")
    creation_bytes = subprocess.run(
        ["git", "show", f"{creation_commits[0]}:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(creation_bytes.returncode == 0 and creation_bytes.stdout == current_bytes, f"{field} must remain byte-identical to its creation commit: {ref}")
    return path


def canonical_utc_timestamp(value: Any, field: str) -> str:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be canonical UTC RFC3339 seconds")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed), f"{field} must be UTC")
    require(parsed.microsecond == 0 and parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, f"{field} must use canonical UTC RFC3339 seconds")
    return value


def validate_independent_reviews(record: dict[str, Any]) -> None:
    reviews: dict[str, dict[str, Any]] = {}
    for field, role in (("securityReviewRef", "SECURITY"), ("operabilityReviewRef", "OPERABILITY")):
        review = load(canonical_review_path(record.get(field), field))
        require(set(review) == REVIEW_FIELDS, f"{field} field set drift: {sorted(set(review) ^ REVIEW_FIELDS)}")
        require(review.get("schemaVersion") == REVIEW_SCHEMA, f"{field} schemaVersion drift")
        for binding in (
            "admissionId",
            "migrationRunId",
            "environmentGenerationId",
            "sourceCommitSha",
            "predecessorReleaseId",
            "successorReleaseId",
        ):
            require(review.get(binding) == record.get(binding), f"{field} {binding} binding mismatch")
        require(review.get("reviewRole") == role, f"{field} reviewRole must be {role}")
        reviewer_id = review.get("reviewerId")
        require(isinstance(reviewer_id, str) and REVIEWER_ID.fullmatch(reviewer_id), f"{field} reviewerId invalid")
        require(review.get("decision") == "APPROVED", f"{field} decision must be APPROVED")
        canonical_utc_timestamp(review.get("reviewedAt"), f"{field}.reviewedAt")
        require(review.get("productionTrafficChanged") is False, f"{field} cannot change production traffic")
        require(review.get("productionCredentialsUsed") is False, f"{field} cannot use production credentials")
        require(review.get("automaticPromotionAuthorized") is False, f"{field} cannot authorize automatic promotion")
        reviews[role] = review
    require(record["securityReviewRef"] != record["operabilityReviewRef"], "security and operability review records must be distinct")
    require(reviews["SECURITY"]["reviewerId"] != reviews["OPERABILITY"]["reviewerId"], "security and operability reviewers must be distinct")


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("admissionId"), str) and ADMISSION_ID.fullmatch(record["admissionId"]), "admissionId invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "sourceCommitSha does not exist")
    require(git("merge-base", "--is-ancestor", source, "HEAD") == "", "sourceCommitSha must be an ancestor of current HEAD")

    migration_ref = record.get("migrationEvidenceRef")
    require(isinstance(migration_ref, str) and migration_ref and not Path(migration_ref).is_absolute() and ".." not in Path(migration_ref).parts, "migrationEvidenceRef invalid")
    migration_path = ROOT / migration_ref
    require(migration_path.is_file(), "migrationEvidenceRef does not exist")
    migration = load(migration_path)
    require(migration.get("schemaVersion") == "memory-os-migration-rehearsal-evidence.v1", "migration evidence schema drift")
    require(migration.get("migrationRunId") == record.get("migrationRunId"), "migrationRunId binding mismatch")
    require(migration.get("sourceCommitSha") == source, "migration evidence source commit mismatch")
    require(migration.get("environment") == "PRODUCTION_EQUIVALENT", "only production-equivalent migration evidence may be admitted")
    require(migration.get("productionTraffic") is False and migration.get("productionCredentials") is False, "production-equivalent migration evidence must not use production traffic/credentials")
    require(migration.get("productionEvidence") is False and migration.get("productionReady") is False, "migration evidence cannot already claim production")
    require(migration.get("lockBudgetResult") == "PASS", "migration lock budget must pass")
    require(migration.get("preflightResult") == "PASS" and migration.get("applyResult") == "PASS" and migration.get("verificationResult") == "PASS", "migration rehearsal must pass preflight/apply/verification")
    artifact_link = migration.get("recoveryArtifactLink")
    require(isinstance(artifact_link, dict) and artifact_link.get("artifactVerified") is True, "migration recovery artifact must be verified")

    generation_id = record.get("environmentGenerationId")
    manifest = record.get("environmentManifestSha256")
    require(isinstance(generation_id, str) and generation_id, "environmentGenerationId required")
    require(isinstance(manifest, str) and DIGEST.fullmatch(manifest), "environmentManifestSha256 invalid")
    generation = registered_generation(generation_id)
    require(generation.get("environmentManifestSha256") == manifest, "environment manifest digest does not match registered generation")
    try:
        require_registered_production_equivalent_rehearsal(
            migration_run_id=record["migrationRunId"],
            source_commit_sha=source,
            environment_generation_id=generation_id,
        )
    except LedgerBindingFailure as exc:
        raise Fail(f"canonical migration ledger binding invalid: {exc}") from exc

    predecessor = record.get("predecessorReleaseId")
    successor = record.get("successorReleaseId")
    require(isinstance(predecessor, str) and isinstance(successor, str) and predecessor != successor, "distinct predecessor/successor release IDs required")
    approved_release(predecessor)
    successor_row = approved_release(successor)
    require(successor_row.get("commitSha") == source, "successor approved release must bind migration source commit")
    approved_release_pair(predecessor, successor)

    compatibility_refs = evidence_refs(record.get("compatibilityEvidenceRefs"), "compatibilityEvidenceRefs")
    mixed_refs = evidence_refs(record.get("mixedVersionObservationRefs"), "mixedVersionObservationRefs")
    recovery_refs = evidence_refs(record.get("recoveryEvidenceRefs"), "recoveryEvidenceRefs")
    for ref in recovery_refs:
        value = load(ROOT / ref)
        require(json_contains_generation(value, generation_id), f"recovery evidence is not bound to environment generation: {ref}")
    require(set(compatibility_refs) != set(mixed_refs) or len(compatibility_refs) > 1, "compatibility and mixed-version evidence must not collapse to one unreviewed reference")

    backfill_required = record.get("backfillRequired")
    require(isinstance(backfill_required, bool), "backfillRequired must be boolean")
    backfill_refs = record.get("backfillEvidenceRefs")
    if backfill_required:
        evidence_refs(backfill_refs, "backfillEvidenceRefs")
    else:
        require(backfill_refs == [], "backfillEvidenceRefs must be empty when backfillRequired=false")

    validate_independent_reviews(record)
    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be a list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(isinstance(finding.get("findingId"), str) and finding["findingId"], f"unresolvedFindings[{index}].findingId invalid")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "Critical/High findings block migration admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")
    require(record.get("evidenceComplete") is True, "evidenceComplete must be true")
    require(record.get("productionEvidence") is False, "production-equivalent migration admission cannot be production evidence")
    require(record.get("productionReady") is False, "migration admission cannot make application productionReady")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "account_id", "session_id", "@"):
        require(forbidden not in serialized, f"record contains forbidden runtime material: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    rules = contract.get("admissionRules")
    require(isinstance(rules, dict) and rules.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "migration admission contract must require post-append revalidation and rollback")
    require(set(registry) == {"schemaVersion", "appendOnly", "admittedRehearsalCount", "admissions", "evidenceDigestsByAdmissionId", "productionEvidence", "productionReady"}, "registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-migration-production-shaped-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    admissions = registry.get("admissions")
    require(isinstance(admissions, list), "registry admissions missing")
    require(all(isinstance(item, dict) for item in admissions), "registry contains invalid admission")
    count = registry.get("admittedRehearsalCount")
    require(isinstance(count, int) and not isinstance(count, bool), "admittedRehearsalCount must be an integer")
    require(count == len(admissions), "admittedRehearsalCount drift")
    digest_authority = registry.get("evidenceDigestsByAdmissionId")
    require(isinstance(digest_authority, dict), "evidenceDigestsByAdmissionId must be an object")
    require(registry.get("productionEvidence") is False, "registry cannot claim production evidence")
    require(registry.get("productionReady") is False, "registry cannot claim production readiness")
    ids: set[str] = set()
    runs: set[str] = set()
    for index, record in enumerate(admissions):
        validate_record(record)
        admission_id = record.get("admissionId")
        migration_run_id = record.get("migrationRunId")
        require(admission_id not in ids, f"duplicate admissionId at admissions[{index}]: {admission_id}")
        require(migration_run_id not in runs, f"duplicate migrationRunId at admissions[{index}]: {migration_run_id}")
        ids.add(admission_id)
        runs.add(migration_run_id)
        expected_digests = external_evidence_digests(record)
        stored_digests = digest_authority.get(admission_id)
        require(isinstance(stored_digests, dict), f"missing external evidence digest authority for admission: {admission_id}")
        require(stored_digests == expected_digests, f"external evidence digest authority drift for admission: {admission_id}")
    require(set(digest_authority) == ids, "evidence digest authority contains unknown or missing admission IDs")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".migration-production-admission.", suffix=".tmp", dir=REGISTRY.parent)
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


def atomic_write_bytes(value: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".migration-production-admission.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def append_registry_transactionally(registry: dict[str, Any], original_bytes: bytes) -> None:
    atomic_write(registry)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        atomic_write_bytes(original_bytes)
        raise


def main() -> int:
    require_actual_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    record_path = Path(args.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input admission record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(record_path)
    validate_record(record)
    record_digests = external_evidence_digests(record)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("migration production admission registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["admissionId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        original_registry_bytes = REGISTRY.read_bytes()
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        admissions = registry["admissions"]
        require(all(item.get("admissionId") != record["admissionId"] for item in admissions), "admissionId already registered")
        require(all(item.get("migrationRunId") != record["migrationRunId"] for item in admissions), "migrationRunId already admitted")
        admissions.append(record)
        registry["evidenceDigestsByAdmissionId"][record["admissionId"]] = record_digests
        registry["admittedRehearsalCount"] = len(admissions)
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        append_registry_transactionally(registry, original_registry_bytes)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered production-shaped migration rehearsal admission: {record['admissionId']}")
    print("Production evidence and application production readiness remain false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ADMISSION FAILED: {exc}")
        raise SystemExit(1)
