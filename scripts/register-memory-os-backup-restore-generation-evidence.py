#!/usr/bin/env python3
"""Append one reviewed generation-bound backup/restore evidence record."""

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
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_ID = re.compile(r"^brge_[a-z0-9][a-z0-9_-]{7,63}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def repo_ref(value: Any, field: str, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    require(isinstance(value, str) and value and not Path(value).is_absolute(), f"{field} invalid")
    path = Path(value)
    require(".." not in path.parts and (ROOT / path).is_file(), f"{field} evidence path missing")
    return value


def generation_by_id(generations: list[Any], generation_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(generation_id, str) and generation_id, f"{field} required")
    matches = [row for row in generations if isinstance(row, dict) and row.get("generationId") == generation_id]
    require(len(matches) == 1, f"{field} is not a unique registered generation")
    return matches[0]


def candidate(record: dict[str, Any]) -> bool:
    return (
        record.get("evidenceComplete") is True
        and record.get("isolatedRestoreVerified") is True
        and record.get("postgresPitrVerified") is True
        and record.get("independentObjectRetentionVerified") is True
        and record.get("tlsVerified") is True
        and record.get("restoreOnlyCredentialSeparationVerified") is True
        and record.get("databaseObjectRecoveryCoherenceVerified") is True
        and record.get("nonResurrectionVerification") == "PASS"
        and isinstance(record.get("approvedRecoveryObjectivesRef"), str)
        and isinstance(record.get("measuredRpoSeconds"), int)
        and isinstance(record.get("measuredRtoSeconds"), int)
        and isinstance(record.get("securityReviewRef"), str)
        and isinstance(record.get("operabilityReviewRef"), str)
        and record.get("securityReviewRef") != record.get("operabilityReviewRef")
        and not record.get("unresolvedFindings")
    )


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("evidenceId"), str) and EVIDENCE_ID.fullmatch(record["evidenceId"]), "evidenceId invalid")
    source_commit = record.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source_commit + "^{commit}") == "", "sourceCommitSha does not exist")

    generation_registry = load(GEN_REGISTRY)
    generations = generation_registry.get("generations")
    require(isinstance(generations, list) and generations, "no production-equivalent environment generation is registered")
    source_generation = generation_by_id(generations, record.get("sourceEnvironmentGenerationId"), "sourceEnvironmentGenerationId")
    target_generation = generation_by_id(generations, record.get("restoreTargetGenerationId"), "restoreTargetGenerationId")
    require(record.get("sourceEnvironmentManifestSha256") == source_generation.get("environmentManifestSha256"), "source environment manifest digest mismatch")
    require(record.get("restoreTargetManifestSha256") == target_generation.get("environmentManifestSha256"), "restore target manifest digest mismatch")
    require(source_commit == target_generation.get("sourceCommitSha"), "sourceCommitSha must match restore target generation source commit")

    for field in (
        "sourceEnvironmentManifestSha256", "restoreTargetManifestSha256", "backupArtifactSha256",
        "backupManifestSha256", "databaseRecoveryPointDigest", "objectRecoveryPointDigest",
        "restoreEvidenceBundleSha256", "restoredBackupArtifactSha256",
    ):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} invalid")
    require(record["restoredBackupArtifactSha256"] == record["backupArtifactSha256"], "restore must reference the exact backup artifact digest")

    for field in (
        "isolatedRestoreVerified", "postgresPitrVerified", "independentObjectRetentionVerified", "tlsVerified",
        "restoreOnlyCredentialSeparationVerified", "databaseObjectRecoveryCoherenceVerified", "evidenceComplete",
    ):
        require(isinstance(record.get(field), bool), f"{field} must be boolean")
    require(record.get("nonResurrectionVerification") in {"PASS", "FAIL", "NOT_RUN"}, "nonResurrectionVerification invalid")

    objectives_ref = repo_ref(record.get("approvedRecoveryObjectivesRef"), "approvedRecoveryObjectivesRef", required=False)
    rpo = record.get("measuredRpoSeconds")
    rto = record.get("measuredRtoSeconds")
    if objectives_ref is None:
        require(rpo is None and rto is None, "RPO/RTO measurements cannot satisfy admission without approved recovery objectives")
    else:
        require(isinstance(rpo, int) and not isinstance(rpo, bool) and rpo >= 0, "measuredRpoSeconds invalid")
        require(isinstance(rto, int) and not isinstance(rto, bool) and rto >= 0, "measuredRtoSeconds invalid")

    source_id = record["sourceEnvironmentGenerationId"]
    target_id = record["restoreTargetGenerationId"]
    material_ref = repo_ref(record.get("materialDeltaReviewRef"), "materialDeltaReviewRef", required=False)
    if source_id != target_id:
        require(material_ref is not None, "cross-generation restore requires materialDeltaReviewRef")
    security_ref = repo_ref(record.get("securityReviewRef"), "securityReviewRef", required=False)
    operability_ref = repo_ref(record.get("operabilityReviewRef"), "operabilityReviewRef", required=False)
    if security_ref is not None and operability_ref is not None:
        require(security_ref != operability_ref, "security and operability reviews must be distinct")

    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL findings block registry admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}] status invalid")

    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password",
        "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@", "latest",
    ):
        require(forbidden not in serialized, f"record contains forbidden recovery material: {forbidden}")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".backup-restore-generation.", suffix=".tmp", dir=REGISTRY.parent)
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
    input_path = Path(args.record).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input recovery evidence record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    validate_record(record)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("backup/restore generation evidence registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["evidenceId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        require(registry.get("appendOnly") is True, "registry must remain append-only")
        rows = registry.get("records")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry records invalid")
        require(all(row.get("evidenceId") != record["evidenceId"] for row in rows), "evidenceId already registered")
        rows.append(record)
        registry["registeredEvidenceCount"] = len(rows)
        registry["completeGenerationBoundBackupCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True)
        registry["completeGenerationBoundRestoreCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True and row.get("isolatedRestoreVerified") is True and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256"))
        registry["productionEquivalentRecoveryCandidateCount"] = sum(1 for row in rows if candidate(row))
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        registry["limitations"] = [
            "generation-bound recovery evidence remains non-production evidence",
            "production-equivalent recovery candidates require all fail-closed controls and independent reviews",
            "this registry never establishes application production readiness"
        ]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered generation-bound backup/restore evidence: {record['evidenceId']}")
    print(f"production-equivalent recovery candidate: {str(candidate(record)).lower()}")
    print("production evidence: false")
    print("application production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
