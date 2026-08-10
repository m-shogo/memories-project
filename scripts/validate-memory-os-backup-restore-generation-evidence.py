#!/usr/bin/env python3
"""Validate append-only, drill-request-bound generation recovery evidence authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_BINDING = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
SEMANTIC_NEGATIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-semantic-generation-negative.py"


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


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_generation_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(path: Path, label: str) -> None:
    require(path.is_file(), f"{label} missing")
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n" + completed.stdout[-6000:] + completed.stderr[-6000:],
    )


def validate_negative_admission_suite(contract: dict[str, Any]) -> None:
    expected_ref = str(NEGATIVE_VALIDATOR.relative_to(ROOT))
    require(contract.get("negativeAdmissionValidator") == expected_ref, "negative admission validator ref drift")
    require(NEGATIVE_VALIDATOR.is_file(), "negative admission validator missing")
    cases = contract.get("negativeAdmissionCases")
    require(isinstance(cases, list) and len(cases) >= 15 and len(cases) == len(set(cases)), "negative admission cases incomplete or duplicated")
    run_validator(NEGATIVE_VALIDATOR, "negative admission suite")
    run_validator(SEMANTIC_NEGATIVE_VALIDATOR, "semantic generation negative admission suite")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    drill_registry = load(DRILL_REGISTRY)
    binding = load(GEN_BINDING)
    writer = load_writer()

    require(contract.get("schemaVersion") == "memory-os-backup-restore-generation-evidence.v1", "contract schema drift")
    expected_refs = {
        "registry": REGISTRY,
        "environmentGenerationRegistry": GEN_REGISTRY,
        "recoveryObjectivesRegistry": OBJECTIVES_REGISTRY,
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "generationBindingContract": GEN_BINDING,
        "writer": WRITER,
        "negativeAdmissionValidator": NEGATIVE_VALIDATOR,
    }
    for field, path in expected_refs.items():
        require(contract.get(field) == str(path.relative_to(ROOT)), f"contract ref drift: {field}")
        require(path.is_file(), f"contract artifact missing: {field}")
    require(SEMANTIC_NEGATIVE_VALIDATOR.is_file(), "semantic generation negative admission validator missing")
    for field in ("validator", "reconcile", "workflow", "typedNonResurrectionAdmissionContract", "typedNonResurrectionAdmissionRegistry"):
        ref = contract.get(field)
        require(isinstance(ref, str) and ref and (ROOT / ref).is_file(), f"contract artifact missing: {field}")

    rules = contract.get("recordRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "recordRules must remain fail-closed")
    for key in (
        "drillRequestMustExist",
        "drillRequestMustBeCurrentlyExecutableForNewEvidence",
        "historicalEvidenceMayRemainAuditableAfterDrillRequestBecomesStale",
        "drillRequestSourceGenerationMustMatchEvidence",
        "drillRequestRestoreTargetGenerationMustMatchEvidence",
        "drillRequestRecoveryObjectivesIdMustMatchEvidence",
        "typedNonResurrectionCoverageRequiredForProductionEquivalentRestoreCandidate",
        "genericNonResurrectionPassAloneCannotCreateCandidate",
    ):
        require(rules.get(key) is True, f"required fail-closed rule missing: {key}")

    promotion = contract.get("promotionBoundary")
    require(isinstance(promotion, dict), "promotionBoundary required")
    require(promotion.get("productionEquivalentRecoveryCandidateMayBeDerivedFromCompleteReviewedRecord") is True, "candidate derivation rule drift")
    require(promotion.get("completeReviewedRecordAlsoRequiresAdmittedDrillRequestBinding") is True, "candidate must remain drill-request-bound")
    require(promotion.get("completeReviewedRecordAlsoRequiresTypedNonResurrectionCoverage") is True, "candidate must remain typed-overlay-bound")
    require(promotion.get("productionEvidenceMayBeDerived") is False, "registry cannot derive production evidence")
    require(promotion.get("productionReadyMayBeDerived") is False, "registry cannot derive production readiness")
    require(promotion.get("humanProductionPromotionDecisionRequiredSeparately") is True, "human production decision must remain separate")

    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry production boundary drift")
    rows = registry.get("records")
    count = registry.get("registeredEvidenceCount")
    bound_count = registry.get("drillRequestBoundEvidenceCount")
    backup_count = registry.get("completeGenerationBoundBackupCount")
    restore_count = registry.get("completeGenerationBoundRestoreCount")
    candidate_count = registry.get("productionEquivalentRecoveryCandidateCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry records invalid")
    require(isinstance(count, int) and count == len(rows), "registeredEvidenceCount drift")
    require(all(isinstance(value, int) and value >= 0 for value in (bound_count, backup_count, restore_count, candidate_count)), "registry derived counts invalid")

    ids: set[str] = set()
    derived_bound = 0
    for row in rows:
        evidence_id = row.get("evidenceId")
        require(isinstance(evidence_id, str) and evidence_id not in ids, f"duplicate evidenceId: {evidence_id}")
        ids.add(evidence_id)
        writer.validate_record(row, require_current_drill_request=False)
        derived_bound += 1
    derived_backup = sum(1 for row in rows if row.get("evidenceComplete") is True)
    derived_restore = sum(
        1 for row in rows
        if row.get("evidenceComplete") is True
        and row.get("isolatedRestoreVerified") is True
        and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
    )
    derived_candidates = sum(1 for row in rows if writer.candidate(row))
    require(bound_count == derived_bound == count, "every generation evidence row must remain drill-request-bound")
    require(backup_count == derived_backup, "completeGenerationBoundBackupCount drift")
    require(restore_count == derived_restore, "completeGenerationBoundRestoreCount drift")
    require(candidate_count == derived_candidates, "productionEquivalentRecoveryCandidateCount drift")
    require(0 <= candidate_count <= restore_count <= backup_count <= bound_count <= count, "generation evidence count ordering invalid")

    generation_count = generations.get("registeredGenerationCount")
    objective_count = objectives.get("approvedObjectiveCount")
    objective_rows = objectives.get("records")
    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(generation_count, int) and generation_count >= 0, "generation registry count invalid")
    require(isinstance(objective_count, int) and objective_count >= 0, "approvedObjectiveCount invalid")
    require(isinstance(objective_rows, list) and len(objective_rows) == objective_count, "recovery objectives registry count drift")
    require(isinstance(drill_rows, list) and isinstance(drill_count, int) and drill_count == len(drill_rows), "drill request registry count drift")
    require(isinstance(current_drill_count, int) and 0 <= current_drill_count <= drill_count, "current drill request count invalid")
    require(drill_registry.get("productionEvidence") is False and drill_registry.get("productionReady") is False, "drill request registry production boundary drift")
    if generation_count == 0 or drill_count == 0:
        require(count == 0, "recovery evidence cannot exist without registered generations and a reviewed drill request")
    if objective_count == 0 or current_drill_count == 0:
        require(candidate_count == 0, "current recovery candidate cannot exist without current objectives and executable drill request")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    require(boundary.get("registeredEvidenceCount") == count, "contract evidence count drift")
    require(boundary.get("drillRequestBoundEvidenceCount") == derived_bound, "contract drill-bound evidence count drift")
    require(boundary.get("completeGenerationBoundBackupCount") == derived_backup, "contract backup count drift")
    require(boundary.get("completeGenerationBoundRestoreCount") == derived_restore, "contract restore count drift")
    require(boundary.get("productionEquivalentRecoveryCandidateCount") == derived_candidates, "contract candidate count drift")
    require(boundary.get("productionEquivalentRestoreEvidence") is (derived_candidates > 0), "contract production-equivalent restore derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "contract cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    require(readiness.get("negativeAdmissionSuiteImplemented") is True, "negativeAdmissionSuiteImplemented must remain true")
    require(readiness.get("environmentGenerationAvailable") is (generation_count > 0), "environmentGenerationAvailable drift")
    require(readiness.get("approvedRecoveryObjectivesAvailable") is (objective_count > 0), "approvedRecoveryObjectivesAvailable drift")
    require(readiness.get("drillRequestAvailable") is (drill_count > 0), "drillRequestAvailable drift")
    require(readiness.get("generationBoundBackupAvailable") is (derived_backup > 0), "generationBoundBackupAvailable drift")
    require(readiness.get("generationBoundRestoreAvailable") is (derived_restore > 0), "generationBoundRestoreAvailable drift")
    require(readiness.get("productionEquivalentRecoveryCandidateAvailable") is (derived_candidates > 0), "candidate readiness drift")
    require(readiness.get("independentReviewCompleted") is (derived_candidates > 0), "independentReviewCompleted drift")
    require(readiness.get("productionEquivalentRestoreEvidence") is (derived_candidates > 0), "productionEquivalentRestoreEvidence readiness drift")
    require(readiness.get("productionReady") is False, "recovery registry cannot make application production ready")

    binding_boundary = binding.get("currentBoundary")
    binding_readiness = binding.get("readiness")
    require(isinstance(binding_boundary, dict), "generation binding currentBoundary missing")
    require(isinstance(binding_readiness, dict), "generation binding readiness missing")
    require(binding_boundary.get("registeredProductionEquivalentGenerationCount") == generation_count, "generation binding generation count drift")
    require(binding_boundary.get("generationBoundBackupCount") == derived_backup, "generation binding backup count drift")
    require(binding_boundary.get("generationBoundRestoreCount") == derived_restore, "generation binding restore count drift")
    require(binding_boundary.get("productionEquivalentRecoveryCandidateCount") == derived_candidates, "generation binding candidate count drift")
    require(binding_boundary.get("productionEquivalentRestoreEvidence") is (derived_candidates > 0), "generation binding restore evidence drift")
    require(binding_boundary.get("independentReviewCompleted") is (derived_candidates > 0), "generation binding independent review drift")
    require(binding_boundary.get("humanProductionPromotionReviewCompleted") is False, "generation binding candidate cannot complete human promotion review")
    require(binding_boundary.get("humanProductionPromotionAuthorized") is False, "generation binding candidate cannot authorize human promotion")
    require(binding_boundary.get("productionEvidence") is False and binding_boundary.get("productionReady") is False, "generation binding cannot promote production")
    require(binding_boundary.get("productionDecision") == "NO_GO", "generation binding production decision must remain NO_GO")
    require(binding_readiness.get("productionEquivalentRecoveryCandidateAvailable") is (derived_candidates > 0), "generation binding candidate readiness drift")
    require(binding_readiness.get("independentReviewCompleted") is (derived_candidates > 0), "generation binding independent review readiness drift")
    require(binding_readiness.get("humanProductionPromotionReviewCompleted") is False, "generation binding readiness cannot imply human promotion review")
    require(binding_readiness.get("humanProductionPromotionAuthorized") is False, "generation binding readiness cannot imply human promotion authority")
    require(binding_readiness.get("productionReady") is False, "generation binding readiness cannot promote production")

    validate_negative_admission_suite(contract)

    print("Memory OS drill-bound generation backup/restore evidence validation PASS")
    print(f"registered/current drill requests: {drill_count}/{current_drill_count}")
    print(f"registered/drill-bound recovery evidence: {count}/{derived_bound}")
    print(f"complete generation-bound restores: {derived_restore}")
    print(f"production-equivalent recovery candidates: {derived_candidates}")
    print("candidate-level independent review cross-authority binding: enforced")
    print("human production-promotion separation cross-authority binding: enforced")
    print("historical evidence audit after request supersession: allowed")
    print("new evidence without current drill request: forbidden")
    print("negative admission suite: PASS")
    print("semantic generation negative admission suite: PASS")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
