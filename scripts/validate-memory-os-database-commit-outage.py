#!/usr/bin/env python3
"""Fail-closed validation for the local database commit outage drill."""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/database-commit-outage-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("non-finite database outage JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite database outage JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate database outage JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    """Admit only regular, unambiguous JSON inside the repository."""
    require(isinstance(path, Path), "database outage JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "database outage JSON symlink rejected")
    require(path.is_file(), "database outage JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise ValidationFailure("database outage JSON path escaped repository") from None
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError):
        raise ValidationFailure("database outage JSON unreadable or invalid") from None
    require(isinstance(value, dict), "database outage JSON root must be an object")
    return value

def strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> str:
    require(result.get("schemaVersion") == "memory-os-database-commit-outage-results.v1",
            "database outage result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "database outage result commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"database outage result SHA {commit_sha} != expected {expected_sha}")
    environment = result.get("environment")
    require(isinstance(environment, dict), "database outage result environment missing")
    require(environment.get("mode") ==
            "GITHUB_ACTIONS_UBUNTU_POSTGRES16_MINIO_UNREACHABLE_COMMIT_POOL",
            "database outage environment mode drift")
    require(environment.get("productionEvidence") is False,
            "database outage result cannot claim production evidence")
    require(environment.get("containsSecrets") is False,
            "database outage result must state containsSecrets false")
    require(environment.get("syntheticDataOnly") is True,
            "database outage result must use synthetic data only")
    require(result.get("result") == "PASS", "database outage drill result is not PASS")
    require(result.get("integrityResult") == "PASS",
            "database outage drill integrity is not PASS")
    require(result.get("exitCode") == 0, "database outage drill exitCode is not zero")
    duration = result.get("durationSeconds")
    require(isinstance(duration, (int, float)) and not isinstance(duration, bool),
            "database outage duration is invalid")
    try:
        finite_duration = math.isfinite(float(duration))
    except (OverflowError, ValueError):
        finite_duration = False
    require(finite_duration and duration >= 0, "database outage duration is invalid")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "database outage assertions missing")

    common = {
        "previewRowsDuringOutage": 0,
        "jobStateDuringOutage": "preview_building",
        "sealedSpoolEntriesAfterFailure": 1,
        "previewRowsAfterRecovery": 1,
        "candidateRowsAfterRecovery": 2,
        "rejectionRowsAfterRecovery": 1,
        "sameSourceAndPreviewIdReused": True,
        "recoveryMarkedAsReplay": False,
    }
    for field, value in common.items():
        require(assertions.get(field) == value,
                f"database outage assertion failed: {field}")

    modern = (
        assertions.get("sameSpoolIdReused") is True and
        assertions.get("resumeWithoutObjectStore") is True and
        assertions.get("resumeWithoutParser") is True
    )
    limitations = strings(result.get("limitations"), "result.limitations", 6)
    joined = "\n".join(limitations)
    if modern:
        for phrase in (
            "not PostgreSQL process loss",
            "not replication failover",
            "same sealed spool",
            "ephemeral PostgreSQL 16 and MinIO",
            "host restart not executed",
            "not production chaos evidence",
        ):
            require(phrase in joined, f"database outage limitation omitted: {phrase}")
        generation = "SAME_SEALED_SPOOL_RESUME"
    else:
        require(expected_sha is None,
                "legacy new-spool result cannot satisfy an exact-source same-spool validation")
        require(assertions.get("newSpoolAttemptUsed") is True,
                "database outage result is neither legacy nor same-spool format")
        for phrase in (
            "not PostgreSQL process loss",
            "not replication failover",
            "new spool attempt",
            "ephemeral PostgreSQL 16 and MinIO",
            "not production chaos evidence",
        ):
            require(phrase in joined, f"legacy database outage limitation omitted: {phrase}")
        generation = "LEGACY_NEW_SPOOL_ATTEMPT"

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "minio_root_password",
        "objectversionid", "spoolpath", "secretaccesskey", "user content",
    ):
        require(forbidden not in serialized,
                f"database outage result contains forbidden value: {forbidden}")
    return generation


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-database-commit-outage.v1",
            "database outage contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-database-commit-outage-results.v1",
            "database outage results schemaVersion drift")
    require(contract.get("runnerCommand") ==
            "go test ./internal/importflow -run ^TestFlowRecoversAfterDatabaseCommitOutage$ -count=1",
            "database outage runner command drift")
    require(contract.get("workingDirectory") == "services/import-api",
            "database outage workingDirectory drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-database-commit-outage.py",
            "database outage validator path drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_MINIO_WITH_UNREACHABLE_COMMIT_POOL",
            "database outage dependency mode drift")
    assertions = strings(contract.get("requiredAssertions"), "requiredAssertions", 8)
    require(any("same request" in value and "spool ID" in value for value in assertions),
            "contract must bind recovery to the exact same request/spool")
    require(any("object storage" in value and "parser" in value for value in assertions),
            "contract must prove object/parser-independent resume")
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "database outage privacy must be an object")
    require(privacy.get("productionEvidence") is False,
            "database outage contract cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "databaseUrlInEvidenceForbidden",
        "credentialsInEvidenceForbidden", "objectKeyOrVersionInEvidenceForbidden",
        "spoolPathInEvidenceForbidden", "userContentInEvidenceForbidden",
    ):
        require(privacy.get(flag) is True, f"database outage privacy.{flag} must be true")
    strings(contract.get("limitations"), "limitations", 6)
    test_path = ROOT / "services/import-api/internal/importflow/database_outage_drill_linux_test.go"
    require(test_path.is_file(), "database outage Go test missing")
    source = test_path.read_text(encoding="utf-8")
    for snippet in (
        "127.0.0.1:1", "ConnectTimeout", "assertNothingImported",
        "sealed spool evidence", "healthyCommitter", "ResumeCommit",
        "env.flow.Objects = nil", "env.flow.Supervisor = nil",
    ):
        require(snippet in source, f"database outage test missing boundary: {snippet}")
    resume_path = ROOT / "services/import-api/internal/importflow/resume.go"
    require(resume_path.is_file(), "ResumeCommit implementation missing")
    resume = resume_path.read_text(encoding="utf-8")
    for snippet in (
        "func (f *Flow) ResumeCommit", "verifier.Verify", "CollectSealedRecords",
        "decodeCommitRows", "f.Committer.Commit",
    ):
        require(snippet in resume, f"ResumeCommit missing boundary: {snippet}")
    require("f.Objects" not in resume and "f.Supervisor" not in resume,
            "ResumeCommit must not depend on object storage or parser supervisor")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "database outage readiness must be an object")
    for foundation in (
        "contractDefined", "testImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "sameSealedSpoolCommitResumeImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"database outage readiness.{foundation} must be true")
    for unproven in (
        "databaseProcessLossExecuted", "replicationFailoverExecuted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven database outage readiness cannot be true: {unproven}")
    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 8)
    for ref in refs:
        require((ROOT / ref).is_file(), f"database outage evidence missing: {ref}")
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source database outage result is missing")
    generation = "ABSENT"
    for candidate in (RESULT_PATH, *RESULT_PATH.parents):
        require(not candidate.is_symlink(), "database outage result symlink rejected")
    if RESULT_PATH.is_file():
        generation = validate_result(load(RESULT_PATH), expected_sha)
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "database outage CI evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") != "READY",
            "local database outage drill cannot make OPS-P0-009 READY")
    print("Memory OS database commit outage validation PASS")
    print(f"result present: {RESULT_PATH.is_file()}")
    print(f"result generation: {generation}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"DATABASE COMMIT OUTAGE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
