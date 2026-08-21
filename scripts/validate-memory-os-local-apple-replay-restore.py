#!/usr/bin/env python3
"""Fail-closed validator for local Apple replay-guard restore evidence."""

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
CONTRACT = ROOT / "contracts/operations/local-apple-replay-restore-contract.v1.json"
MIGRATION = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_REFS = {
    "contracts/operations/local-apple-replay-restore-contract.v1.json",
    "scripts/run-memory-os-local-apple-replay-restore.py",
    "scripts/validate-memory-os-local-apple-replay-restore.py",
    ".github/workflows/local-apple-replay-restore.yml",
    "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json",
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
    require(result.get("schemaVersion") == "memory-os-local-apple-replay-restore-results.v1", "result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA40.fullmatch(commit_sha), "result commit SHA invalid")
    require(source_is_ancestor(commit_sha), "Apple replay restore result source is not an ancestor of current HEAD")
    if expected_sha:
        require(commit_sha == expected_sha, "Apple replay restore result is not exact-source")
    environment = result.get("environment")
    require(isinstance(environment, dict), "environment missing")
    require(environment.get("databaseMode") == "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE", "database mode drift")
    require(isinstance(environment.get("databaseIdentityDigest"), str) and DIGEST.fullmatch(environment["databaseIdentityDigest"]), "database identity digest invalid")
    for key in ("productionTraffic", "productionCredentials", "productionEvidence", "containsSecrets"):
        require(environment.get(key) is False, f"evidence boundary drift: {key}")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario missing")
    require(scenario.get("scenarioId") == "apple-live-replay-guard-logical-restore", "scenario ID drift")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "scenario is not PASS")
    require(scenario.get("migrationFilesApplied") == migration_count, "migration coverage drift")
    require(isinstance(scenario.get("databaseDumpBytes"), int) and scenario["databaseDumpBytes"] > 0, "database dump size invalid")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions missing")
    require(assertions.get("sourceReplayRowsBeforeBackup") == 2, "source replay row count drift")
    require(assertions.get("restoredReplayRows") == 2, "restored replay row count drift")
    require(assertions.get("identicalReplayPairRejectedAfterRestore") is True, "identical replay pair was not rejected after restore")
    require(assertions.get("replayRowsUnchangedAfterRejectedReuse") is True, "failed replay reuse changed durable replay rows")
    limitations = result.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 5, "limitations incomplete")
    joined = "\n".join(str(value) for value in limitations)
    for phrase in ("same PostgreSQL cluster", "synthetic nonce", "WAL/PITR", "not real Sign in with Apple", "not production"):
        require(phrase in joined, f"limitation omitted: {phrase}")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "abababababababababababababababab", "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",
        "postgres://", "postgresql://", "password", "pgpassword",
        "memory_os_replay_source_", "memory_os_replay_target_",
    ):
        require(forbidden not in serialized, f"result contains forbidden raw material: {forbidden}")


def main() -> int:
    for path, label in (
        (CONTRACT, "Apple replay restore contract"),
        (MIGRATION, "migration lifecycle authority"),
        (STATUS, "production operability status"),
    ):
        require_repo_regular_file(path, label)

    contract = load(CONTRACT)
    migration = load(MIGRATION)
    require(contract.get("schemaVersion") == "memory-os-local-apple-replay-restore.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-local-apple-replay-restore-results.v1", "results schema drift")
    require(contract.get("runner") == "scripts/run-memory-os-local-apple-replay-restore.py", "runner ref drift")
    require(contract.get("validator") == "scripts/validate-memory-os-local-apple-replay-restore.py", "validator ref drift")
    require(contract.get("workflow") == ".github/workflows/local-apple-replay-restore.yml", "workflow ref drift")
    require(contract.get("resultPath") == "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json", "result ref drift")
    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "contract scenario missing")
    for field, minimum in (("requiredSteps", 10), ("successCriteria", 7), ("abortCriteria", 7)):
        values = scenario.get(field)
        require(isinstance(values, list) and len(values) >= minimum and len(values) == len(set(values)), f"scenario {field} incomplete")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("syntheticDataOnly") is True, "replay restore must remain synthetic-only")
    for key in ("productionEvidence", "postgresPitrEvidence", "crossClusterEvidence", "realAppleTrafficEvidence", "productionReady"):
        require(boundary.get(key) is False, f"local replay restore cannot enable {key}")
    require("remain consumed" in str(boundary.get("replayNonResurrectionScope")), "replay scope drift")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list) and set(refs) == EXPECTED_REFS and len(refs) == len(set(refs)), "evidenceRefs drift")
    for ref in refs:
        require_repo_regular_file(ROOT / ref, f"Apple replay restore evidence ref {ref}")
    runner = (ROOT / contract["runner"]).read_text(encoding="utf-8")
    for snippet in (
        "consume_apple_replay", "memory_auth_runtime", "source live replay row count must be two",
        "restored live replay row count must be two", "identical nonce/code pair was accepted after restore",
        "pg_dump", "pg_restore", "os.close(fd)",
    ):
        require(snippet in runner, f"runner binding missing: {snippet}")

    migrations = migration.get("migrationSequence")
    require(isinstance(migrations, list) and migrations, "migration sequence missing")
    migration_count = len(migrations)
    for filename in migrations:
        require_repo_regular_file(ROOT / "infra/postgresql/security" / filename, f"migration {filename}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for key in ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(readiness.get(key) is True, f"foundation readiness false: {key}")
    for key in ("productionReplayRestoreProven", "productionReady"):
        require(readiness.get(key) is False, f"local replay restore cannot promote {key}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA40.fullmatch(expected_sha) is not None, "EXPECTED_COMMIT_SHA invalid")
        require(RESULT.is_file(), "exact-source replay restore result missing")
    result_present = RESULT.is_file()
    require(readiness.get("exactSourcePassResultCommitted") is result_present,
            "readiness exactSourcePassResultCommitted does not match committed result presence")
    require(readiness.get("localReplayGuardRestoreProven") is result_present,
            "readiness localReplayGuardRestoreProven does not match committed PASS evidence presence")
    if result_present:
        require_repo_regular_file(RESULT, "Apple replay restore result")
        validate_result(load(RESULT), expected_sha, migration_count)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "local replay restore cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY", "local replay restore cannot make OPS-P0-007 READY")
    require_canonical_gaps(gate.get("missingEvidence"), Fail)

    print("Memory OS local Apple replay restore validation PASS")
    print(f"canonical migrations: {migration_count}")
    print(f"result present: {result_present}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL APPLE REPLAY RESTORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
