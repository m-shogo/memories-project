#!/usr/bin/env python3
"""Fail-closed validation for the local PostgreSQL logical restore drill."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/local-logical-restore-contract.v1.json"
MIGRATION_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
EXPECTED_EVIDENCE = {
    "contracts/operations/local-logical-restore-contract.v1.json",
    "scripts/run-memory-os-local-logical-restore.sh",
    "scripts/validate-memory-os-local-logical-restore.py",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None,
                    migration_count: int, sql_test_count: int) -> None:
    require(result.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "logical restore result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "logical restore result requires a full source commit SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"logical restore result SHA {commit_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment must be an object")
    require(environment.get("databaseMode") ==
            "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
            "result database mode drift")
    require(environment.get("productionEvidence") is False,
            "local logical restore cannot be production evidence")
    require(environment.get("containsSecrets") is False,
            "result must state that it contains no secrets")
    digest = environment.get("databaseIdentityDigest")
    require(isinstance(digest, str) and DIGEST_RE.fullmatch(digest) is not None,
            "database identity must be a SHA-256 digest")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "result scenario must be an object")
    require(scenario.get("scenarioId") ==
            "postgresql-logical-dump-isolated-restore-smoke",
            "scenario ID drift")
    require(scenario.get("result") == "PASS", "logical restore result is not PASS")
    require(scenario.get("integrityResult") == "PASS",
            "logical restore integrity is not PASS")
    require(scenario.get("migrationFilesApplied") == migration_count,
            "not every canonical migration was applied")
    require(scenario.get("sqlIntegrationTestsExecuted") == sql_test_count,
            "not every SQL integration test was executed")
    require(isinstance(scenario.get("durationSeconds"), int) and
            scenario["durationSeconds"] >= 0,
            "result duration is invalid")
    require(isinstance(scenario.get("dumpBytes"), int) and scenario["dumpBytes"] > 0,
            "logical dump size is invalid")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "result assertions must be an object")
    require(assertions.get("runtimeRolesWithoutBypassRls") == 4,
            "runtime role/BYPASSRLS assertion failed")
    require(isinstance(assertions.get("forceRlsTables"), int) and
            assertions["forceRlsTables"] > 0,
            "FORCE RLS assertion failed")
    for field in (
        "deletedSyntheticAccountsAfterRestore",
        "deletedSyntheticSessionDigestsAfterRestore",
        "deletedSyntheticSessionsResolvedAfterRestore",
    ):
        require(assertions.get(field) == 0,
                f"synthetic deleted state resurrected: {field}")

    limitations = result.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 5,
            "result limitations must remain explicit")
    joined = "\n".join(str(item) for item in limitations)
    for phrase in (
        "same PostgreSQL cluster",
        "not PITR",
        "not object-store",
        "not approved RPO or RTO",
        "synthetic deletion",
    ):
        require(phrase in joined, f"result limitation omitted: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password", "pgpassword",
        "dddddddddddddddddddddddddddddddd", "acct_restore_deleted_0001",
        "ses_restore_deleted_0001",
    ):
        require(forbidden not in serialized,
                f"result contains forbidden evidence value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    migration = load(MIGRATION_PATH)
    require(contract.get("schemaVersion") == "memory-os-local-logical-restore.v1",
            "logical restore contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-local-logical-restore-results.v1",
            "logical restore results schemaVersion drift")
    require(contract.get("sourceMigrationContract") ==
            "contracts/operations/migration-lifecycle-contract.v1.json",
            "source migration contract drift")
    require(contract.get("runner") ==
            "scripts/run-memory-os-local-logical-restore.sh",
            "runner path drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-local-logical-restore.py",
            "validator path drift")
    require(contract.get("resultPath") ==
            "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
            "result path drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
            "dependency mode drift")

    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "scenario must be an object")
    require(scenario.get("scenarioId") ==
            "postgresql-logical-dump-isolated-restore-smoke",
            "contract scenario ID drift")
    for field, minimum in (("requiredSteps", 10), ("successCriteria", 8),
                           ("abortCriteria", 5)):
        items = scenario.get(field)
        require(isinstance(items, list) and len(items) >= minimum,
                f"scenario.{field} is incomplete")
        require(len(items) == len(set(items)), f"scenario.{field} contains duplicates")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be an object")
    for false_claim in (
        "productionEvidence", "pitrEvidence", "physicalBackupEvidence",
        "crossClusterEvidence", "objectStoreRestoreEvidence",
        "rpoMeasured", "rtoMeasured",
    ):
        require(boundary.get(false_claim) is False,
                f"local restore cannot claim {false_claim}")
    require("synthetic" in str(boundary.get("deletionNonResurrectionScope")),
            "non-resurrection scope must remain synthetic")

    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "privacy must be an object")
    for flag in (
        "syntheticDataOnly", "rawDatabaseUrlInEvidenceForbidden",
        "passwordInEvidenceForbidden", "tokenDigestValueInEvidenceForbidden",
        "userContentForbidden", "databaseIdentityStoredAsDigestOnly",
    ):
        require(privacy.get(flag) is True, f"privacy.{flag} must be true")

    runner_path = ROOT / contract["runner"]
    require(runner_path.is_file(), "logical restore runner missing")
    runner = runner_path.read_text(encoding="utf-8")
    for snippet in (
        "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP",
        'case "$PGHOST" in',
        "pg_dump --format=custom",
        "pg_restore --exit-on-error",
        "relation.relforcerowsecurity = true",
        "SET ROLE memory_auth_runtime",
        "test_memory_os_*.sql",
        "synthetic deletion did not complete before dump",
        "deleted synthetic account resurrected",
        "deleted synthetic session digest resurrected",
        "MEMORY_OS_COMMIT_SHA must be a full commit SHA",
    ):
        require(snippet in runner, f"runner missing safety/evidence boundary: {snippet}")
    for dangerous in (
        "--clean --create", "DROP DATABASE postgres", "PGPASSWORD=postgres://",
    ):
        require(dangerous not in runner, f"runner contains dangerous pattern: {dangerous}")

    migration_sequence = migration.get("migrationSequence")
    require(isinstance(migration_sequence, list) and migration_sequence,
            "canonical migration sequence is invalid")
    migration_count = len(migration_sequence)
    for filename in migration_sequence:
        require((ROOT / "infra/postgresql/security" / filename).is_file(),
                f"canonical migration missing: {filename}")
    sql_tests = sorted((ROOT / "infra/postgresql/security").glob("test_memory_os_*.sql"))
    require(sql_tests, "no SQL integration tests found")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in ("contractDefined", "runnerImplemented", "validatorImplemented"):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "productionBackupConfigured", "pitrConfigured",
        "independentObjectRetentionConfigured", "crossClusterRestoreCompleted",
        "rpoRtoApprovedAndMeasured", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven restore readiness cannot be true: {unproven}")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "logical restore evidenceRefs invalid")
    require(set(refs) == EXPECTED_EVIDENCE, f"evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source logical restore result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha, migration_count, len(sql_tests))

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "local restore cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "local same-cluster logical restore cannot make OPS-P0-007 READY")

    print("Memory OS local logical restore validation PASS")
    print(f"canonical migrations: {migration_count}  SQL integration tests: {len(sql_tests)}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print(f"OPS-P0-007 status: {matches[0].get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOCAL LOGICAL RESTORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
