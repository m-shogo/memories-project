#!/usr/bin/env python3
"""Fail closed if restore-drill preflight is more permissive than semantic generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
ELIGIBILITY = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_for_preflight_consistency", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    preflight_contract = load(PREFLIGHT)
    eligibility_contract = load(ELIGIBILITY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REQUESTS)
    helper = load_helper()
    strict = helper.derive()

    preflight = preflight_contract.get("currentState")
    eligibility = eligibility_contract.get("currentBoundary")
    require(isinstance(preflight, dict) and isinstance(eligibility, dict), "preflight/eligibility authority state missing")
    strict_pair_count = strict["eligibleDirectedPairCount"]
    strict_eligible_count = strict["preflightEligibleGenerationCount"]
    strict_unsuperseded_eligible_count = strict["unsupersededPreflightEligibleGenerationCount"]
    strict_distinct_env_count = strict["distinctPreflightEligibleEnvironmentCount"]
    require(eligibility.get("preflightEligibleGenerationCount") == strict_eligible_count, "eligibility contract eligible generation count drift")
    require(eligibility.get("unsupersededPreflightEligibleGenerationCount") == strict_unsuperseded_eligible_count, "eligibility contract unsuperseded eligible count drift")
    require(eligibility.get("distinctPreflightEligibleEnvironmentCount") == strict_distinct_env_count, "eligibility contract distinct environment count drift")
    require(eligibility.get("eligibleDirectedRestorePairCount") == strict_pair_count, "eligibility contract pair count drift")

    preflight_pair_count = preflight.get("eligibleDirectedSourceTargetPairCount")
    require(isinstance(preflight_pair_count, int) and preflight_pair_count >= 0, "preflight pair count invalid")
    require(preflight_pair_count <= strict_pair_count, "restore preflight counts a source-target pair that is not semantically eligible")

    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    require(isinstance(objective_count, int) and objective_count >= 0, "approved objective count invalid")
    objective_available = objective_count > 0 and isinstance(current_objective, str) and bool(current_objective)
    request_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(request_count, int) and request_count >= 0, "current executable request count invalid")

    strict_submission_eligible = strict_pair_count > 0 and objective_available
    preflight_eligible = preflight.get("eligibleToSubmitReviewedDrillRequest")
    require(isinstance(preflight_eligible, bool), "preflight eligibility invalid")
    if preflight_eligible:
        require(strict_submission_eligible, "restore preflight is READY using noneligible generation prerequisites")
    if request_count > 0:
        require(strict_submission_eligible and strict_pair_count > 0, "current executable request survives without strict semantic generation pair")

    decision = preflight.get("preflightDecision")
    require(isinstance(decision, str) and decision, "preflight decision invalid")
    if not strict_submission_eligible:
        require(decision.startswith("BLOCKED_"), "preflight decision must remain BLOCKED while strict semantic prerequisites are missing")
    if request_count > 0:
        require(decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST", "current executable request requires READY_EXISTING preflight")

    for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady"):
        require(preflight.get(field) is False, f"preflight must keep {field}=false")
    require(preflight.get("productionDecision") == "NO_GO", "preflight production decision drift")
    require(eligibility.get("productionEvidence") is False and eligibility.get("productionReady") is False and eligibility.get("productionDecision") == "NO_GO", "eligibility production boundary drift")

    print("Memory OS restore preflight generation-eligibility consistency PASS")
    print(f"strict eligible generations: {strict_eligible_count}")
    print(f"strict unsuperseded eligible generations: {strict_unsuperseded_eligible_count}")
    print(f"strict distinct eligible environments: {strict_distinct_env_count}")
    print(f"strict/preflight directed restore pairs: {strict_pair_count}/{preflight_pair_count}")
    print(f"strict submission eligible: {str(strict_submission_eligible).lower()}")
    print("noneligible generation can make preflight READY: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RESTORE PREFLIGHT GENERATION ELIGIBILITY CONSISTENCY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
