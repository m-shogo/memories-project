#!/usr/bin/env python3
"""Negative suite for recovery-candidate versus human-promotion separation."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_restore_generation_binding_negative_target", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation binding validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def candidate_state(module) -> dict[Path, dict[str, Any]]:
    real_load = module.load
    contract = copy.deepcopy(real_load(module.CONTRACT))
    backup = copy.deepcopy(real_load(module.BACKUP_POLICY))
    local = copy.deepcopy(real_load(module.LOCAL_FOUNDATIONS))
    generation = copy.deepcopy(real_load(module.GENERATION))
    evidence_contract = copy.deepcopy(real_load(module.EVIDENCE_CONTRACT))

    contract["currentBoundary"].update({
        "registeredProductionEquivalentGenerationCount": 1,
        "generationBoundBackupCount": 1,
        "generationBoundRestoreCount": 1,
        "productionEquivalentRecoveryCandidateCount": 1,
        "productionEquivalentRestoreEvidence": True,
        "independentReviewCompleted": True,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    })
    contract["readiness"].update({
        "environmentGenerationAvailable": True,
        "generationBoundBackupAvailable": True,
        "generationBoundRestoreAvailable": True,
        "productionEquivalentRecoveryCandidateAvailable": True,
        "independentReviewCompleted": True,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
        "productionEquivalentRestoreEvidence": True,
        "productionReady": False,
    })
    generation["currentBoundary"].update({
        "registeredGenerationCount": 1,
        "productionEvidence": False,
        "productionReady": False,
    })
    generation_registry = {
        "appendOnly": True,
        "productionEvidence": False,
        "registeredGenerationCount": 1,
        "generations": [{}],
    }
    evidence_registry = {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "productionEvidence": False,
        "productionReady": False,
        "registeredEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 1,
        "completeGenerationBoundRestoreCount": 1,
        "productionEquivalentRecoveryCandidateCount": 1,
        "records": [{"syntheticCandidate": True}],
    }
    return {
        module.CONTRACT: contract,
        module.BACKUP_POLICY: backup,
        module.LOCAL_FOUNDATIONS: local,
        module.GENERATION: generation,
        module.GEN_REGISTRY: generation_registry,
        module.EVIDENCE_CONTRACT: evidence_contract,
        module.EVIDENCE_REGISTRY: evidence_registry,
    }


def run_with_state(module, state: dict[Path, dict[str, Any]]) -> int:
    original_load = module.load
    original_load_evidence_writer = module.load_evidence_writer

    def fake_load(path: Path) -> dict[str, Any]:
        if path in state:
            return copy.deepcopy(state[path])
        return original_load(path)

    class SyntheticEvidenceWriter:
        @staticmethod
        def validate_record(record: dict[str, Any], *, require_current_drill_request: bool = True) -> None:
            require(isinstance(record, dict), "synthetic evidence row invalid")

        @staticmethod
        def candidate(record: dict[str, Any]) -> bool:
            return record.get("syntheticCandidate") is True

    module.load = fake_load
    module.load_evidence_writer = lambda: SyntheticEvidenceWriter
    try:
        return module.main()
    finally:
        module.load = original_load
        module.load_evidence_writer = original_load_evidence_writer


def main() -> int:
    module = load_module()
    state = candidate_state(module)

    require(run_with_state(module, state) == 0, "candidate baseline must validate with evidence review but without human promotion review")
    print("PASS baseline: recovery candidate includes independently re-derived evidence review while human promotion review remains false")

    manufactured_aggregate = copy.deepcopy(state)
    manufactured_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["syntheticCandidate"] = False
    expect_rejected(
        "recovery candidate aggregate without current executable reviewed candidate evidence",
        lambda: run_with_state(module, manufactured_aggregate),
    )

    missing_boundary_review = copy.deepcopy(state)
    missing_boundary_review[module.CONTRACT]["currentBoundary"]["independentReviewCompleted"] = False
    expect_rejected(
        "recovery candidate without independent evidence review boundary",
        lambda: run_with_state(module, missing_boundary_review),
    )

    missing_readiness_review = copy.deepcopy(state)
    missing_readiness_review[module.CONTRACT]["readiness"]["independentReviewCompleted"] = False
    expect_rejected(
        "recovery candidate without independent evidence review readiness",
        lambda: run_with_state(module, missing_readiness_review),
    )

    independent_review_rule = copy.deepcopy(state)
    independent_review_rule[module.CONTRACT]["promotionRules"]["independentReviewRequired"] = False
    expect_rejected(
        "recovery candidate independent-review requirement disabled",
        lambda: run_with_state(module, independent_review_rule),
    )

    candidate_rederivation_rule = copy.deepcopy(state)
    candidate_rederivation_rule[module.CONTRACT]["promotionRules"]["candidateCountMustBeRederivedFromCurrentExecutableReviewedEvidence"] = False
    expect_rejected(
        "recovery candidate aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, candidate_rederivation_rule),
    )

    promotion_reviewed = copy.deepcopy(state)
    promotion_reviewed[module.CONTRACT]["currentBoundary"]["humanProductionPromotionReviewCompleted"] = True
    promotion_reviewed[module.CONTRACT]["readiness"]["humanProductionPromotionReviewCompleted"] = True
    expect_rejected(
        "recovery candidate cannot automatically complete human production-promotion review",
        lambda: run_with_state(module, promotion_reviewed),
    )

    promoted = copy.deepcopy(state)
    promoted[module.CONTRACT]["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    promoted[module.CONTRACT]["readiness"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        "recovery candidate cannot automatically authorize production promotion",
        lambda: run_with_state(module, promoted),
    )

    automatic_review_rule = copy.deepcopy(state)
    automatic_review_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyCompletesHumanProductionPromotionReview"] = True
    expect_rejected(
        "automatic candidate-to-human-promotion-review rule",
        lambda: run_with_state(module, automatic_review_rule),
    )

    automatic_promotion_rule = copy.deepcopy(state)
    automatic_promotion_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyAuthorizesProductionPromotion"] = True
    expect_rejected(
        "automatic candidate-to-production-promotion rule",
        lambda: run_with_state(module, automatic_promotion_rule),
    )

    print("Memory OS backup/restore generation binding negative suite PASS")
    print("candidate aggregate without current executable reviewed candidate evidence accepted: false")
    print("candidate aggregate re-derivation contract can be disabled: false")
    print("candidate without independent evidence review accepted: false")
    print("candidate requires independent evidence review: true")
    print("candidate implies human production-promotion review: false")
    print("candidate implies production promotion: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
