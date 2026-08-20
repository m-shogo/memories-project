#!/usr/bin/env python3
"""Negative suite for end-to-end backup/restore admission-chain authority."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-admission-chain.py"


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


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_admission_chain_reconcile_negative_target", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain reconciler")
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


def expect_reconciler_path_rejected(reconciler: Any, field: str, escaped: Path, action: Callable[[], Any]) -> None:
    original = getattr(reconciler, field)
    setattr(reconciler, field, escaped)
    try:
        expect_rejected(reconciler, f"reconciler {field} path escapes repository root", action)
    finally:
        setattr(reconciler, field, original)


def expect_reconciler_rejected_without_contract_write(
    reconciler: Any,
    name: str,
    action: Callable[[], Any],
) -> None:
    before = reconciler.CONTRACT.read_text(encoding="utf-8")
    expect_rejected(reconciler, name, action)
    after = reconciler.CONTRACT.read_text(encoding="utf-8")
    require(after == before, f"reconciler mutated admission-chain contract before rejecting: {name}")


def expect_reconciler_operability_rollback(reconciler: Any) -> None:
    before = reconciler.CONTRACT.read_text(encoding="utf-8")
    calls: list[Path] = []
    original_run_validator = reconciler.run_validator

    def fake_run_validator(path: Path, label: str) -> None:
        calls.append(path)
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("synthetic aggregate operability rejection")

    reconciler.run_validator = fake_run_validator
    try:
        expect_rejected(
            reconciler,
            "reconciler aggregate operability rejection after contract write",
            lambda: reconciler.main(),
        )
    finally:
        reconciler.run_validator = original_run_validator

    after = reconciler.CONTRACT.read_text(encoding="utf-8")
    require(after == before, "reconciler left admission-chain contract mutated after aggregate operability rejection")
    require(
        calls == [reconciler.VALIDATOR, reconciler.OPERABILITY_VALIDATOR],
        "reconciler post-write validator order drift",
    )


def main() -> int:
    module = load_module()
    real_load = module.load
    contract = copy.deepcopy(real_load(module.CONTRACT))
    inventory = copy.deepcopy(real_load(module.INVENTORY))
    preflight_contract = copy.deepcopy(real_load(module.PREFLIGHT_CONTRACT))
    drill_registry = copy.deepcopy(real_load(module.DRILL_REGISTRY))
    generation_registry = copy.deepcopy(real_load(module.GEN_REGISTRY))
    typed_registry = copy.deepcopy(real_load(module.TYPED_REGISTRY))

    require(run_with_overrides(module, {}) == 0, "canonical admission-chain baseline must validate")
    print("PASS baseline: canonical end-to-end admission chain validates")

    escaped_authority = Path("/tmp/memory-os-backup-restore-admission-chain-escaped.json")
    expect_rejected(
        module,
        "admission-chain JSON authority path escapes repository root",
        lambda: module.load(escaped_authority),
    )
    expect_rejected(
        module,
        "admission-chain module authority path escapes repository root",
        lambda: module.load_module(escaped_authority, "memory_os_escaped_admission_chain_authority"),
    )

    drill_class_drift = copy.deepcopy(drill_registry)
    drill_class_drift["registryClass"] = "CORRUPT_RESTORE_REQUEST_AUTHORITY"
    expect_rejected(
        module,
        "drill request registry class drift at chain boundary",
        lambda: run_with_overrides(module, {module.DRILL_REGISTRY: drill_class_drift}),
    )

    drill_append_only_drift = copy.deepcopy(drill_registry)
    drill_append_only_drift["appendOnly"] = False
    expect_rejected(
        module,
        "drill request append-only boundary disabled at chain boundary",
        lambda: run_with_overrides(module, {module.DRILL_REGISTRY: drill_append_only_drift}),
    )

    generation_schema_drift = copy.deepcopy(generation_registry)
    generation_schema_drift["schemaVersion"] = "memory-os-backup-restore-generation-evidence-registry.v0"
    expect_rejected(
        module,
        "generation evidence registry schema drift at chain boundary",
        lambda: run_with_overrides(module, {module.GEN_REGISTRY: generation_schema_drift}),
    )

    generation_append_only_drift = copy.deepcopy(generation_registry)
    generation_append_only_drift["appendOnly"] = False
    expect_rejected(
        module,
        "generation evidence append-only boundary disabled at chain boundary",
        lambda: run_with_overrides(module, {module.GEN_REGISTRY: generation_append_only_drift}),
    )

    typed_schema_drift = copy.deepcopy(typed_registry)
    typed_schema_drift["schemaVersion"] = "memory-os-backup-restore-non-resurrection-admission-registry.v0"
    expect_rejected(
        module,
        "typed non-resurrection registry schema drift at chain boundary",
        lambda: run_with_overrides(module, {module.TYPED_REGISTRY: typed_schema_drift}),
    )

    typed_append_only_drift = copy.deepcopy(typed_registry)
    typed_append_only_drift["appendOnly"] = False
    expect_rejected(
        module,
        "typed non-resurrection append-only boundary disabled at chain boundary",
        lambda: run_with_overrides(module, {module.TYPED_REGISTRY: typed_append_only_drift}),
    )

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

    projected_inventory_review = copy.deepcopy(inventory)
    projected_inventory_review["backupRestoreIndependentEvidenceReviewCompleted"] = True
    expect_rejected(
        module,
        "inventory-only independent evidence review projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_inventory_review}),
    )

    projected_ops7_review = copy.deepcopy(inventory)
    ops7 = next(row for row in projected_ops7_review["areas"] if row.get("id") == "OPS-P0-007")
    ops7["independentEvidenceReviewCompleted"] = True
    expect_rejected(
        module,
        "OPS-P0-007-only independent evidence review projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_ops7_review}),
    )

    projected_inventory_human_review = copy.deepcopy(inventory)
    projected_inventory_human_review["humanProductionPromotionReviewCompleted"] = True
    expect_rejected(
        module,
        "inventory-only human production-promotion review projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_inventory_human_review}),
    )

    projected_ops7_human_authorization = copy.deepcopy(inventory)
    ops7 = next(row for row in projected_ops7_human_authorization["areas"] if row.get("id") == "OPS-P0-007")
    ops7["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        module,
        "OPS-P0-007-only human production-promotion authorization projection",
        lambda: run_with_overrides(module, {module.INVENTORY: projected_ops7_human_authorization}),
    )

    promoted = copy.deepcopy(contract)
    promoted["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        module,
        "chain-level automatic human production promotion",
        lambda: run_with_overrides(module, {module.CONTRACT: promoted}),
    )

    reconciler = load_reconciler()
    reconcile_load = reconciler.load
    reconcile_preflight = copy.deepcopy(reconcile_load(reconciler.PREFLIGHT))
    reconcile_drill = copy.deepcopy(reconcile_load(reconciler.DRILL_REGISTRY))
    reconcile_generation = copy.deepcopy(reconcile_load(reconciler.GEN_REGISTRY))
    reconcile_binding = copy.deepcopy(reconcile_load(reconciler.BINDING_CONTRACT))
    reconcile_typed = copy.deepcopy(reconcile_load(reconciler.TYPED_REGISTRY))

    escaped_reconcile = Path("/tmp/memory-os-backup-restore-admission-chain-reconcile-escaped.json")
    expect_reconciler_path_rejected(
        reconciler,
        "CONTRACT",
        escaped_reconcile,
        lambda: reconciler.main(),
    )
    expect_reconciler_path_rejected(
        reconciler,
        "GEN_WRITER",
        escaped_reconcile,
        lambda: reconciler.load_generation_writer(),
    )

    reconcile_drill_class_drift = copy.deepcopy(reconcile_drill)
    reconcile_drill_class_drift["registryClass"] = "CORRUPT_RESTORE_REQUEST_AUTHORITY"
    expect_reconciler_rejected_without_contract_write(
        reconciler,
        "reconciler drill request registry class drift",
        lambda: run_with_overrides(reconciler, {reconciler.DRILL_REGISTRY: reconcile_drill_class_drift}),
    )

    reconcile_generation_append_only = copy.deepcopy(reconcile_generation)
    reconcile_generation_append_only["appendOnly"] = False
    expect_reconciler_rejected_without_contract_write(
        reconciler,
        "reconciler generation evidence append-only boundary disabled",
        lambda: run_with_overrides(reconciler, {reconciler.GEN_REGISTRY: reconcile_generation_append_only}),
    )

    reconcile_typed_append_only = copy.deepcopy(reconcile_typed)
    reconcile_typed_append_only["appendOnly"] = False
    expect_reconciler_rejected_without_contract_write(
        reconciler,
        "reconciler typed non-resurrection append-only boundary disabled",
        lambda: run_with_overrides(reconciler, {reconciler.TYPED_REGISTRY: reconcile_typed_append_only}),
    )

    manufactured_reconcile_backup = copy.deepcopy(reconcile_generation)
    manufactured_reconcile_backup["completeGenerationBoundBackupCount"] = 1
    expect_reconciler_rejected_without_contract_write(
        reconciler,
        "reconciler manufactured generation-bound backup aggregate",
        lambda: run_with_overrides(
            reconciler,
            {reconciler.GEN_REGISTRY: manufactured_reconcile_backup},
        ),
    )

    manufactured_reconcile_recovery = copy.deepcopy(reconcile_generation)
    manufactured_reconcile_recovery["completeGenerationBoundBackupCount"] = 1
    manufactured_reconcile_recovery["completeGenerationBoundRestoreCount"] = 1
    expect_reconciler_rejected_without_contract_write(
        reconciler,
        "reconciler coordinated manufactured backup/restore aggregates",
        lambda: run_with_overrides(
            reconciler,
            {reconciler.GEN_REGISTRY: manufactured_reconcile_recovery},
        ),
    )

    reconcile_boolean_pair = copy.deepcopy(reconcile_preflight)
    reconcile_boolean_pair["currentState"]["eligibleDirectedSourceTargetPairCount"] = False
    expect_rejected(
        reconciler,
        "reconciler boolean preflight pair count",
        lambda: run_with_overrides(reconciler, {reconciler.PREFLIGHT: reconcile_boolean_pair}),
    )

    reconcile_boolean_drill = copy.deepcopy(reconcile_drill)
    reconcile_boolean_drill["registeredRequestCount"] = False
    expect_rejected(
        reconciler,
        "reconciler boolean drill registry count",
        lambda: run_with_overrides(reconciler, {reconciler.DRILL_REGISTRY: reconcile_boolean_drill}),
    )

    reconcile_boolean_generation = copy.deepcopy(reconcile_generation)
    reconcile_boolean_generation["registeredEvidenceCount"] = False
    expect_rejected(
        reconciler,
        "reconciler boolean generation evidence count",
        lambda: run_with_overrides(reconciler, {reconciler.GEN_REGISTRY: reconcile_boolean_generation}),
    )

    reconcile_boolean_binding = copy.deepcopy(reconcile_binding)
    reconcile_boolean_binding["currentBoundary"]["generationBoundBackupCount"] = False
    expect_rejected(
        reconciler,
        "reconciler boolean generation-bound backup count",
        lambda: run_with_overrides(reconciler, {reconciler.BINDING_CONTRACT: reconcile_boolean_binding}),
    )

    reconcile_boolean_typed = copy.deepcopy(reconcile_typed)
    reconcile_boolean_typed["completeRecordCount"] = False
    expect_rejected(
        reconciler,
        "reconciler boolean typed complete count",
        lambda: run_with_overrides(reconciler, {reconciler.TYPED_REGISTRY: reconcile_boolean_typed}),
    )

    expect_reconciler_operability_rollback(reconciler)

    print("Memory OS backup/restore admission-chain negative suite PASS")
    print("escaped JSON/module authority path accepted: false")
    print("shared drill/generation/typed registry shape corruption accepted: false")
    print("escaped reconciler contract/module authority path accepted: false")
    print("reconciler shared registry shape corruption repaired before rejection: false")
    print("reconciler manufactured recovery aggregates accepted before contract write: false")
    print("chain stage deletion/reordering accepted: false")
    print("backup/restore aggregate rederivation downgrade accepted: false")
    print("typed eight-domain rederivation downgrade accepted: false")
    print("inventory recovery aggregate projection accepted: false")
    print("boolean-as-count authority accepted: false")
    print("integer-as-review/promotion-boolean authority accepted: false")
    print("inventory review/promotion projection accepted: false")
    print("reconciler boolean aggregate authority accepted: false")
    print("post-write aggregate operability rejection leaves contract mutation behind: false")
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
