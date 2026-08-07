#!/usr/bin/env python3
"""Fail-closed validator for deletion lease-abandonment recovery evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-lease-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schemaVersion") == "memory-os-deletion-lease-recovery.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-lease-recovery-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-lease-expiry-reclaim-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("accounts") == 2, "account count drift")
    require(contract.get("leaseSeconds") == 1, "test lease must remain one second and explicitly non-production")

    cases = contract.get("interruptionCases")
    require(isinstance(cases, list) and len(cases) == 2, "exactly two interruption cases required")
    case_ids = {case.get("caseId") for case in cases if isinstance(case, dict)}
    require(case_ids == {"claimed-before-erasure", "object-erased-before-db-sweep"}, "interruption case set drift")

    sequence = contract.get("requiredSequence")
    require(isinstance(sequence, list), "requiredSequence must be list")
    required_fragments = (
        "do not call Release, Sweep or Complete",
        "cannot claim before lease expiry",
        "database object ledger intentionally retained",
        "object erasure remains idempotent",
        "no uploaded object version is resurrected",
    )
    joined = "\n".join(item for item in sequence if isinstance(item, str))
    for fragment in required_fragments:
        require(fragment in joined, f"required recovery sequence fragment missing: {fragment}")

    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict), "successCriteria must be object")
    expected = {
        "initialClaims": 2,
        "claimsAvailableBeforeExpiry": 0,
        "replacementWorkerReceipts": 2,
        "uniqueReplacementReceipts": 2,
        "replacementWorkerErrors": 0,
        "finalDeletionPending": 0,
        "finalDeletionStuck": 0,
        "finalOwnedRowCount": 0,
        "finalDeletedTombstonesEpoch2": 2,
        "remainingObjectVersions": 0,
        "productionEvidence": False,
    }
    for key, value in expected.items():
        require(criteria.get(key) == value, f"success criterion drift: {key}")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    require(boundary.get("leaseAbandonmentSimulatesProcessInterruption") is True, "simulation classification required")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "actualProcessKillCovered",
        "actualHostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"foundation cannot enable {key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    for key in (
        "runnerImplemented",
        "validatorImplemented",
        "automaticWorkflowImplemented",
        "exactSourceResultCommitted",
        "leaseExpiryReclaimProven",
        "partialObjectErasureRecoveryProven",
        "actualProcessKillCovered",
        "actualHostFailureCovered",
        "productionDependenciesTested",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in (
        "actualProcessKillCovered",
        "actualHostFailureCovered",
        "productionDependenciesTested",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"local simulation can never enable readiness.{key}")

    limitations = contract.get("limitations")
    require(isinstance(limitations, list), "limitations must be list")
    text = "\n".join(item for item in limitations if isinstance(item, str))
    for fragment in (
        "not an operating-system SIGKILL or host crash",
        "not a production lease recommendation",
        "do not establish deletion throughput or capacity",
        "not production-equivalent dependencies",
    ):
        require(fragment in text, f"limitation missing: {fragment}")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema mismatch")
    commit = result.get("commitSha")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, "full source commit SHA required")
    if expected_sha is not None:
        require(commit == expected_sha, f"result source {commit} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment required")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "result dependency mode drift")
    require(environment.get("syntheticDataOnly") is True, "result must remain synthetic-only")
    require(environment.get("leaseAbandonmentSimulation") is True, "simulation classification missing")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "actualProcessKillCovered",
        "actualHostFailureCovered",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"result environment.{key} must remain false")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario required")
    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict), "success criteria missing")
    for key, expected in criteria.items():
        if key == "productionEvidence":
            continue
        require(scenario.get(key) == expected, f"result criterion mismatch: {key}")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    for key in (
        "noClaimBeforeExpiry",
        "bothClaimsReclaimedAfterExpiry",
        "partialObjectErasureRecoveredIdempotently",
        "noResurrection",
        "backlogConverged",
        "allOwnedRowsErased",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    require(assertions.get("actualProcessKillCovered") is False, "simulation cannot claim process kill")
    require(assertions.get("actualHostFailureCovered") is False, "simulation cannot claim host failure")
    require(assertions.get("productionEvidence") is False, "simulation cannot claim production evidence")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "Bearer ",
        "X-Amz-Credential",
        "acct_",
        "job_",
        "upl_",
        "quarantine/",
    ):
        require(forbidden not in serialized, f"forbidden runtime material in result: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    validate_contract(contract)
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion lease recovery validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("actual process kill covered: false")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION LEASE RECOVERY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
