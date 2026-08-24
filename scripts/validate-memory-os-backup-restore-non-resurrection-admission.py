#!/usr/bin/env python3
"""Validate typed non-resurrection coverage for generation-bound restore admission."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-negative.py"
PATH_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py"
LOCAL_APPLE_VALIDATOR = ROOT / "scripts/validate-memory-os-local-apple-replay-restore.py"
LOCAL_COHERENT_VALIDATOR = ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def domain_validation_failure(exc: BaseException) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RuntimeError) and current.__class__.__name__ == "Fail":
            return True
        current = current.__cause__ or current.__context__
    return False

def repo_relative(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"artifact path missing, unreadable, or escapes repository root: {path}") from exc

def enforce_runtime_authorities() -> None:
    canonical_lock = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
    require(EXPECTED_LOCK == canonical_lock, "typed non-resurrection append-lock authority drift")
    require(EXPECTED_LOCK.parent == REGISTRY.parent, "typed non-resurrection append lock must share registry authority directory")
    require(not EXPECTED_LOCK.is_symlink(), "typed non-resurrection append lock must not be a symlink")
    if EXPECTED_LOCK.exists():
        require(EXPECTED_LOCK.is_file(), "typed non-resurrection materialized append lock must be a regular file")
        try:
            resolved = EXPECTED_LOCK.resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise Fail("typed non-resurrection materialized append lock is unreadable") from exc
        require(resolved == canonical_lock, "typed non-resurrection materialized append lock authority drift")

def canonical_repo_file_ref(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value, f"{field} must be a non-empty repository-relative path")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be a canonical repository-relative path")
    path = ROOT / relative
    require(repo_relative(path) == relative and path.is_file(), f"{field} artifact missing or escapes repository: {value}")
    return path

def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value

def load_module(path: Path, name: str):
    relative = repo_relative(path)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_validator(path: Path, label: str) -> None:
    repo_relative(path)
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-3000:]}{completed.stderr[-3000:]}")

CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
CANONICAL_MODULE_FROM_SPEC = importlib.util.module_from_spec

def enforce_execution_transport(
    canonical_subprocess_run=CANONICAL_SUBPROCESS_RUN,
    canonical_spec_from_file_location=CANONICAL_SPEC_FROM_FILE_LOCATION,
    canonical_module_from_spec=CANONICAL_MODULE_FROM_SPEC,
) -> None:
    if subprocess.run is not canonical_subprocess_run:
        raise Fail("typed non-resurrection subprocess execution transport drift")
    if importlib.util.spec_from_file_location is not canonical_spec_from_file_location:
        raise Fail("typed non-resurrection import spec transport drift")
    if importlib.util.module_from_spec is not canonical_module_from_spec:
        raise Fail("typed non-resurrection module loader transport drift")

CANONICAL_EXECUTION_GUARD = enforce_execution_transport

def main(canonical_execution_guard=CANONICAL_EXECUTION_GUARD) -> int:
    if enforce_execution_transport is not canonical_execution_guard:
        raise Fail("typed non-resurrection execution guard drift")
    enforce_execution_transport()
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation_contract = load(GEN_CONTRACT)
    generation_registry = load(GEN_REGISTRY)
    writer = load_module(WRITER, "memory_os_non_resurrection_writer")
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_recovery_writer_overlay")

    typed_writer_authorities = (
        ("CONTRACT", "CANONICAL_CONTRACT", CONTRACT, "typed non-resurrection contract"),
        ("REGISTRY", "CANONICAL_REGISTRY", REGISTRY, "typed non-resurrection registry"),
        ("GEN_EVIDENCE_REGISTRY", "CANONICAL_GEN_EVIDENCE_REGISTRY", GEN_REGISTRY, "generation evidence registry"),
    )
    for runtime_name, canonical_name, expected_path, field in typed_writer_authorities:
        runtime_path = getattr(writer, runtime_name, None)
        canonical_path = getattr(writer, canonical_name, None)
        require(runtime_path == expected_path, f"typed writer runtime authority drift: {runtime_name}")
        require(canonical_path == expected_path, f"typed writer canonical authority drift: {canonical_name}")
        writer.require_canonical_runtime_authority(runtime_path, canonical_path, field)
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "typed writer append lock authority drift")
    require(writer_lock.parent == REGISTRY.parent, "typed writer append lock must share registry authority directory")
    require(getattr(writer, "GEN_WRITER", None) == GEN_WRITER, "typed writer generation recovery executable drift")
    writer.canonical_repo_file(GEN_WRITER, "generation recovery writer")

    generation_writer_authorities = (
        ("CONTRACT", GEN_CONTRACT, "generation evidence contract"),
        ("REGISTRY", GEN_REGISTRY, "generation evidence registry"),
        ("NON_RESURRECTION_CONTRACT", CONTRACT, "typed non-resurrection contract"),
        ("CANONICAL_NON_RESURRECTION_CONTRACT", CONTRACT, "canonical typed non-resurrection contract"),
        ("NON_RESURRECTION_REGISTRY", REGISTRY, "typed non-resurrection registry"),
        ("CANONICAL_NON_RESURRECTION_REGISTRY", REGISTRY, "canonical typed non-resurrection registry"),
    )
    for name, expected_path, field in generation_writer_authorities:
        require(getattr(generation_writer, name, None) == expected_path, f"generation writer typed-overlay authority drift: {name}")
        if hasattr(generation_writer, "canonical_repo_file") and expected_path.is_file():
            generation_writer.canonical_repo_file(expected_path, field)
    generation_environment_writer = getattr(generation_writer, "GEN_WRITER", None)
    generation_objectives_writer = getattr(generation_writer, "OBJECTIVES_WRITER", None)
    generation_drill_writer = getattr(generation_writer, "DRILL_REQUEST_WRITER", None)
    generation_non_resurrection_writer = getattr(generation_writer, "NON_RESURRECTION_WRITER", None)
    require(generation_environment_writer == ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py", "generation writer environment authority executable drift")
    require(generation_objectives_writer == ROOT / "scripts/register-memory-os-recovery-objectives.py", "generation writer recovery objectives executable drift")
    require(generation_drill_writer == ROOT / "scripts/request-memory-os-backup-restore-drill.py", "generation writer drill request executable drift")
    require(generation_non_resurrection_writer == WRITER, "generation writer typed overlay executable drift")
    generation_writer.canonical_repo_file(generation_environment_writer, "environment generation writer")
    generation_writer.canonical_repo_file(generation_objectives_writer, "recovery objectives writer")
    generation_writer.canonical_repo_file(generation_drill_writer, "restore drill request writer")
    generation_writer.canonical_repo_file(generation_non_resurrection_writer, "typed non-resurrection writer")

    try:
        validated_rows = writer.validate_registry_for_append(registry)
    except Exception as exc:
        if domain_validation_failure(exc):
            raise Fail(f"typed writer append authority invalid: {exc}") from exc
        raise

    require(contract.get("schemaVersion") == "memory-os-backup-restore-non-resurrection-admission.v1", "contract schema drift")
    for field in ("registry", "generationEvidenceRegistry", "writer", "validator", "negativeAdmissionValidator", "reconcile", "workflow"):
        canonical_repo_file_ref(contract.get(field), f"contract.{field}")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "recordRules must remain fail-closed")
    coverage_rule = contract.get("candidateCoverageRule")
    require(isinstance(coverage_rule, dict) and coverage_rule and all(value is True for value in coverage_rule.values()), "candidateCoverageRule drift")
    required_domains = contract.get("requiredDomains")
    require(isinstance(required_domains, list) and len(required_domains) == 8 and len(required_domains) == len(set(required_domains)), "requiredDomains drift")

    require(generation_contract.get("typedNonResurrectionAdmissionContract") == str(CONTRACT.relative_to(ROOT)), "generation contract typed overlay ref drift")
    require(generation_contract.get("typedNonResurrectionAdmissionRegistry") == str(REGISTRY.relative_to(ROOT)), "generation contract typed overlay registry ref drift")
    generation_rules = generation_contract.get("recordRules")
    require(isinstance(generation_rules, dict) and generation_rules.get("typedNonResurrectionCoverageRequiredForProductionEquivalentRestoreCandidate") is True, "generation contract typed coverage gate missing")
    require(generation_rules.get("genericNonResurrectionPassAloneCannotCreateCandidate") is True, "generation contract generic PASS bypass guard missing")
    generation_promotion = generation_contract.get("promotionBoundary")
    require(isinstance(generation_promotion, dict) and generation_promotion.get("completeReviewedRecordAlsoRequiresTypedNonResurrectionCoverage") is True, "generation promotion boundary is not typed-overlay bound")

    local = contract.get("localFoundationEvidence")
    require(isinstance(local, dict), "localFoundationEvidence missing")
    require(local.get("localEvidenceMaySatisfyProductionEquivalentTypedRecord") is False, "local evidence cannot satisfy production-equivalent typed record")
    for key in ("appleReplayRestoreContract", "appleReplayRestoreResult", "coherentRecoverySetContract", "coherentRecoverySetResult"):
        canonical_repo_file_ref(local.get(key), f"localFoundationEvidence.{key}")
    run_validator(LOCAL_APPLE_VALIDATOR, "local Apple replay restore validator")
    run_validator(LOCAL_COHERENT_VALIDATOR, "local coherent recovery-set validator")

    require(registry.get("schemaVersion") == "memory-os-backup-restore-non-resurrection-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry production boundary drift")
    rows = registry.get("records")
    count = registry.get("registeredRecordCount")
    complete_count = registry.get("completeRecordCount")
    covered_count = registry.get("candidateCoveredCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "typed registry records invalid")
    require(validated_rows == rows, "typed writer append authority row projection drift")
    require(valid_count(count) and count == len(rows), "registeredRecordCount drift")
    require(valid_count(complete_count), "completeRecordCount invalid")
    require(valid_count(covered_count), "candidateCoveredCount invalid")
    ids: set[str] = set()
    generation_ids: set[str] = set()
    for row in rows:
        writer.validate_record(row)
        record_id = row.get("recordId")
        generation_id = row.get("generationEvidenceId")
        require(isinstance(record_id, str) and record_id not in ids, f"duplicate recordId: {record_id}")
        require(isinstance(generation_id, str) and generation_id not in generation_ids, f"duplicate typed coverage for generation evidence: {generation_id}")
        ids.add(record_id)
        generation_ids.add(generation_id)
    derived_complete = sum(1 for row in rows if row.get("evidenceComplete") is True)
    require(complete_count == derived_complete, "completeRecordCount drift")

    generation_rows = generation_registry.get("records")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation recovery registry records invalid")
    base_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.base_candidate(row)}
    final_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.candidate(row)}
    require(None not in base_candidate_ids and None not in final_candidate_ids, "candidate evidenceId missing")
    complete_typed_ids = {row.get("generationEvidenceId") for row in rows if row.get("evidenceComplete") is True}
    covered_base_ids = base_candidate_ids & complete_typed_ids
    pending_typed_ids = base_candidate_ids - complete_typed_ids
    require(final_candidate_ids == covered_base_ids, "final candidate derivation bypasses typed non-resurrection coverage")
    require(covered_count == len(covered_base_ids), "candidateCoveredCount drift")
    generation_candidate_count = generation_registry.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(generation_candidate_count), "generation registry final candidate count invalid")
    require(generation_candidate_count == len(final_candidate_ids), "generation registry final candidate count drift")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    for field in (
        "registeredTypedRecordCount",
        "completeTypedRecordCount",
        "productionEquivalentRecoveryCandidateCount",
        "candidateCoveredCount",
        "preOverlayEligiblePendingTypedCoverageCount",
    ):
        require(valid_count(boundary.get(field)), f"contract {field} must be a non-boolean count")
    require(boundary.get("registeredTypedRecordCount") == count, "contract typed record count drift")
    require(boundary.get("completeTypedRecordCount") == derived_complete, "contract complete typed count drift")
    require(boundary.get("productionEquivalentRecoveryCandidateCount") == len(final_candidate_ids), "contract candidate count drift")
    require(boundary.get("candidateCoveredCount") == len(covered_base_ids), "contract covered candidate count drift")
    require(boundary.get("preOverlayEligiblePendingTypedCoverageCount") == len(pending_typed_ids), "contract pending typed coverage count drift")
    require(boundary.get("productionEquivalentNonResurrectionEvidence") is (len(final_candidate_ids) > 0), "contract non-resurrection evidence derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "contract cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    require(readiness.get("localAppleReplayRestoreProven") is True, "local Apple replay proof readiness drift")
    require(readiness.get("localCoherentRecoverySetProven") is True, "local coherent recovery proof readiness drift")
    require(readiness.get("productionEquivalentCandidateAvailable") is (len(final_candidate_ids) > 0), "candidate availability drift")
    require(readiness.get("productionEquivalentCandidateTypedCoverageComplete") is (len(final_candidate_ids) > 0), "typed candidate coverage readiness drift")
    require(readiness.get("independentReviewCompleted") is (len(final_candidate_ids) > 0), "independent review readiness drift")
    require(readiness.get("productionEquivalentNonResurrectionEvidence") is (len(final_candidate_ids) > 0), "non-resurrection readiness drift")
    require(readiness.get("productionReady") is False, "overlay cannot make application production ready")

    run_validator(NEGATIVE, "non-resurrection negative admission suite")
    run_validator(PATH_NEGATIVE, "non-resurrection contract path negative suite")
    print("Memory OS backup/restore typed non-resurrection admission validation PASS")
    print(f"pre-overlay eligible generation records: {len(base_candidate_ids)}")
    print(f"typed records: {count}")
    print(f"final production-equivalent recovery candidates: {len(final_candidate_ids)}")
    print(f"pending typed coverage: {len(pending_typed_ids)}")
    print("typed/generation writer canonical cross-authority binding without records: enforced")
    print("standalone typed validator delegates append/upstream authority: true")
    print("typed/generation upstream writer identities canonical: true")
    print("canonical typed writer append lock authority validated: true")
    print("typed validator execution transport substitution accepted: false")
    print("boolean typed/generation/boundary counts accepted: false")
    print("generic PASS candidate bypass: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
