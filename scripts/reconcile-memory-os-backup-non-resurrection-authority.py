#!/usr/bin/env python3
"""Reconcile typed non-resurrection admission without promoting production readiness."""
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
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
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

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)

def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation_registry = load(GEN_REGISTRY)
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_recovery_writer_reconcile")

    typed_rows = registry.get("records")
    generation_rows = generation_registry.get("records")
    require(isinstance(typed_rows, list) and all(isinstance(row, dict) for row in typed_rows), "typed registry rows invalid")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation recovery rows invalid")

    base_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.base_candidate(row)}
    complete_typed_ids = {row.get("generationEvidenceId") for row in typed_rows if row.get("evidenceComplete") is True}
    covered_base_ids = base_candidate_ids & complete_typed_ids
    pending_typed_ids = base_candidate_ids - complete_typed_ids
    final_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.candidate(row)}
    require(None not in base_candidate_ids and None not in final_candidate_ids, "candidate evidenceId missing")
    require(final_candidate_ids == covered_base_ids, "final candidate derivation bypasses typed non-resurrection coverage")

    registry["registeredRecordCount"] = len(typed_rows)
    registry["completeRecordCount"] = sum(1 for row in typed_rows if row.get("evidenceComplete") is True)
    registry["candidateCoveredCount"] = len(covered_base_ids)
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    generation_registry["productionEquivalentRecoveryCandidateCount"] = len(final_candidate_ids)
    generation_registry["productionEvidence"] = False
    generation_registry["productionReady"] = False
    GEN_REGISTRY.write_text(json.dumps(generation_registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    boundary["registeredTypedRecordCount"] = len(typed_rows)
    boundary["completeTypedRecordCount"] = registry["completeRecordCount"]
    boundary["productionEquivalentRecoveryCandidateCount"] = len(final_candidate_ids)
    boundary["candidateCoveredCount"] = len(covered_base_ids)
    boundary["uncoveredCandidateCount"] = len(pending_typed_ids)
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
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=True)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} and gate.get("blocking") is True, "OPS-P0-007 must remain blocking and incomplete")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 authority arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(existing, LOCAL_APPLE_EVIDENCE)
    append_once(existing, f"{EVIDENCE_PREFIX} pre-overlay eligible generation records={len(base_candidate_ids)}, typed records={len(typed_rows)}, complete typed records={registry['completeRecordCount']}, final production-equivalent recovery candidates={len(final_candidate_ids)}, pending typed coverage={len(pending_typed_ids)}; a generic nonResurrectionVerification PASS is insufficient and final candidate derivation requires separate deleted-account/session, expired/revoked-session, Apple nonce/code replay, deletion-lease and idempotent-effect evidence with distinct security/operability review; productionEvidence and productionReady remain false")
    for ref in REFS:
        require((ROOT / ref).is_file(), f"non-resurrection authority evidence ref missing: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    for phrase in ("postgresql backup", "independent object", "rpo", "isolated restore", "non-resurrection", "independent review"):
        require(phrase in joined, f"production backup/restore blocker must remain: {phrase}")
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Memory OS backup/restore typed non-resurrection authority reconciliation PASS")
    print(f"pre-overlay eligible generation records: {len(base_candidate_ids)}")
    print(f"final production-equivalent recovery candidates: {len(final_candidate_ids)}")
    print(f"pending typed coverage: {len(pending_typed_ids)}")
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
