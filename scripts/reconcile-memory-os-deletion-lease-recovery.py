#!/usr/bin/env python3
"""Promote only exact-source local lease-recovery evidence into its narrow contract authority."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CANONICAL_ROOT = Path(__file__).resolve().parents[1]
ROOT = CANONICAL_ROOT
CANONICAL_CONTRACT_PATH = CANONICAL_ROOT / "contracts/operations/deletion-lease-recovery-contract.v1.json"
CANONICAL_RESULT_PATH = CANONICAL_ROOT / "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json"
CANONICAL_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-lease-recovery.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
VALIDATOR = CANONICAL_VALIDATOR


class ReconcileFailure(RuntimeError):
    """Raised when lease-recovery reconciliation authority is not canonical."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_exact_path(label: str, actual: Path, expected: Path, *, must_exist: bool = True) -> None:
    if actual != expected:
        raise ReconcileFailure(f"{label} path is not canonical")
    if actual.is_symlink():
        raise ReconcileFailure(f"{label} authority may not be a symlink")
    if not actual.exists():
        if must_exist:
            raise ReconcileFailure(f"{label} authority is unreadable")
        return
    try:
        actual_resolved = actual.resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
    except OSError as exc:
        raise ReconcileFailure(f"{label} authority is unreadable") from exc
    if actual_resolved != expected_resolved:
        raise ReconcileFailure(f"{label} authority does not resolve canonically")
    if not actual_resolved.is_file():
        raise ReconcileFailure(f"{label} authority must be a regular file")


def validate_authority_identity() -> None:
    if ROOT != CANONICAL_ROOT or ROOT.resolve() != CANONICAL_ROOT.resolve():
        raise ReconcileFailure("repository root authority is not canonical")
    _require_exact_path("lease recovery contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH)
    _require_exact_path("lease recovery result", RESULT_PATH, CANONICAL_RESULT_PATH, must_exist=False)
    _require_exact_path("lease recovery validator", VALIDATOR, CANONICAL_VALIDATOR)


def run_validator(expected_sha: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--require-result",
            "--expected-commit-sha",
            expected_sha,
        ],
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


def write_contract_transactionally(contract: dict[str, Any], expected_sha: str) -> None:
    original = CONTRACT_PATH.read_bytes()
    candidate = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(CONTRACT_PATH, candidate)
    try:
        run_validator(expected_sha)
    except BaseException:
        atomic_write_bytes(CONTRACT_PATH, original)
        raise


def main() -> int:
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    if len(expected_sha) != 40:
        raise SystemExit("EXPECTED_COMMIT_SHA must be a full source commit SHA")

    validate_authority_identity()
    run_validator(expected_sha)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    if result.get("commitSha") != expected_sha:
        raise SystemExit("result/source mismatch")

    environment = result.get("environment", {})
    scenario = result.get("scenario", {})
    if environment.get("productionEvidence") is not False:
        raise SystemExit("local lease recovery result cannot be production evidence")
    if environment.get("productionEquivalentDependencies") is not False:
        raise SystemExit("local lease recovery result cannot be production-equivalent")
    if environment.get("actualProcessKillCovered") is not False:
        raise SystemExit("lease abandonment simulation cannot claim process kill")
    if environment.get("actualHostFailureCovered") is not False:
        raise SystemExit("lease abandonment simulation cannot claim host failure")
    if scenario.get("result") != "PASS" or scenario.get("integrityResult") != "PASS":
        raise SystemExit("lease recovery result must PASS before reconciliation")

    readiness = contract.setdefault("readiness", {})
    readiness["runnerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["leaseExpiryReclaimProven"] = True
    readiness["partialObjectErasureRecoveryProven"] = True

    # These classifications are deliberately immutable for this local proof.
    readiness["actualProcessKillCovered"] = False
    readiness["actualHostFailureCovered"] = False
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.setdefault("evidenceBoundary", {})
    boundary["actualProcessKillCovered"] = False
    boundary["actualHostFailureCovered"] = False
    boundary["productionEvidence"] = False
    boundary["productionEquivalentDependencies"] = False
    boundary["productionReady"] = False

    write_contract_transactionally(contract, expected_sha)
    print("Memory OS deletion lease recovery reconciliation PASS")
    print("lease expiry reclaim proven: true")
    print("partial object erasure recovery proven: true")
    print("actual process kill covered: false")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
