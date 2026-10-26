#!/usr/bin/env python3
"""Validate the deletion pre-fence in-flight linearization contract and optional exact-source result."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-linearization-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-linearization-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


EXPECTED_LIMITATIONS = ("Preview read is the first in-flight surface proven", "one account and one deletion worker", "local PostgreSQL 16 and MinIO on a GitHub-hosted runner", "does not prove host-failure behavior or multi-account worker saturation", "not production deletion-capacity evidence",)
EXPECTED_BOUNDARY_KEYS = ("syntheticDataOnly", "productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "previewReadSurfaceOnly", "hostFailureCovered", "multiAccountWorkerSaturationCovered", "productionReady",)
EXPECTED_READINESS_KEYS = ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented", "exactSourceResultCommitted", "preFenceInFlightLinearizationProven", "productionDependenciesTested", "independentReviewCompleted", "productionReady",)

EXPECTED_PATHS: dict[str, str] = {
    "resultPath": "docs/fixtures/memory-os-operability/deletion-prefence-linearization-results.sample.v1.json",
    "runner": "services/import-api/internal/httpserver/deletion_prefence_linearization_test.go",
    "validator": "scripts/validate-memory-os-deletion-prefence-linearization.py",
    "reconcile": "scripts/reconcile-memory-os-deletion-prefence-linearization.py",
    "workflow": ".github/workflows/deletion-prefence-linearization.yml",
}

EXPECTED_SEQUENCE = (
    "create one synthetic active account, session and committed Preview",
    "start 32 authenticated Preview requests",
    "prove all 32 session lookups completed successfully at account epoch 1",
    "pause all 32 requests before the fenced Preview service executes",
    "DELETE /v1/account returns 202 with durable deletion epoch 2",
    "release the already-authenticated old-epoch requests",
    "all 32 requests return exactly 401 with no transport error or successful response",
    "leased deletion worker completes exactly one receipt",
    "all account-owned rows are erased and deleted tombstone remains at epoch 2",
)


EXPECTED_ABORT = (
    "any request reaches the service before all 32 old-epoch session resolutions are paused",
    "DELETE does not return 202 with epoch 2",
    "any released old-epoch request returns anything other than 401",
    "any released request has a transport error",
    "deletion worker processes zero or more than one account",
    "any account-owned row survives worker completion",
    "result contains bearer token, account id, job id, Preview id, object key, endpoint credential or database URL",
)


EXPECTED_CRITERIA: dict[str, Any] = {
    "authenticatedBeforeFence": 32,
    "deletionRequestStatus": 202,
    "deletionEpoch": 2,
    "releasedAfterFence": 32,
    "unauthorizedAfterFence": 32,
    "unexpectedStatusCount": 0,
    "transportErrors": 0,
    "workerReceiptCount": 1,
    "finalOwnedRowCount": 0,
    "finalAccountState": "deleted",
    "finalAccountEpoch": 2,
    "productionEvidence": False,
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def reject_nonfinite_constant(_value: str) -> None:
    raise Fail("non-finite pre-fence JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite pre-fence JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate pre-fence JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "pre-fence JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "pre-fence JSON symlink rejected")
    require(path.is_file(), "pre-fence JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError, RuntimeError):
        raise Fail("pre-fence JSON path escaped repository") from None
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("pre-fence JSON unreadable or invalid") from None
    require(isinstance(value, dict), "pre-fence JSON root must be object")
    return value

def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("contractId") == "memory-os.operability.deletion-prefence-linearization.v1", "contract identity drift")
    require(contract.get("schemaVersion") == "memory-os-deletion-prefence-linearization.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-prefence-linearization-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-prefence-inflight-linearization-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(type(contract.get("inFlightRequests")) is int and contract["inFlightRequests"] == 32,
            "in-flight request count drift")
    require(contract.get("surface") == "GET /v1/import-jobs/{jobId}/preview", "surface drift")

    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict) and criteria.keys() == EXPECTED_CRITERIA.keys(),
            "success criteria key set drift")
    for key, expected in EXPECTED_CRITERIA.items():
        actual = criteria[key]
        require(type(actual) is type(expected) and actual == expected,
                f"success criterion type/value drift: {key}")

    for key, expected in EXPECTED_PATHS.items():
        require(contract.get(key) == expected, f"contract source/path binding drift: {key}")

    for key, expected in (("requiredSequence", EXPECTED_SEQUENCE), ("abortCriteria", EXPECTED_ABORT)):
        actual = contract.get(key)
        require(type(actual) is list and actual == list(expected),
                f"reviewed {key} list drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.keys() == set(EXPECTED_BOUNDARY_KEYS), "evidence boundary key set drift")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "hostFailureCovered",
        "multiAccountWorkerSaturationCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local checkpoint cannot enable {key}")
    require(boundary.get("previewReadSurfaceOnly") is True, "Preview-only limitation must remain explicit")

    require(type(contract.get("limitations")) is list and
            contract["limitations"] == list(EXPECTED_LIMITATIONS),
            "reviewed limitations list drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    require(readiness.keys() == set(EXPECTED_READINESS_KEYS), "readiness key set drift")
    for key in EXPECTED_READINESS_KEYS:
        require(type(readiness[key]) is bool, f"readiness.{key} must be boolean")
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
        "authenticatedBeforeFence",
        "deletionRequestStatus",
        "deletionEpoch",
        "releasedAfterFence",
        "unauthorizedAfterFence",
        "unexpectedStatusCount",
        "transportErrors",
        "workerReceiptCount",
        "finalOwnedRowCount",
        "finalAccountState",
        "finalAccountEpoch",
    ):
        require(key in scenario and type(scenario[key]) is type(criteria[key])
                and scenario[key] == criteria[key], f"result criterion mismatch: {key}")
    require(type(scenario.get("inFlightRequests")) is int
            and scenario["inFlightRequests"] == contract["inFlightRequests"], "in-flight request count mismatch")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    for key in (
        "allAuthenticatedBeforeFence",
        "allReleasedAfterFenceUnauthorized",
        "noUnexpectedStatuses",
        "noTransportErrors",
        "deletionWorkerCompleted",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    require(assertions.get("productionEvidence") is False, "productionEvidence assertion must stay false")

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
        require(forbidden not in serialized, "forbidden runtime material in result")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    validate_contract(contract)
    for candidate in (RESULT_PATH, *RESULT_PATH.parents):
        require(not candidate.is_symlink(), "pre-fence result symlink rejected")
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion pre-fence linearization validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION PRE-FENCE LINEARIZATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
