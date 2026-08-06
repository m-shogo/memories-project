#!/usr/bin/env python3
"""Fail-closed validation for the historical candidate compatibility drill."""

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
REJECTION_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-rejections.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
ACTIVE_BASELINE_SHA = "2af6e8e10755cc707c6bdd958a049a0f4afb3d70"
REJECTED_BASELINE_SHA = "a1f39560468ebd5d39c4dd7a336140cb455cf2e8"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
RESULT_REF = "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"
FOUNDATION_REFS = {
    "contracts/operations/mixed-version-candidate-contract.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-candidate-rejections.v1.json",
    "scripts/run-memory-os-mixed-version-candidate.sh",
    "scripts/validate-memory-os-mixed-version-candidate.py",
    "scripts/reconcile-memory-os-mixed-version-candidate.py",
    ".github/workflows/mixed-version-candidate.yml",
}


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
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
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


def validate_rejections(contract: dict[str, Any]) -> set[str]:
    require(contract.get("rejectedCandidateRegistry") ==
            str(REJECTION_PATH.relative_to(ROOT)),
            "rejected candidate registry path drift")
    registry = load(REJECTION_PATH)
    require(registry.get("schemaVersion") ==
            "memory-os-mixed-version-candidate-rejections.v1",
            "candidate rejection registry schema drift")
    require(registry.get("productionEvidence") is False and
            registry.get("releaseCompatibilityEvidence") is False and
            registry.get("containsSecrets") is False,
            "candidate rejection registry overclaims evidence")
    candidates = registry.get("candidates")
    require(isinstance(candidates, list) and candidates,
            "candidate rejection registry is empty")
    rejected: set[str] = set()
    for item in candidates:
        require(isinstance(item, dict), "rejected candidate must be an object")
        sha = item.get("commitSha")
        require(isinstance(sha, str) and SHA_RE.fullmatch(sha) is not None,
                "rejected candidate SHA is invalid")
        require(sha not in rejected, "rejected candidate SHA is duplicated")
        rejected.add(sha)
        require(item.get("classification") ==
                "REJECTED_HISTORICAL_CANDIDATE_NOT_RELEASE",
                "rejected candidate classification drift")
        require(item.get("result") == "REJECTED",
                "rejected candidate must remain rejected")
        strings(item.get("decisiveFailures"), "decisiveFailures") if False else None
        failures = item.get("decisiveFailures")
        require(isinstance(failures, list) and failures,
                "rejected candidate needs decisive failures")
        for failure in failures:
            require(isinstance(failure, dict) and failure.get("surface") and
                    failure.get("expected") and failure.get("observed"),
                    "rejected candidate failure record is incomplete")
        refs = strings(item.get("evidenceRefs"), "rejected.evidenceRefs", 4)
        for ref in refs:
            require((ROOT / ref).exists(), f"rejection evidence missing: {ref}")
    require(REJECTED_BASELINE_SHA in rejected,
            "known rejected candidate disappeared from registry")
    return rejected


def validate_result(result: dict[str, Any], contract: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "candidate result schema drift")
    current_sha = result.get("currentCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "currentCommitSha must be a full SHA")
    require(result.get("candidateBaselineCommitSha") == ACTIVE_BASELINE_SHA,
            "result does not use the active candidate baseline")
    require(is_ancestor(ACTIVE_BASELINE_SHA, current_sha),
            "active candidate is not an ancestor of result source")
    if expected_sha:
        require(current_sha == expected_sha,
                f"result source {current_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "candidate result environment missing")
    require(environment.get("mode") == contract["dependencyMode"],
            "candidate dependency mode drift")
    require(environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("candidateBaselineOnly") is True and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "candidate result overclaims evidence")
    require(isinstance(environment.get("databaseIdentityDigest"), str) and
            DIGEST_RE.fullmatch(environment["databaseIdentityDigest"]) is not None,
            "database identity must be a SHA-256 digest")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "candidate scenario missing")
    require(scenario.get("scenarioId") ==
            "historical-candidate-on-current-expanded-schema",
            "candidate scenario ID drift")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "candidate compatibility result is not PASS")
    require(isinstance(scenario.get("currentMigrationsAppliedPerDatabase"), int) and
            scenario["currentMigrationsAppliedPerDatabase"] >= 11,
            "current migration coverage is insufficient")
    require(isinstance(scenario.get("candidateBaselineSqlTestsExecuted"), int) and
            scenario["candidateBaselineSqlTestsExecuted"] >= 1,
            "candidate SQL tests were not executed")
    require(isinstance(scenario.get("currentSqlTestsExecuted"), int) and
            scenario["currentSqlTestsExecuted"] >= 11,
            "current SQL tests were not executed")
    candidate_packages = scenario.get("candidateBaselineGoPackagesExecuted")
    require(isinstance(candidate_packages, int) and 3 <= candidate_packages <= 4,
            "candidate Go package coverage is outside the reviewed bound")
    require(scenario.get("currentGoPackagesExecuted") == candidate_packages,
            "candidate/current Go package coverage differs")
    require(scenario.get("baselineSqlOrderSource") in {
        "BASELINE_MIGRATION_REGISTRY", "BASELINE_SECURITY_CONTRACTS_WORKFLOW"
    }, "candidate SQL order lacks baseline-owned authority")
    require(isinstance(scenario.get("memoryOsSchemaFingerprintSha256"), str) and
            DIGEST_RE.fullmatch(scenario["memoryOsSchemaFingerprintSha256"]) is not None,
            "schema fingerprint must be a digest")
    assertions = scenario.get("assertions")
    expected_assertions = {
        "baselineIsAncestorOfCurrent",
        "currentExpandedSchemaAppliedToBothDatabases",
        "candidateBaselineSqlTestsPassed",
        "candidateBaselineGoTestsPassed",
        "candidateExecutionPreservedSchemaFingerprint",
        "currentSqlTestsPassed",
        "currentGoTestsPassed",
    }
    require(isinstance(assertions, dict) and set(assertions) == expected_assertions and
            all(assertions.values()), "candidate assertions are incomplete or failed")
    require(strings(result.get("limitations"), "result.limitations", 7) ==
            contract["limitations"], "candidate limitations drift")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "minioadmin",
        "secretaccesskey", "accesskeyid", "authorization: bearer",
        "/tmp/memory-os-mixed-version", "token_digest",
    ):
        require(forbidden not in serialized,
                f"candidate result contains forbidden value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-mixed-version-candidate.v1" and
            contract.get("resultsSchemaVersion") ==
            "memory-os-mixed-version-candidate-results.v1",
            "candidate contract schema drift")
    baseline = contract.get("candidateBaseline")
    require(isinstance(baseline, dict) and
            baseline.get("commitSha") == ACTIVE_BASELINE_SHA,
            "active candidate baseline SHA drift")
    require(baseline.get("classification") == "HISTORICAL_CANDIDATE_NOT_RELEASE" and
            baseline.get("mustBeAncestorOfCurrent") is True and
            baseline.get("releaseApproved") is False,
            "active candidate classification drift")
    require(is_ancestor(ACTIVE_BASELINE_SHA, "HEAD"),
            "active candidate is not an ancestor of HEAD")
    rejected = validate_rejections(contract)
    require(ACTIVE_BASELINE_SHA not in rejected,
            "active candidate is present in the rejection registry")

    expected_paths = {
        "runner": "scripts/run-memory-os-mixed-version-candidate.sh",
        "validator": "scripts/validate-memory-os-mixed-version-candidate.py",
        "workflow": ".github/workflows/mixed-version-candidate.yml",
        "reconcile": "scripts/reconcile-memory-os-mixed-version-candidate.py",
        "resultPath": RESULT_REF,
        "diagnosticPath": "docs/fixtures/memory-os-operability/mixed-version-candidate-diagnostic.last.json",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"candidate {field} path drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_MINIO_TWO_DATABASE_CANDIDATE_BASELINE",
            "candidate dependency mode drift")
    strings(contract.get("requiredSteps"), "requiredSteps", 10)
    strings(contract.get("successCriteria"), "successCriteria", 9)
    strings(contract.get("abortCriteria"), "abortCriteria", 9)
    strings(contract.get("limitations"), "limitations", 7)

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict) and boundary.get("candidateBaselineOnly") is True,
            "candidate evidence boundary missing")
    for field in (
        "productionEvidence", "releaseCompatibilityEvidence",
        "rollingDeploymentEvidence", "sharedLiveTrafficEvidence",
        "downgradeEvidence", "contractMigrationEvidence", "productionReady",
    ):
        require(boundary.get(field) is False, f"candidate contract cannot claim {field}")

    runner_source = (ROOT / contract["runner"]).read_text(encoding="utf-8")
    for snippet in (
        "merge-base --is-ancestor", "worktree add --detach",
        "BASELINE_SECURITY_CONTRACTS_WORKFLOW", "GO_PACKAGE_CANDIDATES",
        "SCHEMA_BEFORE_SHA", "SCHEMA_AFTER_SHA",
    ):
        require(snippet in runner_source, f"candidate runner missing boundary: {snippet}")
    for forbidden in ("git checkout -f", "git reset --hard", "DROP DATABASE postgres"):
        require(forbidden not in runner_source,
                f"candidate runner contains dangerous pattern: {forbidden}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source candidate result is missing")
    result_present = RESULT_PATH.is_file()
    if result_present:
        validate_result(load(RESULT_PATH), contract, expected_sha)

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "candidate readiness missing")
    for field in (
        "contractDefined", "runnerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"candidate foundation missing: {field}")
    if not expected_sha:
        require(readiness.get("exactSourcePassResultCommitted") is result_present,
                "candidate readiness disagrees with result presence")
    for field in (
        "approvedReleaseBaselineAvailable", "simultaneousMixedTrafficExecuted",
        "rollingDeploymentFailureExecuted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"candidate evidence cannot promote readiness.{field}")

    refs = set(strings(contract.get("evidenceRefs"), "evidenceRefs", 6))
    require(FOUNDATION_REFS <= refs,
            f"candidate foundation refs missing: {sorted(FOUNDATION_REFS - refs)}")
    if readiness.get("exactSourcePassResultCommitted") is True:
        require(result_present and RESULT_REF in refs,
                "committed candidate result is not registered")
    elif not expected_sha:
        require(RESULT_REF not in refs,
                "uncommitted candidate result is listed as evidence")
    for ref in refs:
        require((ROOT / ref).exists(), f"candidate evidence missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "candidate evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY",
            "candidate evidence cannot make OPS-P0-008 READY")

    print("Memory OS mixed-version candidate validation PASS")
    print(f"active baseline: {ACTIVE_BASELINE_SHA}")
    print(f"rejected baselines: {len(rejected)}")
    print(f"result present: {result_present}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"MIXED-VERSION CANDIDATE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
