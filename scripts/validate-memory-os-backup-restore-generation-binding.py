#!/usr/bin/env python3
"""Validate fail-closed generation binding for future production-equivalent restore evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
BACKUP_POLICY = ROOT / "contracts/operations/backup-restore-contract.v1.json"
LOCAL_FOUNDATIONS = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
GENERATION = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"


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


def main() -> int:
    contract = load(CONTRACT)
    backup = load(BACKUP_POLICY)
    local = load(LOCAL_FOUNDATIONS)
    generation = load(GENERATION)
    registry = load(REGISTRY)

    require(contract.get("schemaVersion") == "memory-os-backup-restore-generation-binding.v1", "contract schema drift")
    require(contract.get("backupRestorePolicyContract") == str(BACKUP_POLICY.relative_to(ROOT)), "backup policy ref drift")
    require(contract.get("localFoundationEvidence") == str(LOCAL_FOUNDATIONS.relative_to(ROOT)), "local foundation ref drift")
    require(contract.get("environmentGenerationContract") == str(GENERATION.relative_to(ROOT)), "generation contract ref drift")
    require(contract.get("environmentGenerationRegistry") == str(REGISTRY.relative_to(ROOT)), "generation registry ref drift")

    bindings = contract.get("requiredBindings")
    require(isinstance(bindings, dict) and bindings, "requiredBindings required")
    for key, value in bindings.items():
        require(value is True, f"restore generation binding must remain true: {key}")

    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules required")
    for key in (
        "legacyLocalRestoreCanBeRelabeled",
        "backupTimestampAloneIsSufficient",
        "environmentIdWithoutGenerationIsSufficient",
        "sameDatabaseEngineVersionAloneIsSufficient",
        "sameObjectStoreVendorAloneIsSufficient",
        "hashOnlyWithoutRegisteredGenerationIsSufficient",
        "restoreIntoProductionRequired",
        "productionCredentialsRequired",
    ):
        require(promotion.get(key) is False, f"unsafe restore promotion rule: {key}")
    require(promotion.get("isolatedRestoreRequired") is True, "isolated restore must remain required")
    require(promotion.get("independentReviewRequired") is True, "independent review must remain required")

    # Canonical policy stays explicitly unconfigured for production. Local
    # foundations prove exact-source mechanics only and are a separate authority.
    backup_readiness = backup.get("readiness")
    require(isinstance(backup_readiness, dict), "backup policy readiness missing")
    for key in (
        "policyDefined", "protectedDomainsDefined", "restoreLifecycleDefined",
        "mandatoryVerificationDefined", "promotionGuardsDefined",
        "evidenceRecordDefined", "runbookDefined",
    ):
        require(backup_readiness.get(key) is True, f"backup policy foundation regressed: {key}")
    for key in (
        "rpoDefined", "rtoDefined", "postgresBackupConfigured", "postgresPitrConfigured",
        "objectIndependentRetentionConfigured", "backupMonitoringConfigured",
        "isolatedRestoreEnvironmentImplemented", "nonResurrectionAutomationImplemented",
        "restoreDrillCompleted", "productionPromotionRehearsed",
        "independentReviewCompleted", "ready",
    ):
        require(backup_readiness.get(key) is False, f"unproven backup policy state promoted: {key}")
    require(backup.get("productionDecision") == "NO_GO", "backup policy production decision drift")

    require(local.get("schemaVersion") == "memory-os-backup-local-foundation-evidence.v1", "local foundation schema drift")
    require(local.get("productionEvidence") is False and local.get("productionDecision") == "NO_GO", "local foundation evidence boundary drift")
    foundations = local.get("foundations")
    require(isinstance(foundations, list) and len(foundations) == 2, "two local restore foundations required")
    by_id = {item.get("id"): item for item in foundations if isinstance(item, dict)}
    require(set(by_id) == {"LOCAL_POSTGRESQL_LOGICAL_RESTORE", "LOCAL_EXACT_OBJECT_VERSION_RESTORE"}, "local foundation set drift")
    for foundation_id, item in by_id.items():
        require(item.get("status") == "PASS_EVIDENCE_COMMITTED", f"local foundation not committed PASS: {foundation_id}")
        for field in ("contract", "result", "validator", "workflow"):
            ref = item.get(field)
            require(isinstance(ref, str) and (ROOT / ref).is_file(), f"local foundation ref missing: {foundation_id}.{field}")
    combined = local.get("combinedBoundary")
    require(isinstance(combined, dict), "local combined boundary missing")
    require(combined.get("bothExactSourceResultsCommitted") is True, "local exact-source restore results must remain committed")
    for key in (
        "coherentDatabaseObjectRestoreCompleted", "postgresPitrConfigured",
        "independentObjectRetentionConfigured", "productionTlsAndCredentialSeparationVerified",
        "rpoRtoApprovedAndMeasured", "productionPromotionRehearsed",
        "independentReviewCompleted", "productionReady",
    ):
        require(combined.get(key) is False, f"local foundation cannot promote {key}")

    registry_count = registry.get("registeredGenerationCount")
    generations = registry.get("generations")
    require(registry.get("appendOnly") is True, "environment generation registry must be append-only")
    require(registry.get("productionEvidence") is False, "generation registry cannot be production evidence")
    require(registry_count == 0, "current restore foundation expects zero production-equivalent generations")
    require(isinstance(generations, list) and len(generations) == 0, "empty generation registry drift")
    require(registry.get("currentGenerationId") is None, "empty generation registry must have null current generation")

    generation_boundary = generation.get("currentBoundary")
    require(isinstance(generation_boundary, dict), "generation boundary missing")
    require(generation_boundary.get("registeredGenerationCount") == 0, "generation contract count drift")
    require(generation_boundary.get("productionEquivalentDependencies") is False, "generation foundation cannot be equivalent yet")
    require(generation_boundary.get("productionReady") is False, "generation foundation cannot be production ready")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    require(boundary.get("registeredProductionEquivalentGenerationCount") == 0, "restore generation count drift")
    require(boundary.get("generationBoundBackupCount") == 0, "generation-bound backup count must remain zero")
    require(boundary.get("generationBoundRestoreCount") == 0, "generation-bound restore count must remain zero")
    for key in ("productionEquivalentRestoreEvidence", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"restore generation foundation cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    for key in (
        "contractDefined", "validatorImplemented", "automaticWorkflowImplemented",
        "localPostgresqlRestoreFoundationAvailable", "localObjectVersionRestoreFoundationAvailable",
    ):
        require(readiness.get(key) is True, f"restore generation foundation incomplete: {key}")
    for key in (
        "environmentGenerationAvailable", "generationBoundBackupAvailable",
        "generationBoundRestoreAvailable", "independentReviewCompleted",
        "productionEquivalentRestoreEvidence", "productionReady",
    ):
        require(readiness.get(key) is False, f"restore generation foundation cannot enable readiness.{key}")

    print("Memory OS backup/restore generation binding PASS")
    print("local PostgreSQL restore foundation: committed PASS")
    print("local exact object-version restore foundation: committed PASS")
    print("registered production-equivalent generations: 0")
    print("generation-bound backups/restores: 0")
    print("production-equivalent restore evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
