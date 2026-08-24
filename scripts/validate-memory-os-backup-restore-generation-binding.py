#!/usr/bin/env python3
"""Validate fail-closed generation binding for production-equivalent restore evidence."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
BACKUP_POLICY_REL = Path("contracts/operations/backup-restore-contract.v1.json")
LOCAL_FOUNDATIONS_REL = Path("contracts/operations/backup-local-foundation-evidence.v1.json")
GENERATION_REL = Path("contracts/operations/production-equivalent-environment-generation-contract.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
EVIDENCE_CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
EVIDENCE_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
EVIDENCE_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
CONTRACT = ROOT / CONTRACT_REL
BACKUP_POLICY = ROOT / BACKUP_POLICY_REL
LOCAL_FOUNDATIONS = ROOT / LOCAL_FOUNDATIONS_REL
GENERATION = ROOT / GENERATION_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
EVIDENCE_CONTRACT = ROOT / EVIDENCE_CONTRACT_REL
EVIDENCE_REGISTRY = ROOT / EVIDENCE_REGISTRY_REL
EVIDENCE_WRITER = ROOT / EVIDENCE_WRITER_REL
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


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"artifact path escapes repository root: {path}") from exc


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "generation binding contract"),
        (BACKUP_POLICY, BACKUP_POLICY_REL, "backup restore policy contract"),
        (LOCAL_FOUNDATIONS, LOCAL_FOUNDATIONS_REL, "local restore foundation evidence"),
        (GENERATION, GENERATION_REL, "environment generation contract"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (EVIDENCE_CONTRACT, EVIDENCE_CONTRACT_REL, "generation evidence contract"),
        (EVIDENCE_REGISTRY, EVIDENCE_REGISTRY_REL, "generation evidence registry"),
        (EVIDENCE_WRITER, EVIDENCE_WRITER_REL, "generation evidence writer"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_evidence_writer():
    require_exact_repo_file(EVIDENCE_WRITER, EVIDENCE_WRITER_REL, "generation evidence writer")
    relative = EVIDENCE_WRITER_REL
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_writer_for_binding", EVIDENCE_WRITER)
    require(spec is not None and spec.loader is not None, f"cannot load generation evidence writer: {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot load generation evidence writer {relative}: {exc}") from exc
    return module


CANONICAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
CANONICAL_MODULE_FROM_SPEC = importlib.util.module_from_spec


def enforce_execution_transport(
    canonical_spec_from_file_location=CANONICAL_SPEC_FROM_FILE_LOCATION,
    canonical_module_from_spec=CANONICAL_MODULE_FROM_SPEC,
) -> None:
    if importlib.util.spec_from_file_location is not canonical_spec_from_file_location:
        raise Fail("generation binding import spec transport drift")
    if importlib.util.module_from_spec is not canonical_module_from_spec:
        raise Fail("generation binding module loader transport drift")


CANONICAL_EXECUTION_GUARD = enforce_execution_transport


def main(canonical_execution_guard=CANONICAL_EXECUTION_GUARD) -> int:
    if enforce_execution_transport is not canonical_execution_guard:
        raise Fail("generation binding execution guard drift")
    enforce_execution_transport()
    enforce_runtime_authorities()
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
        require(contract.get(field) == str(repo_relative(path)), f"{field} ref drift")
    require(EVIDENCE_WRITER.is_file(), "generation evidence writer missing")

    bindings = contract.get("requiredBindings")
    require(isinstance(bindings, dict) and bindings and all(value is True for value in bindings.values()), "restore generation bindings must remain fail-closed")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules required")
    for key in (
        "legacyLocalRestoreCanBeRelabeled", "backupTimestampAloneIsSufficient",
        "environmentIdWithoutGenerationIsSufficient", "sameDatabaseEngineVersionAloneIsSufficient",
        "sameObjectStoreVendorAloneIsSufficient", "hashOnlyWithoutRegisteredGenerationIsSufficient",
        "restoreIntoProductionRequired", "productionCredentialsRequired",
        "recoveryCandidateAutomaticallyCompletesHumanProductionPromotionReview",
        "recoveryCandidateAutomaticallyAuthorizesProductionPromotion",
    ):
        require(promotion.get(key) is False, f"unsafe restore promotion rule: {key}")
    require(promotion.get("isolatedRestoreRequired") is True, "isolated restore must remain required")
    require(promotion.get("independentReviewRequired") is True, "candidate-level independent evidence review must remain required")
    require(promotion.get("backupCountMustBeRederivedFromImmutableEvidence") is True, "backup aggregate must be re-derived from immutable generation evidence")
    require(promotion.get("restoreCountMustBeRederivedFromImmutableEvidence") is True, "restore aggregate must be re-derived from immutable generation evidence")
    require(promotion.get("candidateCountMustBeRederivedFromCurrentExecutableReviewedEvidence") is True, "candidate aggregate must be re-derived from current executable reviewed evidence")
    require(promotion.get("humanProductionPromotionReviewRemainsSeparate") is True, "human production-promotion review must remain separate")

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
            require(isinstance(ref, str) and ref, f"local foundation ref invalid: {foundation_id}.{field}")
            ref_path = Path(ref)
            require(not ref_path.is_absolute() and ".." not in ref_path.parts, f"local foundation ref must be canonical repository-relative path: {foundation_id}.{field}")
            relative = repo_relative(ROOT / ref_path)
            require(relative == ref_path, f"local foundation ref must remain canonical after resolution: {foundation_id}.{field}")
            require((ROOT / relative).is_file(), f"local foundation ref missing: {foundation_id}.{field}")
    coherent = by_id["LOCAL_COHERENT_DATABASE_OBJECT_RECOVERY_SET"]
    require(any("recovery-set" in str(value) for value in coherent.get("proves", [])), "coherent local recovery-set proof drift")

    generation_count = gen_registry.get("registeredGenerationCount")
    generations = gen_registry.get("generations")
    require(gen_registry.get("appendOnly") is True and gen_registry.get("productionEvidence") is False, "generation registry boundary drift")
    require(valid_count(generation_count), "registered generation count invalid")
    require(isinstance(generations, list) and len(generations) == generation_count, "generation registry count drift")
    generation_boundary = generation.get("currentBoundary")
    require(isinstance(generation_boundary, dict), "generation boundary missing")
    require(valid_count(generation_boundary.get("registeredGenerationCount")), "generation contract registeredGenerationCount must be a non-boolean count")
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
    require(valid_count(evidence_count) and isinstance(evidence_rows, list) and len(evidence_rows) == evidence_count, "generation evidence count drift")
    require(all(isinstance(row, dict) for row in evidence_rows), "generation evidence rows invalid")
    for value, field in ((backup_count, "backup"), (restore_count, "restore"), (candidate_count, "candidate")):
        require(valid_count(value) and value <= evidence_count, f"generation-bound {field} count invalid")
    require(candidate_count <= restore_count <= backup_count, "generation recovery count ordering invalid")
    if generation_count == 0:
        require(evidence_count == 0, "recovery evidence cannot exist without registered environment generations")

    evidence_writer = load_evidence_writer()
    derived_backup_count = 0
    derived_restore_count = 0
    derived_candidate_count = 0
    for row in evidence_rows:
        evidence_writer.validate_record(row, require_current_drill_request=False)
        if row.get("evidenceComplete") is True:
            derived_backup_count += 1
        if (
            row.get("evidenceComplete") is True
            and row.get("isolatedRestoreVerified") is True
            and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
        ):
            derived_restore_count += 1
        if evidence_writer.candidate(row):
            derived_candidate_count += 1
    require(backup_count == derived_backup_count, "generation evidence registry backup aggregate drift from immutable evidence rows")
    require(restore_count == derived_restore_count, "generation evidence registry restore aggregate drift from immutable evidence rows")
    require(candidate_count == derived_candidate_count, "generation evidence registry candidate aggregate drift from current executable reviewed evidence")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    expected = {
        "registeredProductionEquivalentGenerationCount": generation_count,
        "generationBoundBackupCount": backup_count,
        "generationBoundRestoreCount": restore_count,
        "productionEquivalentRecoveryCandidateCount": candidate_count,
    }
    for field, value in expected.items():
        require(valid_count(boundary.get(field)), f"restore generation boundary {field} must be a non-boolean count")
        require(boundary.get(field) == value, f"restore generation boundary drift: {field}")
    require(boundary.get("productionEquivalentRestoreEvidence") is (candidate_count > 0), "productionEquivalentRestoreEvidence derivation drift")
    require(boundary.get("independentReviewCompleted") is (candidate_count > 0), "candidate-level independent evidence review derivation drift")
    require(boundary.get("humanProductionPromotionReviewCompleted") is False, "recovery candidate must not complete human production-promotion review")
    require(boundary.get("humanProductionPromotionAuthorized") is False, "recovery candidate must not authorize human production promotion")
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
    require(readiness.get("humanProductionPromotionReviewCompleted") is False, "candidate availability must not imply human promotion review completion")
    require(readiness.get("humanProductionPromotionAuthorized") is False, "candidate availability must not imply production promotion authority")
    require(readiness.get("productionReady") is False, "restore generation foundation cannot make application production ready")

    print("Memory OS backup/restore generation binding PASS")
    print("generation binding canonical data/writer authority substitution accepted: false")
    print("generation binding execution transport substitution accepted: false")
    print("generation binding execution guard substitution accepted: false")
    print(f"local restore foundations validated: {len(foundations)}")
    print("required PostgreSQL logical restore foundation: committed PASS")
    print("required exact object-version restore foundation: committed PASS")
    print("required coherent database/object recovery-set foundation: committed PASS")
    print(f"registered production-equivalent generations: {generation_count}")
    print(f"generation-bound backups/restores: {backup_count}/{restore_count}")
    print("backup/restore aggregates re-derived from immutable generation evidence: true")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print("recovery candidate aggregate re-derived from current executable reviewed evidence: true")
    print("boolean generation/evidence/boundary counts accepted: false")
    print(f"candidate-level independent evidence review complete: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed by recovery candidate: false")
    print("human production promotion authorized by recovery candidate: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
