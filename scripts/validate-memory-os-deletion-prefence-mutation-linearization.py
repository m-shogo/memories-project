#!/usr/bin/env python3
"""Validate Apply/upload pre-fence mutation linearization contract and optional exact-source result."""

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
CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-mutation-linearization-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-mutation-linearization-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


EXPECTED_RESULT_KEYS = ("schemaVersion", "commitSha", "generatedAt", "environment", "scenario", "limitations",)
EXPECTED_RESULT_LIMITATIONS = ("covers Apply and upload authorization but not upload completion already in flight", "one synthetic account and one deletion worker", "local PostgreSQL 16 and MinIO on a GitHub-hosted runner", "not production deletion-capacity evidence",)
EXPECTED_ENVIRONMENT_KEYS = ("os", "arch", "goVersion", "dependencyMode", "syntheticDataOnly", "productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "containsSecrets",)
EXPECTED_SCENARIO_KEYS = ("scenarioId", "applyRequests", "uploadAuthorizationRequests", "authenticatedBeforeFence", "deletionRequestStatus", "deletionEpoch", "applyUnauthorizedAfterFence", "uploadAuthorizationUnauthorizedAfterFence", "unexpectedStatusCount", "transportErrors", "preWorkerApplyConfirmationRows", "preWorkerMemoryItemRows", "preWorkerUploadAuthorizationRows", "preWorkerQuarantineRows", "workerReceiptCount", "finalOwnedRowCount", "finalAccountState", "finalAccountEpoch", "assertions", "result", "integrityResult",)
EXPECTED_ASSERTION_KEYS = ("allApplyUnauthorizedAfterFence", "allAuthenticatedBeforeFence", "allUploadAuthorizationUnauthorizedAfterFence", "deletionWorkerCompleted", "finalOwnedRowCount", "noPreWorkerMutation", "noTransportErrors", "noUnexpectedStatuses", "productionEvidence",)
EXPECTED_LIMITATIONS = ("covers Apply and upload authorization but not upload completion already in flight", "one synthetic account and one deletion worker", "local PostgreSQL 16 and MinIO on a GitHub-hosted runner", "does not prove host/process failure behavior", "not production deletion-capacity evidence",)
EXPECTED_BOUNDARY_KEYS = ("syntheticDataOnly", "productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "applySurfaceCovered", "uploadAuthorizationSurfaceCovered", "uploadCompletionSurfaceCovered", "hostFailureCovered", "productionReady",)
EXPECTED_READINESS_KEYS = ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented", "exactSourceResultCommitted", "preFenceMutationLinearizationProven", "productionDependenciesTested", "independentReviewCompleted", "productionReady",)

EXPECTED_PATHS: dict[str, str] = {
    "resultPath": "docs/fixtures/memory-os-operability/deletion-prefence-mutation-linearization-results.sample.v1.json",
    "runner": "services/import-api/internal/httpserver/deletion_prefence_mutation_linearization_test.go",
    "validator": "scripts/validate-memory-os-deletion-prefence-mutation-linearization.py",
    "reconcile": "scripts/reconcile-memory-os-deletion-prefence-mutation-linearization.py",
    "workflow": ".github/workflows/deletion-prefence-mutation-linearization.yml",
}

EXPECTED_RULES = (
    "runnerMustBeGofmtClean",
    "exactSourceBindingRequired",
    "failureDiagnosticRequired",
    "staleEvidenceRejected",
)


EXPECTED_SEQUENCE = (
    "create one synthetic active account, one committed Preview and 16 upload-target import jobs",
    "start 16 Apply and 16 upload-authorization HTTP requests",
    "prove all 32 session resolutions complete successfully at account epoch 1",
    "pause all 32 before their fenced services execute",
    "DELETE /v1/account returns 202 with durable deletion epoch 2",
    "release the already-authenticated old-epoch requests",
    "all 16 Apply and all 16 upload-authorization requests return exactly 401",
    "before deletion worker erasure, apply_confirmation, memory_item, upload_authorization and quarantine_object mutation counts attributable to the paused requests remain zero",
    "leased deletion worker completes exactly one receipt and all account-owned rows converge to zero",
)


EXPECTED_ABORT = (
    "any request reaches its fenced service before all 32 old-epoch sessions are paused",
    "DELETE does not return 202 with epoch 2",
    "any released Apply or upload-authorization request returns anything other than 401",
    "any released request has a transport error",
    "any Apply or upload durable mutation appears before worker erasure",
    "deletion worker processes zero or more than one account",
    "any account-owned row survives worker completion",
    "result contains bearer token, account id, job id, Preview id, object key, idempotency key, endpoint credential or database URL",
)


EXPECTED_CRITERIA: dict[str, Any] = {
    "authenticatedBeforeFence": 32,
    "deletionRequestStatus": 202,
    "deletionEpoch": 2,
    "applyUnauthorizedAfterFence": 16,
    "uploadAuthorizationUnauthorizedAfterFence": 16,
    "unexpectedStatusCount": 0,
    "transportErrors": 0,
    "preWorkerApplyConfirmationRows": 0,
    "preWorkerMemoryItemRows": 0,
    "preWorkerUploadAuthorizationRows": 0,
    "preWorkerQuarantineRows": 0,
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
    raise Fail("non-finite pre-fence mutation JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite pre-fence mutation JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate pre-fence mutation JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "pre-fence mutation JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "pre-fence mutation JSON symlink rejected")
    require(path.is_file(), "pre-fence mutation JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError, RuntimeError):
        raise Fail("pre-fence mutation JSON path escaped repository") from None
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("pre-fence mutation JSON unreadable or invalid") from None
    require(isinstance(value, dict), "pre-fence mutation JSON root must be object")
    return value

def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("contractId") == "memory-os.operability.deletion-prefence-mutation-linearization.v1", "contract identity drift")
    require(contract.get("schemaVersion") == "memory-os-deletion-prefence-mutation-linearization.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-prefence-mutation-linearization-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-prefence-mutation-linearization-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(type(contract.get("applyRequests")) is int and contract["applyRequests"] == 16, "Apply request count drift")
    require(type(contract.get("uploadAuthorizationRequests")) is int and contract["uploadAuthorizationRequests"] == 16, "upload authorization request count drift")
    require(type(contract.get("totalInFlightRequests")) is int and contract["totalInFlightRequests"] == 32, "total in-flight request count drift")
    surfaces = contract.get("surfaces")
    require(type(surfaces) is list and surfaces == [
        "POST /v1/previews/{previewId}/apply",
        "POST /v1/import-jobs/{jobId}/upload-authorizations",
    ], "reviewed surface list drift")

    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict) and criteria.keys() == EXPECTED_CRITERIA.keys(),
            "success criteria key set drift")
    for key, expected in EXPECTED_CRITERIA.items():
        actual = criteria[key]
        require(type(actual) is type(expected) and actual == expected,
                f"success criterion type/value drift: {key}")

    for key, expected in EXPECTED_PATHS.items():
        require(contract.get(key) == expected, f"contract source/path binding drift: {key}")

    rules = contract.get("validationRules")
    require(type(rules) is dict and rules.keys() == set(EXPECTED_RULES),
            "validation rule key set drift")
    for key in EXPECTED_RULES:
        require(rules[key] is True, f"validation rule must remain true: {key}")

    for key, expected in (("requiredSequence", EXPECTED_SEQUENCE), ("abortCriteria", EXPECTED_ABORT)):
        actual = contract.get(key)
        require(type(actual) is list and actual == list(expected),
                f"reviewed {key} list drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.keys() == set(EXPECTED_BOUNDARY_KEYS), "evidence boundary key set drift")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    require(boundary.get("applySurfaceCovered") is True, "Apply coverage must remain explicit")
    require(boundary.get("uploadAuthorizationSurfaceCovered") is True, "upload authorization coverage must remain explicit")
    require(boundary.get("uploadCompletionSurfaceCovered") is False, "upload completion must remain unproven")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "hostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local mutation proof cannot enable {key}")

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
        require(readiness.get(key) is False, f"local mutation proof cannot enable readiness.{key}")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.keys() == set(EXPECTED_RESULT_KEYS), "result top-level key set drift")
    require(type(result.get("limitations")) is list and
            result["limitations"] == list(EXPECTED_RESULT_LIMITATIONS),
            "reviewed result limitations drift")
    generated_at = result.get("generatedAt")
    require(type(generated_at) is str and
            re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z", generated_at) is not None,
            "result generatedAt must be exact UTC RFC3339 seconds")
    try:
        datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise Fail("result generatedAt calendar invalid") from None

    require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema mismatch")
    commit = result.get("commitSha")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, "full source commit SHA required")
    if expected_sha is not None:
        require(commit == expected_sha, f"result source {commit} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment required")
    require(environment.keys() == set(EXPECTED_ENVIRONMENT_KEYS), "environment key set drift")
    for key in ("os", "arch", "goVersion"):
        require(type(environment.get(key)) is str and bool(environment[key].strip()),
                f"environment.{key} metadata must be nonempty string")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "result dependency mode drift")
    require(environment.get("syntheticDataOnly") is True, "result must remain synthetic-only")
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
    require(scenario.keys() == set(EXPECTED_SCENARIO_KEYS), "scenario key set drift")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), "result scenario drift")
    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict), "success criteria missing")
    for key in (
        "authenticatedBeforeFence",
        "deletionRequestStatus",
        "deletionEpoch",
        "applyUnauthorizedAfterFence",
        "uploadAuthorizationUnauthorizedAfterFence",
        "unexpectedStatusCount",
        "transportErrors",
        "preWorkerApplyConfirmationRows",
        "preWorkerMemoryItemRows",
        "preWorkerUploadAuthorizationRows",
        "preWorkerQuarantineRows",
        "workerReceiptCount",
        "finalOwnedRowCount",
        "finalAccountState",
        "finalAccountEpoch",
    ):
        require(key in scenario and type(scenario[key]) is type(criteria[key])
                and scenario[key] == criteria[key], f"result criterion mismatch: {key}")
    require(type(scenario.get("applyRequests")) is int and scenario["applyRequests"] == contract["applyRequests"], "Apply request count mismatch")
    require(type(scenario.get("uploadAuthorizationRequests")) is int and scenario["uploadAuthorizationRequests"] == contract["uploadAuthorizationRequests"], "upload authorization count mismatch")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    require(assertions.keys() == set(EXPECTED_ASSERTION_KEYS), "assertion key set drift")
    require(type(assertions["finalOwnedRowCount"]) is int and
            assertions["finalOwnedRowCount"] == scenario["finalOwnedRowCount"],
            "assertion final owned row count drift")
    for key in (
        "allAuthenticatedBeforeFence",
        "allApplyUnauthorizedAfterFence",
        "allUploadAuthorizationUnauthorizedAfterFence",
        "noUnexpectedStatuses",
        "noTransportErrors",
        "noPreWorkerMutation",
        "deletionWorkerCompleted",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    require(assertions.get("productionEvidence") is False, "productionEvidence assertion must remain false")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "bearer ",
        "x-amz-credential",
        "acct_",
        "job_",
        "preview_",
        "idem-",
        "quarantine/",
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
        require(not candidate.is_symlink(), "pre-fence mutation result symlink rejected")
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion pre-fence mutation linearization validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("upload completion pre-fence coverage: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION PRE-FENCE MUTATION LINEARIZATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
