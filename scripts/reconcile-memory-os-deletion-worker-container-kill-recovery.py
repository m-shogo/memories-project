#!/usr/bin/env python3
"""Promote only exact-source local Docker container-kill recovery evidence into its narrow contract authority."""

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
CANONICAL_CONTRACT_PATH = CANONICAL_ROOT / "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json"
CANONICAL_RESULT_PATH = CANONICAL_ROOT / "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json"
CANONICAL_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py"
CANONICAL_SUBPROCESS_RUN = subprocess.run
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
VALIDATOR = CANONICAL_VALIDATOR


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def require_exact_path(label: str, actual: Path, expected: Path) -> None:
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
    require_exact_path("container-kill contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH)
    require_exact_path("container-kill result", RESULT_PATH, CANONICAL_RESULT_PATH)
    require_exact_path("container-kill validator", VALIDATOR, CANONICAL_VALIDATOR)
    require(subprocess.run is CANONICAL_SUBPROCESS_RUN, "validator execution transport is not canonical")


def run_validator(expected_sha: str) -> None:
    validate_authority_identity()
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
    validate_authority_identity()
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
    require(len(expected_sha) == 40 and all(ch in "0123456789abcdef" for ch in expected_sha), "EXPECTED_COMMIT_SHA must be a full source commit SHA")
    validate_authority_identity()
    run_validator(expected_sha)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    require(result.get("commitSha") == expected_sha, "container-kill result/source mismatch")
    environment = result.get("environment", {})
    scenario = result.get("scenario", {})
    require(isinstance(environment, dict), "container-kill environment missing")
    require(isinstance(scenario, dict), "container-kill scenario missing")
    for key in ("actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        require(environment.get(key) is True, f"container recovery coverage missing: {key}")
    for key in ("actualHostFailureCovered", "availabilityZoneFailureCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        require(environment.get(key) is False, f"local container proof may not enable {key}")
    require(
        scenario.get("killedContainerExitCode") == 137 and scenario.get("replacementContainerExitCode") == 0,
        "container exit-code proof incomplete",
    )
    require(scenario.get("replacementAttempt2Confirmed") is True, "replacement attempt-2 proof incomplete")
    require(
        scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS",
        "container-kill result must PASS",
    )

    readiness = contract.setdefault("readiness", {})
    require(isinstance(readiness, dict), "readiness missing")
    readiness["fixtureImplemented"] = True
    readiness["workerHelperImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["actualContainerKillRecoveryProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.setdefault("evidenceBoundary", {})
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    boundary["actualProcessKillCovered"] = True
    boundary["actualContainerKillCovered"] = True
    boundary["replacementContainerRecoveryCovered"] = True
    boundary["actualHostFailureCovered"] = False
    boundary["availabilityZoneFailureCovered"] = False
    boundary["productionEvidence"] = False
    boundary["productionEquivalentDependencies"] = False
    boundary["productionReady"] = False

    write_contract_transactionally(contract, expected_sha)
    print("Memory OS deletion worker container-kill recovery reconciliation PASS")
    print("actual container kill recovery proven: true")
    print("replacement container recovery proven: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"DELETION CONTAINER-KILL RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
