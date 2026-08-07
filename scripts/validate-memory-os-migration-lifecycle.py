#!/usr/bin/env python3
"""Fail-closed validation for the Memory OS PostgreSQL migration lifecycle."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SECURITY_WORKFLOW_PATH = ROOT / ".github/workflows/security-contracts.yml"
MIGRATION_EVIDENCE_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
MIGRATION_EVIDENCE_REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
MIGRATION_EVIDENCE_WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
MIGRATION_EVIDENCE_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
MIGRATION_EVIDENCE_WORKFLOW = ROOT / ".github/workflows/migration-evidence-registry.yml"
EXPECTED_PHASES = [
    "PREFLIGHT",
    "EXPAND",
    "MIGRATE_DATA",
    "OBSERVE_MIXED_VERSION",
    "CONTRACT",
]
REQUIRED_RUNBOOK_HEADINGS = [
    "## Non-negotiable invariants",
    "## Phase 0 — Preflight",
    "## Phase 1 — EXPAND",
    "## Phase 2 — MIGRATE_DATA",
    "## Phase 3 — OBSERVE_MIXED_VERSION",
    "## Phase 4 — CONTRACT",
    "## Failure decision tree",
    "## Verification record",
    "## Current limitations",
]
REQUIRED_RUNBOOK_PHRASES = [
    "A PostgreSQL transaction rollback does **not** prove",
    "forward-fix",
    "old-version drain",
    "isolated restore",
    "FORCE RLS",
    "bounded, idempotent, resumable",
    "Production decision remains: **NO_GO**",
]
REQUIRED_STATUS_REFS = {
    ".github/workflows/security-contracts.yml",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "docs/runbooks/memory-os-migration-recovery.md",
    "scripts/validate-memory-os-migration-lifecycle.py",
}
SHA_FILE_RE = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def unique_strings(value: Any, field: str) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-migration-lifecycle.v1",
            "unsupported migration lifecycle schemaVersion")

    directory_ref = contract.get("canonicalDirectory")
    runbook_ref = contract.get("canonicalRunbook")
    validator_ref = contract.get("validator")
    require(directory_ref == "infra/postgresql/security", "canonicalDirectory drift")
    require(runbook_ref == "docs/runbooks/memory-os-migration-recovery.md",
            "canonicalRunbook drift")
    require(validator_ref == "scripts/validate-memory-os-migration-lifecycle.py",
            "validator path drift")

    contract_refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs")
    missing_contract_refs = REQUIRED_STATUS_REFS - set(contract_refs)
    require(not missing_contract_refs,
            f"migration contract omits evidence: {sorted(missing_contract_refs)}")
    for ref in contract_refs:
        require((ROOT / ref).is_file(), f"migration contract evidence path missing: {ref}")

    migration_dir = ROOT / directory_ref
    require(migration_dir.is_dir(), "canonical migration directory is missing")
    sequence = unique_strings(contract.get("migrationSequence"), "migrationSequence")
    require(all(SHA_FILE_RE.fullmatch(name) for name in sequence),
            "migrationSequence contains a non-canonical filename")
    actual = sorted(
        path.name
        for path in migration_dir.glob("*.sql")
        if path.is_file() and not path.name.startswith("test_")
    )
    require(actual == sequence,
            f"canonical migration registry mismatch: expected={sequence}, actual={actual}")

    try:
        security_workflow = SECURITY_WORKFLOW_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("Security Contracts workflow is missing") from exc
    require("image: postgres:16-alpine" in security_workflow,
            "clean migration CI must use the PostgreSQL 16 service baseline")
    positions: list[int] = []
    for migration in sequence:
        require(security_workflow.count(migration) == 1,
                f"Security Contracts must apply {migration} exactly once")
        positions.append(security_workflow.index(migration))
    require(positions == sorted(positions),
            "Security Contracts migration application order differs from the canonical registry")
    require("psql --set=ON_ERROR_STOP=1" in security_workflow,
            "clean migration CI must stop on the first SQL error")

    strategy = contract.get("strategy")
    require(isinstance(strategy, dict), "strategy must be an object")
    require(strategy.get("name") == "EXPAND_MIGRATE_CONTRACT", "strategy name drift")
    require(strategy.get("defaultRecovery") == "FORWARD_FIX",
            "default recovery must remain FORWARD_FIX")
    for required_true in (
        "mixedVersionWindowRequired",
        "oldApplicationVersionMustRemainCompatibleDuringExpand",
        "backfillsMustBeIdempotentAndResumable",
        "contractRequiresOldVersionDrain",
        "contractRequiresIndependentRecoveryPoint",
        "schemaChangeAndLargeBackfillMustBeSeparateSteps",
    ):
        require(strategy.get(required_true) is True, f"strategy.{required_true} must be true")
    require(strategy.get("productionAutoApply") is False,
            "productionAutoApply must remain false")
    require(strategy.get("destructiveChangeInSameRelease") is False,
            "destructiveChangeInSameRelease must remain false")

    phases = contract.get("phases")
    require(isinstance(phases, list), "phases must be a list")
    phase_names = [item.get("phase") for item in phases if isinstance(item, dict)]
    require(phase_names == EXPECTED_PHASES,
            f"migration phase order drift: {phase_names}")
    for item in phases:
        require(isinstance(item, dict), "phase entries must be objects")
        require(isinstance(item.get("exitCriteria"), str) and item["exitCriteria"].strip(),
                f"{item.get('phase')}: exitCriteria is required")
        for list_field in ("requiredEvidence", "allowed", "forbidden"):
            if list_field in item:
                unique_strings(item[list_field], f"{item.get('phase')}.{list_field}")

    recovery = contract.get("recoveryDecision")
    require(isinstance(recovery, dict), "recoveryDecision must be an object")
    require(recovery.get("beforeMutation") == "STOP_AND_CORRECT",
            "before-mutation recovery drift")
    require("FORWARD_FIX" in str(recovery.get("additiveMigrationCommittedApplicationUnhealthy")),
            "committed additive migration must retain forward-fix")
    require("NEVER_ASSUME_DOWN_MIGRATION_IS_SAFE" in str(recovery.get("contractMigrationCommitted")),
            "contract recovery must forbid assumed-safe down migration")

    guards = contract.get("operatorGuards")
    require(isinstance(guards, dict), "operatorGuards must be an object")
    for guard in (
        "requireExactHead",
        "requireCleanWorkingTree",
        "requireExplicitTargetDatabase",
        "requireProductionConfirmationPhrase",
        "requireSingleWriterMigrationLock",
        "requireLockTimeout",
        "requireStatementTimeout",
        "requirePostMigrationVerification",
        "forbidSuperuserRuntimeTraffic",
        "forbidSecretValuesInEvidence",
    ):
        require(guards.get(guard) is True, f"operatorGuards.{guard} must be true")

    evidence_record = contract.get("evidenceRecord")
    require(isinstance(evidence_record, dict), "evidenceRecord must be an object")
    fields = unique_strings(evidence_record.get("requiredFields"), "evidenceRecord.requiredFields")
    for field in (
        "migrationRunId",
        "databaseIdentityDigest",
        "sourceCommitSha",
        "recoveryPointReference",
        "verificationResult",
        "recoveryDecision",
        "openRisks",
    ):
        require(field in fields, f"evidenceRecord missing required field: {field}")
    require(evidence_record.get("appendOnly") is True,
            "migration evidence record must remain append-only")
    require(evidence_record.get("privacyClass") == "operational_sensitive_no_secrets",
            "migration evidence privacy class drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "policyDefined",
        "runbookDefined",
        "migrationRegistryComplete",
        "ciDryRunAgainstCleanDatabase",
        "operatorEvidenceRecordImplemented",
    ):
        require(readiness.get(foundation) is True, f"readiness.{foundation} must be true")
    for path in (
        MIGRATION_EVIDENCE_CONTRACT,
        MIGRATION_EVIDENCE_REGISTRY,
        MIGRATION_EVIDENCE_WRITER,
        MIGRATION_EVIDENCE_VALIDATOR,
        MIGRATION_EVIDENCE_WORKFLOW,
    ):
        require(path.is_file(), f"operator evidence authority missing: {path.relative_to(ROOT)}")
    evidence_authority = load(MIGRATION_EVIDENCE_CONTRACT)
    evidence_readiness = evidence_authority.get("readiness")
    require(isinstance(evidence_readiness, dict), "operator evidence readiness missing")
    for implemented in (
        "registryImplemented",
        "writerImplemented",
        "validatorImplemented",
        "automaticWorkflowImplemented",
        "operatorEvidenceRecordImplemented",
    ):
        require(evidence_readiness.get(implemented) is True,
                f"operator evidence authority incomplete: {implemented}")
    require(evidence_authority.get("currentAuthority", {}).get("productionEvidence") is False,
            "operator evidence authority cannot manufacture production evidence")
    for unproven in (
        "mixedVersionCompatibilityProven",
        "productionShapedRehearsalCompleted",
        "isolatedRestoreLinked",
        "automatedDestructiveRollback",
        "ready",
    ):
        require(readiness.get(unproven) is False,
                f"unproven migration readiness cannot be true: {unproven}")

    runbook_path = ROOT / runbook_ref
    try:
        runbook = runbook_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("canonical migration runbook is missing") from exc
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"runbook missing heading: {heading}")
    for phrase in REQUIRED_RUNBOOK_PHRASES:
        require(phrase in runbook, f"runbook missing binding phrase: {phrase}")

    status = load(STATUS_PATH)
    areas = status.get("areas")
    require(isinstance(areas, list), "operability status areas must be a list")
    matches = [area for area in areas if isinstance(area, dict) and area.get("id") == "OPS-P0-001"]
    require(len(matches) == 1, "OPS-P0-001 must exist exactly once")
    area = matches[0]
    refs = area.get("evidenceRefs")
    require(isinstance(refs, list), "OPS-P0-001 evidenceRefs must be a list")
    missing_refs = REQUIRED_STATUS_REFS - set(refs)
    require(not missing_refs,
            f"OPS-P0-001 omits migration lifecycle evidence: {sorted(missing_refs)}")
    if area.get("status") == "READY":
        for required_for_ready in (
            "ciDryRunAgainstCleanDatabase",
            "mixedVersionCompatibilityProven",
            "productionShapedRehearsalCompleted",
            "isolatedRestoreLinked",
            "operatorEvidenceRecordImplemented",
            "ready",
        ):
            require(readiness.get(required_for_ready) is True,
                    f"OPS-P0-001 READY without readiness.{required_for_ready}")
    else:
        missing_evidence = area.get("missingEvidence")
        require(isinstance(missing_evidence, list) and missing_evidence,
                "incomplete OPS-P0-001 requires missingEvidence")
        for phrase in ("production-shaped rehearsal", "mixed-version"):
            require(any(phrase in item for item in missing_evidence),
                    f"OPS-P0-001 missingEvidence must retain: {phrase}")

    require(status.get("productionDecision") == "NO_GO",
            "migration foundations cannot change productionDecision from NO_GO")

    print("Memory OS migration lifecycle validation PASS")
    print(f"canonical migrations: {len(sequence)}")
    print("clean PostgreSQL CI dry-run: configured and registry-ordered")
    print("operator evidence registry: implemented")
    print(f"OPS-P0-001 status: {area.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"MIGRATION LIFECYCLE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
