#!/usr/bin/env python3
"""Fail-closed validation for the candidate mixed-version compatibility drill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-candidate-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
BASELINE_SHA = "a1f39560468ebd5d39c4dd7a336140cb455cf2e8"
FOUNDATION_REFS = {
    "contracts/operations/mixed-version-candidate-contract.v1.json",
    "scripts/run-memory-os-mixed-version-candidate.sh",
    "scripts/validate-memory-os-mixed-version-candidate.py",
    "scripts/reconcile-memory-os-mixed-version-candidate.py",
    ".github/workflows/mixed-version-candidate.yml",
}
RESULT_REF = "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"


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


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def is_ancestor(base: str, head: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, head],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def validate_result(result: dict[str, Any], contract: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "mixed-version result schemaVersion drift")
    current_sha = result.get("currentCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "currentCommitSha must be a full SHA")
    require(result.get("candidateBaselineCommitSha") == BASELINE_SHA,
            "candidate baseline result SHA drift")
    require(is_ancestor(BASELINE_SHA, current_sha),
            "candidate baseline is not an ancestor of result current SHA")
    if expected_sha:
        require(current_sha == expected_sha,
                f"mixed-version result SHA {current_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "mixed-version environment missing")
    require(environment.get("mode") == contract["dependencyMode"],
            "mixed-version environment mode drift")
    require(environment.get("productionEvidence") is False,
            "candidate drill cannot claim production evidence")
    require(environment.get("releaseCompatibilityEvidence") is False,
            "candidate drill cannot claim release compatibility")
    require(environment.get("candidateBaselineOnly") is True,
            "candidate drill must remain candidate-only")
    require(environment.get("containsSecrets") is False,
            "mixed-version result must state containsSecrets=false")
    require(environment.get("syntheticDataOnly") is True,
            "mixed-version result must use synthetic data only")
    digest = environment.get("databaseIdentityDigest")
    require(isinstance(digest, str) and DIGEST_RE.fullmatch(digest) is not None,
            "database identity must be a digest")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "mixed-version scenario missing")
    require(scenario.get("scenarioId") ==
            "historical-candidate-on-current-expanded-schema",
            "mixed-version scenario ID drift")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "mixed-version candidate result is not PASS")
    require(isinstance(scenario.get("durationSeconds"), int) and
            scenario["durationSeconds"] >= 0,
            "mixed-version duration invalid")
    require(isinstance(scenario.get("currentMigrationsAppliedPerDatabase"), int) and
            scenario["currentMigrationsAppliedPerDatabase"] >= 11,
            "current migration count is insufficient")
    require(isinstance(scenario.get("candidateBaselineSqlTestsExecuted"), int) and
            scenario["candidateBaselineSqlTestsExecuted"] >= 1,
            "candidate baseline SQL tests were not executed")
    require(isinstance(scenario.get("currentSqlTestsExecuted"), int) and
            scenario["currentSqlTestsExecuted"] >= 11,
            "current canonical SQL tests were not executed")
    baseline_packages = scenario.get("candidateBaselineGoPackagesExecuted")
    current_packages = scenario.get("currentGoPackagesExecuted")
    require(isinstance(baseline_packages, int) and 3 <= baseline_packages <= 4,
            "candidate common Go package count is outside the reviewed bound")
    require(current_packages == baseline_packages,
            "candidate/current Go package coverage differs")
    require(scenario.get("baselineSqlOrderSource") in {
        "BASELINE_MIGRATION_REGISTRY",
        "BASELINE_SECURITY_CONTRACTS_WORKFLOW",
    }, "baseline SQL order is not tied to a baseline-owned authority")
    schema_digest = scenario.get("memoryOsSchemaFingerprintSha256")
    require(isinstance(schema_digest, str) and DIGEST_RE.fullmatch(schema_digest) is not None,
            "schema fingerprint must be a digest")

    expected_assertions = {
        "baselineIsAncestorOfCurrent",
        "currentExpandedSchemaAppliedToBothDatabases",
        "candidateBaselineSqlTestsPassed",
        "candidateBaselineGoTestsPassed",
        "candidateExecutionPreservedSchemaFingerprint",
        "currentSqlTestsPassed",
        "currentGoTestsPassed",
    }
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and set(assertions) == expected_assertions,
            "mixed-version assertion set drift")
    require(all(assertions.get(field) is True for field in expected_assertions),
            "mixed-version result contains a failed assertion")

    limitations = strings(result.get("limitations"), "result.limitations", 7)
    require(limitations == contract["limitations"],
            "result limitations must exactly match the contract")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "minioadmin",
        "secretaccesskey", "accesskeyid", "authorization: bearer",
        "/tmp/memory-os-mixed-version", "token_digest",
    ):
        require(forbidden not in serialized,
                f"mixed-version result contains forbidden evidence value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-mixed-version-candidate.v1",
            "mixed-version contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-mixed-version-candidate-results.v1",
            "mixed-version result schemaVersion drift")
    baseline = contract.get("candidateBaseline")
    require(isinstance(baseline, dict), "candidateBaseline missing")
    require(baseline.get("commitSha") == BASELINE_SHA,
            "contract baseline SHA drift")
    require(baseline.get("classification") == "HISTORICAL_CANDIDATE_NOT_RELEASE",
            "baseline classification drift")
    require(baseline.get("mustBeAncestorOfCurrent") is True,
            "baseline ancestor guard missing")
    require(baseline.get("releaseApproved") is False,
            "candidate baseline cannot be release-approved")
    require(is_ancestor(BASELINE_SHA, "HEAD"),
            "candidate baseline is not an ancestor of current HEAD")

    expected_paths = {
        "runner": "scripts/run-memory-os-mixed-version-candidate.sh",
        "validator": "scripts/validate-memory-os-mixed-version-candidate.py",
        "workflow": ".github/workflows/mixed-version-candidate.yml",
        "reconcile": "scripts/reconcile-memory-os-mixed-version-candidate.py",
        "resultPath": RESULT_REF,
        "diagnosticPath": "docs/fixtures/memory-os-operability/mixed-version-candidate-diagnostic.last.json",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"mixed-version {field} path drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_MINIO_TWO_DATABASE_CANDIDATE_BASELINE",
            "mixed-version dependency mode drift")
    strings(contract.get("requiredSteps"), "requiredSteps", 10)
    strings(contract.get("successCriteria"), "successCriteria", 9)
    strings(contract.get("abortCriteria"), "abortCriteria", 9)
    strings(contract.get("limitations"), "limitations", 7)

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("candidateBaselineOnly") is True,
            "candidate-only boundary missing")
    for field in (
        "productionEvidence", "releaseCompatibilityEvidence",
        "rollingDeploymentEvidence", "sharedLiveTrafficEvidence",
        "downgradeEvidence", "contractMigrationEvidence", "productionReady",
    ):
        require(boundary.get(field) is False,
                f"candidate contract cannot claim {field}")
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "privacy missing")
    for field in (
        "syntheticDataOnly", "databaseUrlInEvidenceForbidden",
        "credentialInEvidenceForbidden", "rawWorktreePathInEvidenceForbidden",
        "userContentInEvidenceForbidden", "databaseIdentityStoredAsDigestOnly",
    ):
        require(privacy.get(field) is True, f"privacy.{field} must be true")

    runner_path = ROOT / contract["runner"]
    require(runner_path.is_file(), "mixed-version runner missing")
    source = runner_path.read_text(encoding="utf-8")
    for snippet in (
        "merge-base --is-ancestor", "worktree add --detach",
        "CURRENT_MIGRATIONS", "BASELINE_SECURITY_CONTRACTS_WORKFLOW",
        "BASELINE_SQL_ORDER_SOURCE", "GO_PACKAGE_CANDIDATES",
        "pg_dump --dbname \"$BASELINE_DB\" --schema-only",
        "SCHEMA_BEFORE_SHA", "SCHEMA_AFTER_SHA",
        "candidate baseline is not an approved release",
    ):
        require(snippet in source, f"mixed-version runner missing boundary: {snippet}")
    for forbidden in (
        "git checkout -f", "git reset --hard", "DROP DATABASE postgres",
        "print(PGPASSWORD", "traceback.print_exc",
    ):
        require(forbidden not in source, f"mixed-version runner contains dangerous pattern: {forbidden}")

    result_present = RESULT_PATH.is_file()
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(result_present, "exact-source mixed-version result is missing")
    if result_present:
        validate_result(load(RESULT_PATH), contract, expected_sha)

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for field in (
        "contractDefined", "runnerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True,
                f"implemented foundation is not registered: {field}")
    # During the workflow's result-commit step, the result exists before the
    # authority reconcile commit. EXPECTED_COMMIT_SHA marks that bounded
    # transient; outside it, the contract flag and repository evidence must
    # agree exactly.
    if not expected_sha:
        require(readiness.get("exactSourcePassResultCommitted") is result_present,
                "exact-source result readiness disagrees with repository evidence")
    else:
        require(readiness.get("exactSourcePassResultCommitted") in {False, True},
                "exact-source readiness must remain boolean")
    for field in (
        "approvedReleaseBaselineAvailable", "simultaneousMixedTrafficExecuted",
        "rollingDeploymentFailureExecuted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"unproven mixed-version readiness cannot be true: {field}")

    refs = set(strings(contract.get("evidenceRefs"), "evidenceRefs", 5))
    require(FOUNDATION_REFS <= refs,
            f"candidate foundation evidence is incomplete: {sorted(FOUNDATION_REFS - refs)}")
    if readiness.get("exactSourcePassResultCommitted") is True:
        require(RESULT_REF in refs and result_present,
                "committed-result claim lacks the exact result evidence")
    elif not expected_sha:
        require(RESULT_REF not in refs,
                "uncommitted result must not be listed as contract evidence")
    for ref in refs:
        require((ROOT / ref).is_file(), f"mixed-version evidence missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "candidate mixed-version evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") != "READY",
            "candidate baseline evidence cannot make OPS-P0-008 READY")

    print("Memory OS mixed-version candidate validation PASS")
    print(f"baseline: {BASELINE_SHA}")
    print(f"result present: {result_present}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"MIXED-VERSION CANDIDATE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
