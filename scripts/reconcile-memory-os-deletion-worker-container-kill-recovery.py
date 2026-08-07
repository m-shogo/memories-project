#!/usr/bin/env python3
"""Promote only exact-source local Docker container-kill recovery evidence into its narrow contract authority."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-container-kill-recovery.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    if len(expected_sha) != 40:
        raise SystemExit("EXPECTED_COMMIT_SHA must be a full source commit SHA")
    subprocess.run(
        ["python", str(VALIDATOR), "--require-result", "--expected-commit-sha", expected_sha],
        cwd=ROOT,
        check=True,
    )
    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    if result.get("commitSha") != expected_sha:
        raise SystemExit("container-kill result/source mismatch")
    environment = result.get("environment", {})
    scenario = result.get("scenario", {})
    for key in ("actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        if environment.get(key) is not True:
            raise SystemExit(f"container recovery coverage missing: {key}")
    for key in ("actualHostFailureCovered", "availabilityZoneFailureCovered", "productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"local container proof may not enable {key}")
    if scenario.get("killedContainerExitCode") != 137 or scenario.get("replacementContainerExitCode") != 0:
        raise SystemExit("container exit-code proof incomplete")
    if scenario.get("replacementAttempt2Confirmed") is not True:
        raise SystemExit("replacement attempt-2 proof incomplete")
    if scenario.get("result") != "PASS" or scenario.get("integrityResult") != "PASS":
        raise SystemExit("container-kill result must PASS")

    readiness = contract.setdefault("readiness", {})
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
    boundary["actualProcessKillCovered"] = True
    boundary["actualContainerKillCovered"] = True
    boundary["replacementContainerRecoveryCovered"] = True
    boundary["actualHostFailureCovered"] = False
    boundary["availabilityZoneFailureCovered"] = False
    boundary["productionEvidence"] = False
    boundary["productionEquivalentDependencies"] = False
    boundary["productionReady"] = False

    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print("Memory OS deletion worker container-kill recovery reconciliation PASS")
    print("actual container kill recovery proven: true")
    print("replacement container recovery proven: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
