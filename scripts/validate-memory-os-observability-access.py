#!/usr/bin/env python3
"""Fail-closed validation for observability retention and access policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = ROOT / "contracts/operations/observability-event-contract.v1.json"
ACCESS_PATH = ROOT / "contracts/operations/observability-retention-access-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_ROLES = {
    "on_call_observer",
    "incident_commander",
    "security_reviewer",
    "observability_platform_admin",
}
EXPECTED_TIERS = {
    "hot-searchable": 14,
    "warm-operational": 90,
    "reviewed-incident-snapshot": 365,
}
EXPECTED_EVIDENCE = {
    "contracts/operations/observability-retention-access-contract.v1.json",
    "docs/runbooks/memory-os-observability-access.md",
    "scripts/validate-memory-os-observability-access.py",
}
REQUIRED_RUNBOOK_HEADINGS = (
    "## Non-negotiable rules",
    "## Standard access request",
    "## Role boundaries",
    "## Break-glass procedure",
    "## Incident evidence export",
    "## Retention operation",
    "## Retention expiry verification",
    "## Sink health response",
    "## Access review",
    "## Closure requirements",
    "## Current limitations",
)


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


def unique_objects(items: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(items, list) and items, f"{field} must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        require(isinstance(item, dict), f"{field} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier,
                f"{field}.{key} is required")
        require(identifier not in result, f"duplicate {field} identifier: {identifier}")
        result[identifier] = item
    return result


def nonempty_unique_strings(value: Any, field: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be a non-empty list")
    require(all(isinstance(item, str) and item for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def main() -> int:
    event = load(EVENT_PATH)
    access = load(ACCESS_PATH)
    require(access.get("schemaVersion") ==
            "memory-os-observability-retention-access.v1",
            "access policy schemaVersion drift")
    require(access.get("sourceEventContract") ==
            "contracts/operations/observability-event-contract.v1.json",
            "source event contract drift")
    require(access.get("canonicalRunbook") ==
            "docs/runbooks/memory-os-observability-access.md",
            "canonical runbook path drift")
    require(access.get("status") == "POLICY_DEFINED_NOT_CONFIGURED",
            "access policy status must remain honest")

    forbidden_event_fields = set(event.get("forbiddenFieldNames", []))
    for required in (
        "message", "error", "body", "payload", "token", "authorization",
        "clientSecret", "privateKey", "password", "email", "appleSubject",
        "accountId", "url", "path", "sql", "content",
    ):
        require(required in forbidden_event_fields,
                f"event contract no longer forbids sensitive field: {required}")

    classification = access.get("classification")
    require(isinstance(classification, dict), "classification must be an object")
    require(classification.get("default") ==
            "operational_sensitive_no_user_content",
            "default log classification drift")
    for flag in (
        "personalDataForbidden",
        "secretValuesForbidden",
        "rawRequestOrResponseBodiesForbidden",
        "rawErrorsOrStackTracesForbidden",
        "databaseQueriesOrParametersForbidden",
        "presignedUrlsAndObjectKeysForbidden",
        "accountAndAppleIdentityForbidden",
    ):
        require(classification.get(flag) is True,
                f"classification.{flag} must be true")

    retention = access.get("retention")
    require(isinstance(retention, dict), "retention must be an object")
    require(retention.get("timezone") == "UTC", "retention timezone drift")
    tiers = unique_objects(retention.get("tiers"), "id", "retention tiers")
    require(set(tiers) == set(EXPECTED_TIERS),
            f"retention tier drift: {sorted(tiers)}")
    previous = 0
    for tier_id in ("hot-searchable", "warm-operational", "reviewed-incident-snapshot"):
        tier = tiers[tier_id]
        days = EXPECTED_TIERS[tier_id]
        require(tier.get("retentionDays") == days,
                f"{tier_id}: retention day drift")
        require(tier.get("required") is True,
                f"{tier_id}: must remain required")
        require(days > previous, "longer-lived tier ordering is invalid")
        previous = days
    for flag in (
        "automaticExpiryRequired",
        "expiryFailureAlertRequired",
        "retentionDeletionVerificationRequired",
        "silentRetentionExtensionForbidden",
        "silentRetentionReductionForbidden",
        "legalHoldRequiresDocumentedScopeAndExpiry",
    ):
        require(retention.get(flag) is True, f"retention.{flag} must be true")
    require(retention.get("backendConfigured") is False,
            "production log backend is not configured")
    require(retention.get("expiryVerified") is False,
            "retention expiry is not verified")

    roles = unique_objects(access.get("accessRoles"), "id", "access roles")
    require(set(roles) == EXPECTED_ROLES, f"access role drift: {sorted(roles)}")
    for role_id, role in roles.items():
        permissions = nonempty_unique_strings(role.get("permissions"),
                                              f"accessRoles.{role_id}.permissions")
        forbidden = nonempty_unique_strings(role.get("forbidden"),
                                            f"accessRoles.{role_id}.forbidden")
        require(set(permissions).isdisjoint(forbidden),
                f"{role_id}: a permission is also forbidden")
    require(any("bulk export" in item for item in roles["on_call_observer"]["forbidden"]),
            "on-call observer must not bulk export")
    require(any("own break-glass" in item for item in roles["security_reviewer"]["forbidden"]),
            "security reviewer must not self-approve break-glass")
    require(any("routine event-content access" in item
                for item in roles["observability_platform_admin"]["forbidden"]),
            "platform admin must not have routine content access")

    controls = access.get("accessControls")
    require(isinstance(controls, dict), "accessControls must be an object")
    for flag in (
        "leastPrivilegeRequired",
        "individualIdentityRequired",
        "sharedAccountsForbidden",
        "multiFactorAuthenticationRequired",
        "productionAndNonProductionSeparated",
        "accessAuditAppendOnlyRequired",
    ):
        require(controls.get(flag) is True, f"accessControls.{flag} must be true")
    require(controls.get("accessReviewIntervalDays") == 90,
            "access review interval drift")
    require(controls.get("inactiveAccessRevocationDays") == 30,
            "inactive access revocation drift")
    require(controls.get("accessAuditRetentionDays") == 365,
            "access audit retention drift")
    require(controls.get("groupAssignmentConfigured") is False,
            "production identity groups are not configured")
    require(controls.get("periodicReviewCompleted") is False,
            "periodic access review is not completed")

    break_glass = access.get("breakGlass")
    require(isinstance(break_glass, dict), "breakGlass must be an object")
    for flag in (
        "defaultDenied",
        "incidentReferenceRequired",
        "independentApproverRequired",
        "automaticExpiryRequired",
        "reasonAndScopeRequired",
        "allQueriesAuditedRequired",
        "postAccessReviewRequired",
        "secretOrPersonalDataSearchForbidden",
    ):
        require(break_glass.get(flag) is True,
                f"breakGlass.{flag} must be true")
    require(break_glass.get("maximumDurationMinutes") == 60,
            "break-glass duration drift")
    require(break_glass.get("configured") is False,
            "break-glass is not configured")
    require(break_glass.get("tested") is False,
            "break-glass is not tested")

    export = access.get("export")
    require(isinstance(export, dict), "export must be an object")
    for flag in (
        "defaultDenied",
        "incidentReferenceRequired",
        "privacyReviewRequired",
        "boundedTimeRangeRequired",
        "boundedFieldSetRequired",
        "checksumAndSourceCommitRequired",
        "encryptedDestinationRequired",
        "automaticExpiryRequired",
        "rawBackendDumpForbidden",
    ):
        require(export.get(flag) is True, f"export.{flag} must be true")
    require(export.get("configured") is False, "export workflow is not configured")
    require(export.get("tested") is False, "export workflow is not tested")

    sink = access.get("sinkHealth")
    require(isinstance(sink, dict), "sinkHealth must be an object")
    require(sink.get("ingestionFreshnessMaximumMinutes") == 5,
            "sink freshness boundary drift")
    for flag in (
        "droppedEventAlertRequired",
        "schemaRejectionAlertRequired",
        "accessAuditFailureIsSev0",
        "retentionExpiryFailureIsHighSeverity",
    ):
        require(sink.get(flag) is True, f"sinkHealth.{flag} must be true")
    require(sink.get("configured") is False, "sink monitoring is not configured")
    require(sink.get("verified") is False, "sink monitoring is not verified")

    change = access.get("changeControl")
    require(isinstance(change, dict), "changeControl must be an object")
    for flag in (
        "infrastructureAsCodeRequired",
        "exactSourceCommitRequired",
        "independentReviewRequired",
        "rollbackPlanRequired",
        "productionConfirmationRequired",
        "automaticProductionDecisionChangeForbidden",
    ):
        require(change.get(flag) is True, f"changeControl.{flag} must be true")

    readiness = access.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "retentionPolicyDefined",
        "accessRolesDefined",
        "breakGlassPolicyDefined",
        "exportPolicyDefined",
        "sinkHealthRequirementsDefined",
        "runbookDefined",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "productionBackendConfigured",
        "identityGroupsConfigured",
        "accessAuditConfigured",
        "retentionEnforced",
        "breakGlassTested",
        "exportTested",
        "operatorReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven observability readiness cannot be true: {unproven}")

    runbook_path = ROOT / access["canonicalRunbook"]
    require(runbook_path.is_file(), "observability access runbook missing")
    runbook = runbook_path.read_text(encoding="utf-8")
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"runbook missing heading: {heading}")
    for phrase in (
        "Production decision remains: **NO_GO**",
        "Shared accounts and unlogged administrative access are forbidden",
        "Grant the minimum role for no more than 60 minutes",
        "No production log backend is configured",
        "No log-derived paging route is configured",
    ):
        require(phrase in runbook, f"runbook missing binding phrase: {phrase}")

    refs = access.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "observability access evidenceRefs invalid")
    require(set(refs) == EXPECTED_EVIDENCE, f"evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "policy definitions cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-003"]
    require(len(matches) == 1, "OPS-P0-003 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "policy without backend enforcement cannot make OPS-P0-003 READY")

    print("Memory OS observability access validation PASS")
    print(f"access roles: {len(roles)}  retention tiers: {len(tiers)}")
    print("production configuration: NOT_CONFIGURED")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"OBSERVABILITY ACCESS VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
