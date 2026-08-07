#!/usr/bin/env python3
"""Promote only exact-source local SIGKILL recovery evidence into its narrow contract authority."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-sigkill-recovery.py"


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

    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print("Memory OS deletion worker SIGKILL recovery reconciliation PASS")
    print("actual SIGKILL recovery proven: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
