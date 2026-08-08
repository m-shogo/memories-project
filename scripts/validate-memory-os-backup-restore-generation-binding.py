#!/usr/bin/env python3
"""Validate fail-closed generation binding for production-equivalent restore evidence."""

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
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EVIDENCE_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
EVIDENCE_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
REQUIRED_LOCAL_FOUNDATIONS = {
    "LOCAL_POSTGRESQL_LOGICAL_RESTORE",
    "LOCAL_EXACT_OBJECT_VERSION_RESTORE",
    "LOCAL_COHERENT_DATABASE_OBJECT_RECOVERY_SET",
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


def main() -> int:
    contract = load(CONTRACT)
    backup = load(BACKUP_POLICY)
    local = load(LOCAL_FOUNDATIONS)
    generation = load(GENERATION)
    gen_registry = load(GEN_REGISTRY)
    evidence_contract = load(EVIDENCE_CONTRACT)
    evidence_registry = load(EVIDENCE_REGISTRY)

    require(contract.get("schemaVersion") == "memory-os-backup-restore-generation-binding.v1", "contract schema drift")
    refs = {
        "backupRestorePolicyContract": BACKUP_POLICY,
        "localFoundationEvidence": LOCAL_FOUNDATIONS,
        "environmentGenerationContract": GENERATION,
        "environmentGenerationRegistry": GEN_REGISTRY,
        "generationEvidenceContract": EVIDENCE_CONTRACT,
        "generationEvidenceRegistry": EVIDENCE_REGISTRY,
    }
    for field, path in refs.items():
        require(contract.get(field) == str(path.relative_to(ROOT)), f"{field} ref drift")

    bindings = contract.get("requiredBindings")
    require(isinstance(bindings, dict) and bindings and all(value is True for value in bindings.values()), "restore generation bindings must remain fail-closed")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules required")
    for key in (
        "legacyLocalRestoreCanBeRelabeled", "backupTimestampAloneIsSufficient",
        "environmentIdWithoutGenerationIsSufficient", "sameDatabaseEngineVersionAloneIsSufficient",
        "sameObjectStoreVendorAloneIsSufficient", "hashOnlyWithoutRegisteredGenerationIsSufficient",
        "restoreIntoProductionRequired", "productionCredentialsRequired",
    ):
        require(promotion.get(key) is False, f"unsafe restore promotion rule: {key}")
    require(promotion.get("isolatedRestoreRequired") is True, "isolated restore must remain required")
    require(promotion.get("independentReviewRequired") is True, "independent review must remain required")

    backup_readiness = backup.get("readiness")
    require(isinstance(backup_readiness, dict), "backup policy readiness missing")
    for key in (
        "policyDefined", "protectedDomainsDefined", "restoreLifecycleDefined",
        "mandatoryVerificationDefined", "promotionGuardsDefined", "evidenceRecordDefined", "runbookDefined",
    ):
        require(backup_readiness.get(key) is True, f"backup policy foundation regressed: {key}")
    require(backup.get("productionDecision") == "NO_GO", "backup policy production decision drift")
    require(backup_readiness.get("ready") is False, "backup policy cannot be READY from generation evidence")

    require(local.get("schemaVersion") == "memory-os-backup-local-foundation-evidence.v1", "local foundation schema drift")
    require(local.get("productionEvidence") is False and local.get("productionDecision") == "NO_GO", "local foundation evidence boundary drift")
    foundations = local.get("foundations")
    require(isinstance(foundations, list) and all(isinstance(item, dict) for item in foundations), "local restore foundations invalid")
    by_id = {item.get("id"): item for item in foundations}
    require(len(by_id) == len(foundations), "local foundation IDs must be unique")
    require(REQUIRED_LOCAL_FOUNDATIONS.issubset(set(by_id)), f"required local foundation missing: {sorted(REQUIRED_LOCAL_FOUNDATIONS - set(by_id))}")
    for foundation_id, item in by_id.items():
        require(isinstance(foundation_id, str) and foundation_id, "local foundation ID invalid")
        require(item.get("status") == "PASS_EVIDENCE_COMMITTED", f"local foundation not committed PASS: {foundation_id}")
        for field in ("contract", "result", "validator", "workflow"):
            ref = item.get(field)
            require(isinstance(ref, str) and (ROOT / ref).is_file(), f"local foundation ref missing: {foundation_id}.{field}")
    coherent = by_id["LOCAL_COHERENT_DATABASE_OBJECT_RECOVERY_SET"]
    require(any("recovery-set" in str(value) for value in coherent.get("proves", [])), "coherent local recovery-set proof drift")

    generation_count = gen_registry.get("registeredGenerationCount")
    generations = gen_registry.get("generations")
    require(gen_registry.get("appendOnly") is True and gen_registry.get("productionEvidence") is False, "generation registry boundary drift")
    require(isinstance(generation_count, int) and generation_count >= 0, "registered generation count invalid")
    require(isinstance(generations, list) and len(generations) == generation_count, "generation registry count drift")
    generation_boundary = generation.get("currentBoundary")
    require(isinstance(generation_boundary, dict), "generation boundary missing")
    require(generation_boundary.get("registeredGenerationCount") == generation_count, "generation contract count drift")
    require(generation_boundary.get("productionEvidence") is False and generation_boundary.get("productionReady") is False, "generation authority cannot promote production")

    require(evidence_contract.get("schemaVersion") == "memory-os-backup-restore-generation-evidence.v1", "generation evidence contract schema drift")
    require(evidence_registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(evidence_registry.get("appendOnly") is True and evidence_registry.get("productionEvidence") is False and evidence_registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    evidence_count = evidence_registry.get("registeredEvidenceCount")
    backup_count = evidence_registry.get("completeGenerationBoundBackupCount")
    restore_count = evidence_registry.get("completeGenerationBoundRestoreCount")
    candidate_count = evidence_registry.get("productionEquivalentRecoveryCandidateCount")
    evidence_rows = evidence_registry.get("records")
    require(isinstance(evidence_count, int) and isinstance(evidence_rows, list) and len(evidence_rows) == evidence_count, "generation evidence count drift")
    for value, field in ((backup_count, "backup"), (restore_count, "restore"), (candidate_count, "candidate")):
        require(isinstance(value, int) and 0 <= value <= evidence_count, f"generation-bound {field} count invalid")
    require(candidate_count <= restore_count <= backup_count, "generation recovery count ordering invalid")
    if generation_count == 0:
        require(evidence_count == 0, "recovery evidence cannot exist without registered environment generations")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    expected = {
        "registeredProductionEquivalentGenerationCount": generation_count,
        "generationBoundBackupCount": backup_count,
        "generationBoundRestoreCount": restore_count,
        "productionEquivalentRecoveryCandidateCount": candidate_count,
    }
    for field, value in expected.items():
        require(boundary.get(field) == value, f"restore generation boundary drift: {field}")
    require(boundary.get("productionEquivalentRestoreEvidence") is (candidate_count > 0), "productionEquivalentRestoreEvidence derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "restore generation foundation cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    for key in (
        "contractDefined", "validatorImplemented", "automaticWorkflowImplemented",
        "generationEvidenceRegistryImplemented", "localPostgresqlRestoreFoundationAvailable", "localObjectVersionRestoreFoundationAvailable",
    ):
        require(readiness.get(key) is True, f"restore generation foundation incomplete: {key}")
    derived = {
        "environmentGenerationAvailable": generation_count > 0,
        "generationBoundBackupAvailable": backup_count > 0,
        "generationBoundRestoreAvailable": restore_count > 0,
        "productionEquivalentRecoveryCandidateAvailable": candidate_count > 0,
        "independentReviewCompleted": candidate_count > 0,
        "productionEquivalentRestoreEvidence": candidate_count > 0,
    }
    for field, value in derived.items():
        require(readiness.get(field) is value, f"restore generation readiness drift: {field}")
    require(readiness.get("productionReady") is False, "restore generation foundation cannot make application production ready")

    print("Memory OS backup/restore generation binding PASS")
    print(f"local restore foundations validated: {len(foundations)}")
    print("required PostgreSQL logical restore foundation: committed PASS")
    print("required exact object-version restore foundation: committed PASS")
    print("required coherent database/object recovery-set foundation: committed PASS")
    print(f"registered production-equivalent generations: {generation_count}")
    print(f"generation-bound backups/restores: {backup_count}/{restore_count}")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
