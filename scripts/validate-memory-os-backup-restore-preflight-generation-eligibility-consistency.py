#!/usr/bin/env python3
"""Fail closed if restore-drill preflight is more permissive than semantic generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_REL = Path("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
ELIGIBILITY_REL = Path("contracts/operations/production-equivalent-environment-eligibility-contract.v1.json")
OBJECTIVES_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_REQUESTS_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
OBJECTIVES_WRITER_REL = Path("scripts/register-memory-os-recovery-objectives.py")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency.py")
PREFLIGHT = ROOT / PREFLIGHT_REL
ELIGIBILITY = ROOT / ELIGIBILITY_REL
OBJECTIVES = ROOT / OBJECTIVES_REL
DRILL_REQUESTS = ROOT / DRILL_REQUESTS_REL
HELPER = ROOT / HELPER_REL
OBJECTIVES_WRITER = ROOT / OBJECTIVES_WRITER_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (PREFLIGHT, PREFLIGHT_REL, "restore preflight contract"),
        (ELIGIBILITY, ELIGIBILITY_REL, "environment eligibility contract"),
        (OBJECTIVES, OBJECTIVES_REL, "recovery objectives registry"),
        (DRILL_REQUESTS, DRILL_REQUESTS_REL, "restore drill request registry"),
        (HELPER, HELPER_REL, "generation eligibility helper"),
        (OBJECTIVES_WRITER, OBJECTIVES_WRITER_REL, "recovery objectives writer"),
        (DRILL_WRITER, DRILL_WRITER_REL, "restore drill request writer"),
        (VALIDATOR, VALIDATOR_REL, "preflight generation eligibility consistency validator"),
    ):
        require_exact_repo_file(path, expected, field)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {display_path(path)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {display_path(path)}")
    return value


def load_module(path: Path, expected_relative: Path, name: str, field: str):
    require_exact_repo_file(path, expected_relative, field)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {field}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    enforce_runtime_authorities()
    preflight_contract = load(PREFLIGHT)
    eligibility_contract = load(ELIGIBILITY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REQUESTS)
    helper = load_module(
        HELPER,
        HELPER_REL,
        "memory_os_generation_eligibility_for_preflight_consistency",
        "generation eligibility helper",
    )
    objectives_writer = load_module(
        OBJECTIVES_WRITER,
        OBJECTIVES_WRITER_REL,
        "memory_os_recovery_objectives_for_preflight_consistency",
        "recovery objectives writer",
    )
    drill_writer = load_module(
        DRILL_WRITER,
        DRILL_WRITER_REL,
        "memory_os_restore_drill_request_for_preflight_consistency",
        "restore drill request writer",
    )

    try:
        objective_rows = objectives_writer.validate_registry_for_append(objectives)
    except objectives_writer.Fail as exc:
        raise Fail(f"recovery objective registry authority invalid: {exc}") from exc
    try:
        requests = drill_writer.validate_registry_for_append(drill_registry)
    except drill_writer.Fail as exc:
        raise Fail(f"drill request registry authority invalid: {exc}") from exc

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
    require(
        isinstance(preflight_pair_count, int) and not isinstance(preflight_pair_count, bool) and preflight_pair_count >= 0,
        "preflight pair count invalid",
    )
    require(preflight_pair_count <= strict_pair_count, "restore preflight counts a source-target pair that is not semantically eligible")

    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    require(isinstance(objective_count, int) and not isinstance(objective_count, bool) and objective_count == len(objective_rows), "approved objective count invalid")
    if objective_count == 0:
        require(current_objective is None, "empty recovery objective registry must have null currentObjectiveId")
        objective_available = False
    else:
        require(isinstance(current_objective, str) and current_objective == objective_rows[-1].get("objectiveId"), "current recovery objective authority drift")
        objective_available = True

    registered_request_count = drill_registry.get("registeredRequestCount")
    request_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(registered_request_count, int) and not isinstance(registered_request_count, bool) and registered_request_count == len(requests), "registered drill request count invalid")
    require(isinstance(request_count, int) and not isinstance(request_count, bool) and 0 <= request_count <= registered_request_count, "current executable request count invalid")

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
    print("canonical data/executable authorities enforced: true")
    print("recovery objective append-only authority delegated: true")
    print("drill request append-only authority delegated: true")
    print("boolean authority counters accepted: false")
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
