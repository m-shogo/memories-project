#!/usr/bin/env python3
"""Fail-closed validator for Memory OS migration lifecycle policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
MIGRATION_DIR = ROOT / "infra/postgresql/security"
EVIDENCE_REGISTRY_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
EVIDENCE_REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
EVIDENCE_WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
EVIDENCE_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
EVIDENCE_WORKFLOW = ROOT / ".github/workflows/migration-evidence-registry.yml"
EXPECTED_SEQUENCE = [
    "001_memory_os_import_rls.sql",
    "002_memory_os_account_control.sql",
    "002_memory_os_upload_authorization.sql",
    "003_memory_os_preview_domain.sql",
    "004_memory_os_account_session.sql",
    "005_memory_os_apply_memory.sql",
    "006_memory_os_deletion_fencing.sql",
    "007_memory_os_app_login.sql",
    "008_memory_os_deletion_runtime.sql",
    "009_memory_os_deletion_visibility.sql",
    "010_memory_os_apple_identity.sql",
]
REQUIRED_STATUS_REFS = {
    ".github/workflows/security-contracts.yml",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "docs/runbooks/memory-os-migration-recovery.md",
    "scripts/validate-memory-os-migration-lifecycle.py",
}
REQUIRED_RUNBOOK_HEADINGS = [
    "## Non-negotiable rules",
    "## Before any migration",
    "## Expand",
    "## Migrate data",
    "## Observe mixed versions",
    "## Contract",
    "## Failure and recovery decisions",
    "## Evidence record",
    "## Current limitations",
]
REQUIRED_RUNBOOK_PHRASES = [
    "Production decision remains: **NO_GO**",
    "A transaction rollback is not evidence that a migration rollback strategy is complete",
    "Forward-fix is the default after a committed additive schema change",
    "Never assume a down migration is safe after a destructive contract migration",
]


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
    require(isinstance(value, list) and value, f"{field} must be a non-empty list")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-migration-lifecycle.v1",
            "unsupported migration lifecycle schemaVersion")
    require(contract.get("canonicalDirectory") == "infra/postgresql/security",
            "canonical migration directory drift")
    runbook_ref = contract.get("canonicalRunbook")
    require(runbook_ref == "docs/runbooks/memory-os-migration-recovery.md",
            "canonical runbook drift")
    require(contract.get("validator") == "scripts/validate-memory-os-migration-lifecycle.py",
            "validator path drift")

    sequence = unique_strings(contract.get("migrationSequence"), "migrationSequence")
    require(sequence == EXPECTED_SEQUENCE,
            f"canonical migration sequence drift: {sequence}")
    for filename in sequence:
        require((MIGRATION_DIR / filename).is_file(), f"missing canonical migration: {filename}")

    strategy = contract.get("strategy")
    require(isinstance(strategy, dict), "strategy must be an object")
    require(strategy.get("name") == "EXPAND_MIGRATE_CONTRACT", "migration strategy drift")
    require(strategy.get("defaultRecovery") == "FORWARD_FIX", "default recovery must remain FORWARD_FIX")
    for key in (
        "productionAutoApply", "destructiveChangeInSameRelease",
    ):
        require(strategy.get(key) is False, f"strategy.{key} must remain false")
    for key in (
        "mixedVersionWindowRequired", "oldApplicationVersionMustRemainCompatibleDuringExpand",
        "backfillsMustBeIdempotentAndResumable", "contractRequiresOldVersionDrain",
        "contractRequiresIndependentRecoveryPoint", "schemaChangeAndLargeBackfillMustBeSeparateSteps",
    ):
        require(strategy.get(key) is True, f"strategy.{key} must remain true")

    phases = contract.get("phases")
    require(isinstance(phases, list) and [item.get("phase") for item in phases if isinstance(item, dict)] ==
            ["PREFLIGHT", "EXPAND", "MIGRATE_DATA", "OBSERVE_MIXED_VERSION", "CONTRACT"],
            "migration lifecycle phases drift")
    for item in phases:
        require(isinstance(item, dict), "phase entries must be objects")
        require(isinstance(item.get("exitCriteria"), str) and item["exitCriteria"],
                f"{item.get('phase')}.exitCriteria required")
        for list_field in ("requiredEvidence", "allowed", "forbidden"):
            if list_field in item:
                unique_strings(item[list_field], f"{item.get('phase')}.{list_field}")

    recovery = contract.get("recoveryDecision")
    require(isinstance(recovery, dict), "recoveryDecision must be an object")
    require(recovery.get("beforeMutation") == "STOP_AND_CORRECT", "before-mutation recovery drift")
    require("FORWARD_FIX" in str(recovery.get("additiveMigrationCommittedApplicationUnhealthy")),
            "committed additive migration must retain forward-fix")
    require("NEVER_ASSUME_DOWN_MIGRATION_IS_SAFE" in str(recovery.get("contractMigrationCommitted")),
            "contract recovery must forbid assumed-safe down migration")

    guards = contract.get("operatorGuards")
    require(isinstance(guards, dict), "operatorGuards must be an object")
    for guard in (
        "requireExactHead", "requireCleanWorkingTree", "requireExplicitTargetDatabase",
        "requireProductionConfirmationPhrase", "requireSingleWriterMigrationLock",
        "requireLockTimeout", "requireStatementTimeout", "requirePostMigrationVerification",
        "forbidSuperuserRuntimeTraffic", "forbidSecretValuesInEvidence",
    ):
        require(guards.get(guard) is True, f"operatorGuards.{guard} must be true")

    evidence_record = contract.get("evidenceRecord")
    require(isinstance(evidence_record, dict), "evidenceRecord must be an object")
    fields = unique_strings(evidence_record.get("requiredFields"), "evidenceRecord.requiredFields")
    for field in (
        "migrationRunId", "databaseIdentityDigest", "sourceCommitSha",
        "recoveryPointReference", "verificationResult", "recoveryDecision", "openRisks",
    ):
        require(field in fields, f"evidenceRecord missing required field: {field}")
    require(evidence_record.get("appendOnly") is True, "migration evidence record must remain append-only")
    require(evidence_record.get("privacyClass") == "operational_sensitive_no_secrets",
            "migration evidence privacy class drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "policyDefined", "runbookDefined", "migrationRegistryComplete",
        "ciDryRunAgainstCleanDatabase", "operatorEvidenceRecordImplemented",
    ):
        require(readiness.get(foundation) is True, f"readiness.{foundation} must be true")
    for path in (EVIDENCE_REGISTRY_CONTRACT, EVIDENCE_REGISTRY, EVIDENCE_WRITER, EVIDENCE_VALIDATOR, EVIDENCE_WORKFLOW):
        require(path.is_file(), f"operator evidence authority missing: {path.relative_to(ROOT)}")
    evidence_authority = load(EVIDENCE_REGISTRY_CONTRACT)
    evidence_readiness = evidence_authority.get("readiness")
    require(isinstance(evidence_readiness, dict) and
            evidence_readiness.get("registryImplemented") is True and
            evidence_readiness.get("writerImplemented") is True and
            evidence_readiness.get("validatorImplemented") is True and
            evidence_readiness.get("automaticWorkflowImplemented") is True and
            evidence_readiness.get("operatorEvidenceRecordImplemented") is True,
            "operator evidence authority is not fully implemented")
    require(evidence_authority.get("currentAuthority", {}).get("productionEvidence") is False,
            "operator evidence authority cannot create production evidence")
    for unproven in (
        "mixedVersionCompatibilityProven", "productionShapedRehearsalCompleted",
        "isolatedRestoreLinked", "automatedDestructiveRollback", "ready",
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
            "ciDryRunAgainstCleanDatabase", "mixedVersionCompatibilityProven",
            "productionShapedRehearsalCompleted", "isolatedRestoreLinked",
            "operatorEvidenceRecordImplemented", "ready",
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
