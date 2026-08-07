#!/usr/bin/env python3
"""Validate the bounded multi-account deletion-worker saturation contract and optional result."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
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
    require(contract.get("schemaVersion") == "memory-os-deletion-worker-saturation.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-worker-saturation-results.v1", "results schema drift")
    require(contract.get("scenarioId") == "multi-account-deletion-worker-saturation-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("deletingAccounts") == 24, "deleting account count drift")
    require(contract.get("workerCount") == 4, "worker count drift")
    require(contract.get("maxAccountsPerWorker") == 6, "worker claim bound drift")
    require(contract.get("controlPreviewRequests") == 400, "control request count drift")
    require(contract.get("controlPreviewConcurrency") == 16, "control concurrency drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "hostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local saturation contract cannot enable {key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    for key in ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in ("productionDependenciesTested", "independentReviewCompleted", "productionReady"):
        require(readiness.get(key) is False, f"local evidence cannot enable readiness.{key}")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema mismatch")
    commit = result.get("commitSha")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, "full commit SHA required")
    if expected_sha is not None:
        require(commit == expected_sha, f"result source {commit} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment required")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "result dependency mode drift")
    require(environment.get("syntheticDataOnly") is True, "result must be synthetic-only")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"result environment.{key} must remain false")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario required")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), "result scenario drift")
    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict), "success criteria missing")
    for key in (
        "allDeletionRequestsAccepted",
        "deletionEpoch",
        "workerErrors",
        "workerReceiptCount",
        "uniqueWorkerReceiptCount",
        "duplicateWorkerReceiptCount",
        "controlPreview2xx",
        "controlPreview5xx",
        "controlPreviewTransportErrors",
        "finalDeletionPending",
        "finalDeletionStuck",
        "finalOwnedRowCount",
        "allDeletionTombstonesEpoch2",
    ):
        require(scenario.get(key) == criteria.get(key), f"result criterion mismatch: {key}")
    require(scenario.get("deletingAccounts") == contract.get("deletingAccounts"), "deleting account count mismatch")
    require(scenario.get("workerCount") == contract.get("workerCount"), "worker count mismatch")
    require(scenario.get("maxAccountsPerWorker") == contract.get("maxAccountsPerWorker"), "worker claim bound mismatch")
    require(scenario.get("controlPreviewRequests") == contract.get("controlPreviewRequests"), "control request count mismatch")
    require(scenario.get("controlPreviewConcurrency") == contract.get("controlPreviewConcurrency"), "control concurrency mismatch")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    for key in (
        "allDeletionRequestsAccepted",
        "workerReceiptsUnique",
        "controlPreviewAll2xx",
        "deletionBacklogConverged",
        "finalOwnedRowsZero",
        "allDeletionTombstonesEpoch2",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    for key in ("capacityBoundaryEstablished", "operationalThresholdApproved", "productionEvidence"):
        require(assertions.get(key) is False, f"local result cannot enable assertion {key}")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "Bearer ",
        "X-Amz-Credential",
        "acct_",
        "job_",
    ):
        require(forbidden not in serialized, f"forbidden sensitive/runtime material in result: {forbidden}")


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

    print("Memory OS deletion-worker saturation validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("capacity boundary established: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION WORKER SATURATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
