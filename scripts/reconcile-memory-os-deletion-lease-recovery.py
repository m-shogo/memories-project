#!/usr/bin/env python3
"""Promote only exact-source local lease-recovery evidence into its narrow contract authority."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-lease-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-lease-recovery.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    if len(expected_sha) != 40:
        raise SystemExit("EXPECTED_COMMIT_SHA must be a full source commit SHA")

    subprocess.run(
        [
            "python",
            str(VALIDATOR),
            "--require-result",
            "--expected-commit-sha",
            expected_sha,
        ],
        cwd=ROOT,
        check=True,
    )

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

    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print("Memory OS deletion lease recovery reconciliation PASS")
    print("lease expiry reclaim proven: true")
    print("partial object erasure recovery proven: true")
    print("actual process kill covered: false")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
