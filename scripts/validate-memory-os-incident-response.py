#!/usr/bin/env python3
"""Fail-closed validator for Memory OS incident response foundations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/incident-response-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_SEVERITIES = ["SEV0", "SEV1", "SEV2", "SEV3"]
EXPECTED_ACK_MINUTES = {
    "SEV0": 5,
    "SEV1": 15,
    "SEV2": 60,
    "SEV3": 240,
}
EXPECTED_ROLES = {
    "INCIDENT_COMMANDER",
    "OPERATIONS_LEAD",
    "SECURITY_PRIVACY_LEAD",
    "SYSTEM_OWNER",
    "COMMUNICATIONS_LEAD",
    "SCRIBE",
}
EXPECTED_LIFECYCLE = [
    "DETECT_AND_DECLARE",
    "TRIAGE_AND_SCOPE",
    "CONTAIN",
    "PRESERVE_AND_DIAGNOSE",
    "RECOVER",
    "VERIFY",
    "CLOSE_AND_FOLLOW_UP",
]
EXPECTED_DRILLS = {
    "IR-DRILL-001": "SEV0",
    "IR-DRILL-002": "SEV1",
    "IR-DRILL-003": "SEV1",
    "IR-DRILL-004": "SEV1",
    "IR-DRILL-005": "SEV0",
    "IR-DRILL-006": "SEV0",
}
REQUIRED_EVIDENCE_FIELDS = {
    "incidentId",
    "declaredAt",
    "detectedBy",
    "severity",
    "incidentCommander",
    "affectedSurfaces",
    "confirmedFacts",
    "knownPriorConditions",
    "hypotheses",
    "containmentActions",
    "evidenceRefs",
    "recoveryDecision",
    "verificationResults",
    "communications",
    "openRisks",
    "closedAt",
    "closureApprovals",
}
REQUIRED_STATUS_REFS = {
    "contracts/operations/incident-response-contract.v1.json",
    "docs/runbooks/memory-os-incident-response.md",
    "scripts/validate-memory-os-incident-response.py",
}
REQUIRED_RUNBOOK_HEADINGS = [
    "## Immediate rules",
    "## Severity model",
    "## Roles",
    "## Mandatory stop conditions",
    "## Phase 1 — Detect and declare",
    "## Phase 2 — Triage and scope",
    "## Phase 3 — Contain",
    "## Phase 4 — Preserve and diagnose",
    "## Phase 5 — Recover",
    "## Phase 6 — Verify",
    "## Phase 7 — Communicate",
    "## Phase 8 — Close and follow up",
    "## Tabletop scenarios",
    "## Current limitations",
]
REQUIRED_RUNBOOK_PHRASES = [
    "Production decision remains: **NO_GO**",
    "Prefer fail-closed or read-only behavior",
    "Separate confirmed facts, known prior conditions, hypotheses and opinion",
    "A transaction rollback, process restart, queue retry or component recovery does **not** prove full incident recovery",
    "deletion/session non-resurrection",
    "No pager, status page, external contact tree or user-notification channel is configured",
    "does not claim that a tabletop or production drill has been completed",
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


def unique_object_map(value: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{field} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        require(isinstance(item, dict), f"{field} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier.strip(),
                f"{field}.{key} is required")
        require(identifier not in result, f"duplicate {field} identifier: {identifier}")
        result[identifier] = item
    return result


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-incident-response.v1",
            "unsupported incident response schemaVersion")
    require(contract.get("canonicalRunbook") == "docs/runbooks/memory-os-incident-response.md",
            "canonicalRunbook drift")
    require(contract.get("validator") == "scripts/validate-memory-os-incident-response.py",
            "validator path drift")
    require(contract.get("productionDecision") == "NO_GO",
            "incident foundations cannot change productionDecision")

    principles = unique_strings(contract.get("principles"), "principles", minimum=6)
    for required_phrase in (
        "protect user data",
        "preserve evidence",
        "confirmed fact",
        "full recovery",
        "non-resurrection",
        "incident command",
    ):
        require(any(required_phrase in item for item in principles),
                f"principles omit binding concept: {required_phrase}")

    severities_list = contract.get("severityLevels")
    require(isinstance(severities_list, list), "severityLevels must be a list")
    severity_ids = [item.get("id") for item in severities_list if isinstance(item, dict)]
    require(severity_ids == EXPECTED_SEVERITIES,
            f"severity order drift: {severity_ids}")
    severities = unique_object_map(severities_list, "id", "severityLevels")
    for severity_id, expected_ack in EXPECTED_ACK_MINUTES.items():
        item = severities[severity_id]
        require(item.get("acknowledgementTargetMinutes") == expected_ack,
                f"{severity_id}: acknowledgement target drift")
        unique_strings(item.get("examples"), f"{severity_id}.examples", minimum=3)
        unique_strings(item.get("closureApproval"), f"{severity_id}.closureApproval")
        require(isinstance(item.get("defaultContainment"), str) and item["defaultContainment"],
                f"{severity_id}: defaultContainment is required")
    require(severities["SEV0"].get("incidentCommanderRequired") is True,
            "SEV0 requires incident command")
    require(severities["SEV0"].get("securityPrivacyLeadRequired") is True,
            "SEV0 requires a security/privacy lead")
    require(severities["SEV0"].get("changeFreezeRequired") is True,
            "SEV0 requires a change freeze")
    require(severities["SEV1"].get("incidentCommanderRequired") is True,
            "SEV1 requires incident command")
    require(severities["SEV1"].get("changeFreezeRequired") is True,
            "SEV1 requires a change freeze")
    for severity_id in ("SEV0", "SEV1"):
        require(severities[severity_id].get("userCommunicationAssessmentRequired") is True,
                f"{severity_id} requires user-communication assessment")

    roles = unique_object_map(contract.get("roles"), "id", "roles")
    require(set(roles) == EXPECTED_ROLES, f"role set drift: {sorted(roles)}")
    for role_id, item in roles.items():
        unique_strings(item.get("responsibilities"), f"roles.{role_id}.responsibilities", minimum=2)

    lifecycle_list = contract.get("lifecycle")
    require(isinstance(lifecycle_list, list), "lifecycle must be a list")
    lifecycle_names = [item.get("phase") for item in lifecycle_list if isinstance(item, dict)]
    require(lifecycle_names == EXPECTED_LIFECYCLE,
            f"incident lifecycle order drift: {lifecycle_names}")
    lifecycle = unique_object_map(lifecycle_list, "phase", "lifecycle")
    for phase, item in lifecycle.items():
        unique_strings(item.get("requiredActions"), f"lifecycle.{phase}.requiredActions", minimum=3)
        require(isinstance(item.get("exitCriteria"), str) and item["exitCriteria"].strip(),
                f"lifecycle.{phase}.exitCriteria is required")

    stop_conditions = unique_strings(
        contract.get("mandatoryStopConditions"),
        "mandatoryStopConditions",
        minimum=8,
    )
    for required_stop in (
        "target environment",
        "destructive mutation",
        "cross-tenant",
        "incident evidence",
        "source commit",
        "deletion or expired-session",
        "role is unassigned",
        "secret",
    ):
        require(any(required_stop in item for item in stop_conditions),
                f"mandatoryStopConditions omit: {required_stop}")

    communication = contract.get("communicationRules")
    require(isinstance(communication, dict), "communicationRules must be an object")
    for required_true in (
        "factInferenceOpinionSeparated",
        "timestampsRequired",
        "nextUpdatePointRequiredForSEV0AndSEV1",
        "unsupportedRootCauseForbidden",
        "unsupportedRecoveryClaimForbidden",
        "userCommunicationRequiresScopeAndPrivacyAssessment",
        "advertisingOrMarketingLanguageForbidden",
    ):
        require(communication.get(required_true) is True,
                f"communicationRules.{required_true} must be true")
    require(communication.get("externalChannelsConfigured") is False,
            "external channels are not configured by this repository")

    evidence = contract.get("evidenceRecord")
    require(isinstance(evidence, dict), "evidenceRecord must be an object")
    require(evidence.get("appendOnly") is True, "incident evidence must be append-only")
    require(evidence.get("privacyClass") == "operational_sensitive_no_secrets",
            "incident evidence privacy class drift")
    evidence_fields = set(unique_strings(evidence.get("requiredFields"),
                                         "evidenceRecord.requiredFields"))
    require(evidence_fields == REQUIRED_EVIDENCE_FIELDS,
            f"incident evidence field set drift: {sorted(evidence_fields)}")

    drills = unique_object_map(contract.get("requiredDrillScenarios"), "id", "requiredDrillScenarios")
    require(set(drills) == set(EXPECTED_DRILLS), f"drill scenario set drift: {sorted(drills)}")
    for drill_id, expected_severity in EXPECTED_DRILLS.items():
        item = drills[drill_id]
        require(item.get("expectedSeverity") == expected_severity,
                f"{drill_id}: expectedSeverity drift")
        require(isinstance(item.get("scenario"), str) and item["scenario"].strip(),
                f"{drill_id}: scenario is required")
        unique_strings(item.get("requiredVerification"),
                       f"{drill_id}.requiredVerification", minimum=3)

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "severityModelDefined",
        "rolesDefined",
        "lifecycleDefined",
        "containmentAndRecoveryRulesDefined",
        "evidenceRecordDefined",
        "runbookDefined",
        "tabletopPlanDefined",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "pagingAndAlertRoutingConfigured",
        "externalContactTreeConfigured",
        "tabletopCompleted",
        "productionRecoveryDrillCompleted",
        "independentReviewCompleted",
        "ready",
    ):
        require(readiness.get(unproven) is False,
                f"unproven incident readiness cannot be true: {unproven}")

    evidence_refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs")
    require(set(evidence_refs) == REQUIRED_STATUS_REFS,
            f"incident evidenceRefs drift: {evidence_refs}")
    for ref in evidence_refs:
        require((ROOT / ref).is_file(), f"incident evidence path missing: {ref}")

    runbook_path = ROOT / contract["canonicalRunbook"]
    try:
        runbook = runbook_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("canonical incident runbook is missing") from exc
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"incident runbook missing heading: {heading}")
    for phrase in REQUIRED_RUNBOOK_PHRASES:
        require(phrase in runbook, f"incident runbook missing binding phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "incident foundations cannot change productionDecision from NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability status areas must be a list")
    matches = [area for area in areas if isinstance(area, dict) and area.get("id") == "OPS-P0-002"]
    require(len(matches) == 1, "OPS-P0-002 must exist exactly once")
    area = matches[0]
    require(area.get("status") in {"PARTIAL", "READY"},
            "OPS-P0-002 must be PARTIAL or READY after incident foundations")
    status_refs = area.get("evidenceRefs")
    require(isinstance(status_refs, list), "OPS-P0-002 evidenceRefs must be a list")
    missing_status_refs = REQUIRED_STATUS_REFS - set(status_refs)
    require(not missing_status_refs,
            f"OPS-P0-002 omits incident evidence: {sorted(missing_status_refs)}")

    if area.get("status") == "READY":
        for requirement in (
            "pagingAndAlertRoutingConfigured",
            "externalContactTreeConfigured",
            "tabletopCompleted",
            "productionRecoveryDrillCompleted",
            "independentReviewCompleted",
            "ready",
        ):
            require(readiness.get(requirement) is True,
                    f"OPS-P0-002 READY without readiness.{requirement}")
    else:
        missing = area.get("missingEvidence")
        require(isinstance(missing, list) and missing,
                "PARTIAL OPS-P0-002 requires missingEvidence")
        for required_gap in (
            "paging",
            "contact",
            "tabletop",
            "production-shaped recovery drill",
            "independent review",
        ):
            require(any(required_gap in item for item in missing),
                    f"OPS-P0-002 missingEvidence must retain: {required_gap}")

    print("Memory OS incident response validation PASS")
    print(f"severity levels: {len(severities)}")
    print(f"required drill scenarios: {len(drills)}")
    print(f"OPS-P0-002 status: {area.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"INCIDENT RESPONSE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
