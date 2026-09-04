#!/usr/bin/env python3
"""Reconcile typed non-resurrection admission without promoting production readiness."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
TYPED_WRITER_REL = Path("scripts/register-memory-os-backup-restore-non-resurrection-evidence.py")
GEN_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-non-resurrection-admission.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
TYPED_WRITER = ROOT / TYPED_WRITER_REL
GEN_WRITER = ROOT / GEN_WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
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
        (CONTRACT, CONTRACT_REL, "typed non-resurrection contract"),
        (REGISTRY, REGISTRY_REL, "typed non-resurrection registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "generation evidence registry"),
        (TYPED_WRITER, TYPED_WRITER_REL, "typed non-resurrection writer"),
        (GEN_WRITER, GEN_WRITER_REL, "generation evidence writer"),
        (VALIDATOR, VALIDATOR_REL, "typed non-resurrection validator"),
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
    require(path.parent.is_dir(), f"authority parent missing: {relative.parent}")
    temp_name: str | None = None
    mode = path.stat().st_mode & 0o777 if path.exists() else None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise Fail(f"cannot atomically write {relative}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass

def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value

def load_module(path: Path, name: str):
    if path == TYPED_WRITER:
        relative = require_exact_repo_file(path, TYPED_WRITER_REL, "typed non-resurrection writer")
    elif path == GEN_WRITER:
        relative = require_exact_repo_file(path, GEN_WRITER_REL, "generation evidence writer")
    else:
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

def replace_single_prefixed(values: list[Any], prefix: str, value: str) -> None:
    matches = [index for index, item in enumerate(values) if isinstance(item, str) and item.startswith(prefix)]
    require(len(matches) <= 1, f"duplicate authority evidence prefix: {prefix}")
    if matches:
        values[matches[0]] = value
    else:
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
    require(declared_complete_typed_ids == validated_complete_typed_ids, "typed registry evidenceComplete includes record that fails canonical typed validation")
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
    append_once(existing, LOCAL_APPLE_EVIDENCE)
    overlay_evidence = f"{EVIDENCE_PREFIX} pre-overlay eligible generation records={len(base_candidate_ids)}, typed records={len(typed_rows)}, complete typed records={registry['completeRecordCount']}, final production-equivalent recovery candidates={len(final_candidate_ids)}, pending typed coverage={len(pending_typed_ids)}; a generic nonResurrectionVerification PASS is insufficient and final candidate derivation requires separate deleted-account/session, expired/revoked-session, Apple nonce/code replay, deletion-lease and idempotent-effect evidence with distinct security/operability review; productionEvidence and productionReady remain false"
    replace_single_prefixed(existing, EVIDENCE_PREFIX, overlay_evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"non-resurrection authority evidence ref missing: {ref}")
        append_once(refs, ref)

    rendered = {
        REGISTRY: json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        GEN_REGISTRY: json.dumps(generation_registry, indent=2, ensure_ascii=False) + "\n",
        CONTRACT: json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        STATUS: json.dumps(status, indent=2, ensure_ascii=False) + "\n",
    }
    try:
        for path, text in rendered.items():
            write_text(path, text)
        run_post_validator(VALIDATOR, VALIDATOR_REL, "typed non-resurrection validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        for path, text in original_text.items():
            write_text(path, text)
        raise

    print("Memory OS backup/restore typed non-resurrection authority reconciliation PASS")
    print("canonical typed/generation data, writer and validator authorities enforced: true")
    print(f"pre-overlay eligible generation records: {len(base_candidate_ids)}")
    print(f"final production-equivalent recovery candidates: {len(final_candidate_ids)}")
    print(f"pending typed coverage: {len(pending_typed_ids)}")
    print("corrupt append-only registry auto-healed by reconcile: false")
    print("typed/generation/contract/status writes use atomic same-directory replace: true")
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
