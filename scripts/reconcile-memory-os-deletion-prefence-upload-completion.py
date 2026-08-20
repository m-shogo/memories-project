#!/usr/bin/env python3
"""Reconcile exact-source in-flight upload completion fence evidence into its local-only contract."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-upload-completion-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-prefence-upload-completion.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    expected = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected) is not None, "EXPECTED_COMMIT_SHA must be full SHA")
    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    require(result.get("commitSha") == expected, "result does not match exact source")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario missing")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "result is not PASS")
    require(scenario.get("issuedAndUploadedBeforeFence") == 16, "pre-fence upload setup incomplete")
    require(scenario.get("realHeadCompletedBeforeFence") == 16, "real MinIO HEAD proof incomplete")
    require(scenario.get("completionUnauthorizedAfterFence") == 16, "post-HEAD fence rejection proof incomplete")
    for key in (
        "unexpectedStatusCount",
        "transportErrors",
        "preWorkerConsumedAuthorizationRows",
        "preWorkerQuarantineRows",
        "finalOwnedRowCount",
    ):
        require(scenario.get(key) == 0, f"completion/integrity criterion drift: {key}")
    require(scenario.get("preWorkerIssuedAuthorizationRows") == 16, "issued authorization ledger did not remain intact")
    require(scenario.get("workerReceiptCount") == 1, "deletion worker receipt count drift")
    require(scenario.get("erasedObjectVersions") == 16, "object-version erasure count drift")
    require(scenario.get("finalAccountState") == "deleted" and scenario.get("finalAccountEpoch") == 2, "final deletion tombstone drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["preFenceUploadCompletionLinearizationProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("realMinioHeadCovered") is True, "real MinIO HEAD coverage drift")
    require(boundary.get("postHeadFenceCovered") is True, "post-HEAD fence coverage drift")
    require(boundary.get("hostFailureCovered") is False, "host failure cannot be promoted by this proof")
    require(boundary.get("productionEvidence") is False, "local proof cannot become production evidence")
    require(boundary.get("productionEquivalentDependencies") is False, "local proof cannot become production-equivalent evidence")

    original = CONTRACT_PATH.read_bytes()
    try:
        CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        subprocess.run(
            ["python", str(VALIDATOR), "--require-result", "--expected-commit-sha", expected],
            cwd=ROOT,
            check=True,
        )
    except BaseException:
        CONTRACT_PATH.write_bytes(original)
        raise

    print("Memory OS deletion pre-fence upload-completion authority reconciled")
    print("real MinIO HEAD before fence: true")
    print("post-HEAD epoch checkpoint: true")
    print("host failure covered: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"DELETION PRE-FENCE UPLOAD COMPLETION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
