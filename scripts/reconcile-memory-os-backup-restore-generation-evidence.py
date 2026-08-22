#!/usr/bin/env python3
"""Reconcile drill-bound generation recovery evidence without promoting production readiness."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
OBJECTIVES_REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
BINDING_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-evidence.py")
BINDING_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-binding.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
OBJECTIVES_REGISTRY = ROOT / OBJECTIVES_REGISTRY_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
BINDING = ROOT / BINDING_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
BINDING_VALIDATOR = ROOT / BINDING_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
REFS = (
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    ".github/workflows/backup-restore-generation-evidence.yml",
)
EVIDENCE_PREFIX = "generation-bound backup/restore evidence admission is append-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


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
        (CONTRACT, CONTRACT_REL, "generation evidence contract"),
        (REGISTRY, REGISTRY_REL, "generation evidence registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (OBJECTIVES_REGISTRY, OBJECTIVES_REGISTRY_REL, "recovery objectives registry"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (BINDING, BINDING_REL, "generation binding contract"),
        (WRITER, WRITER_REL, "generation evidence writer"),
        (VALIDATOR, VALIDATOR_REL, "generation evidence validator"),
        (BINDING_VALIDATOR, BINDING_VALIDATOR_REL, "generation binding validator"),
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


def load_writer():
    relative = require_exact_repo_file(WRITER, WRITER_REL, "generation evidence writer")
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_generation_reconcile_writer", WRITER)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_post_validator(path: Path, expected_relative: Path, label: str) -> None:
    require_exact_repo_file(path, expected_relative, label)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")


def main() -> int:
    enforce_runtime_authorities()
    original_text = {
        REGISTRY: read_text(REGISTRY),
        CONTRACT: read_text(CONTRACT),
        BINDING: read_text(BINDING),
        STATUS: read_text(STATUS),
    }
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    objectives_registry = load(OBJECTIVES_REGISTRY)
    drill_registry = load(DRILL_REGISTRY)
    binding = load(BINDING)
    status = load(STATUS)
    writer = load_writer()

    try:
        writer.validate_registry_for_append(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ != "Fail":
            raise
        raise Fail(f"append-only generation recovery authority invalid before reconcile: {exc}") from exc

    rows = registry.get("records")
    count = registry.get("registeredEvidenceCount")
    generation_count = gen_registry.get("registeredGenerationCount")
    objective_count = objectives_registry.get("approvedObjectiveCount")
    current_objective_id = objectives_registry.get("currentObjectiveId")
    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(rows, list) and writer.valid_count(count) and len(rows) == count, "recovery evidence registry count drift")
    require(all(writer.valid_count(value) for value in (generation_count, objective_count, drill_count, current_drill_count)), "recovery dependency counts invalid")
    require(isinstance(drill_rows, list) and drill_count == len(drill_rows), "drill request registry count drift")
    require(current_drill_count <= drill_count, "current drill request count invalid")

    for row in rows:
        writer.validate_record(row, require_current_drill_request=False)
    bound_count = len(rows)
    backup_count = sum(1 for row in rows if row.get("evidenceComplete") is True)
    restore_count = sum(
        1 for row in rows
        if row.get("evidenceComplete") is True
        and row.get("isolatedRestoreVerified") is True
        and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
    )
    candidate_count = sum(1 for row in rows if writer.candidate(row))
    require(0 <= candidate_count <= restore_count <= backup_count <= bound_count <= count, "rederived recovery evidence count ordering invalid")
    if generation_count == 0 or drill_count == 0:
        require(count == 0, "recovery evidence cannot exist without registered generations and reviewed drill request")
    if objective_count == 0:
        require(current_objective_id is None, "empty objective registry requires null currentObjectiveId")
    if objective_count == 0 or current_drill_count == 0:
        require(candidate_count == 0, "current candidate cannot survive without current objective and executable drill request")

    registry["drillRequestBoundEvidenceCount"] = bound_count
    registry["completeGenerationBoundBackupCount"] = backup_count
    registry["completeGenerationBoundRestoreCount"] = restore_count
    registry["productionEquivalentRecoveryCandidateCount"] = candidate_count
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    limitations = registry.get("limitations")
    require(isinstance(limitations, list), "recovery evidence limitations missing")
    for text in (
        "new generation evidence requires one currently executable reviewed restore drill request with matching source, target and recovery objective",
        "historical generation evidence remains auditable after its drill request becomes stale, but it immediately stops qualifying as a current recovery candidate",
    ):
        append_once(limitations, text)

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "generation recovery contract authority missing")
    boundary["registeredEvidenceCount"] = count
    boundary["drillRequestBoundEvidenceCount"] = bound_count
    boundary["completeGenerationBoundBackupCount"] = backup_count
    boundary["completeGenerationBoundRestoreCount"] = restore_count
    boundary["productionEquivalentRecoveryCandidateCount"] = candidate_count
    boundary["productionEquivalentRestoreEvidence"] = candidate_count > 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["registryDefined"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["environmentGenerationAvailable"] = generation_count > 0
    readiness["approvedRecoveryObjectivesAvailable"] = objective_count > 0
    readiness["drillRequestAvailable"] = drill_count > 0
    readiness["generationBoundBackupAvailable"] = backup_count > 0
    readiness["generationBoundRestoreAvailable"] = restore_count > 0
    readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    readiness["independentReviewCompleted"] = candidate_count > 0
    readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    readiness["productionReady"] = False

    binding_boundary = binding.get("currentBoundary")
    binding_readiness = binding.get("readiness")
    require(isinstance(binding_boundary, dict) and isinstance(binding_readiness, dict), "generation binding authority missing")
    binding_boundary["registeredProductionEquivalentGenerationCount"] = generation_count
    binding_boundary["generationBoundBackupCount"] = backup_count
    binding_boundary["generationBoundRestoreCount"] = restore_count
    binding_boundary["productionEquivalentRecoveryCandidateCount"] = candidate_count
    binding_boundary["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_boundary["independentReviewCompleted"] = candidate_count > 0
    binding_boundary["humanProductionPromotionReviewCompleted"] = False
    binding_boundary["humanProductionPromotionAuthorized"] = False
    binding_boundary["productionEvidence"] = False
    binding_boundary["productionReady"] = False
    binding_boundary["productionDecision"] = "NO_GO"
    binding_readiness["generationEvidenceRegistryImplemented"] = True
    binding_readiness["environmentGenerationAvailable"] = generation_count > 0
    binding_readiness["generationBoundBackupAvailable"] = backup_count > 0
    binding_readiness["generationBoundRestoreAvailable"] = restore_count > 0
    binding_readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    binding_readiness["independentReviewCompleted"] = candidate_count > 0
    binding_readiness["humanProductionPromotionReviewCompleted"] = False
    binding_readiness["humanProductionPromotionAuthorized"] = False
    binding_readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_readiness["productionReady"] = False
    if generation_count == 0:
        binding["limitations"] = [
            "the existing exact-source local PostgreSQL and MinIO restore proofs remain local-only",
            "no production-equivalent environment generation or generation-bound recovery evidence is currently registered",
            "recovery objectives and reviewed restore drill requests remain separately governed and cannot be invented by restore evidence",
            "candidate-level independent evidence review is not human production-promotion review",
            "a production-equivalent recovery candidate cannot complete or authorize the separate human production-promotion decision",
            "production traffic and production credentials remain unnecessary and forbidden as automatic promotion shortcuts"
        ]
    else:
        binding["limitations"] = [
            "registered environment generations and generation-bound recovery records remain non-production evidence",
            "new generation recovery evidence requires a currently executable reviewed restore drill request",
            "a production-equivalent recovery candidate also requires the current approved recovery objective ID, measured RPO/RTO/object-database skew within target and complete typed non-resurrection coverage with independent evidence review",
            "candidate-level independent evidence review does not complete human production-promotion review",
            "production promotion remains a separate human-reviewed decision and is never authorized by candidate derivation",
            "local restore foundations cannot be relabeled into generation-bound evidence"
        ]

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} and gate.get("blocking") is True, "OPS-P0-007 must remain blocking and incomplete")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    require_canonical_gaps(missing, Fail)
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(existing, (
        f"{EVIDENCE_PREFIX} registered environment generations={generation_count}, approved recovery objectives={objective_count}, reviewed/current restore drill requests={drill_count}/{current_drill_count}, recovery records={count}, drill-request-bound records={bound_count}, complete generation-bound restores={restore_count}, production-equivalent recovery candidates={candidate_count}; candidate-level independent evidence review={str(candidate_count > 0).lower()}, human production-promotion review/authorization=false/false; immutable history is preserved after request supersession but current candidate derivation is recomputed fail-closed from the current request/objective/typed-evidence state, while productionEvidence and productionReady remain false"
    ))
    for ref in REFS:
        require_repo_file(ROOT / ref, f"generation recovery evidence ref missing: {ref}")
        append_once(refs, ref)

    rendered = {
        REGISTRY: json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        CONTRACT: json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        BINDING: json.dumps(binding, indent=2, ensure_ascii=False) + "\n",
        STATUS: json.dumps(status, indent=2, ensure_ascii=False) + "\n",
    }
    try:
        for path, text in rendered.items():
            write_text(path, text)
        run_post_validator(BINDING_VALIDATOR, BINDING_VALIDATOR_REL, "generation binding validator")
        run_post_validator(VALIDATOR, VALIDATOR_REL, "generation evidence validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        for path, text in original_text.items():
            write_text(path, text)
        raise

    print("Memory OS drill-bound generation recovery authority reconciliation PASS")
    print("canonical generation evidence data/writer/validator authorities enforced: true")
    print(f"registered/current drill requests: {drill_count}/{current_drill_count}")
    print(f"registered/drill-bound recovery evidence: {count}/{bound_count}")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print(f"candidate-level independent evidence review complete: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production promotion authorized: false")
    print("candidate counters rederived from append-only records: true")
    print("corrupt append-only registry auto-healed by reconcile: false")
    print("failed post-validation leaves derived generation/status mutation behind: false")
    print("production evidence: false")
    print("OPS-P0-007: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
