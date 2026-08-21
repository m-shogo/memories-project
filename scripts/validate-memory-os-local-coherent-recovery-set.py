#!/usr/bin/env python3
"""Fail-closed validator for the local PostgreSQL + MinIO coherent recovery-set drill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
ROOT_REAL = ROOT.resolve()
CONTRACT_PATH = ROOT / "contracts/operations/local-coherent-recovery-set-contract.v1.json"
MIGRATION_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_REFS = {
    "contracts/operations/local-coherent-recovery-set-contract.v1.json",
    "scripts/run-memory-os-local-coherent-recovery-set.py",
    "scripts/validate-memory-os-local-coherent-recovery-set.py",
    ".github/workflows/local-coherent-recovery-set.yml",
    "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_repo_regular_file(path: Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise Fail(f"{label} escapes repository root") from exc
    require(relative != Path("."), f"{label} cannot resolve to repository root")
    current = ROOT
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), f"{label} uses symlink component: {relative.as_posix()}")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise Fail(f"{label} is missing or unreadable: {relative.as_posix()}") from exc
    try:
        resolved.relative_to(ROOT_REAL)
    except ValueError as exc:
        raise Fail(f"{label} resolves outside repository root: {relative.as_posix()}") from exc
    require(resolved.is_file(), f"{label} must be a regular file: {relative.as_posix()}")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA40.fullmatch(value) is None:
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


def validate_result(result: dict[str, Any], expected_sha: str | None, migration_count: int) -> None:
    require(result.get("schemaVersion") == "memory-os-local-coherent-recovery-set-results.v1", "result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA40.fullmatch(commit_sha), "result commitSha invalid")
    require(source_is_ancestor(commit_sha), "coherent recovery result source is not an ancestor of current HEAD")
    if expected_sha:
        require(commit_sha == expected_sha, "coherent recovery result is not exact-source")
    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment missing")
    require(environment.get("dependencyMode") == "EPHEMERAL_POSTGRESQL_16_PLUS_LOCAL_MINIO_COHERENT_RECOVERY_SET", "dependency mode drift")
    for key in ("productionTraffic", "productionCredentials", "productionEvidence", "containsSecrets"):
        require(environment.get(key) is False, f"result boundary drift: {key}")
    for field in ("databaseEndpointDigest", "objectEndpointDigest"):
        require(isinstance(environment.get(field), str) and DIGEST.fullmatch(environment[field]), f"{field} invalid")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario missing")
    require(scenario.get("scenarioId") == "postgres-object-shared-recovery-set-local", "scenario ID drift")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "scenario is not PASS")
    require(scenario.get("migrationFilesApplied") == migration_count, "canonical migration coverage drift")
    require(isinstance(scenario.get("databaseDumpBytes"), int) and scenario["databaseDumpBytes"] > 0, "database dump size invalid")
    for field in (
        "recoverySetDigest", "databaseRecoverySetDigest", "objectRecoverySetDigest",
        "objectChecksumSha256", "sourceObjectVersionDigest", "backupObjectVersionDigest",
        "restoreObjectVersionDigest",
    ):
        require(isinstance(scenario.get(field), str) and DIGEST.fullmatch(scenario[field]), f"scenario digest invalid: {field}")
    recovery = scenario["recoverySetDigest"]
    require(scenario["databaseRecoverySetDigest"] == recovery, "database recovery-set binding mismatch")
    require(scenario["objectRecoverySetDigest"] == recovery, "object recovery-set binding mismatch")
    require(len({scenario["sourceObjectVersionDigest"], scenario["backupObjectVersionDigest"], scenario["restoreObjectVersionDigest"]}) == 3,
            "provider version digests must remain distinct")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions, "assertions missing")
    for key in (
        "sourceDatabaseDestroyedBeforeRestore",
        "sourceObjectVersionsDestroyedBeforeRestore",
        "databaseRecoverySetBindingMatched",
        "objectRecoverySetBindingMatched",
        "databaseObjectRecoverySetMatched",
        "exactBackupObjectChecksumMatched",
        "deliberateOneSidedSkewRejected",
    ):
        require(assertions.get(key) is True, f"required coherent recovery assertion failed: {key}")

    limitations = result.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 5, "result limitations incomplete")
    joined = "\n".join(str(value) for value in limitations)
    for phrase in ("local PostgreSQL", "WAL/PITR", "does not measure temporal", "not independent provider", "not production"):
        require(phrase in joined, f"result limitation missing: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password", "minioadmin", "access_key", "secret_key",
        "memory-os-coherent-source-", "memory-os-coherent-backup-", "memory-os-coherent-restore-",
        "synthetic/coherent-recovery-set.json", "acct_recovery_",
    ):
        require(forbidden not in serialized, f"result contains forbidden raw material: {forbidden}")


def main() -> int:
    for path, label in (
        (CONTRACT_PATH, "coherent recovery contract"),
        (MIGRATION_PATH, "migration lifecycle authority"),
        (STATUS_PATH, "production operability status"),
    ):
        require_repo_regular_file(path, label)

    contract = load(CONTRACT_PATH)
    migration = load(MIGRATION_PATH)
    require(contract.get("schemaVersion") == "memory-os-local-coherent-recovery-set.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-local-coherent-recovery-set-results.v1", "results schema drift")
    require(contract.get("runner") == "scripts/run-memory-os-local-coherent-recovery-set.py", "runner ref drift")
    require(contract.get("validator") == "scripts/validate-memory-os-local-coherent-recovery-set.py", "validator ref drift")
    require(contract.get("workflow") == ".github/workflows/local-coherent-recovery-set.yml", "workflow ref drift")
    require(contract.get("resultPath") == "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json", "result ref drift")
    require(contract.get("dependencyMode") == "EPHEMERAL_POSTGRESQL_16_PLUS_LOCAL_MINIO_COHERENT_RECOVERY_SET", "dependency mode drift")
    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "contract scenario missing")
    for field, minimum in (("requiredSteps", 14), ("successCriteria", 10), ("abortCriteria", 7)):
        values = scenario.get(field)
        require(isinstance(values, list) and len(values) >= minimum and len(values) == len(set(values)), f"scenario {field} incomplete")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("coherentLocalRecoverySetBindingEvidence") is True, "local coherence boundary missing")
    for key in (
        "productionEvidence", "productionEquivalentDependencies", "postgresPitrEvidence",
        "independentObjectRetentionEvidence", "crossClusterEvidence", "recoveryPointTimeSkewMeasured",
        "approvedRpoRtoEvidence", "productionReady",
    ):
        require(boundary.get(key) is False, f"local coherence contract cannot enable {key}")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list) and set(refs) == EXPECTED_REFS and len(refs) == len(set(refs)), "evidenceRefs drift")
    for ref in refs:
        require_repo_regular_file(ROOT / ref, f"coherent recovery evidence ref {ref}")

    runner = (ROOT / contract["runner"]).read_text(encoding="utf-8")
    for snippet in (
        "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP",
        "MEMORY_OS_ALLOW_EPHEMERAL_OBJECT_DELETE",
        "recovery-set-sha256",
        "pg_dump",
        "pg_restore",
        "purge_bucket(client, source_bucket)",
        "DROP DATABASE",
        "database/object coherent recovery-set comparison failed",
        "deliberate one-sided recovery-set skew was accepted",
    ):
        require(snippet in runner, f"runner safety binding missing: {snippet}")

    migrations = migration.get("migrationSequence")
    require(isinstance(migrations, list) and migrations, "canonical migrations missing")
    migration_count = len(migrations)
    for filename in migrations:
        require_repo_regular_file(ROOT / "infra/postgresql/security" / filename, f"migration {filename}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for key in ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(readiness.get(key) is True, f"readiness foundation false: {key}")
    for key in ("exactSourcePassResultCommitted", "deliberateSkewRejected", "coherentLocalRecoverySetBindingProven"):
        require(readiness.get(key) is RESULT_PATH.is_file(), f"readiness/result drift: {key}")
    for key in ("productionEquivalentRestoreEvidence", "productionReady"):
        require(readiness.get(key) is False, f"local coherence cannot promote {key}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA40.fullmatch(expected_sha) is not None, "EXPECTED_COMMIT_SHA invalid")
        require(RESULT_PATH.is_file(), "exact-source coherent recovery result missing")
    if RESULT_PATH.is_file():
        require_repo_regular_file(RESULT_PATH, "coherent recovery result")
        validate_result(load(RESULT_PATH), expected_sha, migration_count)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "local coherence cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY", "local coherence cannot make OPS-P0-007 READY")
    require_canonical_gaps(gate.get("missingEvidence"), Fail)

    print("Memory OS local coherent recovery-set validation PASS")
    print(f"canonical migrations: {migration_count}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print(f"coherent local recovery-set binding proven: {RESULT_PATH.is_file()}")
    print("temporal recovery-point skew measured: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL COHERENT RECOVERY SET VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
