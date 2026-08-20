#!/usr/bin/env python3
"""Validate deterministic strict OPS-P0-007 Backup/Restore admission snapshot."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
BLOCKER_HELPER = ROOT / "scripts/memory_os_backup_restore_blockers.py"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_EVIDENCE = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
OBJECTIVE_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
GEN_EVIDENCE_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
TYPED_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
GEN_BLOCKER = "TWO_DISTINCT_SEMANTICALLY_ELIGIBLE_ENVIRONMENTS"
OBJECTIVE_BLOCKER = "CURRENT_APPROVED_RECOVERY_OBJECTIVE"
SNAPSHOT_FIELDS = {
    "schemaVersion",
    "deterministic",
    "areaId",
    "stage",
    "strictPrerequisiteBlockers",
    "strictPrerequisiteBlockerCount",
    "registeredEnvironmentGenerationCount",
    "preflightEligibleGenerationCount",
    "unsupersededPreflightEligibleGenerationCount",
    "distinctPreflightEligibleEnvironmentCount",
    "eligibleDirectedRestorePairCount",
    "approvedRecoveryObjectiveCount",
    "currentRecoveryObjectiveId",
    "reviewedDrillRequestCount",
    "currentExecutableDrillRequestCount",
    "generationRecoveryEvidenceCount",
    "drillRequestBoundGenerationRecoveryEvidenceCount",
    "completeTypedNonResurrectionRecordCount",
    "finalProductionEquivalentRecoveryCandidateCount",
    "canonicalMissingEvidenceCount",
    "downstreamRequirements",
    "nextAction",
    "requestCreated",
    "restoreExecuted",
    "productionTrafficChanged",
    "productionEvidence",
    "productionReady",
    "productionDecision",
}
DOWNSTREAM_REQUIREMENTS = [
    "submit one externally reviewed planning-only restore drill request bound to an eligible source/target generation pair and the current approved recovery objective",
    "revalidate the drill request immediately before any isolated restore execution",
    "admit request-bound generation recovery evidence with exact backup/manifest/restore hashes and measured approved objectives",
    "bind all eight typed non-resurrection domains with independent security and operability review",
    "retain the canonical six production backup/restore blockers until genuine production-shaped evidence closes them",
    "make any production promotion as a separate human decision",
]
NEXT_ACTIONS = {
    "PREREQUISITES_BLOCKED": "produce and independently review two distinct semantically eligible non-production environment generations; independently approve explicit recovery objectives without AI-selected defaults",
    "READY_FOR_REVIEWED_DRILL_REQUEST": "submit one external planning-only restore drill request for human review using an eligible directed generation pair and the current approved objective",
    "READY_FOR_ISOLATED_RESTORE_EVIDENCE": "immediately revalidate the current reviewed drill request before isolated execution, then register exact request-bound generation recovery evidence",
    "READY_FOR_TYPED_NON_RESURRECTION_EVIDENCE": "bind all eight typed non-resurrection domains with independent security and operability review before any final recovery candidate",
    "RECOVERY_CANDIDATE_AVAILABLE_PRODUCTION_STILL_NO_GO": "retain NO_GO until the canonical six production backup/restore blockers are genuinely closed and a separate human production promotion decision is made",
}


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


def load_module(path: Path, name: str):
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"cannot resolve canonical authority module: {path}") from exc
    require(relative == resolved and path.is_file(), f"authority module escapes canonical repository path: {relative}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_registry(module, registry: dict[str, Any], label: str) -> list[dict[str, Any]]:
    validator = getattr(module, "validate_registry_for_append", None)
    failure_type = getattr(module, "Fail", RuntimeError)
    require(callable(validator), f"{label} canonical registry validator missing")
    require(isinstance(failure_type, type) and issubclass(failure_type, BaseException), f"{label} failure type invalid")
    try:
        rows = validator(registry)
    except failure_type as exc:
        raise Fail(f"{label} canonical registry authority invalid: {exc}") from exc
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), f"{label} canonical registry validator returned invalid rows")
    return rows


def load_helper():
    return load_module(ELIGIBILITY_HELPER, "memory_os_generation_eligibility_ops_p0_007_snapshot_validator")


def main() -> int:
    snapshot = load(SNAPSHOT)
    helper = load_helper()
    blocker_helper = load_module(BLOCKER_HELPER, "memory_os_backup_restore_blockers_ops_p0_007_snapshot_validator")
    eligibility = helper.derive()
    objectives = load(OBJECTIVES)
    requests = load(DRILL_REQUESTS)
    generation_evidence = load(GEN_EVIDENCE)
    typed = load(TYPED)
    status = load(STATUS)

    objective_writer = load_module(OBJECTIVE_WRITER, "memory_os_objective_writer_ops_p0_007_snapshot_validator")
    request_writer = load_module(DRILL_REQUEST_WRITER, "memory_os_drill_request_writer_ops_p0_007_snapshot_validator")
    generation_writer = load_module(GEN_EVIDENCE_WRITER, "memory_os_generation_evidence_writer_ops_p0_007_snapshot_validator")
    typed_writer = load_module(TYPED_WRITER, "memory_os_typed_non_resurrection_writer_ops_p0_007_snapshot_validator")
    validate_registry(objective_writer, objectives, "recovery objective")
    validate_registry(request_writer, requests, "restore drill request")
    validate_registry(generation_writer, generation_evidence, "generation recovery evidence")
    validate_registry(typed_writer, typed, "typed non-resurrection")

    require(set(snapshot) == SNAPSHOT_FIELDS, "snapshot field set drift")
    require(snapshot.get("schemaVersion") == "memory-os-ops-p0-007-admission-snapshot.v1", "snapshot schema drift")
    require(snapshot.get("deterministic") is True and snapshot.get("areaId") == "OPS-P0-007", "snapshot identity drift")
    require(snapshot.get("productionEvidence") is False and snapshot.get("productionReady") is False and snapshot.get("productionDecision") == "NO_GO", "snapshot cannot promote production")
    for field in ("requestCreated", "restoreExecuted", "productionTrafficChanged"):
        require(snapshot.get(field) is False, f"snapshot must keep {field}=false")

    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    request_count = requests.get("registeredRequestCount")
    current_request_count = requests.get("currentExecutableRequestCount")
    generation_evidence_count = generation_evidence.get("registeredEvidenceCount")
    drill_bound_count = generation_evidence.get("drillRequestBoundEvidenceCount")
    candidate_count = generation_evidence.get("productionEquivalentRecoveryCandidateCount")
    typed_complete = typed.get("completeRecordCount")
    for value, field in (
        (objective_count, "approvedRecoveryObjectiveCount"),
        (request_count, "reviewedDrillRequestCount"),
        (current_request_count, "currentExecutableDrillRequestCount"),
        (generation_evidence_count, "generationRecoveryEvidenceCount"),
        (drill_bound_count, "drillRequestBoundGenerationRecoveryEvidenceCount"),
        (typed_complete, "completeTypedNonResurrectionRecordCount"),
        (candidate_count, "finalProductionEquivalentRecoveryCandidateCount"),
    ):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field} invalid")
    require(current_request_count <= request_count, "current request count exceeds history")
    require(drill_bound_count == generation_evidence_count, "all generation recovery evidence must be drill-request-bound")
    require(candidate_count <= generation_evidence_count, "candidate count exceeds generation evidence")

    strict_blockers: list[str] = []
    if eligibility["eligibleDirectedPairCount"] == 0:
        strict_blockers.append(GEN_BLOCKER)
    objective_available = objective_count > 0 and isinstance(current_objective, str) and bool(current_objective)
    if not objective_available:
        strict_blockers.append(OBJECTIVE_BLOCKER)

    expected_counts = {
        "registeredEnvironmentGenerationCount": eligibility["registeredGenerationCount"],
        "preflightEligibleGenerationCount": eligibility["preflightEligibleGenerationCount"],
        "unsupersededPreflightEligibleGenerationCount": eligibility["unsupersededPreflightEligibleGenerationCount"],
        "distinctPreflightEligibleEnvironmentCount": eligibility["distinctPreflightEligibleEnvironmentCount"],
        "eligibleDirectedRestorePairCount": eligibility["eligibleDirectedPairCount"],
        "approvedRecoveryObjectiveCount": objective_count,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "generationRecoveryEvidenceCount": generation_evidence_count,
        "drillRequestBoundGenerationRecoveryEvidenceCount": drill_bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
    }
    for field, value in expected_counts.items():
        require(snapshot.get(field) == value, f"snapshot count drift: {field}")
    require(snapshot.get("currentRecoveryObjectiveId") == current_objective, "snapshot current objective drift")
    require(snapshot.get("strictPrerequisiteBlockers") == strict_blockers, "snapshot strict blocker set drift")
    require(snapshot.get("strictPrerequisiteBlockerCount") == len(strict_blockers), "snapshot strict blocker count drift")

    ops7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 status missing")
    missing = ops7.get("missingEvidence")
    require_canonical_gaps = getattr(blocker_helper, "require_canonical_gaps", None)
    canonical_gaps = getattr(blocker_helper, "CANONICAL_GAPS", None)
    require(callable(require_canonical_gaps), "canonical OPS-P0-007 blocker validator missing")
    require(isinstance(canonical_gaps, tuple) and len(canonical_gaps) == 6, "canonical OPS-P0-007 blocker authority invalid")
    try:
        require_canonical_gaps(missing, Fail)
    except Fail:
        raise
    except Exception as exc:
        raise Fail(f"canonical OPS-P0-007 blocker authority invalid: {exc}") from exc
    require(snapshot.get("canonicalMissingEvidenceCount") == len(canonical_gaps), "snapshot canonical blocker count drift")
    require(ops7.get("blocking") is True, "OPS-P0-007 must remain blocking")
    require(status.get("productionDecision") == "NO_GO", "status production decision drift")

    if strict_blockers:
        expected_stage = "PREREQUISITES_BLOCKED"
    elif current_request_count == 0:
        expected_stage = "READY_FOR_REVIEWED_DRILL_REQUEST"
    elif generation_evidence_count == 0:
        expected_stage = "READY_FOR_ISOLATED_RESTORE_EVIDENCE"
    elif typed_complete == 0 or candidate_count == 0:
        expected_stage = "READY_FOR_TYPED_NON_RESURRECTION_EVIDENCE"
    else:
        expected_stage = "RECOVERY_CANDIDATE_AVAILABLE_PRODUCTION_STILL_NO_GO"
    require(snapshot.get("stage") == expected_stage, "snapshot stage drift")
    require(snapshot.get("downstreamRequirements") == DOWNSTREAM_REQUIREMENTS, "snapshot downstream requirement projection drift")
    require(snapshot.get("nextAction") == NEXT_ACTIONS[expected_stage], "snapshot nextAction projection drift")

    if current_request_count > 0:
        require(eligibility["eligibleDirectedPairCount"] > 0 and objective_available, "current request cannot exist without strict prerequisites")
    if generation_evidence_count > 0:
        require(request_count > 0, "generation recovery evidence cannot exist without reviewed request history")
    if candidate_count > 0:
        require(typed_complete > 0 and current_request_count > 0, "final candidate requires typed evidence and current request")

    print("Memory OS OPS-P0-007 strict admission snapshot validation PASS")
    print("canonical append-only registry validators enforced: true")
    print("canonical production blocker authority enforced: true")
    print("snapshot exact field set enforced: true")
    print("snapshot downstream requirement and next-action projection enforced: true")
    print(f"stage: {expected_stage}")
    print(f"strict prerequisite blockers: {len(strict_blockers)}")
    print(f"eligible directed restore pairs: {eligibility['eligibleDirectedPairCount']}")
    print(f"reviewed/current drill requests: {request_count}/{current_request_count}")
    print(f"generation recovery evidence: {generation_evidence_count}")
    print(f"final recovery candidates: {candidate_count}")
    print(f"canonical OPS-P0-007 blockers preserved: {len(canonical_gaps)}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPS-P0-007 ADMISSION SNAPSHOT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
