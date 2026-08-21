#!/usr/bin/env python3
"""Fail-closed validation for the local PostgreSQL logical restore drill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_REAL = ROOT.resolve()
CONTRACT_PATH = ROOT / "contracts/operations/local-logical-restore-contract.v1.json"
MIGRATION_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
EXPECTED_EVIDENCE = {
    "contracts/operations/local-logical-restore-contract.v1.json",
    "scripts/run-memory-os-local-logical-restore.sh",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/reconcile-memory-os-local-logical-restore.py",
    ".github/workflows/local-logical-restore.yml",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
MIGRATION_PREFIX_RE = re.compile(r"^[0-9]+_")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def require_repo_regular_file(path: Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValidationFailure(f"{label} escapes repository root") from exc
    require(relative != Path("."), f"{label} cannot resolve to repository root")
    current = ROOT
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), f"{label} uses symlink component: {relative.as_posix()}")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ValidationFailure(f"{label} is missing or unreadable: {relative.as_posix()}") from exc
    try:
        resolved.relative_to(ROOT_REAL)
    except ValueError as exc:
        raise ValidationFailure(f"{label} resolves outside repository root: {relative.as_posix()}") from exc
    require(resolved.is_file(), f"{label} must be a regular file: {relative.as_posix()}")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def validate_result(result: dict[str, Any], expected_sha: str | None,
                    migration_count: int, sql_test_count: int) -> None:
    require(result.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "logical restore result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "logical restore result requires a full source commit SHA")
    require(source_is_ancestor(commit_sha),
            "logical restore result source is not an ancestor of current HEAD")
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
            "not every canonical SQL integration test was executed")
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
        "expiredSyntheticSessionsResolvedAfterRestore",
        "revokedSyntheticSessionsResolvedAfterRestore",
    ):
        require(assertions.get(field) == 0,
                f"synthetic session/deletion state became usable after restore: {field}")
    require(assertions.get("expiredSyntheticSessionRowsAfterRestore") == 1,
            "expired synthetic session state was not preserved after restore")
    require(assertions.get("revokedSyntheticSessionRowsAfterRestore") == 1,
            "revoked synthetic session state was not preserved after restore")

    limitations = result.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 5,
            "result limitations must remain explicit")
    joined = "\n".join(str(item) for item in limitations)
    for phrase in (
        "same PostgreSQL cluster",
        "not PITR",
        "not object-store",
        "not approved RPO or RTO",
        "expired/revoked session",
    ):
        require(phrase in joined, f"result limitation omitted: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password", "pgpassword",
        "dddddddddddddddddddddddddddddddd", "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "ffffffffffffffffffffffffffffffff", "acct_restore_deleted_0001",
        "acct_restore_session_owner_0001", "ses_restore_deleted_0001",
        "ses_restore_expired_0001", "ses_restore_revoked_0001",
    ):
        require(forbidden not in serialized,
                f"result contains forbidden evidence value: {forbidden}")


def main() -> int:
    for path, label in (
        (CONTRACT_PATH, "logical restore contract"),
        (MIGRATION_PATH, "migration lifecycle authority"),
        (STATUS_PATH, "production operability status"),
    ):
        require_repo_regular_file(path, label)

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
    require(contract.get("workflow") == ".github/workflows/local-logical-restore.yml",
            "workflow path drift")
    require(contract.get("reconcile") ==
            "scripts/reconcile-memory-os-local-logical-restore.py",
            "reconcile path drift")
    require(contract.get("resultPath") ==
            "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
            "result path drift")
    require(contract.get("diagnosticPath") ==
            "docs/fixtures/memory-os-operability/local-logical-restore-diagnostic.last.json",
            "diagnostic path drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
            "dependency mode drift")

    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "scenario must be an object")
    require(scenario.get("scenarioId") ==
            "postgresql-logical-dump-isolated-restore-smoke",
            "contract scenario ID drift")
    for field, minimum in (("requiredSteps", 14), ("successCriteria", 11),
                           ("abortCriteria", 6)):
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
    scope = str(boundary.get("deletionNonResurrectionScope"))
    for phrase in ("synthetic", "expired", "revoked", "non-resolvable"):
        require(phrase in scope,
                f"non-resurrection scope must include {phrase}")

    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "privacy must be an object")
    for flag in (
        "syntheticDataOnly", "rawDatabaseUrlInEvidenceForbidden",
        "passwordInEvidenceForbidden", "tokenDigestValueInEvidenceForbidden",
        "userContentForbidden", "databaseIdentityStoredAsDigestOnly",
    ):
        require(privacy.get(flag) is True, f"privacy.{flag} must be true")

    migration_sequence = migration.get("migrationSequence")
    require(isinstance(migration_sequence, list) and migration_sequence,
            "canonical migration sequence is invalid")
    migration_count = len(migration_sequence)
    sql_tests: list[Path] = []
    for filename in migration_sequence:
        migration_file = ROOT / "infra/postgresql/security" / filename
        require_repo_regular_file(migration_file, f"canonical migration {filename}")
        test_filename = "test_" + MIGRATION_PREFIX_RE.sub("", filename)
        test_file = ROOT / "infra/postgresql/security" / test_filename
        require_repo_regular_file(test_file, f"canonical SQL test {test_filename}")
        sql_tests.append(test_file)
    require(len(sql_tests) == migration_count,
            "canonical SQL test count must match migration count")
    require(sql_tests[0].name == "test_memory_os_import_rls.sql",
            "test helper bootstrap must execute first")

    runner_path = ROOT / contract["runner"]
    require_repo_regular_file(runner_path, "logical restore runner")
    runner = runner_path.read_text(encoding="utf-8")
    for snippet in (
        "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP",
        'case "$PGHOST" in',
        "pg_dump --format=custom",
        "pg_restore --exit-on-error",
        "relation.relforcerowsecurity = true",
        "SET ROLE memory_auth_runtime",
        'test_name="test_${migration#*_}"',
        "SQL integration test count does not match migration count",
        "synthetic deletion did not complete before dump",
        "expired/revoked synthetic session setup is invalid before dump",
        "deleted synthetic account resurrected",
        "expired synthetic token resolved after restore",
        "revoked synthetic token resolved after restore",
        "MEMORY_OS_COMMIT_SHA must be a full commit SHA",
    ):
        require(snippet in runner, f"runner missing safety/evidence boundary: {snippet}")
    require("find \"$MIGRATION_DIR\"" not in runner,
            "runner must not derive SQL test order from filename sorting")
    for dangerous in (
        "--clean --create", "DROP DATABASE postgres", "PGPASSWORD=postgres://",
    ):
        require(dangerous not in runner, f"runner contains dangerous pattern: {dangerous}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "exactSourcePassResultTrackedInStatus",
        "expiredRevokedSessionChecksImplemented",
    ):
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
        require_repo_regular_file(ROOT / ref, f"logical restore evidence ref {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source logical restore result is missing")
    if RESULT_PATH.is_file():
        require_repo_regular_file(RESULT_PATH, "logical restore result")
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
    print("expired/revoked session proof required: true")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOCAL LOGICAL RESTORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
