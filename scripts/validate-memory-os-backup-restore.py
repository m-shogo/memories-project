#!/usr/bin/env python3
"""Fail-closed validator for Memory OS backup and restore foundations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/backup-restore-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_DOMAINS = {
    "POSTGRESQL_CANONICAL_STATE",
    "OBJECT_VERSIONS",
    "MIGRATION_AND_RELEASE_METADATA",
    "INCIDENT_AND_DELETION_EVIDENCE",
}
EXPECTED_LIFECYCLE = [
    "DECLARE_AND_PLAN",
    "SELECT_RECOVERY_POINT",
    "RESTORE_ISOLATED",
    "VERIFY_STRUCTURE_AND_AUTHORITY",
    "VERIFY_DATA_AND_IDEMPOTENCY",
    "VERIFY_NON_RESURRECTION",
    "MEASURE_RECOVERY_OBJECTIVES",
    "PROMOTION_DECISION",
    "CLOSE_AND_REMEDIATE",
]
EXPECTED_DRILLS = {
    "RESTORE-DRILL-001",
    "RESTORE-DRILL-002",
    "RESTORE-DRILL-003",
    "RESTORE-DRILL-004",
    "RESTORE-DRILL-005",
}
REQUIRED_STATUS_REFS = {
    "contracts/operations/backup-restore-contract.v1.json",
    "docs/runbooks/memory-os-backup-restore.md",
    "scripts/validate-memory-os-backup-restore.py",
}
REQUIRED_RUNBOOK_HEADINGS = [
    "## Current state",
    "## Non-negotiable rules",
    "## Required inputs",
    "## Phase 1 — Declare and plan",
    "## Phase 2 — Select a coherent recovery point",
    "## Phase 3 — Restore in isolation",
    "## Phase 4 — Verify structure and authority",
    "## Phase 5 — Verify data and idempotency",
    "## Phase 6 — Verify deletion and session non-resurrection",
    "## Phase 7 — Measure RPO and RTO",
    "## Phase 8 — Promotion decision",
    "## Required drill matrix",
    "## Backup operation requirements",
    "## Current limitations",
]
REQUIRED_RUNBOOK_PHRASES = [
    "Production decision remains: **NO_GO**",
    "object versioning ≠ independent backup",
    "healthy restored service ≠ safe promotion",
    "Do not substitute latest",
    "A privileged administrative query is not an RLS test",
    "Any resurrection is SEV0",
    "A green `/healthz` is not promotion evidence",
    "None of these drills is currently completed",
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


def unique_strings(value: Any, field: str, *, minimum: int = 1) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} must contain at least {minimum} item(s)")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def object_map(value: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{field} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        require(isinstance(item, dict), f"{field} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier,
                f"{field}.{key} is required")
        require(identifier not in result, f"duplicate {field} identifier: {identifier}")
        result[identifier] = item
    return result


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-backup-restore.v1",
            "unsupported backup/restore schemaVersion")
    require(contract.get("canonicalRunbook") == "docs/runbooks/memory-os-backup-restore.md",
            "canonicalRunbook drift")
    require(contract.get("validator") == "scripts/validate-memory-os-backup-restore.py",
            "validator path drift")
    require(contract.get("productionDecision") == "NO_GO",
            "backup foundations cannot change productionDecision")

    principles = unique_strings(contract.get("principles"), "principles", minimum=8)
    for phrase in (
        "backup creation",
        "object versioning",
        "recovery point",
        "isolated environment",
        "deleted accounts",
        "FORCE RLS",
        "database and object",
        "independently owned",
        "promotion",
    ):
        require(any(phrase in item for item in principles),
                f"backup principles omit: {phrase}")

    objectives = contract.get("recoveryObjectives")
    require(isinstance(objectives, dict), "recoveryObjectives must be an object")
    for objective in ("rpo", "rto", "maximumAcceptableObjectDatabaseSkew"):
        item = objectives.get(objective)
        require(isinstance(item, dict), f"recoveryObjectives.{objective} must be an object")
        require(item.get("status") == "NOT_DEFINED",
                f"{objective} must remain NOT_DEFINED until approved")
        require(item.get("approvedValue") is None,
                f"{objective} cannot have an unapproved value")
        require(item.get("owner") == "UNASSIGNED",
                f"{objective} owner is not assigned")
    require(objectives["rpo"].get("measurementMethod") is None,
            "RPO measurement method is not approved")
    require(objectives["rto"].get("measurementMethod") is None,
            "RTO measurement method is not approved")

    domains = object_map(contract.get("protectedDomains"), "id", "protectedDomains")
    require(set(domains) == EXPECTED_DOMAINS,
            f"protected domain set drift: {sorted(domains)}")
    for domain_id, item in domains.items():
        unique_strings(item.get("includes"), f"protectedDomains.{domain_id}.includes")
        require(isinstance(item.get("requiredMechanism"), str)
                and item["requiredMechanism"],
                f"{domain_id}: requiredMechanism is required")
        require(item.get("configured") is False,
                f"{domain_id}: production protection is not configured")
        require(item.get("independentRetention") is False,
                f"{domain_id}: independent retention is not proven")
        require(item.get("restoreTested") is False,
                f"{domain_id}: restore is not tested")
    require(domains["OBJECT_VERSIONS"].get("localVersioningEvidence") is True,
            "local object versioning evidence must remain recorded")

    controls = contract.get("backupControls")
    require(isinstance(controls, dict), "backupControls must be an object")
    for required_true in (
        "encryptionAtRestRequired",
        "encryptionInTransitRequired",
        "backupCredentialsSeparateFromRuntimeRequired",
        "leastPrivilegeRequired",
        "crossEnvironmentRestoreAuthoritySeparated",
        "retentionAndExpiryPolicyRequired",
        "immutabilityOrDeletionProtectionRequired",
        "backupJobMonitoringRequired",
        "backupFreshnessAlertRequired",
        "periodicRestoreRequired",
        "secretValuesInEvidenceForbidden",
    ):
        require(controls.get(required_true) is True,
                f"backupControls.{required_true} must be true")
    require(controls.get("productionConfigurationComplete") is False,
            "production backup configuration is not complete")

    lifecycle_list = contract.get("restoreLifecycle")
    require(isinstance(lifecycle_list, list), "restoreLifecycle must be a list")
    lifecycle_names = [item.get("phase") for item in lifecycle_list if isinstance(item, dict)]
    require(lifecycle_names == EXPECTED_LIFECYCLE,
            f"restore lifecycle order drift: {lifecycle_names}")
    lifecycle = object_map(lifecycle_list, "phase", "restoreLifecycle")
    for phase, item in lifecycle.items():
        unique_strings(item.get("requiredActions"),
                       f"restoreLifecycle.{phase}.requiredActions", minimum=3)
        require(isinstance(item.get("exitCriteria"), str) and item["exitCriteria"],
                f"restoreLifecycle.{phase}.exitCriteria is required")

    verification = contract.get("mandatoryVerification")
    require(isinstance(verification, dict), "mandatoryVerification must be an object")
    require(set(verification) == {
        "schemaAndMigration",
        "tenantAndAuthority",
        "previewApply",
        "sessionsAndReplay",
        "deletion",
        "objectsAndParser",
    }, "mandatoryVerification section set drift")
    for section, checks in verification.items():
        unique_strings(checks, f"mandatoryVerification.{section}", minimum=3)

    guards = unique_strings(contract.get("promotionGuards"), "promotionGuards", minimum=8)
    for phrase in (
        "cross-tenant",
        "deleted data",
        "database and object",
        "object version or parser artifact",
        "migration sequence",
        "RPO or RTO",
        "production credentials",
        "approval is missing",
        "FAIL, PARTIAL or NOT_RUN",
    ):
        require(any(phrase in item for item in guards),
                f"promotionGuards omit: {phrase}")

    evidence = contract.get("evidenceRecord")
    require(isinstance(evidence, dict), "evidenceRecord must be an object")
    require(evidence.get("appendOnly") is True,
            "restore evidence must remain append-only")
    require(evidence.get("privacyClass") == "operational_sensitive_no_secrets",
            "restore evidence privacy class drift")
    evidence_fields = set(unique_strings(evidence.get("requiredFields"),
                                         "evidenceRecord.requiredFields"))
    for required_field in (
        "restoreRunId",
        "databaseRecoveryPoint",
        "objectRecoveryPoint",
        "measuredRpo",
        "measuredRto",
        "verificationResults",
        "nonResurrectionResults",
        "promotionDecision",
        "openRisks",
    ):
        require(required_field in evidence_fields,
                f"restore evidence omits: {required_field}")

    drills = object_map(contract.get("requiredDrills"), "id", "requiredDrills")
    require(set(drills) == EXPECTED_DRILLS,
            f"restore drill set drift: {sorted(drills)}")
    for drill_id, item in drills.items():
        require(isinstance(item.get("scenario"), str) and item["scenario"],
                f"{drill_id}: scenario is required")
        require(item.get("completed") is False,
                f"{drill_id}: no restore drill is currently completed")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "policyDefined",
        "protectedDomainsDefined",
        "restoreLifecycleDefined",
        "mandatoryVerificationDefined",
        "promotionGuardsDefined",
        "evidenceRecordDefined",
        "runbookDefined",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "rpoDefined",
        "rtoDefined",
        "postgresBackupConfigured",
        "postgresPitrConfigured",
        "objectIndependentRetentionConfigured",
        "backupMonitoringConfigured",
        "isolatedRestoreEnvironmentImplemented",
        "nonResurrectionAutomationImplemented",
        "restoreDrillCompleted",
        "productionPromotionRehearsed",
        "independentReviewCompleted",
        "ready",
    ):
        require(readiness.get(unproven) is False,
                f"unproven backup readiness cannot be true: {unproven}")

    refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs")
    require(set(refs) == REQUIRED_STATUS_REFS,
            f"backup evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"backup evidence path missing: {ref}")

    runbook_path = ROOT / contract["canonicalRunbook"]
    try:
        runbook = runbook_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("canonical backup/restore runbook is missing") from exc
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"backup runbook missing heading: {heading}")
    for phrase in REQUIRED_RUNBOOK_PHRASES:
        require(phrase in runbook, f"backup runbook missing binding phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "backup foundations cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    area = matches[0]
    require(area.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL", "READY"},
            "OPS-P0-007 status is incompatible with backup foundations")
    status_refs = area.get("evidenceRefs")
    require(isinstance(status_refs, list), "OPS-P0-007 evidenceRefs must be a list")
    missing_refs = REQUIRED_STATUS_REFS - set(status_refs)
    require(not missing_refs,
            f"OPS-P0-007 omits backup evidence: {sorted(missing_refs)}")

    if area.get("status") == "READY":
        for requirement in (
            "rpoDefined",
            "rtoDefined",
            "postgresBackupConfigured",
            "postgresPitrConfigured",
            "objectIndependentRetentionConfigured",
            "backupMonitoringConfigured",
            "isolatedRestoreEnvironmentImplemented",
            "nonResurrectionAutomationImplemented",
            "restoreDrillCompleted",
            "productionPromotionRehearsed",
            "independentReviewCompleted",
            "ready",
        ):
            require(readiness.get(requirement) is True,
                    f"OPS-P0-007 READY without readiness.{requirement}")
    else:
        missing = area.get("missingEvidence")
        require(isinstance(missing, list) and missing,
                "incomplete OPS-P0-007 requires missingEvidence")
        for required_gap in (
            "PostgreSQL backup and PITR",
            "independent object",
            "RPO and RTO",
            "isolated restore",
            "non-resurrection",
            "restore drill",
            "backup monitoring",
            "independent review",
        ):
            require(any(required_gap in item for item in missing),
                    f"OPS-P0-007 missingEvidence must retain: {required_gap}")

    print("Memory OS backup/restore validation PASS")
    print(f"protected domains: {len(domains)}")
    print(f"required restore drills: {len(drills)}")
    print(f"OPS-P0-007 status: {area.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"BACKUP RESTORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
