#!/usr/bin/env python3
"""Reconcile bounded counters for the end-to-end backup/restore admission chain."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-admission-chain-contract.v1.json")
PREFLIGHT_REL = Path("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
BINDING_CONTRACT_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
TYPED_REGISTRY_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
GEN_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
TYPED_WRITER_REL = Path("scripts/register-memory-os-backup-restore-non-resurrection-evidence.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-admission-chain.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
PREFLIGHT = ROOT / PREFLIGHT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
BINDING_CONTRACT = ROOT / BINDING_CONTRACT_REL
TYPED_REGISTRY = ROOT / TYPED_REGISTRY_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
GEN_WRITER = ROOT / GEN_WRITER_REL
TYPED_WRITER = ROOT / TYPED_WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL


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
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "admission-chain contract"),
        (PREFLIGHT, PREFLIGHT_REL, "preflight contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "generation evidence registry"),
        (BINDING_CONTRACT, BINDING_CONTRACT_REL, "generation binding contract"),
        (TYPED_REGISTRY, TYPED_REGISTRY_REL, "typed non-resurrection registry"),
        (DRILL_WRITER, DRILL_WRITER_REL, "drill request writer"),
        (GEN_WRITER, GEN_WRITER_REL, "generation evidence writer"),
        (TYPED_WRITER, TYPED_WRITER_REL, "typed non-resurrection writer"),
        (VALIDATOR, VALIDATOR_REL, "admission-chain validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise Fail(f"cannot write {relative}: {exc}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer(path: Path, name: str, label: str):
    if path == DRILL_WRITER:
        relative = require_exact_repo_file(path, DRILL_WRITER_REL, f"{label} writer")
    elif path == GEN_WRITER:
        relative = require_exact_repo_file(path, GEN_WRITER_REL, f"{label} writer")
    elif path == TYPED_WRITER:
        relative = require_exact_repo_file(path, TYPED_WRITER_REL, f"{label} writer")
    else:
        relative = require_repo_file(path, f"{label} writer missing")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def load_generation_writer():
    """Compatibility entry point retained for existing negative-suite path checks."""
    return load_writer(GEN_WRITER, "memory_os_generation_writer_admission_chain_reconcile", "generation evidence")


def validate_shared_registry(module: Any, registry: dict[str, Any], label: str) -> list[dict[str, Any]]:
    validator = getattr(module, "validate_registry_for_append", None)
    require(callable(validator), f"{label} shared registry validator missing")
    try:
        rows = validator(registry)
    except Exception as exc:
        fail_type = getattr(module, "Fail", None)
        if isinstance(fail_type, type) and isinstance(exc, fail_type):
            raise Fail(f"{label} registry authority invalid: {exc}") from exc
        raise
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), f"{label} shared registry rows invalid")
    return rows


def run_validator(path: Path, label: str) -> None:
    if path == VALIDATOR:
        require_exact_repo_file(path, VALIDATOR_REL, f"{label} validator")
    elif path == OPERABILITY_VALIDATOR:
        require_exact_repo_file(path, OPERABILITY_VALIDATOR_REL, f"{label} validator")
    else:
        require_repo_file(path, f"{label} validator missing")
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
        f"post-reconcile {label} failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}",
    )


def main() -> int:
    enforce_runtime_authorities()
    for path, message in (
        (CONTRACT, "admission-chain contract missing"),
        (PREFLIGHT, "preflight contract missing"),
        (DRILL_REGISTRY, "drill request registry missing"),
        (GEN_REGISTRY, "generation evidence registry missing"),
        (BINDING_CONTRACT, "generation binding contract missing"),
        (TYPED_REGISTRY, "typed non-resurrection registry missing"),
        (DRILL_WRITER, "drill request writer missing"),
        (GEN_WRITER, "generation evidence writer missing"),
        (TYPED_WRITER, "typed non-resurrection writer missing"),
        (VALIDATOR, "admission-chain validator missing"),
        (OPERABILITY_VALIDATOR, "operability validator missing"),
        (STATUS, "operability status missing"),
    ):
        require_repo_file(path, message)

    original_contract_text = read_text(CONTRACT)
    contract = load(CONTRACT)
    preflight_contract = load(PREFLIGHT)
    drill_registry = load(DRILL_REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    binding_contract = load(BINDING_CONTRACT)
    typed_registry = load(TYPED_REGISTRY)
    status = load(STATUS)
    drill_writer = load_writer(DRILL_WRITER, "memory_os_drill_writer_admission_chain_reconcile", "drill request")
    gen_writer = load_generation_writer()
    typed_writer = load_writer(TYPED_WRITER, "memory_os_typed_writer_admission_chain_reconcile", "typed non-resurrection")

    drill_rows = validate_shared_registry(drill_writer, drill_registry, "drill request")
    gen_rows = validate_shared_registry(gen_writer, gen_registry, "generation evidence")
    typed_rows = validate_shared_registry(typed_writer, typed_registry, "typed non-resurrection")

    preflight = preflight_contract.get("currentState")
    require(isinstance(preflight, dict), "preflight currentState missing")
    preflight_decision = preflight.get("preflightDecision")
    preflight_eligible = preflight.get("eligibleToSubmitReviewedDrillRequest")
    preflight_pair_count = preflight.get("eligibleDirectedSourceTargetPairCount")
    require(isinstance(preflight_decision, str) and preflight_decision, "preflight decision invalid")
    require(isinstance(preflight_eligible, bool), "preflight eligibility invalid")
    require(valid_count(preflight_pair_count), "preflight pair count invalid")
    for field in ("reviewedDrillRequestCount", "currentExecutableDrillRequestCount"):
        require(valid_count(preflight.get(field)), f"preflight {field} must be a non-boolean count")
    require(all(preflight.get(field) is False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")), "preflight execution boundary drift")
    require(preflight.get("productionDecision") == "NO_GO", "preflight production decision drift")

    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(valid_count(drill_count) and drill_count == len(drill_rows), "drill request registry count drift")
    require(valid_count(current_drill_count) and current_drill_count <= drill_count, "current drill request count invalid")
    require(preflight.get("reviewedDrillRequestCount") == drill_count, "preflight reviewed request count drift")
    require(preflight.get("currentExecutableDrillRequestCount") == current_drill_count, "preflight current request count drift")
    if current_drill_count > 0:
        require(preflight_eligible is True and preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST" and preflight_pair_count > 0, "current request/preflight state mismatch")
    elif preflight_eligible:
        require(preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION" and preflight_pair_count > 0, "eligible preflight state mismatch")
    else:
        require(preflight_decision in {
            "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS",
            "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE",
        } and current_drill_count == 0, "blocked preflight/current request mismatch")

    gen_count = gen_registry.get("registeredEvidenceCount")
    bound_count = gen_registry.get("drillRequestBoundEvidenceCount")
    registry_backup_count = gen_registry.get("completeGenerationBoundBackupCount")
    registry_restore_count = gen_registry.get("completeGenerationBoundRestoreCount")
    registry_candidate_count = gen_registry.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(gen_count) and gen_count == len(gen_rows), "generation evidence count drift")
    require(valid_count(bound_count) and bound_count == gen_count, "every generation evidence row must be drill-request-bound")
    for value, field in ((registry_backup_count, "backup"), (registry_restore_count, "restore"), (registry_candidate_count, "candidate")):
        require(valid_count(value) and value <= gen_count, f"generation {field} count invalid")

    derived_backup_count = sum(1 for row in gen_rows if row.get("evidenceComplete") is True)
    derived_restore_count = sum(
        1
        for row in gen_rows
        if row.get("evidenceComplete") is True
        and row.get("isolatedRestoreVerified") is True
        and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
    )
    candidate_count = sum(1 for row in gen_rows if gen_writer.candidate(row))

    require(registry_backup_count == derived_backup_count, "generation backup count drift from immutable evidence rows")
    require(registry_restore_count == derived_restore_count, "generation restore count drift from immutable evidence rows")
    require(registry_candidate_count == candidate_count, "generation candidate count drift")
    require(candidate_count <= derived_restore_count <= derived_backup_count <= gen_count, "derived recovery aggregate ordering drift")

    binding_boundary = binding_contract.get("currentBoundary")
    require(isinstance(binding_boundary, dict), "generation binding currentBoundary missing")
    backup_count = binding_boundary.get("generationBoundBackupCount")
    restore_count = binding_boundary.get("generationBoundRestoreCount")
    binding_candidate_count = binding_boundary.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(backup_count), "generation-bound backup count invalid")
    require(valid_count(restore_count), "generation-bound restore count invalid")
    require(valid_count(binding_candidate_count), "generation binding candidate count invalid")
    require(backup_count == derived_backup_count, "generation binding backup count drift from immutable evidence rows")
    require(restore_count == derived_restore_count, "generation binding restore count drift from immutable evidence rows")
    require(binding_candidate_count == candidate_count, "generation binding candidate count drift")
    require(candidate_count <= restore_count <= backup_count <= gen_count, "recovery aggregate ordering drift")
    require(binding_boundary.get("independentReviewCompleted") is (candidate_count > 0), "generation binding independent review state drift")
    require(binding_boundary.get("humanProductionPromotionReviewCompleted") is False, "generation binding human production-promotion review must remain unclaimed")
    require(binding_boundary.get("humanProductionPromotionAuthorized") is False, "generation binding human production-promotion authorization must remain unclaimed")
    require(binding_boundary.get("productionEvidence") is False and binding_boundary.get("productionReady") is False and binding_boundary.get("productionDecision") == "NO_GO", "generation binding production boundary drift")

    typed_complete_count = typed_registry.get("completeRecordCount")
    typed_covered_count = typed_registry.get("candidateCoveredCount")
    require(valid_count(typed_complete_count), "typed complete count invalid")
    require(valid_count(typed_covered_count), "typed covered count invalid")
    require(typed_covered_count <= typed_complete_count <= len(typed_rows), "typed registry count ordering invalid")
    require(typed_covered_count == candidate_count, "typed candidate coverage must equal final candidate count")

    require(status.get("productionDecision") == "NO_GO", "chain reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    require_canonical_gaps(gate.get("missingEvidence"), Fail)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "chain currentBoundary missing")
    boundary["preflightDecision"] = preflight_decision
    boundary["preflightEligibleToSubmitReviewedDrillRequest"] = preflight_eligible
    boundary["preflightEligibleDirectedSourceTargetPairCount"] = preflight_pair_count
    boundary["reviewedDrillRequestCount"] = drill_count
    boundary["currentExecutableDrillRequestCount"] = current_drill_count
    boundary["generationEvidenceCount"] = gen_count
    boundary["drillRequestBoundGenerationEvidenceCount"] = bound_count
    boundary["generationBoundBackupCount"] = derived_backup_count
    boundary["generationBoundRestoreCount"] = derived_restore_count
    boundary["completeTypedNonResurrectionRecordCount"] = typed_complete_count
    boundary["finalProductionEquivalentRecoveryCandidateCount"] = candidate_count
    boundary["independentEvidenceReviewCompleted"] = candidate_count > 0
    boundary["humanProductionPromotionReviewCompleted"] = False
    boundary["humanProductionPromotionAuthorized"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        run_validator(VALIDATOR, "admission-chain validator")
        run_validator(OPERABILITY_VALIDATOR, "operability validator")
    except Exception:
        write_text(CONTRACT, original_contract_text)
        raise

    print("Memory OS backup/restore admission chain reconciliation PASS")
    print("shared drill/generation/typed append-only registry authority validated before contract write: true")
    print("canonical admission-chain executable authorities enforced: true")
    print(f"preflight: {preflight_decision}")
    print(f"preflight eligible pairs: {preflight_pair_count}")
    print(f"reviewed/current drill requests: {drill_count}/{current_drill_count}")
    print(f"generation/drill-bound evidence: {gen_count}/{bound_count}")
    print(f"generation-bound backup/restore: {derived_backup_count}/{derived_restore_count}")
    print("backup/restore aggregates re-derived before contract write: true")
    print(f"complete typed records/final candidates: {typed_complete_count}/{candidate_count}")
    print("boolean aggregate counts accepted by reconciler: false")
    print("authority reads and executable refs repository-contained: true")
    print("invalid UTF-8 authority accepted: false")
    print("failed chain/operability post-validation leaves derived contract mutation behind: false")
    print(f"candidate-level independent evidence review completed: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production-promotion authorized: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
