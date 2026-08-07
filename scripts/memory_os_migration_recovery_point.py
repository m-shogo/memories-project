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


class RecoveryPointFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryPointFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RecoveryPointFailure(f"cannot load recovery capability evidence {path}: {exc}") from exc
    require(isinstance(value, dict), f"recovery capability evidence root must be object: {path}")
    return value


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
    evidence = load(evidence_path)

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
