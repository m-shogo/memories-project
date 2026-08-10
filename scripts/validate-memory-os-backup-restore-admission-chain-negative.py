#!/usr/bin/env python3
"""Negative suite for end-to-end backup/restore admission-chain authority."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_admission_chain_negative_target", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def run_with_overrides(module: Any, overrides: dict[Path, dict[str, Any]]) -> int:
    original_load = module.load

    def fake_load(path: Path) -> dict[str, Any]:
        if path in overrides:
            return copy.deepcopy(overrides[path])
        return original_load(path)

    module.load = fake_load
    try:
        return module.main()
    finally:
        module.load = original_load


def main() -> int:
    module = load_module()
    real_load = module.load
    contract = copy.deepcopy(real_load(module.CONTRACT))
    inventory = copy.deepcopy(real_load(module.INVENTORY))
    preflight_contract = copy.deepcopy(real_load(module.PREFLIGHT_CONTRACT))

    require(run_with_overrides(module, {}) == 0, "canonical admission-chain baseline must validate")
    print("PASS baseline: canonical end-to-end admission chain validates")

    missing_restore_stage = copy.deepcopy(contract)
    missing_restore_stage["requiredChain"].remove("generationBoundRestore")
    expect_rejected(
        module,
        "generation-bound restore stage deletion",
        lambda: run_with_overrides(module, {module.CONTRACT: missing_restore_stage}),
    )

    reordered_stage = copy.deepcopy(contract)
    stages = reordered_stage["requiredChain"]
    backup_index = stages.index("generationBoundBackup")
    restore_index = stages.index("generationBoundRestore")
    stages[backup_index], stages[restore_index] = stages[restore_index], stages[backup_index]
    expect_rejected(
        module,
        "backup/restore stage reordering",
        lambda: run_with_overrides(module, {module.CONTRACT: reordered_stage}),
    )

    weakened_backup_rederivation = copy.deepcopy(contract)
    weakened_backup_rederivation["invariants"]["generationBoundBackupCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "backup aggregate rederivation invariant disabled",
        lambda: run_with_overrides(module, {module.CONTRACT: weakened_backup_rederivation}),
    )

    weakened_restore_rederivation = copy.deepcopy(contract)
    weakened_restore_rederivation["invariants"]["generationBoundRestoreCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "restore aggregate rederivation invariant disabled",
        lambda: run_with_overrides(module, {module.CONTRACT: weakened_restore_rederivation}),
    )

    weakened_typed_rederivation = copy.deepcopy(contract)
    weakened_typed_rederivation["invariants"]["typedCompleteCountMustBeRederivedFromValidatedEightDomainEvidence"] = False
    expect_rejected(
        module,
        "typed eight-domain rederivation invariant disabled",
        lambda: run_with_overrides(module, {module.CONTRACT: weakened_typed_rederivation}),
    )

    removed_typed_rederivation = copy.deepcopy(contract)
    del removed_typed_rederivation["invariants"]["typedCompleteCountMustBeRederivedFromValidatedEightDomainEvidence"]
    expect_rejected(
        module,
        "typed eight-domain rederivation invariant removed",
        lambda: run_with_overrides(module, {module.CONTRACT: removed_typed_rederivation}),
    )

    projected_backup = copy.deepcopy(inventory)
    ops7 = next(row for row in projected_backup["areas"] if row.get("id") == "OPS-P0-007")
    ops7["dependencyCounts"]["generationBoundBackups"] = 1
    expect_rejected(
        module,
        "inventory-only generation-bound backup projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_backup}),
    )

    projected_restore = copy.deepcopy(inventory)
    ops7 = next(row for row in projected_restore["areas"] if row.get("id") == "OPS-P0-007")
    ops7["dependencyCounts"]["generationBoundBackups"] = 1
    ops7["dependencyCounts"]["generationBoundRestores"] = 1
    expect_rejected(
        module,
        "coordinated inventory backup/restore projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_restore}),
    )

    boolean_pair_count = copy.deepcopy(preflight_contract)
    boolean_pair_count["currentState"]["eligibleDirectedSourceTargetPairCount"] = False
    expect_rejected(
        module,
        "boolean used as preflight pair count",
        lambda: run_with_overrides(module, {module.PREFLIGHT_CONTRACT: boolean_pair_count}),
    )

    boolean_chain_candidate = copy.deepcopy(contract)
    boolean_chain_candidate["currentBoundary"]["finalProductionEquivalentRecoveryCandidateCount"] = False
    expect_rejected(
        module,
        "boolean used as chain final candidate count",
        lambda: run_with_overrides(module, {module.CONTRACT: boolean_chain_candidate}),
    )

    boolean_inventory_candidate = copy.deepcopy(inventory)
    ops7 = next(row for row in boolean_inventory_candidate["areas"] if row.get("id") == "OPS-P0-007")
    ops7["dependencyCounts"]["productionEquivalentRecoveryCandidates"] = False
    expect_rejected(
        module,
        "boolean used as inventory final candidate count",
        lambda: run_with_overrides(module, {module.INVENTORY: boolean_inventory_candidate}),
    )

    boolean_inventory_request = copy.deepcopy(inventory)
    boolean_inventory_request["reviewedBackupRestoreDrillRequestCount"] = False
    expect_rejected(
        module,
        "boolean used as inventory reviewed request count",
        lambda: run_with_overrides(module, {module.INVENTORY: boolean_inventory_request}),
    )

    integer_preflight_eligibility = copy.deepcopy(contract)
    integer_preflight_eligibility["currentBoundary"]["preflightEligibleToSubmitReviewedDrillRequest"] = 0
    expect_rejected(
        module,
        "integer used as chain preflight eligibility boolean",
        lambda: run_with_overrides(module, {module.CONTRACT: integer_preflight_eligibility}),
    )

    integer_independent_review = copy.deepcopy(contract)
    integer_independent_review["currentBoundary"]["independentEvidenceReviewCompleted"] = 0
    expect_rejected(
        module,
        "integer used as chain independent review boolean",
        lambda: run_with_overrides(module, {module.CONTRACT: integer_independent_review}),
    )

    integer_human_review = copy.deepcopy(contract)
    integer_human_review["currentBoundary"]["humanProductionPromotionReviewCompleted"] = 0
    expect_rejected(
        module,
        "integer used as chain human promotion review boolean",
        lambda: run_with_overrides(module, {module.CONTRACT: integer_human_review}),
    )

    integer_human_authorization = copy.deepcopy(contract)
    integer_human_authorization["currentBoundary"]["humanProductionPromotionAuthorized"] = 0
    expect_rejected(
        module,
        "integer used as chain human promotion authorization boolean",
        lambda: run_with_overrides(module, {module.CONTRACT: integer_human_authorization}),
    )

    promoted = copy.deepcopy(contract)
    promoted["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        module,
        "chain-level automatic human production promotion",
        lambda: run_with_overrides(module, {module.CONTRACT: promoted}),
    )

    print("Memory OS backup/restore admission-chain negative suite PASS")
    print("chain stage deletion/reordering accepted: false")
    print("backup/restore aggregate rederivation downgrade accepted: false")
    print("typed eight-domain rederivation downgrade accepted: false")
    print("inventory recovery aggregate projection accepted: false")
    print("boolean-as-count authority accepted: false")
    print("integer-as-review/promotion-boolean authority accepted: false")
    print("candidate may authorize human production promotion: false")
    print("canonical files mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
