#!/usr/bin/env python3
"""Reconcile migration rehearsal evidence infrastructure into canonical operability authority."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_CONTRACT_REL = Path("contracts/operations/migration-evidence-registry-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/migration-evidence-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-migration-rehearsal-evidence.py")
REGISTRY_VALIDATOR_REL = Path("scripts/validate-memory-os-migration-evidence-registry.py")
RECOVERY_VALIDATOR_REL = Path("scripts/memory_os_migration_recovery_point.py")
ARTIFACT_CONTRACT_REL = Path("contracts/operations/local-migration-recovery-artifact-contract.v1.json")
ARTIFACT_RUNNER_REL = Path("scripts/run-memory-os-local-migration-recovery-artifact.sh")
ARTIFACT_VALIDATOR_REL = Path("scripts/validate-memory-os-local-migration-recovery-artifact.py")
ARTIFACT_EVIDENCE_ROOT_REL = Path("docs/evidence/migrations/recovery")
LOCAL_RESTORE_REL = Path("docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json")
WORKFLOW_REL = Path(".github/workflows/migration-evidence-registry.yml")
LIFECYCLE_REL = Path("contracts/operations/migration-lifecycle-contract.v1.json")
LIFECYCLE_VALIDATOR_REL = Path("scripts/validate-memory-os-migration-lifecycle.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
REGISTRY_CONTRACT = ROOT / REGISTRY_CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
REGISTRY_VALIDATOR = ROOT / REGISTRY_VALIDATOR_REL
RECOVERY_VALIDATOR = ROOT / RECOVERY_VALIDATOR_REL
ARTIFACT_CONTRACT = ROOT / ARTIFACT_CONTRACT_REL
ARTIFACT_RUNNER = ROOT / ARTIFACT_RUNNER_REL
ARTIFACT_VALIDATOR = ROOT / ARTIFACT_VALIDATOR_REL
ARTIFACT_EVIDENCE_ROOT = ROOT / ARTIFACT_EVIDENCE_ROOT_REL
LOCAL_RESTORE = ROOT / LOCAL_RESTORE_REL
WORKFLOW = ROOT / WORKFLOW_REL
LIFECYCLE = ROOT / LIFECYCLE_REL
LIFECYCLE_VALIDATOR = ROOT / LIFECYCLE_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
EXPECTED_POST_WRITE_VALIDATORS = (
    REGISTRY_VALIDATOR,
    LIFECYCLE_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
POST_WRITE_VALIDATORS = EXPECTED_POST_WRITE_VALIDATORS

FOUNDATION_EVIDENCE = (
    "append-only privacy-safe migration rehearsal evidence registry is implemented with exact source/canonical sequence binding, typed SHA-256 recovery-artifact references, a separately validated local logical-restore capability authority, and a per-run actual-artifact restore evidence requirement; arbitrary repository files or digest-only claims cannot satisfy recovery evidence and registrations remain non-production"
)
LOCAL_ARTIFACT_EVIDENCE = (
    "at least one passing local PostgreSQL migration rehearsal created the actual pre-migration logical dump artifact, recorded only its SHA-256/byte count, restored that exact artifact into a separate same-cluster database, verified the pre-migration surface, reapplied the migration, and reran the canonical SQL suite; this is local same-cluster evidence only and does not prove production-equivalent isolated restore or rollback safety"
)
LOCAL_GAP = "passing local migration rehearsal that restores the actual pre-migration artifact and reapplies the migration"
BASE_REFS = (
    "contracts/operations/migration-evidence-registry-contract.v1.json",
    "contracts/operations/migration-evidence-registry.v1.json",
    "scripts/register-memory-os-migration-rehearsal-evidence.py",
    "scripts/validate-memory-os-migration-evidence-registry.py",
    "scripts/memory_os_migration_recovery_point.py",
    "scripts/reconcile-memory-os-migration-evidence-registry.py",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    ".github/workflows/migration-evidence-registry.yml",
    "contracts/operations/local-migration-recovery-artifact-contract.v1.json",
    "scripts/run-memory-os-local-migration-recovery-artifact.sh",
    "scripts/validate-memory-os-local-migration-recovery-artifact.py",
    "scripts/reconcile-memory-os-local-migration-recovery-artifact.py",
    ".github/workflows/local-migration-recovery-artifact.yml",
    "docs/evidence/migrations/recovery/README.md",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


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


def require_exact_repo_directory(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_dir(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    require(
        POST_WRITE_VALIDATORS == EXPECTED_POST_WRITE_VALIDATORS,
        "migration evidence post-write validator chain authority drift",
    )
    for path, expected, field in (
        (REGISTRY_CONTRACT, REGISTRY_CONTRACT_REL, "migration evidence registry contract"),
        (REGISTRY, REGISTRY_REL, "migration evidence registry"),
        (WRITER, WRITER_REL, "migration rehearsal writer"),
        (REGISTRY_VALIDATOR, REGISTRY_VALIDATOR_REL, "migration evidence registry validator"),
        (RECOVERY_VALIDATOR, RECOVERY_VALIDATOR_REL, "migration recovery-point validator"),
        (ARTIFACT_CONTRACT, ARTIFACT_CONTRACT_REL, "local migration recovery artifact contract"),
        (ARTIFACT_RUNNER, ARTIFACT_RUNNER_REL, "local migration recovery artifact runner"),
        (ARTIFACT_VALIDATOR, ARTIFACT_VALIDATOR_REL, "local migration recovery artifact validator"),
        (LOCAL_RESTORE, LOCAL_RESTORE_REL, "local logical restore result"),
        (WORKFLOW, WORKFLOW_REL, "migration evidence workflow"),
        (LIFECYCLE, LIFECYCLE_REL, "migration lifecycle contract"),
        (LIFECYCLE_VALIDATOR, LIFECYCLE_VALIDATOR_REL, "migration lifecycle validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)
    require_exact_repo_directory(
        ARTIFACT_EVIDENCE_ROOT,
        ARTIFACT_EVIDENCE_ROOT_REL,
        "migration recovery evidence root",
    )


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    enforce_runtime_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_migration_rehearsal_writer_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load migration rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_replace_bytes(path: Path, payload: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_replace_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def passing(record: dict[str, Any]) -> bool:
    return all(record.get(field) == "PASS" for field in ("preflightResult", "applyResult", "verificationResult"))


def commit_outputs_transactionally(outputs: dict[Path, dict[str, Any]]) -> None:
    enforce_runtime_authorities()
    originals = {path: path.read_bytes() for path in outputs}
    try:
        for path, value in outputs.items():
            write(path, value)
        for validator in POST_WRITE_VALIDATORS:
            enforce_runtime_authorities()
            subprocess.run(["python", str(validator)], cwd=ROOT, check=True)
    except Exception as exc:
        for path, data in originals.items():
            atomic_replace_bytes(path, data)
        raise Fail(f"migration evidence reconcile validation failed; restored prior authority: {exc}") from exc


def main() -> int:
    enforce_runtime_authorities()
    registry = load(REGISTRY)
    contract = load(REGISTRY_CONTRACT)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise Fail(f"migration evidence registry invalid before reconcile: {exc}") from exc
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "registry contract authority missing")
    records = registry["records"]
    count = registry["rehearsalEvidenceCount"]
    passing_count = registry["passingRehearsalCount"]
    pe_count = registry["productionEquivalentRehearsalCount"]
    local_passing = sum(
        1 for record in records
        if isinstance(record, dict)
        and record.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL"
        and passing(record)
    )

    current["rehearsalEvidenceCount"] = count
    current["passingRehearsalCount"] = passing_count
    current["productionEquivalentRehearsalCount"] = pe_count
    current["productionMigrationEvidenceCount"] = 0
    current["productionEvidence"] = False
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    for flag in (
        "registryImplemented", "writerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "operatorEvidenceRecordImplemented",
        "typedRecoveryArtifactReferenceImplemented", "localRestoreCapabilityBound",
        "perRunRecoveryArtifactEvidenceRequired",
    ):
        readiness[flag] = True
    readiness["localActualRecoveryArtifactRestoreLinked"] = local_passing > 0
    for flag in (
        "productionEquivalentRestoreCapabilityConfigured",
        "productionEquivalentActualRecoveryArtifactRestoreLinked",
        "productionShapedRehearsalCompleted",
        "independentReviewCompleted",
        "productionReady",
    ):
        readiness[flag] = False

    lifecycle = load(LIFECYCLE)
    lifecycle_readiness = lifecycle.get("readiness")
    require(isinstance(lifecycle_readiness, dict), "migration lifecycle readiness missing")
    lifecycle_readiness["operatorEvidenceRecordImplemented"] = True
    lifecycle_readiness["productionShapedRehearsalCompleted"] = False
    lifecycle_readiness["isolatedRestoreLinked"] = False
    lifecycle_readiness["mixedVersionCompatibilityProven"] = False
    lifecycle_readiness["ready"] = False
    if local_passing > 0:
        lifecycle_readiness["note"] = (
            "The non-production migration registry now contains a passing local rehearsal that restored its actual pre-migration logical dump artifact into a separate same-cluster database and successfully reapplied the migration and SQL suite. Production-shaped rehearsal, production-equivalent isolated restore, mixed-version deployment proof and destructive-contract restore linkage remain required."
        )
    else:
        lifecycle_readiness["note"] = (
            "The non-production migration registry requires typed recovery artifacts, validated restore capability and per-run actual-artifact restore evidence. No passing local actual-artifact rehearsal is registered yet; production-shaped rehearsal, production-equivalent isolated restore, mixed-version deployment proof and destructive-contract restore linkage remain required."
        )
    evidence_refs = lifecycle.get("evidenceRefs")
    require(isinstance(evidence_refs, list), "migration lifecycle evidenceRefs missing")
    for ref in BASE_REFS:
        append_once(evidence_refs, ref)
    if local_passing > 0:
        for record in records:
            if isinstance(record, dict) and record.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL" and passing(record):
                evidence_ref = record.get("recoveryPointRestoreEvidenceRef")
                if isinstance(evidence_ref, str):
                    append_once(evidence_refs, evidence_ref)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-001"), None)
    require(isinstance(gate, dict), "OPS-P0-001 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-001 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-001 arrays missing")
    append_once(existing, FOUNDATION_EVIDENCE)
    if local_passing > 0:
        append_once(existing, LOCAL_ARTIFACT_EVIDENCE)
    for ref in BASE_REFS:
        append_once(refs, ref)
    if local_passing > 0:
        for record in records:
            if isinstance(record, dict) and record.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL" and passing(record):
                evidence_ref = record.get("recoveryPointRestoreEvidenceRef")
                if isinstance(evidence_ref, str):
                    append_once(refs, evidence_ref)

    obsolete = {
        "automated recovery-point verification and append-only operator evidence record",
        "automated recovery-point verification bound to an actual isolated recovery artifact",
        "restore of the actual migration rehearsal recovery artifact, bound to the target recovery point and independently verified; local restore capability proof alone is insufficient",
        LOCAL_GAP,
    }
    next_missing = [item for item in missing if item not in obsolete]
    if local_passing == 0:
        next_missing.append(LOCAL_GAP)
    production_gap = "production-equivalent migration recovery artifact restore bound to the actual recovery point and independently reviewed"
    if production_gap not in next_missing:
        next_missing.append(production_gap)
    gate["missingEvidence"] = next_missing
    if local_passing > 0:
        require(LOCAL_GAP not in gate["missingEvidence"],
                "satisfied local actual-artifact gap remained in missingEvidence")

    commit_outputs_transactionally({
        REGISTRY_CONTRACT: contract,
        LIFECYCLE: lifecycle,
        STATUS: status,
    })

    print("Memory OS migration evidence registry reconciliation PASS")
    print("canonical migration evidence data/executable authorities enforced: true")
    print("canonical post-write validator chain enforced: true")
    print(f"registered rehearsals: {count}")
    print(f"local passing actual-artifact rehearsals: {local_passing}")
    print("typed recovery artifact reference: implemented")
    print("local restore capability binding: implemented")
    print(f"local actual recovery artifact restore linkage: {'true' if local_passing else 'false'}")
    print("production-equivalent actual recovery artifact restore linkage: false")
    print("OPS-P0-001: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION EVIDENCE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
