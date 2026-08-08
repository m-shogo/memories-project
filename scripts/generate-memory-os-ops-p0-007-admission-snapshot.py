#!/usr/bin/env python3
"""Generate deterministic strict admission snapshot for OPS-P0-007 Backup/Restore."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_EVIDENCE = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
GEN_BLOCKER = "TWO_DISTINCT_SEMANTICALLY_ELIGIBLE_ENVIRONMENTS"
OBJECTIVE_BLOCKER = "CURRENT_APPROVED_RECOVERY_OBJECTIVE"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_ops_p0_007_snapshot", ELIGIBILITY_HELPER)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    helper = load_helper()
    eligibility = helper.derive()
    objectives = load(OBJECTIVES)
    requests = load(DRILL_REQUESTS)
    generation_evidence = load(GEN_EVIDENCE)
    typed = load(TYPED)
    status = load(STATUS)

    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    request_count = requests.get("registeredRequestCount")
    current_request_count = requests.get("currentExecutableRequestCount")
    generation_evidence_count = generation_evidence.get("registeredEvidenceCount")
    drill_bound_count = generation_evidence.get("drillRequestBoundEvidenceCount")
    candidate_count = generation_evidence.get("productionEquivalentRecoveryCandidateCount")
    typed_complete = typed.get("completeRecordCount")
    numeric = {
        "approvedRecoveryObjectiveCount": objective_count,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "generationRecoveryEvidenceCount": generation_evidence_count,
        "drillRequestBoundGenerationRecoveryEvidenceCount": drill_bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
    }
    for field, value in numeric.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SystemExit(f"{field} invalid")
    if drill_bound_count != generation_evidence_count:
        raise SystemExit("unbound generation recovery evidence exists")
    if current_request_count > request_count:
        raise SystemExit("current drill request count exceeds history")
    if candidate_count > generation_evidence_count:
        raise SystemExit("candidate count exceeds generation evidence")

    ops7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    if not isinstance(ops7, dict):
        raise SystemExit("OPS-P0-007 status missing")
    missing = ops7.get("missingEvidence")
    if not isinstance(missing, list) or len(missing) != 6:
        raise SystemExit("canonical OPS-P0-007 six-blocker boundary drift")
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("production decision must remain NO_GO")

    strict_blockers: list[str] = []
    if eligibility["eligibleDirectedPairCount"] == 0:
        strict_blockers.append(GEN_BLOCKER)
    objective_available = objective_count > 0 and isinstance(current_objective, str) and bool(current_objective)
    if not objective_available:
        strict_blockers.append(OBJECTIVE_BLOCKER)

    if strict_blockers:
        stage = "PREREQUISITES_BLOCKED"
        next_action = "produce and independently review two distinct semantically eligible non-production environment generations; independently approve explicit recovery objectives without AI-selected defaults"
    elif current_request_count == 0:
        stage = "READY_FOR_REVIEWED_DRILL_REQUEST"
        next_action = "submit one external planning-only restore drill request for human review using an eligible directed generation pair and the current approved objective"
    elif generation_evidence_count == 0:
        stage = "READY_FOR_ISOLATED_RESTORE_EVIDENCE"
        next_action = "immediately revalidate the current reviewed drill request before isolated execution, then register exact request-bound generation recovery evidence"
    elif typed_complete == 0 or candidate_count == 0:
        stage = "READY_FOR_TYPED_NON_RESURRECTION_EVIDENCE"
        next_action = "bind all eight typed non-resurrection domains with independent security and operability review before any final recovery candidate"
    else:
        stage = "RECOVERY_CANDIDATE_AVAILABLE_PRODUCTION_STILL_NO_GO"
        next_action = "retain NO_GO until the canonical six production backup/restore blockers are genuinely closed and a separate human production promotion decision is made"

    document = {
        "schemaVersion": "memory-os-ops-p0-007-admission-snapshot.v1",
        "deterministic": True,
        "areaId": "OPS-P0-007",
        "stage": stage,
        "strictPrerequisiteBlockers": strict_blockers,
        "strictPrerequisiteBlockerCount": len(strict_blockers),
        "registeredEnvironmentGenerationCount": eligibility["registeredGenerationCount"],
        "preflightEligibleGenerationCount": eligibility["preflightEligibleGenerationCount"],
        "unsupersededPreflightEligibleGenerationCount": eligibility["unsupersededPreflightEligibleGenerationCount"],
        "distinctPreflightEligibleEnvironmentCount": eligibility["distinctPreflightEligibleEnvironmentCount"],
        "eligibleDirectedRestorePairCount": eligibility["eligibleDirectedPairCount"],
        "approvedRecoveryObjectiveCount": objective_count,
        "currentRecoveryObjectiveId": current_objective,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "generationRecoveryEvidenceCount": generation_evidence_count,
        "drillRequestBoundGenerationRecoveryEvidenceCount": drill_bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
        "canonicalMissingEvidenceCount": len(missing),
        "downstreamRequirements": [
            "submit one externally reviewed planning-only restore drill request bound to an eligible source/target generation pair and the current approved recovery objective",
            "revalidate the drill request immediately before any isolated restore execution",
            "admit request-bound generation recovery evidence with exact backup/manifest/restore hashes and measured approved objectives",
            "bind all eight typed non-resurrection domains with independent security and operability review",
            "retain the canonical six production backup/restore blockers until genuine production-shaped evidence closes them",
            "make any production promotion as a separate human decision",
        ],
        "nextAction": next_action,
        "requestCreated": False,
        "restoreExecuted": False,
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS OPS-P0-007 strict admission snapshot generated")
    print(f"stage: {stage}")
    print(f"strict prerequisite blockers: {len(strict_blockers)}")
    print(f"eligible directed restore pairs: {eligibility['eligibleDirectedPairCount']}")
    print(f"canonical blockers: {len(missing)}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
