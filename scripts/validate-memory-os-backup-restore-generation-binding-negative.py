#!/usr/bin/env python3
"""Negative suite for recovery-candidate versus human-promotion separation."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
STATUS_RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module():
    return load_target(VALIDATOR, "memory_os_restore_generation_binding_negative_target")


def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
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
        "records": [{
            "syntheticCandidate": True,
            "evidenceComplete": True,
            "isolatedRestoreVerified": True,
            "backupArtifactSha256": "a" * 64,
            "restoredBackupArtifactSha256": "a" * 64,
        }],
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


def prove_status_reconcile_boundaries() -> None:
    reconciler = load_target(STATUS_RECONCILER, "memory_os_restore_generation_status_negative_target")
    require(TMP_PARENT.is_dir(), "generation-status temporary fixture parent missing")

    with tempfile.TemporaryDirectory(prefix=".tmp-generation-status-negative-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_rejected(reconciler, "generation status invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8))

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_rejected(reconciler, "generation status authority symlink loop", lambda: reconciler.load(loop_authority))

        contract_copy = tmp / reconciler.CONTRACT.name
        status_copy = tmp / reconciler.STATUS.name
        shutil.copyfile(reconciler.CONTRACT, contract_copy)
        shutil.copyfile(reconciler.STATUS, status_copy)
        original_status = status_copy.read_bytes()

        pass_validator = tmp / "pass-validator.py"
        pass_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
        fail_validator = tmp / "fail-validator.py"
        fail_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(43)\n", encoding="utf-8")

        original_contract_path = reconciler.CONTRACT
        original_status_path = reconciler.STATUS
        original_validator = reconciler.VALIDATOR
        original_backup_validator = reconciler.BACKUP_VALIDATOR
        original_operability_validator = reconciler.OPERABILITY_VALIDATOR
        try:
            reconciler.CONTRACT = contract_copy
            reconciler.STATUS = status_copy
            reconciler.VALIDATOR = pass_validator
            reconciler.BACKUP_VALIDATOR = fail_validator
            reconciler.OPERABILITY_VALIDATOR = pass_validator
            expect_rejected(reconciler, "generation status forced post-validator failure", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status rollback drift after post-validator failure")

            reconciler.BACKUP_VALIDATOR = pass_validator
            reconciler.OPERABILITY_VALIDATOR = fail_validator
            expect_rejected(reconciler, "generation status forced operability failure", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status rollback drift after operability failure")

            contract = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract["currentBoundary"]["generationBoundBackupCount"] = True
            contract_copy.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
            reconciler.OPERABILITY_VALIDATOR = pass_validator
            expect_rejected(reconciler, "generation status boolean boundary count", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status mutated after boolean count rejection")
        finally:
            reconciler.CONTRACT = original_contract_path
            reconciler.STATUS = original_status_path
            reconciler.VALIDATOR = original_validator
            reconciler.BACKUP_VALIDATOR = original_backup_validator
            reconciler.OPERABILITY_VALIDATOR = original_operability_validator

    print("PASS rollback: generation status restored byte-for-byte after forced backup and operability validator failures")


def main() -> int:
    module = load_module()
    state = candidate_state(module)

    require(run_with_state(module, state) == 0, "candidate baseline must validate with evidence review but without human promotion review")
    print("PASS baseline: recovery candidate includes independently re-derived evidence review while human promotion review remains false")

    require(TMP_PARENT.is_dir(), "generation-binding temporary fixture parent missing")
    with tempfile.TemporaryDirectory(prefix=".tmp-generation-binding-load-negative-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_rejected(module, "generation binding invalid UTF-8 authority", lambda: module.load(invalid_utf8))

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_rejected(module, "generation binding unreadable authority directory", lambda: module.load(directory_authority))

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_rejected(module, "generation binding authority symlink loop", lambda: module.load(loop_authority))

    outside_path = Path(tempfile.gettempdir()) / "memory-os-generation-binding-outside-root.json"
    expect_rejected(
        module,
        "generation binding artifact path escapes repository root",
        lambda: module.load(outside_path),
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        escaped_target = Path(temporary_directory) / "outside-local-foundation.json"
        escaped_target.write_text("{}\n", encoding="utf-8")
        link_path = ROOT / ".memory-os-generation-binding-outside-foundation"
        require(not link_path.exists() and not link_path.is_symlink(), "temporary generation-binding symlink path already exists")
        link_path.symlink_to(escaped_target)
        try:
            symlink_state = copy.deepcopy(state)
            symlink_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = str(link_path.relative_to(ROOT))
            expect_rejected(
                module,
                "local foundation evidence symlink escapes repository root",
                lambda: run_with_state(module, symlink_state),
            )
        finally:
            link_path.unlink(missing_ok=True)

    canonical_ref = state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"]
    require(isinstance(canonical_ref, str) and canonical_ref, "baseline local foundation contract ref missing")

    absolute_ref_state = copy.deepcopy(state)
    absolute_ref_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = str((ROOT / canonical_ref).resolve())
    expect_rejected(
        module,
        "local foundation absolute in-repository path is not canonical authority",
        lambda: run_with_state(module, absolute_ref_state),
    )

    parent_alias_state = copy.deepcopy(state)
    parent_alias_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = f"scripts/../{canonical_ref}"
    expect_rejected(
        module,
        "local foundation parent-traversal alias is not canonical authority",
        lambda: run_with_state(module, parent_alias_state),
    )

    impossible_count_order = copy.deepcopy(state)
    impossible_count_order[module.EVIDENCE_REGISTRY]["completeGenerationBoundRestoreCount"] = 0
    expect_rejected(
        module,
        "recovery candidate count cannot exceed complete generation-bound restore count",
        lambda: run_with_state(module, impossible_count_order),
    )

    restore_without_backup = copy.deepcopy(state)
    restore_without_backup[module.EVIDENCE_REGISTRY]["completeGenerationBoundBackupCount"] = 0
    expect_rejected(
        module,
        "generation-bound restore count cannot exceed generation-bound backup count",
        lambda: run_with_state(module, restore_without_backup),
    )

    manufactured_backup_aggregate = copy.deepcopy(state)
    manufactured_backup_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["evidenceComplete"] = False
    expect_rejected(
        module,
        "generation-bound backup aggregate without complete immutable evidence",
        lambda: run_with_state(module, manufactured_backup_aggregate),
    )

    manufactured_restore_aggregate = copy.deepcopy(state)
    manufactured_restore_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["isolatedRestoreVerified"] = False
    expect_rejected(
        module,
        "generation-bound restore aggregate without isolated exact-artifact restore evidence",
        lambda: run_with_state(module, manufactured_restore_aggregate),
    )

    manufactured_aggregate = copy.deepcopy(state)
    manufactured_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["syntheticCandidate"] = False
    expect_rejected(
        module,
        "recovery candidate aggregate without current executable reviewed candidate evidence",
        lambda: run_with_state(module, manufactured_aggregate),
    )

    backup_rederivation_rule = copy.deepcopy(state)
    backup_rederivation_rule[module.CONTRACT]["promotionRules"]["backupCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "generation-bound backup aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, backup_rederivation_rule),
    )

    restore_rederivation_rule = copy.deepcopy(state)
    restore_rederivation_rule[module.CONTRACT]["promotionRules"]["restoreCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "generation-bound restore aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, restore_rederivation_rule),
    )

    missing_boundary_review = copy.deepcopy(state)
    missing_boundary_review[module.CONTRACT]["currentBoundary"]["independentReviewCompleted"] = False
    expect_rejected(
        module,
        "recovery candidate without independent evidence review boundary",
        lambda: run_with_state(module, missing_boundary_review),
    )

    missing_readiness_review = copy.deepcopy(state)
    missing_readiness_review[module.CONTRACT]["readiness"]["independentReviewCompleted"] = False
    expect_rejected(
        module,
        "recovery candidate without independent evidence review readiness",
        lambda: run_with_state(module, missing_readiness_review),
    )

    independent_review_rule = copy.deepcopy(state)
    independent_review_rule[module.CONTRACT]["promotionRules"]["independentReviewRequired"] = False
    expect_rejected(
        module,
        "recovery candidate independent-review requirement disabled",
        lambda: run_with_state(module, independent_review_rule),
    )

    candidate_rederivation_rule = copy.deepcopy(state)
    candidate_rederivation_rule[module.CONTRACT]["promotionRules"]["candidateCountMustBeRederivedFromCurrentExecutableReviewedEvidence"] = False
    expect_rejected(
        module,
        "recovery candidate aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, candidate_rederivation_rule),
    )

    promotion_reviewed = copy.deepcopy(state)
    promotion_reviewed[module.CONTRACT]["currentBoundary"]["humanProductionPromotionReviewCompleted"] = True
    promotion_reviewed[module.CONTRACT]["readiness"]["humanProductionPromotionReviewCompleted"] = True
    expect_rejected(
        module,
        "recovery candidate cannot automatically complete human production-promotion review",
        lambda: run_with_state(module, promotion_reviewed),
    )

    promoted = copy.deepcopy(state)
    promoted[module.CONTRACT]["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    promoted[module.CONTRACT]["readiness"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        module,
        "recovery candidate cannot automatically authorize production promotion",
        lambda: run_with_state(module, promoted),
    )

    automatic_review_rule = copy.deepcopy(state)
    automatic_review_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyCompletesHumanProductionPromotionReview"] = True
    expect_rejected(
        module,
        "automatic candidate-to-human-promotion-review rule",
        lambda: run_with_state(module, automatic_review_rule),
    )

    automatic_promotion_rule = copy.deepcopy(state)
    automatic_promotion_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyAuthorizesProductionPromotion"] = True
    expect_rejected(
        module,
        "automatic candidate-to-production-promotion rule",
        lambda: run_with_state(module, automatic_promotion_rule),
    )

    prove_status_reconcile_boundaries()

    print("Memory OS backup/restore generation binding negative suite PASS")
    print("invalid UTF-8 or unreadable generation-binding authority accepted: false")
    print("generation-binding authority symlink loop accepted: false")
    print("generation status post-validator failure leaves partial status: false")
    print("generation status operability failure leaves partial status: false")
    print("generation status boolean boundary count accepted: false")
    print("artifact path escape accepted: false")
    print("local foundation evidence symlink escape accepted: false")
    print("absolute or parent-traversal local foundation ref accepted: false")
    print("candidate count may exceed complete restore count: false")
    print("generation-bound restore count may exceed backup count: false")
    print("backup aggregate without row-derived complete evidence accepted: false")
    print("restore aggregate without row-derived isolated exact-artifact evidence accepted: false")
    print("backup/restore aggregate re-derivation contract can be disabled: false")
    print("candidate aggregate without current executable reviewed candidate evidence accepted: false")
    print("candidate aggregate re-derivation contract can be disabled: false")
    print("candidate without independent evidence review accepted: false")
    print("candidate requires independent evidence review: true")
    print("candidate implies human production-promotion review: false")
    print("candidate implies production promotion: false")
    print("unexpected exception accepted as a valid rejection: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
