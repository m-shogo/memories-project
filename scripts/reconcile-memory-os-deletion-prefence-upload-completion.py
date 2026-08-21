#!/usr/bin/env python3
"""Reconcile exact-source in-flight upload completion fence evidence into its local-only contract."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CANONICAL_ROOT = Path(__file__).resolve().parents[1]
ROOT = CANONICAL_ROOT
CANONICAL_CONTRACT_PATH = CANONICAL_ROOT / "contracts/operations/deletion-prefence-upload-completion-contract.v1.json"
CANONICAL_RESULT_PATH = CANONICAL_ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json"
CANONICAL_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-prefence-upload-completion.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
VALIDATOR = CANONICAL_VALIDATOR
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


def _require_exact_path(label: str, actual: Path, expected: Path) -> None:
    require(actual == expected, f"{label} path is not canonical")
    require(not actual.is_symlink(), f"{label} authority may not be a symlink")
    try:
        actual_resolved = actual.resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
    except OSError as exc:
        raise Fail(f"{label} authority is unreadable") from exc
    require(actual_resolved == expected_resolved, f"{label} authority does not resolve canonically")
    require(actual_resolved.is_file(), f"{label} authority must be a regular file")


def validate_authority_identity() -> None:
    require(ROOT == CANONICAL_ROOT and ROOT.resolve() == CANONICAL_ROOT.resolve(), "repository root authority is not canonical")
    _require_exact_path("upload completion contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH)
    _require_exact_path("upload completion result", RESULT_PATH, CANONICAL_RESULT_PATH)
    _require_exact_path("upload completion validator", VALIDATOR, CANONICAL_VALIDATOR)


def run_validator(expected: str) -> None:
    subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-result", "--expected-commit-sha", expected],
        cwd=ROOT,
        check=True,
    )


def atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_contract_transactionally(contract: dict[str, Any], expected: str) -> None:
    original = CONTRACT_PATH.read_bytes()
    candidate = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(CONTRACT_PATH, candidate)
    try:
        run_validator(expected)
    except BaseException:
        atomic_write_bytes(CONTRACT_PATH, original)
        raise


def main() -> int:
    expected = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected) is not None, "EXPECTED_COMMIT_SHA must be full SHA")
    validate_authority_identity()
    run_validator(expected)

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

    write_contract_transactionally(contract, expected)

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
