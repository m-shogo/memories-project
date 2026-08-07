#!/usr/bin/env python3
"""Reconcile exact-source multi-account deletion-worker saturation evidence into its local-only contract."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
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
    require(scenario.get("workerReceiptCount") == 24, "worker receipt proof incomplete")
    require(scenario.get("uniqueWorkerReceiptCount") == 24 and scenario.get("duplicateWorkerReceiptCount") == 0, "worker claims were not unique")
    require(scenario.get("controlPreview2xx") == 400, "control Preview proof incomplete")
    require(scenario.get("finalDeletionPending") == 0 and scenario.get("finalDeletionStuck") == 0, "deletion backlog did not converge")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["multiAccountWorkerSaturationProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    for key in (
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "hostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local proof cannot enable {key}")

    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print("Memory OS deletion-worker saturation authority reconciled")
    print("multi-account worker saturation proven: true")
    print("capacity boundary established: false")
    print("production dependencies tested: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"DELETION WORKER SATURATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
