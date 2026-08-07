#!/usr/bin/env python3
"""Validate the in-flight upload-completion deletion fence contract and optional exact-source result."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-upload-completion-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json"
RUNNER_PATH = ROOT / "services/import-api/internal/httpserver/deletion_prefence_upload_completion_test.go"
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
    require(contract.get("schemaVersion") == "memory-os-deletion-prefence-upload-completion.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-prefence-upload-completion-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-prefence-upload-completion-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("inFlightCompletionRequests") == 16, "completion request count drift")
    require(contract.get("surface") == "POST /v1/upload-authorizations/{authorizationId}/complete", "surface drift")
    require(contract.get("pausePoint") == "AFTER_REAL_MINIO_HEAD_BEFORE_POST_HEAD_EPOCH_CHECK", "pause-point drift")

    rules = contract.get("validationRules")
    require(isinstance(rules, dict), "validationRules must be object")
    for key in (
        "runnerMustBeGofmtClean",
        "runnerPackageCompileConfirmed",
        "requestBodySinglePassJSONEncodingRequired",
        "exactSourceBindingRequired",
        "failureDiagnosticRequired",
        "staleEvidenceRejected",
    ):
        require(rules.get(key) is True, f"validation rule must remain true: {key}")

    runner = RUNNER_PATH.read_text(encoding="utf-8")
    helper_start = runner.find("func issueAndPutPrefenceUpload")
    helper_end = runner.find("func TestAccountDeletionPrefenceUploadCompletionLocalDependencies")
    require(helper_start >= 0 and helper_end > helper_start, "upload proof helper not found")
    helper = runner[helper_start:helper_end]
    require("body := map[string]any{" in helper, "upload proof request must pass structured body to live-server helper")
    require("server.request(t, http.MethodPost" in helper, "upload proof must exercise live-server HTTP request helper")
    require("json.Marshal(body)" not in helper, "upload proof request must not pre-marshal a body that server.request marshals")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
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

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    for key in ("contractDefined", "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in ("productionDependenciesTested", "independentReviewCompleted", "productionReady"):
        require(readiness.get(key) is False, f"local completion proof cannot enable readiness.{key}")


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
        require(scenario.get(key) == criteria.get(key), f"result criterion mismatch: {key}")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
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
