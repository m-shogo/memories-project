#!/usr/bin/env python3
"""Promote only exact-source local SIGKILL recovery evidence into its narrow contract authority."""

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
CANONICAL_CONTRACT_PATH = CANONICAL_ROOT / "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json"
CANONICAL_RESULT_PATH = CANONICAL_ROOT / "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json"
CANONICAL_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-worker-sigkill-recovery.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
VALIDATOR = CANONICAL_VALIDATOR


class ReconcileFailure(RuntimeError):
    """Raised when SIGKILL reconciliation authority is not canonical."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_exact_path(label: str, actual: Path, expected: Path) -> None:
    if actual != expected:
        raise ReconcileFailure(f"{label} path is not canonical")
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
    _require_exact_path("SIGKILL recovery contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH)
    _require_exact_path("SIGKILL recovery result", RESULT_PATH, CANONICAL_RESULT_PATH)
    _require_exact_path("SIGKILL recovery validator", VALIDATOR, CANONICAL_VALIDATOR)


def run_validator(expected_sha: str) -> None:
    subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-result", "--expected-commit-sha", expected_sha],
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
        raise SystemExit("SIGKILL result/source mismatch")
    environment = result.get("environment", {})
    scenario = result.get("scenario", {})
    if environment.get("actualProcessKillCovered") is not True:
        raise SystemExit("actual process kill evidence missing")
    for key in ("actualHostFailureCovered", "containerRestartCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"local SIGKILL result may not enable {key}")
    if scenario.get("actualSIGKILLObserved") is not True or scenario.get("replacementReceiptAttempts") != 2:
        raise SystemExit("SIGKILL/reclaim proof incomplete")
    if scenario.get("result") != "PASS" or scenario.get("integrityResult") != "PASS":
        raise SystemExit("SIGKILL result must PASS")

    readiness = contract.setdefault("readiness", {})
    readiness["runnerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["actualSIGKILLRecoveryProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.setdefault("evidenceBoundary", {})
    boundary["actualProcessKillCovered"] = True
    boundary["actualHostFailureCovered"] = False
    boundary["containerRestartCovered"] = False
    boundary["productionEvidence"] = False
    boundary["productionEquivalentDependencies"] = False
    boundary["productionReady"] = False

    write_contract_transactionally(contract, expected_sha)
    print("Memory OS deletion worker SIGKILL recovery reconciliation PASS")
    print("actual SIGKILL recovery proven: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
