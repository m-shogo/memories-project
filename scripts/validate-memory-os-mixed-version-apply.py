#!/usr/bin/env python3
"""Fail-closed validation for mixed-version persisted Apply compatibility."""

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
CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-apply-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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
    require(contract.get("schemaVersion") == "memory-os-mixed-version-apply.v1",
            "mixed-version Apply contract schema drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-mixed-version-apply-results.v1",
            "mixed-version Apply result schema drift")
    old_sha = contract.get("oldBackendCommitSha")
    require(isinstance(old_sha, str) and SHA_RE.fullmatch(old_sha) is not None,
            "pinned old backend SHA is invalid")
    require(contract.get("oldBackendClassification") ==
            "HISTORICAL_CANDIDATE_NOT_APPROVED_RELEASE",
            "old backend classification drift")
    require(contract.get("dependencyMode") ==
            "EPHEMERAL_POSTGRESQL_16_MINIO_TWO_PROCESSES_SHARED_CURRENT_SCHEMA",
            "dependency mode drift")

    for field in ("requiredScenarios", "abortCriteria", "limitations", "evidenceRefs"):
        value = contract.get(field)
        require(isinstance(value, list) and value, f"{field} must be a non-empty list")
    require(len(contract["requiredScenarios"]) == 6,
            "mixed-version Apply scenario count drift")
    for ref in contract["evidenceRefs"]:
        require(isinstance(ref, str) and not ref.startswith("/") and
                ".." not in Path(ref).parts,
                f"unsafe evidence path: {ref}")
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    for field in (
        "productionEvidence", "releaseCompatibilityEvidence", "approvedReleasePair",
        "rollingDeploymentEvidence", "rollbackEvidence", "concurrentClaimRaceEvidence",
        "productionReady",
    ):
        require(boundary.get(field) is False, f"evidence boundary overclaim: {field}")
    require(boundary.get("historicalCandidateOnly") is True,
            "historical candidate boundary missing")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for field in (
        "contractDefined", "fixtureGeneratorImplemented", "runnerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"implementation readiness missing: {field}")
    for field in (
        "approvedReleasePairAvailable", "concurrentClaimRaceExecuted",
        "rollbackRehearsalExecuted", "productionReady",
    ):
        require(readiness.get(field) is False, f"unproven readiness cannot be true: {field}")

    if not RESULT_PATH.is_file():
        require(readiness.get("exactSourcePassResultCommitted") is False,
                "contract claims a result that is not present")
        require(not arguments.expected_commit_sha,
                "exact-source result is required but missing")
        require(not arguments.require_reconciled,
                "reconciled result is required but missing")
        print("Memory OS mixed-version Apply static validation PASS")
        print("exact-source result present: False")
        print("production decision: NO_GO")
        return 0

    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == "memory-os-mixed-version-apply-results.v1",
            "mixed-version Apply result schema drift")
    current_sha = result.get("currentCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "current result SHA is invalid")
    require(result.get("oldBackendCommitSha") == old_sha,
            "result old backend SHA differs from contract")
    require(is_ancestor(old_sha, current_sha),
            "old backend is not an ancestor of result current SHA")
    require(is_ancestor(current_sha, "HEAD"),
            "result current SHA is not an ancestor of HEAD")
    if arguments.expected_commit_sha:
        require(SHA_RE.fullmatch(arguments.expected_commit_sha) is not None,
                "expected commit SHA is invalid")
        require(current_sha == arguments.expected_commit_sha,
                "result was not generated from the expected exact source")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment missing")
    require(environment.get("mode") ==
            "GITHUB_ACTIONS_OR_LOCAL_POSTGRES16_MINIO_TWO_PROCESSES_SHARED_SCHEMA",
            "result environment mode drift")
    require(environment.get("historicalCandidateOnly") is True and
            environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "result evidence boundary drift")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "mixed-version Apply result is not PASS")

    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "result assertions missing")
    expected = contract.get("successCriteria")
    require(isinstance(expected, dict) and expected, "successCriteria missing")
    for field, value in expected.items():
        require(assertions.get(field) == value,
                f"assertion mismatch for {field}: expected {value!r}, got {assertions.get(field)!r}")
    require(assertions.get("rawTokensPersisted") is False and
            assertions.get("rawSyntheticIdsPersisted") is False and
            assertions.get("sharedCurrentSchema") is True and
            assertions.get("oldAndCurrentProcessesConcurrent") is True,
            "required privacy or process assertion missing")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://", "postgresql://", "Bearer ", "password=", "minioadmin",
        "acct_", "job_", "prv_", "spl_", "upl_", "idem-mixed-",
    ):
        require(forbidden not in serialized,
                f"result contains forbidden evidence content: {forbidden}")

    if arguments.require_reconciled:
        require(readiness.get("exactSourcePassResultCommitted") is True,
                "result exists but contract readiness is not reconciled")
    else:
        require(readiness.get("exactSourcePassResultCommitted") in (False, True),
                "exactSourcePassResultCommitted must be boolean")

    print("Memory OS mixed-version Apply validation PASS")
    print(f"old backend: {old_sha[:12]}")
    print(f"current source: {current_sha[:12]}")
    print(f"reconciled: {readiness.get('exactSourcePassResultCommitted') is True}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"MIXED-VERSION APPLY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
