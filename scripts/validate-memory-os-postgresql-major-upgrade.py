#!/usr/bin/env python3
"""Fail-closed validation for PostgreSQL 16 to 17 logical upgrade evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/postgresql-major-upgrade-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json"
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
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-commit-sha", default=os.getenv("EXPECTED_COMMIT_SHA", ""))
    parser.add_argument("--require-reconciled", action="store_true")
    arguments = parser.parse_args()

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-postgresql-major-upgrade.v1",
            "PostgreSQL upgrade contract schema drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-postgresql-major-upgrade-results.v1",
            "PostgreSQL upgrade result schema drift")
    require(contract.get("sourceMajor") == 16 and contract.get("targetMajor") == 17,
            "PostgreSQL upgrade major pair drift")
    require(contract.get("upgradeClass") ==
            "ISOLATED_LOGICAL_FORWARD_RESTORE_TO_FRESH_EXPANDED_SCHEMA",
            "PostgreSQL upgrade class drift")
    for field, expected in {
        "runner": "scripts/run-memory-os-postgresql-major-upgrade.sh",
        "validator": "scripts/validate-memory-os-postgresql-major-upgrade.py",
        "reconcile": "scripts/reconcile-memory-os-postgresql-major-upgrade.py",
        "workflow": ".github/workflows/postgresql-major-upgrade.yml",
        "resultPath": str(RESULT_PATH.relative_to(ROOT)),
    }.items():
        require(contract.get(field) == expected, f"contract path drift: {field}")
    for field in ("requiredPhases", "abortCriteria", "limitations", "evidenceRefs"):
        value = contract.get(field)
        require(isinstance(value, list) and value, f"{field} must be a non-empty list")
    require(len(contract["requiredPhases"]) == 10,
            "PostgreSQL upgrade phase count drift")
    for ref in contract["evidenceRefs"]:
        require(isinstance(ref, str) and not ref.startswith("/") and
                ".." not in Path(ref).parts,
                f"unsafe evidence path: {ref}")
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    policy = contract.get("upgradePolicy")
    require(isinstance(policy, dict) and
            policy.get("expandMigrationsBeforeDataRestore") is True and
            policy.get("dataOnlyRestoreIntoFreshTarget") is True and
            policy.get("automaticInPlaceUpgradeForbidden") is True and
            policy.get("automaticDownMigrationForbidden") is True and
            policy.get("targetToSourceDowngradeForbidden") is True and
            policy.get("automaticTrafficPromotionForbidden") is True and
            policy.get("sourceDatabaseDeletionForbidden") is True and
            policy.get("humanDatabaseRecoveryApprovalRequiredForProduction") is True,
            "PostgreSQL upgrade policy drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    for field in (
        "productionEvidence", "productionTraffic", "productionCredentials",
        "inPlacePgUpgradeEvidence", "physicalReplicationEvidence", "downgradeEvidence",
        "rollingDeploymentEvidence", "approvedRpoRtoEvidence", "productionReady",
    ):
        require(boundary.get(field) is False, f"upgrade evidence overclaim: {field}")
    require(boundary.get("isolatedLogicalForwardUpgradeEvidence") is True,
            "logical forward-upgrade evidence boundary missing")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "upgrade readiness missing")
    for field in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"upgrade foundation missing: {field}")
    for field in (
        "inPlaceUpgradeExecuted", "productionFailoverExecuted", "downgradeExecuted",
        "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False, f"unproven readiness cannot be true: {field}")

    if not RESULT_PATH.is_file():
        require(readiness.get("exactSourcePassResultCommitted") is False and
                readiness.get("postgresql17LogicalForwardUpgradeExecuted") is False,
                "contract claims missing PostgreSQL upgrade result")
        require(not arguments.expected_commit_sha and not arguments.require_reconciled,
                "exact or reconciled PostgreSQL upgrade result is required but missing")
        print("Memory OS PostgreSQL major-upgrade static validation PASS")
        print("exact-source result present: False")
        print("production decision: NO_GO")
        return 0

    result = load(RESULT_PATH)
    require(result.get("schemaVersion") ==
            "memory-os-postgresql-major-upgrade-results.v1",
            "PostgreSQL upgrade result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "PostgreSQL upgrade result commit SHA invalid")
    require(is_ancestor(commit_sha, "HEAD"),
            "PostgreSQL upgrade result source is not an ancestor of HEAD")
    if arguments.expected_commit_sha:
        require(SHA_RE.fullmatch(arguments.expected_commit_sha) is not None and
                commit_sha == arguments.expected_commit_sha,
                "PostgreSQL upgrade result is not from expected exact source")

    environment = result.get("environment")
    require(isinstance(environment, dict) and
            environment.get("mode") ==
            "EPHEMERAL_DOCKER_POSTGRESQL_16_TO_17_LOGICAL_FORWARD_RESTORE" and
            environment.get("productionEvidence") is False and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "PostgreSQL upgrade result evidence boundary drift")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("scenarioId") == "postgresql-16-to-17-logical-forward-upgrade" and
            scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "PostgreSQL upgrade scenario is not PASS")
    require(scenario.get("sourceMajor") == 16 and scenario.get("targetMajor") == 17,
            "PostgreSQL upgrade result major pair drift")
    require(isinstance(scenario.get("migrationFilesAppliedPerDatabase"), int) and
            scenario["migrationFilesAppliedPerDatabase"] > 0 and
            scenario.get("sqlIntegrationTestsExecutedOnTarget") ==
            scenario.get("migrationFilesAppliedPerDatabase"),
            "migration and target SQL-test counts drift")
    require(isinstance(scenario.get("dumpBytes"), int) and scenario["dumpBytes"] > 0,
            "PostgreSQL upgrade dump is empty")
    require(isinstance(scenario.get("schemaAuthorityFingerprintSha256"), str) and
            DIGEST_RE.fullmatch(scenario["schemaAuthorityFingerprintSha256"]) is not None,
            "schema authority fingerprint invalid")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "PostgreSQL upgrade assertions missing")
    expected = contract.get("successCriteria")
    require(isinstance(expected, dict) and expected, "successCriteria missing")
    for field, value in expected.items():
        require(assertions.get(field) == value,
                f"upgrade assertion mismatch for {field}: expected {value!r}, got {assertions.get(field)!r}")
    require(isinstance(assertions.get("forceRlsTables"), int) and
            assertions["forceRlsTables"] > 0,
            "FORCE RLS table verification missing")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "acct_upgrade_",
        "ses_upgrade_", "eeeeeeee", "ffffffff", "memory-os-pg16-",
        "memory-os-pg17-", "postgres:postgres",
    ):
        require(forbidden not in serialized,
                f"PostgreSQL upgrade result contains forbidden content: {forbidden}")

    if arguments.require_reconciled:
        require(readiness.get("exactSourcePassResultCommitted") is True and
                readiness.get("postgresql17LogicalForwardUpgradeExecuted") is True,
                "PostgreSQL upgrade result is not reconciled")
    else:
        require(readiness.get("exactSourcePassResultCommitted") in (False, True) and
                readiness.get("postgresql17LogicalForwardUpgradeExecuted") in (False, True),
                "PostgreSQL upgrade readiness must be boolean")

    print("Memory OS PostgreSQL 16 to 17 upgrade validation PASS")
    print(f"source commit: {commit_sha[:12]}")
    print(f"migrations: {scenario['migrationFilesAppliedPerDatabase']}")
    print(f"target SQL tests: {scenario['sqlIntegrationTestsExecutedOnTarget']}")
    print(f"reconciled: {readiness.get('exactSourcePassResultCommitted') is True}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"POSTGRESQL MAJOR UPGRADE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
