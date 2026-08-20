#!/usr/bin/env python3
"""Reconcile typed non-resurrection admission without promoting production readiness."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
EVIDENCE_PREFIX = "production-equivalent non-resurrection admission overlay is typed and fail-closed:"
LOCAL_APPLE_EVIDENCE = "exact-source local Apple replay-guard logical restore proves synthetic live nonce and authorization-code replay records remain consumed after restore and the identical pair is rejected without durable replay mutation; this remains same-cluster synthetic local evidence and is not PITR or production-equivalent proof"
REFS = (
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-negative.py",
    "scripts/reconcile-memory-os-backup-non-resurrection-authority.py",
    ".github/workflows/backup-restore-non-resurrection-admission.yml",
    "contracts/operations/local-apple-replay-restore-contract.v1.json",
    "docs/fixtures/memory-os-operability/local-apple-replay-restore-results.sample.v1.json",
    "scripts/validate-memory-os-local-apple-replay-restore.py",
    ".github/workflows/local-apple-replay-restore.yml",
)

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path missing, unreadable, or escapes repository: {path}") from exc

def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative

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

def load_module(path: Path, name: str):
    relative = require_repo_file(path, f"module missing: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
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

def main() -> int:
    original_text = {
        REGISTRY: read_text(REGISTRY),
        GEN_REGISTRY: read_text(GEN_REGISTRY),
        CONTRACT: read_text(CONTRACT),
        STATUS: read_text(STATUS),
    }
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation_registry = load(GEN_REGISTRY)
    status = load(STATUS)
    typed_writer = load_module(TYPED_WRITER, "memory_os_non_resurrection_writer_reconcile")
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_recovery_writer_reconcile")

    # Reconciliation may refresh derived contract/status projections, but it
    # must never repair a corrupt append-only evidence registry. Reuse the same
    # writer admission validators before any derived field is rewritten.
    try:
        typed_writer.validate_registry_for_append(registry)
        generation_writer.validate_registry_for_append(generation_registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ != "Fail":
            raise
        raise Fail(f"append-only recovery authority invalid before reconcile: {exc}") from exc

    typed_rows = registry.get("records")
    generation_rows = generation_registry.get("records")
    require(isinstance(typed_rows, list) and all(isinstance(row, dict) for row in typed_rows), "typed registry rows invalid")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation recovery rows invalid")

    base_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.base_candidate(row)}
    declared_complete_typed_ids = {row.get("generationEvidenceId") for row in typed_rows if row.get("evidenceComplete") is True}
    validated_complete_typed_ids = {
        row.get("generationEvidenceId")
        for row in typed_rows
        if row.get("evidenceComplete") is True
        and generation_writer.typed_non_resurrection_covered(row.get("generationEvidenceId"))
    }
    require(
        declared_complete_typed_ids == validated_complete_typed_ids,
        "typed registry evidenceComplete includes record that fails canonical typed validation",
    )
    complete_typed_ids = validated_complete_typed_ids
    covered_base_ids = base_candidate_ids & complete_typed_ids
    pending_typed_ids = base_candidate_ids - complete_typed_ids
    final_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.candidate(row)}
    require(None not in base_candidate_ids and None not in final_candidate_ids, "candidate evidenceId missing")
    require(final_candidate_ids == covered_base_ids, "final candidate derivation bypasses typed non-resurrection coverage")

    registry["registeredRecordCount"] = len(typed_rows)
    registry["completeRecordCount"] = len(complete_typed_ids)
    registry["candidateCoveredCount"] = len(covered_base_ids)
    registry["productionEvidence"] = False
    registry["productionReady"] = False

    generation_registry["productionEquivalentRecoveryCandidateCount"] = len(final_candidate_ids)
    generation_registry["productionEvidence"] = False
    generation_registry["productionReady"] = False

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    boundary["registeredTypedRecordCount"] = len(typed_rows)
    boundary["completeTypedRecordCount"] = registry["completeRecordCount"]
    boundary["productionEquivalentRecoveryCandidateCount"] = len(final_candidate_ids)
    boundary["candidateCoveredCount"] = len(covered_base_ids)
    boundary["preOverlayEligiblePendingTypedCoverageCount"] = len(pending_typed_ids)
    boundary["productionEquivalentNonResurrectionEvidence"] = len(final_candidate_ids) > 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["registryDefined"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["negativeAdmissionSuiteImplemented"] = True
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["localAppleReplayRestoreProven"] = True
    readiness["localCoherentRecoverySetProven"] = True
    readiness["productionEquivalentCandidateAvailable"] = len(final_candidate_ids) > 0
    readiness["productionEquivalentCandidateTypedCoverageComplete"] = len(final_candidate_ids) > 0
    readiness["independentReviewCompleted"] = len(final_candidate_ids) > 0
    readiness["productionEquivalentNonResurrectionEvidence"] = len(final_candidate_ids) > 0
    readiness["productionReady"] = False

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 authority arrays missing")
    require_canonical_gaps(missing, Fail)
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(existing, LOCAL_APPLE_EVIDENCE)
    append_once(existing, f"{EVIDENCE_PREFIX} pre-overlay eligible generation records={len(base_candidate_ids)}, typed records={len(typed_rows)}, complete typed records={registry['completeRecordCount']}, final production-equivalent recovery candidates={len(final_candidate_ids)}, pending typed coverage={len(pending_typed_ids)}; a generic nonResurrectionVerification PASS is insufficient and final candidate derivation requires separate deleted-account/session, expired/revoked-session, Apple nonce/code replay, deletion-lease and idempotent-effect evidence with distinct security/operability review; productionEvidence and productionReady remain false")
    for ref in REFS:
        require_repo_file(ROOT / ref, f"non-resurrection authority evidence ref missing: {ref}")
        append_once(refs, ref)

    require_repo_file(VALIDATOR, "typed non-resurrection validator missing")
    require_repo_file(OPERABILITY_VALIDATOR, "operability validator missing")
    rendered = {
        REGISTRY: json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        GEN_REGISTRY: json.dumps(generation_registry, indent=2, ensure_ascii=False) + "\n",
        CONTRACT: json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        STATUS: json.dumps(status, indent=2, ensure_ascii=False) + "\n",
    }
    try:
        for path, text in rendered.items():
            write_text(path, text)
        completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0, f"typed non-resurrection validator failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")
        completed = subprocess.run([sys.executable, str(OPERABILITY_VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0, f"operability validator failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")
    except Exception:
        for path, text in original_text.items():
            write_text(path, text)
        raise

    print("Memory OS backup/restore typed non-resurrection authority reconciliation PASS")
    print(f"pre-overlay eligible generation records: {len(base_candidate_ids)}")
    print(f"final production-equivalent recovery candidates: {len(final_candidate_ids)}")
    print(f"pending typed coverage: {len(pending_typed_ids)}")
    print("corrupt append-only registry auto-healed by reconcile: false")
    print("failed post-validation leaves typed/generation/status mutation behind: false")
    print("OPS-P0-007: incomplete")
    print("production evidence: false")
    print("productionDecision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP NON-RESURRECTION AUTHORITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
