#!/usr/bin/env python3
"""Validate the in-flight upload-completion deletion fence contract and optional exact-source result."""

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
CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-upload-completion-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json"
RUNNER_PATH = ROOT / "services/import-api/internal/httpserver/deletion_prefence_upload_completion_test.go"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

EXPECTED_RESULT_KEYS = ("schemaVersion", "commitSha", "generatedAt", "environment", "scenario", "limitations",)
EXPECTED_RESULT_LIMITATIONS = ("one synthetic account and 16 in-flight upload-completion requests", "local PostgreSQL 16 and versioned MinIO on a GitHub-hosted runner", "does not prove process or host failure during deletion-worker erasure", "not production deletion-capacity evidence",)
EXPECTED_ENVIRONMENT_KEYS = ("os", "arch", "goVersion", "dependencyMode", "syntheticDataOnly", "productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "containsSecrets",)
EXPECTED_SCENARIO_KEYS = ("scenarioId", "issuedAndUploadedBeforeFence", "realHeadCompletedBeforeFence", "deletionRequestStatus", "deletionEpoch", "completionUnauthorizedAfterFence", "unexpectedStatusCount", "transportErrors", "preWorkerIssuedAuthorizationRows", "preWorkerConsumedAuthorizationRows", "preWorkerQuarantineRows", "workerReceiptCount", "erasedObjectVersions", "finalOwnedRowCount", "finalAccountState", "finalAccountEpoch", "assertions", "result", "integrityResult",)
EXPECTED_ASSERTION_KEYS = ("allCompletionRequestsUnauthorizedAfterFence", "allRealHeadsCompletedBeforeFence", "allUploadedObjectVersionsErased", "deletionWorkerCompleted", "finalOwnedRowCount", "noCompletionMutationBeforeWorker", "noTransportErrors", "noUnexpectedStatuses", "productionEvidence",)
EXPECTED_LIMITATIONS = ("one synthetic account and 16 completion requests", "local PostgreSQL 16 and MinIO on a GitHub-hosted runner", "proves the post-HEAD completion fence but not process/host failure during deletion worker erasure", "not production deletion-capacity evidence",)
EXPECTED_BOUNDARY_KEYS = ("syntheticDataOnly", "productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "realMinioHeadCovered", "postHeadFenceCovered", "hostFailureCovered", "productionReady",)
EXPECTED_READINESS_KEYS = ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented", "exactSourceResultCommitted", "preFenceUploadCompletionLinearizationProven", "productionDependenciesTested", "independentReviewCompleted", "productionReady",)

EXPECTED_PATHS: dict[str, str] = {
    "resultPath": "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json",
    "runner": "services/import-api/internal/httpserver/deletion_prefence_upload_completion_test.go",
    "validator": "scripts/validate-memory-os-deletion-prefence-upload-completion.py",
    "reconcile": "scripts/reconcile-memory-os-deletion-prefence-upload-completion.py",
    "workflow": ".github/workflows/deletion-prefence-upload-completion.yml",
}

EXPECTED_RULES = (
    "runnerMustBeGofmtClean",
    "runnerPackageCompileConfirmed",
    "requestBodySinglePassJSONEncodingRequired",
    "exactSourceBindingRequired",
    "failureDiagnosticRequired",
    "staleEvidenceRejected",
)


EXPECTED_SEQUENCE = (
    "create one synthetic active account and 16 uploadable import jobs",
    "issue 16 upload authorizations at account epoch 1 using the live-server request helper with exactly one JSON encoding pass",
    "perform 16 real presigned PUTs to local versioned MinIO",
    "start 16 authenticated upload-completion requests",
    "prove all 16 requests pass the outer fence and initial database snapshot by reaching and completing real MinIO HEAD",
    "pause all 16 before the guarded object-store post-HEAD epoch checkpoint returns",
    "DELETE /v1/account returns 202 with durable deletion epoch 2",
    "release the 16 already-in-flight completion requests",
    "all 16 return exactly 401 with no transport errors",
    "before worker erasure all 16 authorizations remain issued, zero are consumed and zero quarantine scan rows exist",
    "leased deletion worker erases all uploaded object versions and all owned database rows, leaving deleted epoch-2 tombstone",
)


EXPECTED_ABORT = (
    "upload-authorization fixture applies JSON encoding more than once",
    "any completion request fails to reach real MinIO HEAD before the deletion fence",
    "any request returns from the post-HEAD checkpoint before all 16 are paused",
    "DELETE does not return 202 with epoch 2",
    "any released completion returns anything other than 401",
    "any released completion has a transport error",
    "any authorization becomes consumed or any quarantine scan row appears before worker erasure",
    "worker erases fewer or more than the 16 uploaded object versions",
    "any account-owned row survives worker completion",
    "result contains bearer token, account id, job id, authorization id, object key, signed URL, endpoint credential or database URL",
)


EXPECTED_CRITERIA: dict[str, Any] = {
    "issuedAndUploadedBeforeFence": 16,
    "realHeadCompletedBeforeFence": 16,
    "deletionRequestStatus": 202,
    "deletionEpoch": 2,
    "completionUnauthorizedAfterFence": 16,
    "unexpectedStatusCount": 0,
    "transportErrors": 0,
    "preWorkerIssuedAuthorizationRows": 16,
    "preWorkerConsumedAuthorizationRows": 0,
    "preWorkerQuarantineRows": 0,
    "workerReceiptCount": 1,
    "erasedObjectVersions": 16,
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
    raise Fail("non-finite pre-fence upload JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite pre-fence upload JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate pre-fence upload JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "pre-fence upload JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "pre-fence upload JSON symlink rejected")
    require(path.is_file(), "pre-fence upload JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError, RuntimeError):
        raise Fail("pre-fence upload JSON path escaped repository") from None
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("pre-fence upload JSON unreadable or invalid") from None
    require(isinstance(value, dict), "pre-fence upload JSON root must be object")
    return value

def read_runner() -> str:
    """Read only a regular in-repository Go runner without following symlinks."""
    path = RUNNER_PATH
    require(isinstance(path, Path), "upload runner path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "upload runner symlink rejected")
    require(path.is_file(), "upload runner missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError, RuntimeError):
        raise Fail("upload runner escaped repository") from None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        raise Fail("upload runner unreadable or invalid") from None


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("contractId") == "memory-os.operability.deletion-prefence-upload-completion.v1", "contract identity drift")
    require(contract.get("schemaVersion") == "memory-os-deletion-prefence-upload-completion.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-prefence-upload-completion-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-prefence-upload-completion-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(type(contract.get("inFlightCompletionRequests")) is int
            and contract["inFlightCompletionRequests"] == 16, "completion request count drift")
    require(contract.get("surface") == "POST /v1/upload-authorizations/{authorizationId}/complete", "surface drift")
    require(contract.get("pausePoint") == "AFTER_REAL_MINIO_HEAD_BEFORE_POST_HEAD_EPOCH_CHECK", "pause-point drift")

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

    runner = read_runner()
    helper_start = runner.find("func issueAndPutPrefenceUpload")
    helper_end = runner.find("func TestAccountDeletionPrefenceUploadCompletionLocalDependencies")
    require(helper_start >= 0 and helper_end > helper_start, "upload proof helper not found")
    helper = runner[helper_start:helper_end]
    require("body := map[string]any{" in helper, "upload proof request must pass structured body to live-server helper")
    require("server.request(t, http.MethodPost" in helper, "upload proof must exercise live-server HTTP request helper")
    require("json.Marshal(body)" not in helper, "upload proof request must not pre-marshal a body that server.request marshals")

    for key, expected in (("requiredSequence", EXPECTED_SEQUENCE), ("abortCriteria", EXPECTED_ABORT)):
        actual = contract.get(key)
        require(type(actual) is list and actual == list(expected),
                f"reviewed {key} list drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.keys() == set(EXPECTED_BOUNDARY_KEYS), "evidence boundary key set drift")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    require(boundary.get("realMinioHeadCovered") is True, "real MinIO HEAD coverage required")
    require(boundary.get("postHeadFenceCovered") is True, "post-HEAD fence coverage required")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "hostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local completion proof cannot enable {key}")

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
        require(readiness.get(key) is False, f"local completion proof cannot enable readiness.{key}")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.keys() == set(EXPECTED_RESULT_KEYS), "result top-level key set drift")
    require(type(result.get("limitations")) is list and
            result["limitations"] == list(EXPECTED_RESULT_LIMITATIONS),
            "reviewed result limitations drift")
    generated_at = result.get("generatedAt")
    require(type(generated_at) is str and
            re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at) is not None,
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
        "issuedAndUploadedBeforeFence",
        "realHeadCompletedBeforeFence",
        "deletionRequestStatus",
        "deletionEpoch",
        "completionUnauthorizedAfterFence",
        "unexpectedStatusCount",
        "transportErrors",
        "preWorkerIssuedAuthorizationRows",
        "preWorkerConsumedAuthorizationRows",
        "preWorkerQuarantineRows",
        "workerReceiptCount",
        "erasedObjectVersions",
        "finalOwnedRowCount",
        "finalAccountState",
        "finalAccountEpoch",
    ):
        require(key in scenario and type(scenario[key]) is type(criteria[key])
                and scenario[key] == criteria[key], f"result criterion mismatch: {key}")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    require(assertions.keys() == set(EXPECTED_ASSERTION_KEYS), "assertion key set drift")
    require(type(assertions["finalOwnedRowCount"]) is int and
            assertions["finalOwnedRowCount"] == scenario["finalOwnedRowCount"],
            "assertion final owned row count drift")
    for key in (
        "allRealHeadsCompletedBeforeFence",
        "allCompletionRequestsUnauthorizedAfterFence",
        "noUnexpectedStatuses",
        "noTransportErrors",
        "noCompletionMutationBeforeWorker",
        "allUploadedObjectVersionsErased",
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
        "upl_",
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
        require(not candidate.is_symlink(), "pre-fence upload result symlink rejected")
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion pre-fence upload completion validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("request body single-pass encoding: true")
    print("post-HEAD fence covered: true")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION PRE-FENCE UPLOAD COMPLETION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
