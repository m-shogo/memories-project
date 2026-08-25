#!/usr/bin/env python3
"""Reconcile exact-source Apply/upload pre-fence mutation evidence into its local-only contract."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CANONICAL_ROOT = Path(__file__).resolve().parents[1]
ROOT = CANONICAL_ROOT
CANONICAL_CONTRACT_PATH = CANONICAL_ROOT / "contracts/operations/deletion-prefence-mutation-linearization-contract.v1.json"
CANONICAL_RESULT_PATH = CANONICAL_ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-mutation-linearization-results.sample.v1.json"
CANONICAL_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-prefence-mutation-linearization.py"
CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_OS_REPLACE = os.replace
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


def _require_exact_path(label: str, actual: Path, expected: Path, *, must_exist: bool = True) -> None:
    require(actual == expected, f"{label} path is not canonical")
    require(not actual.is_symlink(), f"{label} authority may not be a symlink")
    if not actual.exists():
        require(not must_exist, f"{label} authority is unreadable")
        return
    try:
        require(actual.resolve(strict=True) == expected.resolve(strict=True), f"{label} authority does not resolve canonically")
    except OSError as exc:
        raise Fail(f"{label} authority is unreadable") from exc
    require(actual.resolve().is_file(), f"{label} authority must be a regular file")


def validate_authority_identity() -> None:
    require(ROOT == CANONICAL_ROOT and ROOT.resolve() == CANONICAL_ROOT.resolve(), "repository root authority is not canonical")
    _require_exact_path("pre-fence mutation contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH)
    _require_exact_path("pre-fence mutation result", RESULT_PATH, CANONICAL_RESULT_PATH, must_exist=False)
    _require_exact_path("pre-fence mutation validator", VALIDATOR, CANONICAL_VALIDATOR)
    require(subprocess.run is CANONICAL_SUBPROCESS_RUN, "validator execution transport is not canonical")
    require(os.replace is CANONICAL_OS_REPLACE, "atomic replacement transport is not canonical")
    require(atomic_write_bytes is CANONICAL_ATOMIC_WRITE_BYTES, "atomic writer authority is not canonical")


def run_validator(expected: str) -> None:
    validate_authority_identity()
    subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-result", "--expected-commit-sha", expected],
        cwd=ROOT,
        check=True,
    )


def atomic_write_bytes(path: Path, data: bytes) -> None:
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, existing_mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def write_contract_transactionally(contract: dict[str, Any], expected: str) -> None:
    validate_authority_identity()
    original = CONTRACT_PATH.read_bytes()
    candidate = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(CONTRACT_PATH, candidate)
    try:
        run_validator(expected)
    except BaseException:
        CANONICAL_ATOMIC_WRITE_BYTES(CONTRACT_PATH, original)
        raise


def main() -> int:
    expected = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected) is not None, "EXPECTED_COMMIT_SHA must be full SHA")
    validate_authority_identity()
    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    require(result.get("commitSha") == expected, "result does not match exact source")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario missing")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "result is not PASS")
    require(scenario.get("authenticatedBeforeFence") == 32, "old-epoch authentication proof incomplete")
    require(scenario.get("applyUnauthorizedAfterFence") == 16, "Apply post-fence rejection proof incomplete")
    require(scenario.get("uploadAuthorizationUnauthorizedAfterFence") == 16, "upload authorization rejection proof incomplete")
    for key in (
        "preWorkerApplyConfirmationRows",
        "preWorkerMemoryItemRows",
        "preWorkerUploadAuthorizationRows",
        "preWorkerQuarantineRows",
        "unexpectedStatusCount",
        "transportErrors",
        "finalOwnedRowCount",
    ):
        require(scenario.get(key) == 0, f"mutation/integrity criterion drift: {key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["preFenceMutationLinearizationProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    require(boundary.get("applySurfaceCovered") is True, "Apply coverage drift")
    require(boundary.get("uploadAuthorizationSurfaceCovered") is True, "upload authorization coverage drift")
    require(boundary.get("uploadCompletionSurfaceCovered") is False, "upload completion cannot be promoted by this proof")
    require(boundary.get("productionEvidence") is False, "local proof cannot become production evidence")
    require(boundary.get("productionEquivalentDependencies") is False, "local proof cannot become production-equivalent evidence")

    write_contract_transactionally(contract, expected)

    print("Memory OS deletion pre-fence mutation authority reconciled")
    print("Apply pre-fence mutation linearization: true")
    print("upload authorization pre-fence mutation linearization: true")
    print("upload completion pre-fence coverage: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"DELETION PRE-FENCE MUTATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
