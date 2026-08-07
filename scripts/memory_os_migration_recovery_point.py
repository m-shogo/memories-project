#!/usr/bin/env python3
"""Shared fail-closed recovery-point validation for migration rehearsal evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECOVERY_REF = re.compile(r"^sha256:([0-9a-f]{64})$")
RUN_ID = re.compile(r"^mig_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")


class RecoveryPointFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryPointFailure(message)


def load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RecoveryPointFailure(f"cannot load {label} {path}: {exc}") from exc
    require(isinstance(value, dict), f"{label} root must be object: {path}")
    return value


def safe_relative_ref(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value, f"{field} is required")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts,
            f"{field} must be a safe repository-relative path")
    return relative


def validate_actual_recovery_artifact_result(
    record: dict[str, Any],
    environment_class: str,
    canonical_migrations: list[str],
    registry_contract: dict[str, Any],
    artifact_digest: str,
) -> None:
    authorities = registry_contract.get("actualRecoveryArtifactAuthorities")
    require(isinstance(authorities, dict), "actualRecoveryArtifactAuthorities must be object")
    authority = authorities.get(environment_class)
    require(isinstance(authority, dict),
            f"actual recovery artifact authority missing for {environment_class}")

    if environment_class != "LOCAL_POSTGRES_REHEARSAL":
        raise RecoveryPointFailure(
            "production-equivalent migration rehearsal cannot register until an environment-specific actual recovery-artifact authority is configured"
        )

    evidence_root_raw = authority.get("evidenceRoot")
    require(isinstance(evidence_root_raw, str) and evidence_root_raw,
            "local actual recovery evidence root is not configured")
    evidence_root = (ROOT / evidence_root_raw).resolve()
    run_id = record.get("migrationRunId")
    require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id) is not None,
            "migrationRunId invalid for recovery artifact linkage")
    restore_ref = safe_relative_ref(
        record.get("recoveryPointRestoreEvidenceRef"),
        "recoveryPointRestoreEvidenceRef",
    )
    restore_path = (ROOT / restore_ref).resolve()
    require(restore_path.is_relative_to(evidence_root),
            "recoveryPointRestoreEvidenceRef must remain inside configured evidence root")
    require(restore_path.name == f"{run_id}.json",
            "recoveryPointRestoreEvidenceRef filename must match migrationRunId")
    require(restore_path.is_file(),
            f"actual recovery artifact restore evidence missing: {restore_ref}")
    result = load(restore_path, "actual recovery artifact restore evidence")

    require(result.get("schemaVersion") == authority.get("schemaVersion"),
            "actual recovery artifact result schemaVersion drift")
    require(result.get("migrationRunId") == run_id,
            "actual recovery artifact result migrationRunId mismatch")
    require(result.get("commitSha") == record.get("sourceCommitSha"),
            "actual recovery artifact result source SHA mismatch")
    require(result.get("environmentClass") == environment_class,
            "actual recovery artifact result environmentClass mismatch")
    require(result.get("migrationUnderTest") == canonical_migrations[-1],
            "actual recovery artifact result migration-under-test is stale")
    require(result.get("baselineMigrationCount") == len(canonical_migrations) - 1,
            "actual recovery artifact baseline migration count is stale")
    require(result.get("finalMigrationCount") == len(canonical_migrations),
            "actual recovery artifact final migration count is stale")
    require(result.get("sqlIntegrationTestsExecutedAfterRecovery") == len(canonical_migrations),
            "actual recovery artifact SQL suite count is stale")
    artifact = result.get("recoveryArtifact")
    require(isinstance(artifact, dict), "actual recovery artifact result lacks recoveryArtifact")
    require(artifact.get("sha256") == artifact_digest,
            "actual restored artifact digest does not match migration record")
    require(artifact.get("reference") == "sha256:" + artifact_digest,
            "actual restored artifact reference does not match migration record")
    require(isinstance(artifact.get("bytes"), int) and artifact["bytes"] > 0,
            "actual restored artifact byte count invalid")
    require(artifact.get("rawArtifactCommitted") is False,
            "raw migration recovery artifact must not be committed")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "actual recovery artifact assertions missing")
    for flag in (
        "sourceBaselineApplied",
        "recoveryArtifactDigestRecorded",
        "migrationAppliedOnSource",
        "migrationSpecificSourceTestPassed",
        "exactRecoveryArtifactRestored",
        "preMigrationSurfaceRecovered",
        "migrationReappliedAfterRestore",
        "canonicalSqlSuitePassedAfterRecovery",
        "actualRecoveryArtifactRestored",
    ):
        require(assertions.get(flag) is True,
                f"actual recovery artifact assertion not proven: {flag}")
    for flag in ("containsSecrets", "productionTraffic", "productionCredentials", "productionEvidence"):
        require(assertions.get(flag) is False,
                f"actual recovery artifact non-production boundary drift: {flag}")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "actual recovery artifact result/integrity must PASS")
    require(authority.get("productionEvidenceRequired") is False,
            "local actual recovery authority cannot require production evidence")


def validate_recovery_point(
    record: dict[str, Any],
    environment_class: str,
    canonical_migrations: list[str],
    registry_contract: dict[str, Any],
) -> None:
    reference = record.get("recoveryPointReference")
    require(isinstance(reference, str), "recoveryPointReference must be string")
    match = RECOVERY_REF.fullmatch(reference)
    require(match is not None, "recoveryPointReference must be sha256:<64 lowercase hex>")
    artifact_digest = record.get("recoveryPointArtifactDigest")
    require(isinstance(artifact_digest, str) and SHA256.fullmatch(artifact_digest) is not None,
            "recoveryPointArtifactDigest must be SHA-256")
    require(match.group(1) == artifact_digest,
            "recoveryPointReference and recoveryPointArtifactDigest must identify the same artifact")
    require(record.get("recoveryPointVerified") is True,
            "recoveryPointVerified must be true")
    require(record.get("restoreCapabilityVerified") is True,
            "restoreCapabilityVerified must be true")

    authorities = registry_contract.get("restoreCapabilityAuthorities")
    require(isinstance(authorities, dict), "restoreCapabilityAuthorities must be object")
    authority = authorities.get(environment_class)
    require(isinstance(authority, dict),
            f"restore capability authority missing for {environment_class}")
    require(authority.get("configured") is True,
            f"restore capability is not configured for {environment_class}")
    evidence_ref = authority.get("evidenceRef")
    require(isinstance(evidence_ref, str) and evidence_ref,
            f"restore capability evidenceRef missing for {environment_class}")
    require(record.get("restoreCapabilityEvidenceRef") == evidence_ref,
            "restoreCapabilityEvidenceRef does not match environment authority")
    evidence_path = ROOT / evidence_ref
    require(evidence_path.is_file(), f"restore capability evidence missing: {evidence_ref}")
    evidence = load(evidence_path, "restore capability evidence")

    expected_schema = authority.get("schemaVersion")
    require(isinstance(expected_schema, str) and evidence.get("schemaVersion") == expected_schema,
            "restore capability schemaVersion drift")
    require(authority.get("productionEvidenceRequired") is False,
            "non-production migration registry cannot require production restore evidence")

    if environment_class == "LOCAL_POSTGRES_REHEARSAL":
        environment = evidence.get("environment")
        scenario = evidence.get("scenario")
        require(isinstance(environment, dict) and environment.get("productionEvidence") is False,
                "local restore capability must remain non-production")
        require(isinstance(scenario, dict), "local restore scenario missing")
        require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS",
                "local restore capability must PASS integrity")
        require(scenario.get("migrationFilesApplied") == len(canonical_migrations),
                "local restore capability migration count is stale")
        assertions = scenario.get("assertions")
        require(isinstance(assertions, dict), "local restore assertions missing")
        require(assertions.get("deletedSyntheticAccountsAfterRestore") == 0,
                "local restore resurrected deleted synthetic account")
        require(assertions.get("deletedSyntheticSessionsResolvedAfterRestore") == 0,
                "local restore resolved a deleted synthetic session")
    else:
        raise RecoveryPointFailure(
            "production-equivalent migration rehearsal cannot register until an environment-specific restore capability authority is configured"
        )

    validate_actual_recovery_artifact_result(
        record,
        environment_class,
        canonical_migrations,
        registry_contract,
        artifact_digest,
    )
