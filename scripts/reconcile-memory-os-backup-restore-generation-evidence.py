#!/usr/bin/env python3
"""Reconcile generation-bound backup/restore evidence without promoting production readiness."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
BINDING = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"
BINDING_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    ".github/workflows/backup-restore-generation-evidence.yml",
)
EVIDENCE_PREFIX = "generation-bound backup/restore evidence admission is append-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    objectives_registry = load(OBJECTIVES_REGISTRY)
    binding = load(BINDING)
    rows = registry.get("records")
    count = registry.get("registeredEvidenceCount")
    backup_count = registry.get("completeGenerationBoundBackupCount")
    restore_count = registry.get("completeGenerationBoundRestoreCount")
    candidate_count = registry.get("productionEquivalentRecoveryCandidateCount")
    generation_count = gen_registry.get("registeredGenerationCount")
    objective_count = objectives_registry.get("approvedObjectiveCount")
    current_objective_id = objectives_registry.get("currentObjectiveId")
    require(isinstance(rows, list) and isinstance(count, int) and len(rows) == count, "recovery evidence registry count drift")
    require(all(isinstance(value, int) for value in (backup_count, restore_count, candidate_count, generation_count, objective_count)), "recovery/generation/objective counts invalid")
    require(0 <= candidate_count <= restore_count <= backup_count <= count, "recovery evidence count ordering invalid")
    if generation_count == 0:
        require(count == 0, "recovery evidence cannot exist without registered environment generations")
    if objective_count == 0:
        require(current_objective_id is None, "empty objective registry requires null currentObjectiveId")
        require(candidate_count == 0, "recovery candidate cannot exist without approved recovery objectives")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "generation recovery contract authority missing")
    boundary["registeredEvidenceCount"] = count
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
    readiness["generationBoundBackupAvailable"] = backup_count > 0
    readiness["generationBoundRestoreAvailable"] = restore_count > 0
    readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    readiness["independentReviewCompleted"] = candidate_count > 0
    readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    readiness["productionReady"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    binding_boundary = binding.get("currentBoundary")
    binding_readiness = binding.get("readiness")
    require(isinstance(binding_boundary, dict) and isinstance(binding_readiness, dict), "generation binding authority missing")
    binding_boundary["registeredProductionEquivalentGenerationCount"] = generation_count
    binding_boundary["generationBoundBackupCount"] = backup_count
    binding_boundary["generationBoundRestoreCount"] = restore_count
    binding_boundary["productionEquivalentRecoveryCandidateCount"] = candidate_count
    binding_boundary["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_boundary["productionEvidence"] = False
    binding_boundary["productionReady"] = False
    binding_boundary["productionDecision"] = "NO_GO"
    binding_readiness["generationEvidenceRegistryImplemented"] = True
    binding_readiness["environmentGenerationAvailable"] = generation_count > 0
    binding_readiness["generationBoundBackupAvailable"] = backup_count > 0
    binding_readiness["generationBoundRestoreAvailable"] = restore_count > 0
    binding_readiness["productionEquivalentRecoveryCandidateAvailable"] = candidate_count > 0
    binding_readiness["independentReviewCompleted"] = candidate_count > 0
    binding_readiness["productionEquivalentRestoreEvidence"] = candidate_count > 0
    binding_readiness["productionReady"] = False
    if generation_count == 0:
        binding["limitations"] = [
            "the existing exact-source local PostgreSQL and MinIO restore proofs remain local-only",
            "no production-equivalent environment generation or generation-bound recovery evidence is currently registered",
            "recovery objectives remain separately governed and cannot be invented by restore evidence",
            "production traffic and production credentials remain unnecessary and forbidden as automatic promotion shortcuts"
        ]
    else:
        binding["limitations"] = [
            "registered environment generations and generation-bound recovery records remain non-production evidence",
            "a production-equivalent recovery candidate also requires the current approved recovery objective ID and measured RPO/RTO/object-database skew within target",
            "production promotion remains a separate human-reviewed decision",
            "local restore foundations cannot be relabeled into generation-bound evidence"
        ]
    BINDING.write_text(json.dumps(binding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    subprocess.run(["python", str(BINDING_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} and gate.get("blocking") is True, "OPS-P0-007 must remain blocking and incomplete")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(existing, (
        f"{EVIDENCE_PREFIX} registered environment generations={generation_count}, approved recovery objectives={objective_count}, current objectiveId={current_objective_id or 'none'}, recovery records={count}, complete generation-bound restores={restore_count}, production-equivalent recovery candidates={candidate_count}; candidate admission requires exact generation/manifest/artifact hashes, current objective binding, measured RPO/RTO/object-database skew within approved targets, isolated restore, PITR, independent object retention, recovery coherence, non-resurrection and distinct security/operability review, while productionEvidence and productionReady remain false"
    ))
    for ref in REFS:
        require((ROOT / ref).is_file(), f"generation recovery evidence ref missing: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    for phrase in ("postgresql backup and pitr", "independent object", "rpo and rto", "isolated restore", "non-resurrection", "independent review"):
        require(phrase in joined, f"production backup/restore blocker must remain: {phrase}")
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Memory OS generation-bound backup/restore authority reconciliation PASS")
    print(f"registered environment generations: {generation_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"registered recovery evidence: {count}")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print("production evidence: false")
    print("OPS-P0-007: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
