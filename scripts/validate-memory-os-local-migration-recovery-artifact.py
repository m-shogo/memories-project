#!/usr/bin/env python3
"""Fail-closed validator for the local actual migration recovery-artifact rehearsal."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
LIFECYCLE_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
RUNNER_PATH = ROOT / "scripts/run-memory-os-local-migration-recovery-artifact.sh"
EVIDENCE_ROOT = ROOT / "docs/evidence/migrations/recovery"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^mig_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
FORBIDDEN = re.compile(
    r"(?:postgres(?:ql)?://|https?://|password|passwd|bearer\s+|private[_ -]?key|secret[_ -]?key|access[_ -]?key|minioadmin|account[_ -]?id|session[_ -]?id|job[_ -]?id|preview[_ -]?id|object[_ -]?key|hostname)",
    re.IGNORECASE,
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def commit_exists(sha: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", sha + "^{commit}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--expected-commit-sha")
    parser.add_argument("--require-result", action="store_true")
    return parser.parse_args()


def iter_strings(value: Any) -> list[str]:
    output: list[str] = []
    if isinstance(value, str):
        output.append(value)
    elif isinstance(value, list):
        for item in value:
            output.extend(iter_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            output.extend(iter_strings(item))
    return output


def validate_result(
    result: dict[str, Any],
    contract: dict[str, Any],
    lifecycle: dict[str, Any],
    expected_sha: str | None,
    result_path: Path,
) -> None:
    require(result.get("schemaVersion") == contract.get("resultSchemaVersion"),
            "result schemaVersion drift")
    run_id = result.get("migrationRunId")
    require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id) is not None,
            "migrationRunId invalid")
    if result_path.is_relative_to(EVIDENCE_ROOT):
        require(result_path.name == f"{run_id}.json",
                "evidence filename must match migrationRunId")

    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA40.fullmatch(source_sha) is not None,
            "result commitSha must be a full lowercase SHA")
    require(commit_exists(source_sha), "result commitSha is not a repository commit")
    if expected_sha is not None:
        require(SHA40.fullmatch(expected_sha) is not None, "expected commit SHA invalid")
        require(source_sha == expected_sha, "result commitSha does not match expected source")

    database_digest = result.get("databaseIdentityDigest")
    require(isinstance(database_digest, str) and SHA256.fullmatch(database_digest) is not None,
            "databaseIdentityDigest must be SHA-256")

    canonical = lifecycle.get("migrationSequence")
    require(isinstance(canonical, list) and len(canonical) >= 2,
            "canonical migration sequence missing")
    under_test = contract.get("migrationUnderTest")
    require(under_test == canonical[-1],
            "contract migrationUnderTest must remain canonical final migration")
    require(result.get("migrationUnderTest") == under_test,
            "result migrationUnderTest drift")
    require(result.get("baselineMigrationCount") == len(canonical) - 1,
            "baseline migration count drift")
    require(result.get("finalMigrationCount") == len(canonical),
            "final migration count drift")
    require(result.get("sqlIntegrationTestsExecutedAfterRecovery") == len(canonical),
            "post-recovery SQL integration test count drift")

    require(result.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL",
            "result environmentClass drift")
    require(result.get("databaseMode") ==
            "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_PREMIGRATION_LOGICAL_RECOVERY",
            "databaseMode drift")
    duration = result.get("durationSeconds")
    require(isinstance(duration, int) and duration >= 0 and duration <= 300,
            "local recovery rehearsal duration invalid")
    apply_duration = result.get("migrationApplyDurationMs")
    require(isinstance(apply_duration, int) and 0 <= apply_duration <= 300000,
            "migrationApplyDurationMs invalid")

    artifact = result.get("recoveryArtifact")
    require(isinstance(artifact, dict), "recoveryArtifact must be object")
    digest = artifact.get("sha256")
    reference = artifact.get("reference")
    require(isinstance(digest, str) and SHA256.fullmatch(digest) is not None,
            "recovery artifact sha256 invalid")
    require(reference == "sha256:" + digest,
            "recovery artifact reference/digest mismatch")
    artifact_bytes = artifact.get("bytes")
    require(isinstance(artifact_bytes, int) and artifact_bytes > 0,
            "recovery artifact byte count invalid")
    require(artifact.get("rawArtifactCommitted") is False,
            "raw recovery artifact must not be committed")

    assertions = result.get("assertions")
    expected_assertions = contract.get("requiredAssertions")
    require(isinstance(assertions, dict) and isinstance(expected_assertions, dict),
            "assertions missing")
    require(set(assertions) == set(expected_assertions), "assertion set drift")
    for key, expected in expected_assertions.items():
        require(assertions.get(key) is expected, f"assertion failed or drifted: {key}")
    require(result.get("result") == "PASS", "recovery artifact rehearsal must PASS")
    require(result.get("integrityResult") == "PASS", "recovery artifact integrity must PASS")
    require(result.get("limitations") == contract.get("limitations"),
            "result limitations drift")

    joined = "\n".join(iter_strings(result))
    require(FORBIDDEN.search(joined) is None,
            "recovery artifact evidence contains forbidden secret/identity-like content")


def main() -> int:
    args = parse_args()
    contract = load(CONTRACT_PATH)
    lifecycle = load(LIFECYCLE_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-local-migration-recovery-artifact-contract.v1",
            "contract schemaVersion drift")
    require(contract.get("migrationLifecycleContract") ==
            "contracts/operations/migration-lifecycle-contract.v1.json",
            "migration lifecycle reference drift")
    require(contract.get("baselineSequenceRule") ==
            "CANONICAL_PREFIX_EXCLUDING_MIGRATION_UNDER_TEST",
            "baseline sequence rule drift")
    require(contract.get("runner") == str(RUNNER_PATH.relative_to(ROOT)),
            "runner path drift")
    require(contract.get("validator") == str(Path(__file__).resolve().relative_to(ROOT)),
            "validator path drift")
    require(contract.get("evidenceRoot") == str(EVIDENCE_ROOT.relative_to(ROOT)),
            "evidence root drift")
    require(RUNNER_PATH.is_file() and EVIDENCE_ROOT.is_dir(),
            "runner/evidence root missing")

    environment = contract.get("environment")
    require(isinstance(environment, dict), "contract environment missing")
    require(environment.get("databaseEngine") == "PostgreSQL" and
            environment.get("databaseMajorVersion") == 16,
            "database baseline drift")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_SAME_CLUSTER",
            "dependency mode drift")
    for flag in ("sourceAndRecoveryDatabaseMustDiffer", "localhostOnly", "syntheticDataOnly"):
        require(environment.get(flag) is True, f"environment.{flag} must be true")
    require(environment.get("productionEquivalent") is False,
            "local rehearsal cannot be production-equivalent")

    expected_assertions = contract.get("requiredAssertions")
    require(isinstance(expected_assertions, dict) and len(expected_assertions) == 13,
            "requiredAssertions drift")
    for flag in (
        "sourceBaselineApplied", "recoveryArtifactDigestRecorded",
        "migrationAppliedOnSource", "migrationSpecificSourceTestPassed",
        "exactRecoveryArtifactRestored", "preMigrationSurfaceRecovered",
        "migrationReappliedAfterRestore", "canonicalSqlSuitePassedAfterRecovery",
        "actualRecoveryArtifactRestored",
    ):
        require(expected_assertions.get(flag) is True,
                f"required assertion must be true: {flag}")
    for flag in ("containsSecrets", "productionTraffic", "productionCredentials", "productionEvidence"):
        require(expected_assertions.get(flag) is False,
                f"non-production assertion must be false: {flag}")

    limitations = contract.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 6,
            "limitations must remain explicit")
    joined_limitations = "\n".join(str(item) for item in limitations)
    for phrase in (
        "same PostgreSQL cluster", "not PITR", "not production-equivalent",
        "not proof that a production migration may be automatically rolled back",
        "does not exercise application traffic", "destructive-contract isolated restore",
    ):
        require(phrase in joined_limitations, f"required limitation missing: {phrase}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "contract readiness missing")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    for flag in (
        "productionEquivalentRecoveryArtifactRestoreProven", "productionReady",
    ):
        require(readiness.get(flag) is False, f"unproven readiness cannot be true: {flag}")

    result_path = args.path.resolve() if args.path else None
    if args.require_result:
        require(result_path is not None and result_path.is_file(), "result path is required")
    if result_path is not None:
        require(result_path.is_file(), f"result path missing: {result_path}")
        validate_result(load(result_path), contract, lifecycle, args.expected_commit_sha, result_path)

    print("Memory OS local migration recovery-artifact validation PASS")
    print(f"result: {'VALIDATED' if result_path is not None else 'NOT_REQUESTED'}")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL MIGRATION RECOVERY ARTIFACT VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
