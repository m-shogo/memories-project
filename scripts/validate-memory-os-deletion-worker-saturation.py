#!/usr/bin/env python3
"""Validate the bounded multi-account deletion-worker saturation contract and optional result."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def reject_nonfinite_constant(value: str) -> None:
    raise Fail("non-finite worker saturation JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite worker saturation JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate worker saturation JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "worker saturation JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "worker saturation JSON symlink rejected")
    require(path.is_file(), "worker saturation JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise Fail("worker saturation JSON path escaped repository") from None
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError):
        raise Fail("worker saturation JSON unreadable or invalid") from None
    require(isinstance(value, dict), "worker saturation JSON root must be object")
    return value


def strict_utc_timestamp(value: Any) -> None:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            "worker saturation generatedAt must be RFC3339 UTC")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Fail("worker saturation generatedAt calendar invalid") from None


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
    strict_utc_timestamp(result.get("generatedAt"))

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
        expected = criteria.get(key)
        actual = scenario.get(key)
        require(type(actual) is type(expected) and actual == expected,
                f"result criterion mismatch: {key}")
    require(type(scenario.get("deletingAccounts")) is int and scenario.get("deletingAccounts") == contract.get("deletingAccounts"), "deleting account count mismatch")
    require(type(scenario.get("workerCount")) is int and scenario.get("workerCount") == contract.get("workerCount"), "worker count mismatch")
    require(type(scenario.get("maxAccountsPerWorker")) is int and scenario.get("maxAccountsPerWorker") == contract.get("maxAccountsPerWorker"), "worker claim bound mismatch")
    require(type(scenario.get("controlPreviewRequests")) is int and scenario.get("controlPreviewRequests") == contract.get("controlPreviewRequests"), "control request count mismatch")
    require(type(scenario.get("controlPreviewConcurrency")) is int and scenario.get("controlPreviewConcurrency") == contract.get("controlPreviewConcurrency"), "control concurrency mismatch")
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

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "bearer ",
        "x-amz-credential",
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
    for candidate in (RESULT_PATH, *RESULT_PATH.parents):
        require(not candidate.is_symlink(), "worker saturation result symlink rejected")
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
