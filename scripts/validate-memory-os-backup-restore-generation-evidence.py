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
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
OBJECTIVES_REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_CONTRACT_REL = Path("contracts/operations/backup-restore-drill-request-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
GEN_BINDING_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
NEGATIVE_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-evidence-negative.py")
SEMANTIC_NEGATIVE_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-semantic-generation-negative.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
OBJECTIVES_REGISTRY = ROOT / OBJECTIVES_REGISTRY_REL
DRILL_CONTRACT = ROOT / DRILL_CONTRACT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
GEN_BINDING = ROOT / GEN_BINDING_REL
WRITER = ROOT / WRITER_REL
NEGATIVE_VALIDATOR = ROOT / NEGATIVE_VALIDATOR_REL
SEMANTIC_NEGATIVE_VALIDATOR = ROOT / SEMANTIC_NEGATIVE_VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT.resolve())
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
        (CONTRACT, CONTRACT_REL, "generation evidence contract"),
        (REGISTRY, REGISTRY_REL, "generation evidence registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (OBJECTIVES_REGISTRY, OBJECTIVES_REGISTRY_REL, "recovery objectives registry"),
        (DRILL_CONTRACT, DRILL_CONTRACT_REL, "drill request contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (GEN_BINDING, GEN_BINDING_REL, "generation binding contract"),
        (WRITER, WRITER_REL, "generation evidence writer"),
        (NEGATIVE_VALIDATOR, NEGATIVE_VALIDATOR_REL, "generation evidence negative validator"),
        (SEMANTIC_NEGATIVE_VALIDATOR, SEMANTIC_NEGATIVE_VALIDATOR_REL, "semantic generation negative validator"),
    ):
        require_exact_repo_file(path, expected, field)


def canonical_contract_ref(ref: Any, field: str) -> Path:
    require(isinstance(ref, str) and ref, f"contract artifact ref invalid: {field}")
    ref_path = Path(ref)
    require(not ref_path.is_absolute() and ".." not in ref_path.parts, f"contract artifact ref must be canonical repository-relative path: {field}")
    relative = repo_relative(ROOT / ref_path)
    require(relative == ref_path, f"contract artifact ref must remain canonical after resolution: {field}")
    require((ROOT / relative).is_file(), f"contract artifact missing: {field}")
    return relative


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "generation evidence writer")
    writer_path = WRITER
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_generation_writer", writer_path)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(path: Path, expected_relative: Path, label: str) -> None:
    require_exact_repo_file(path, expected_relative, label)
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
    expected_ref = NEGATIVE_VALIDATOR_REL.as_posix()
    require(contract.get("negativeAdmissionValidator") == expected_ref, "negative admission validator ref drift")
    cases = contract.get("negativeAdmissionCases")
    require(isinstance(cases, list) and len(cases) >= 15 and len(cases) == len(set(cases)), "negative admission cases incomplete or duplicated")
    run_validator(NEGATIVE_VALIDATOR, NEGATIVE_VALIDATOR_REL, "negative admission suite")
    run_validator(SEMANTIC_NEGATIVE_VALIDATOR, SEMANTIC_NEGATIVE_VALIDATOR_REL, "semantic generation negative admission suite")


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    drill_registry = load(DRILL_REGISTRY)
    binding = load(GEN_BINDING)
    writer = load_writer()

    typed_contract = canonical_contract_ref(contract.get("typedNonResurrectionAdmissionContract"), "typedNonResurrectionAdmissionContract")
    typed_registry = canonical_contract_ref(contract.get("typedNonResurrectionAdmissionRegistry"), "typedNonResurrectionAdmissionRegistry")
    typed_contract_path = ROOT / typed_contract
    typed_registry_path = ROOT / typed_registry
    writer_authorities = (
        ("CONTRACT", CONTRACT, "generation evidence contract"),
        ("REGISTRY", REGISTRY, "generation evidence registry"),
        ("GEN_REGISTRY", GEN_REGISTRY, "environment generation registry"),
        ("CANONICAL_GEN_REGISTRY", GEN_REGISTRY, "canonical environment generation registry"),
        ("OBJECTIVES_REGISTRY", OBJECTIVES_REGISTRY, "recovery objectives registry"),
        ("CANONICAL_OBJECTIVES_REGISTRY", OBJECTIVES_REGISTRY, "canonical recovery objectives registry"),
        ("DRILL_REQUEST_CONTRACT", DRILL_CONTRACT, "drill request contract"),
        ("CANONICAL_DRILL_REQUEST_CONTRACT", DRILL_CONTRACT, "canonical drill request contract"),
        ("DRILL_REQUEST_REGISTRY", DRILL_REGISTRY, "drill request registry"),
        ("CANONICAL_DRILL_REQUEST_REGISTRY", DRILL_REGISTRY, "canonical drill request registry"),
        ("NON_RESURRECTION_CONTRACT", typed_contract_path, "typed non-resurrection contract"),
        ("CANONICAL_NON_RESURRECTION_CONTRACT", typed_contract_path, "canonical typed non-resurrection contract"),
        ("NON_RESURRECTION_REGISTRY", typed_registry_path, "typed non-resurrection registry"),
        ("CANONICAL_NON_RESURRECTION_REGISTRY", typed_registry_path, "canonical typed non-resurrection registry"),
    )
    for name, expected_path, field in writer_authorities:
        require(getattr(writer, name, None) == expected_path, f"generation evidence writer authority drift: {name}")
        if expected_path.is_file():
            writer.canonical_repo_file(expected_path, field)
    generation_writer = getattr(writer, "GEN_WRITER", None)
    objectives_writer = getattr(writer, "OBJECTIVES_WRITER", None)
    non_resurrection_writer = getattr(writer, "NON_RESURRECTION_WRITER", None)
    drill_writer = getattr(writer, "DRILL_REQUEST_WRITER", None)
    require(generation_writer == ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py", "environment generation writer authority drift")
    require(objectives_writer == ROOT / "scripts/register-memory-os-recovery-objectives.py", "recovery objectives writer authority drift")
    require(non_resurrection_writer == ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py", "typed non-resurrection writer authority drift")
    require(drill_writer == ROOT / "scripts/request-memory-os-backup-restore-drill.py", "drill request writer authority drift")
    writer.canonical_repo_file(generation_writer, "environment generation writer")
    writer.canonical_repo_file(objectives_writer, "recovery objectives writer")
    writer.canonical_repo_file(non_resurrection_writer, "typed non-resurrection writer")
    writer.canonical_repo_file(drill_writer, "drill request writer")
    require(callable(getattr(writer, "validate_registry_for_append", None)), "generation writer append authority guard missing")

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
        require(contract.get(field) == str(repo_relative(path)), f"contract ref drift: {field}")
        require(path.is_file(), f"contract artifact missing: {field}")
    for field in ("validator", "reconcile", "workflow"):
        canonical_contract_ref(contract.get(field), field)

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
    require(valid_count(count) and count == len(rows), "registeredEvidenceCount drift")
    require(all(valid_count(value) for value in (bound_count, backup_count, restore_count, candidate_count)), "registry derived counts invalid")

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
    writer.validate_registry_for_append(registry)

    generation_count = generations.get("registeredGenerationCount")
    objective_count = objectives.get("approvedObjectiveCount")
    objective_rows = objectives.get("records")
    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(valid_count(generation_count), "generation registry count invalid")
    require(valid_count(objective_count), "approvedObjectiveCount invalid")
    require(isinstance(objective_rows, list) and len(objective_rows) == objective_count, "recovery objectives registry count drift")
    require(isinstance(drill_rows, list) and valid_count(drill_count) and drill_count == len(drill_rows), "drill request registry count drift")
    require(valid_count(current_drill_count) and current_drill_count <= drill_count, "current drill request count invalid")
    require(drill_registry.get("productionEvidence") is False and drill_registry.get("productionReady") is False, "drill request registry production boundary drift")
    if generation_count == 0 or drill_count == 0:
        require(count == 0, "recovery evidence cannot exist without registered generations and a reviewed drill request")
    if objective_count == 0 or current_drill_count == 0:
        require(candidate_count == 0, "current recovery candidate cannot exist without current objectives and executable drill request")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    boundary_count_fields = (
        "registeredEvidenceCount",
        "drillRequestBoundEvidenceCount",
        "completeGenerationBoundBackupCount",
        "completeGenerationBoundRestoreCount",
        "productionEquivalentRecoveryCandidateCount",
    )
    for field in boundary_count_fields:
        require(valid_count(boundary.get(field)), f"contract {field} must be a non-boolean count")
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
    binding_count_fields = (
        "registeredProductionEquivalentGenerationCount",
        "generationBoundBackupCount",
        "generationBoundRestoreCount",
        "productionEquivalentRecoveryCandidateCount",
    )
    for field in binding_count_fields:
        require(valid_count(binding_boundary.get(field)), f"generation binding {field} must be a non-boolean count")
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
    print("generation evidence validator canonical runtime authorities enforced: true")
    print(f"registered/current drill requests: {drill_count}/{current_drill_count}")
    print(f"registered/drill-bound recovery evidence: {count}/{derived_bound}")
    print(f"complete generation-bound restores: {derived_restore}")
    print(f"production-equivalent recovery candidates: {derived_candidates}")
    print("generation writer canonical cross-authority binding without evidence rows: enforced")
    print("generation writer append authority guard executed: true")
    print("upstream writer identities canonical: true")
    print("boolean registry/contract/binding counts accepted: false")
    print("contract artifact refs canonical and repository-contained: true")
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
