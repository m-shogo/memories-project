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
        "independentReviewCompleted": False,
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
        "independentReviewCompleted": False,
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
        "records": [{}],
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

    def fake_load(path: Path) -> dict[str, Any]:
        if path in state:
            return copy.deepcopy(state[path])
        return original_load(path)

    module.load = fake_load
    try:
        return module.main()
    finally:
        module.load = original_load


def main() -> int:
    module = load_module()
    state = candidate_state(module)

    require(run_with_state(module, state) == 0, "candidate baseline must validate without completing promotion review")
    print("PASS baseline: recovery candidate exists while independent review and production promotion remain false")

    reviewed = copy.deepcopy(state)
    reviewed[module.CONTRACT]["currentBoundary"]["independentReviewCompleted"] = True
    reviewed[module.CONTRACT]["readiness"]["independentReviewCompleted"] = True
    expect_rejected(
        "recovery candidate cannot automatically complete independent review",
        lambda: run_with_state(module, reviewed),
    )

    promoted = copy.deepcopy(state)
    promoted[module.CONTRACT]["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    promoted[module.CONTRACT]["readiness"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        "recovery candidate cannot automatically authorize production promotion",
        lambda: run_with_state(module, promoted),
    )

    automatic_rule = copy.deepcopy(state)
    automatic_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyAuthorizesProductionPromotion"] = True
    expect_rejected(
        "automatic candidate-to-promotion rule",
        lambda: run_with_state(module, automatic_rule),
    )

    print("Memory OS backup/restore generation binding negative suite PASS")
    print("candidate implies independent review: false")
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
