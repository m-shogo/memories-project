#!/usr/bin/env python3
"""Register one production-equivalent migration rehearsal admission.

The underlying migration evidence remains canonical and append-only. This tool
only binds that record to an immutable environment generation, approved release
pair, mixed-version observation, generation-bound recovery evidence and review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOCK = ROOT / "contracts/operations/.migration-production-shaped-admission.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ADMISSION_ID = re.compile(r"^mpa_[a-z0-9][a-z0-9_-]{7,63}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def evidence_refs(value: Any, field: str, *, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} reference(s)")
    require(all(isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        require((ROOT / item).is_file(), f"{field} path missing: {item}")
    return value


def json_contains_generation(value: Any, generation_id: str) -> bool:
    if isinstance(value, dict):
        return any(json_contains_generation(item, generation_id) for item in value.values())
    if isinstance(value, list):
        return any(json_contains_generation(item, generation_id) for item in value)
    return value == generation_id


def registered_generation(generation_id: str) -> dict[str, Any]:
    registry = load(GENERATIONS)
    rows = registry.get("generations")
    require(isinstance(rows, list), "environment generation registry missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("generationId") == generation_id]
    require(len(matches) == 1, "environmentGenerationId is not registered exactly once")
    return matches[0]


def approved_release(release_id: str) -> dict[str, Any]:
    registry = load(RELEASES)
    rows = registry.get("releases")
    require(isinstance(rows, list), "release registry missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("releaseId") == release_id]
    require(len(matches) == 1, f"approved release not found exactly once: {release_id}")
    require(matches[0].get("approvalClass") == "PRODUCTION_RELEASE_BASELINE", f"release is not an approved baseline: {release_id}")
    require(matches[0].get("evidenceComplete") is True and matches[0].get("productionReady") is True, f"approved release evidence incomplete: {release_id}")
    return matches[0]


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("admissionId"), str) and ADMISSION_ID.fullmatch(record["admissionId"]), "admissionId invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "sourceCommitSha does not exist")

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

    predecessor = record.get("predecessorReleaseId")
    successor = record.get("successorReleaseId")
    require(isinstance(predecessor, str) and isinstance(successor, str) and predecessor != successor, "distinct predecessor/successor release IDs required")
    approved_release(predecessor)
    successor_row = approved_release(successor)
    require(successor_row.get("commitSha") == source, "successor approved release must bind migration source commit")

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

    for field in ("securityReviewRef", "operabilityReviewRef"):
        value = record.get(field)
        require(isinstance(value, str) and value and not Path(value).is_absolute() and ".." not in Path(value).parts and (ROOT / value).is_file(), f"{field} invalid")
    require(record["securityReviewRef"] != record["operabilityReviewRef"], "security and operability review records must be distinct")
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
    require(set(registry) == {"schemaVersion", "appendOnly", "admittedRehearsalCount", "admissions", "productionEvidence", "productionReady"}, "registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-migration-production-shaped-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    admissions = registry.get("admissions")
    require(isinstance(admissions, list), "registry admissions missing")
    require(all(isinstance(item, dict) for item in admissions), "registry contains invalid admission")
    count = registry.get("admittedRehearsalCount")
    require(isinstance(count, int) and not isinstance(count, bool), "admittedRehearsalCount must be an integer")
    require(count == len(admissions), "admittedRehearsalCount drift")
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


def main() -> int:
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

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("migration production admission registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["admissionId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        admissions = registry["admissions"]
        require(all(item.get("admissionId") != record["admissionId"] for item in admissions), "admissionId already registered")
        require(all(item.get("migrationRunId") != record["migrationRunId"] for item in admissions), "migrationRunId already admitted")
        admissions.append(record)
        registry["admittedRehearsalCount"] = len(admissions)
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        atomic_write(registry)
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
