#!/usr/bin/env python3
"""Reconcile bounded counters for the end-to-end backup/restore admission chain."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
BINDING_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_admission_chain_reconcile", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    original_contract_text = CONTRACT.read_text(encoding="utf-8")
    contract = load(CONTRACT)
    preflight_contract = load(PREFLIGHT)
    drill_registry = load(DRILL_REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    binding_contract = load(BINDING_CONTRACT)
    typed_registry = load(TYPED_REGISTRY)
    status = load(STATUS)
    gen_writer = load_generation_writer()

    preflight = preflight_contract.get("currentState")
    require(isinstance(preflight, dict), "preflight currentState missing")
    preflight_decision = preflight.get("preflightDecision")
    preflight_eligible = preflight.get("eligibleToSubmitReviewedDrillRequest")
    preflight_pair_count = preflight.get("eligibleDirectedSourceTargetPairCount")
    require(isinstance(preflight_decision, str) and preflight_decision, "preflight decision invalid")
    require(isinstance(preflight_eligible, bool), "preflight eligibility invalid")
    require(valid_count(preflight_pair_count), "preflight pair count invalid")
    for field in ("reviewedDrillRequestCount", "currentExecutableDrillRequestCount"):
        require(valid_count(preflight.get(field)), f"preflight {field} must be a non-boolean count")
    require(all(preflight.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight execution boundary drift")
    require(preflight.get("productionDecision") == "NO_GO", "preflight production decision drift")

    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(drill_rows, list) and valid_count(drill_count) and drill_count == len(drill_rows), "drill request registry count drift")
    require(valid_count(current_drill_count) and current_drill_count <= drill_count, "current drill request count invalid")
    require(preflight.get("reviewedDrillRequestCount") == drill_count, "preflight reviewed request count drift")
    require(preflight.get("currentExecutableDrillRequestCount") == current_drill_count, "preflight current request count drift")
    if current_drill_count > 0:
        require(preflight_eligible is True and preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST" and preflight_pair_count > 0, "current request/preflight state mismatch")
    elif preflight_eligible:
        require(preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION" and preflight_pair_count > 0, "eligible preflight state mismatch")
    else:
        require(preflight_decision in {
            "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS",
            "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE",
        } and current_drill_count == 0, "blocked preflight/current request mismatch")

    gen_rows = gen_registry.get("records")
    gen_count = gen_registry.get("registeredEvidenceCount")
    bound_count = gen_registry.get("drillRequestBoundEvidenceCount")
    registry_candidate_count = gen_registry.get("productionEquivalentRecoveryCandidateCount")
    require(isinstance(gen_rows, list) and valid_count(gen_count) and gen_count == len(gen_rows), "generation evidence count drift")
    require(valid_count(bound_count) and bound_count == gen_count, "every generation evidence row must be drill-request-bound")
    require(valid_count(registry_candidate_count) and registry_candidate_count <= gen_count, "generation candidate count invalid")
    for row in gen_rows:
        gen_writer.validate_record(row, require_current_drill_request=False)
    candidate_count = sum(1 for row in gen_rows if gen_writer.candidate(row))
    require(registry_candidate_count == candidate_count, "generation candidate count drift")

    binding_boundary = binding_contract.get("currentBoundary")
    require(isinstance(binding_boundary, dict), "generation binding currentBoundary missing")
    backup_count = binding_boundary.get("generationBoundBackupCount")
    restore_count = binding_boundary.get("generationBoundRestoreCount")
    binding_candidate_count = binding_boundary.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(backup_count), "generation-bound backup count invalid")
    require(valid_count(restore_count), "generation-bound restore count invalid")
    require(valid_count(binding_candidate_count), "generation binding candidate count invalid")
    require(binding_candidate_count == candidate_count, "generation binding candidate count drift")
    require(candidate_count <= restore_count <= backup_count <= gen_count, "recovery aggregate ordering drift")
    require(binding_boundary.get("independentReviewCompleted") is (candidate_count > 0), "generation binding independent review state drift")
    require(binding_boundary.get("humanProductionPromotionReviewCompleted") is False, "generation binding human production-promotion review must remain unclaimed")
    require(binding_boundary.get("humanProductionPromotionAuthorized") is False, "generation binding human production-promotion authorization must remain unclaimed")
    require(binding_boundary.get("productionEvidence") is False and binding_boundary.get("productionReady") is False and binding_boundary.get("productionDecision") == "NO_GO", "generation binding production boundary drift")

    typed_rows = typed_registry.get("records")
    typed_complete_count = typed_registry.get("completeRecordCount")
    typed_covered_count = typed_registry.get("candidateCoveredCount")
    require(isinstance(typed_rows, list), "typed registry rows invalid")
    require(valid_count(typed_complete_count), "typed complete count invalid")
    require(valid_count(typed_covered_count), "typed covered count invalid")
    require(typed_covered_count <= typed_complete_count <= len(typed_rows), "typed registry count ordering invalid")
    require(typed_covered_count == candidate_count, "typed candidate coverage must equal final candidate count")

    require(status.get("productionDecision") == "NO_GO", "chain reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    require_canonical_gaps(gate.get("missingEvidence"), Fail)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "chain currentBoundary missing")
    boundary["preflightDecision"] = preflight_decision
    boundary["preflightEligibleToSubmitReviewedDrillRequest"] = preflight_eligible
    boundary["preflightEligibleDirectedSourceTargetPairCount"] = preflight_pair_count
    boundary["reviewedDrillRequestCount"] = drill_count
    boundary["currentExecutableDrillRequestCount"] = current_drill_count
    boundary["generationEvidenceCount"] = gen_count
    boundary["drillRequestBoundGenerationEvidenceCount"] = bound_count
    boundary["generationBoundBackupCount"] = backup_count
    boundary["generationBoundRestoreCount"] = restore_count
    boundary["completeTypedNonResurrectionRecordCount"] = typed_complete_count
    boundary["finalProductionEquivalentRecoveryCandidateCount"] = candidate_count
    boundary["independentEvidenceReviewCompleted"] = candidate_count > 0
    boundary["humanProductionPromotionReviewCompleted"] = False
    boundary["humanProductionPromotionAuthorized"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        CONTRACT.write_text(original_contract_text, encoding="utf-8")
        raise Fail(f"post-reconcile admission-chain validator failed; original contract restored:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")

    print("Memory OS backup/restore admission chain reconciliation PASS")
    print(f"preflight: {preflight_decision}")
    print(f"preflight eligible pairs: {preflight_pair_count}")
    print(f"reviewed/current drill requests: {drill_count}/{current_drill_count}")
    print(f"generation/drill-bound evidence: {gen_count}/{bound_count}")
    print(f"generation-bound backup/restore: {backup_count}/{restore_count}")
    print(f"complete typed records/final candidates: {typed_complete_count}/{candidate_count}")
    print("boolean aggregate counts accepted by reconciler: false")
    print("failed post-validation leaves derived contract mutation behind: false")
    print(f"candidate-level independent evidence review completed: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production-promotion authorized: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
