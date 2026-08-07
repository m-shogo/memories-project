#!/usr/bin/env python3
"""Fail-closed validation for rate-limit emergency operations policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
EVIDENCE_CONTRACT_PATH = ROOT / "contracts/operations/rate-limit-operation-evidence-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_MODES = {
    "NORMAL_CONFIGURED": True,
    "STRICT_LOCAL_EMERGENCY": True,
    "ROUTE_FAIL_CLOSED": True,
    "UNLIMITED_OR_FAIL_OPEN": False,
}
EXPECTED_PROXY_MODES = {
    "TRUSTED_PROXY_CONFIGURED": True,
    "TRUSTED_PROXY_DISABLED": True,
    "ARBITRARY_FORWARDED_HEADERS": False,
}
EXPECTED_TRANSITIONS = {
    ("NORMAL_CONFIGURED", "STRICT_LOCAL_EMERGENCY"),
    ("NORMAL_CONFIGURED", "ROUTE_FAIL_CLOSED"),
    ("STRICT_LOCAL_EMERGENCY", "ROUTE_FAIL_CLOSED"),
    ("STRICT_LOCAL_EMERGENCY", "NORMAL_CONFIGURED"),
    ("ROUTE_FAIL_CLOSED", "NORMAL_CONFIGURED"),
}
BASE_EVIDENCE = {
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "docs/runbooks/memory-os-rate-limit-operations.md",
    "scripts/validate-memory-os-rate-limit-operations.py",
}
LEDGER_EVIDENCE = {
    "contracts/operations/rate-limit-operation-evidence-contract.v1.json",
    "docs/evidence/rate-limit-operations/README.md",
    "docs/fixtures/memory-os-operability/rate-limit-operation-record.template.v1.json",
    "scripts/create-memory-os-rate-limit-operation-evidence.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence.py",
    "scripts/reconcile-memory-os-rate-limit-operation-evidence.py",
}
REQUIRED_RUNBOOK_HEADINGS = (
    "## Non-negotiable rules",
    "## Before changing mode",
    "## NORMAL_CONFIGURED",
    "## STRICT_LOCAL_EMERGENCY",
    "## ROUTE_FAIL_CLOSED",
    "## TRUSTED_PROXY_DISABLED",
    "## Shared-store recovery",
    "## Rollback of an operational change",
    "## Required mutation checks",
    "## Evidence closure",
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


def object_map(items: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
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


def unique_strings(items: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(items, list) and len(items) >= minimum,
            f"{field} must contain at least {minimum} item(s)")
    require(all(isinstance(item, str) and item for item in items),
            f"{field} contains invalid values")
    require(len(items) == len(set(items)), f"{field} contains duplicates")
    return items


def main() -> int:
    policy = load(POLICY_PATH)
    operations = load(OPERATIONS_PATH)
    evidence_contract = load(EVIDENCE_CONTRACT_PATH)
    require(operations.get("schemaVersion") == "memory-os-rate-limit-operations.v1",
            "operations schemaVersion drift")
    require(operations.get("sourcePolicyContract") ==
            "contracts/operations/rate-limit-policy-contract.v1.json",
            "source policy contract drift")
    require(operations.get("canonicalRunbook") ==
            "docs/runbooks/memory-os-rate-limit-operations.md",
            "canonical runbook path drift")
    require(operations.get("status") ==
            "POLICY_DEFINED_CONTROL_PLANE_NOT_IMPLEMENTED",
            "operations status must remain honest")

    failure_modes = set(policy.get("failureModes", []))
    require({"fail_closed", "fail_closed_emergency_local", "health_exempt"}
            .issubset(failure_modes), "primary failure-mode set lost a safe mode")
    require("fail_open" not in failure_modes, "primary policy permits fail open")
    policies = policy.get("policies")
    require(isinstance(policies, list), "primary policies must be a list")
    emergency_policy_ids = {
        item.get("policyId") for item in policies
        if isinstance(item, dict) and
        item.get("failureMode") == "fail_closed_emergency_local"
    }
    require(emergency_policy_ids == {"apple-exchange"},
            f"unexpected emergency-local policy set: {sorted(emergency_policy_ids)}")

    modes = object_map(operations.get("operationalModes"), "id", "operationalModes")
    require(set(modes) == set(EXPECTED_MODES), f"operational mode drift: {sorted(modes)}")
    for mode_id, allowed in EXPECTED_MODES.items():
        require(modes[mode_id].get("allowed") is allowed,
                f"{mode_id}: allowed flag drift")
    require("unbounded" in modes["UNLIMITED_OR_FAIL_OPEN"].get("publicTrafficBehavior", ""),
            "forbidden mode must remain explicitly unbounded")

    proxy_modes = object_map(operations.get("proxyModes"), "id", "proxyModes")
    require(set(proxy_modes) == set(EXPECTED_PROXY_MODES),
            f"proxy mode drift: {sorted(proxy_modes)}")
    for mode_id, allowed in EXPECTED_PROXY_MODES.items():
        require(proxy_modes[mode_id].get("allowed") is allowed,
                f"{mode_id}: proxy allowed flag drift")

    transitions = operations.get("allowedTransitions")
    require(isinstance(transitions, list), "allowedTransitions must be a list")
    transition_pairs: set[tuple[str, str]] = set()
    for transition in transitions:
        require(isinstance(transition, dict), "transition must be an object")
        pair = (transition.get("from"), transition.get("to"))
        require(all(isinstance(value, str) and value for value in pair),
                "transition endpoints are required")
        require(pair not in transition_pairs, f"duplicate transition: {pair}")
        transition_pairs.add(pair)
        require(pair[0] != "UNLIMITED_OR_FAIL_OPEN" and
                pair[1] != "UNLIMITED_OR_FAIL_OPEN",
                "a transition references the forbidden fail-open mode")
        require(isinstance(transition.get("condition"), str) and
                transition["condition"], "transition condition is required")
    require(transition_pairs == EXPECTED_TRANSITIONS,
            f"allowed transition drift: {sorted(transition_pairs)}")

    guards = operations.get("activationGuards")
    require(isinstance(guards, dict), "activationGuards must be an object")
    for guard in (
        "incidentReferenceRequired",
        "exactSourceCommitRequired",
        "namedOperatorRequired",
        "independentReviewerRequired",
        "affectedPoliciesExplicitRequired",
        "startAndExpiryRequired",
        "automaticExpiryRequired",
        "publicCommunicationDecisionRequired",
        "rawIpOrTokenEvidenceForbidden",
        "productionConfirmationRequired",
    ):
        require(guards.get(guard) is True, f"activationGuards.{guard} must be true")
    require(guards.get("maximumEmergencyDurationMinutes") == 60,
            "emergency duration boundary drift")

    forbidden_actions = unique_strings(operations.get("forbiddenActions"),
                                       "forbiddenActions", minimum=8)
    joined_forbidden = "\n".join(forbidden_actions)
    for phrase in (
        "fail open",
        "unlimited capacity",
        "disable authentication",
        "arbitrary forwarded",
        "raw IP",
        "clear rate-limit counters",
        "disable structured events",
        "mutation and integrity checks",
    ):
        require(phrase in joined_forbidden,
                f"forbidden action omitted: {phrase}")

    verification = unique_strings(operations.get("recoveryVerification"),
                                  "recoveryVerification", minimum=7)
    joined_verification = "\n".join(verification)
    for phrase in (
        "atomic increment",
        "policy generation",
        "trusted proxy",
        "created no account session replay upload apply or memory mutation",
        "bounded canary",
        "temporary mode expires",
    ):
        require(phrase in joined_verification,
                f"recovery verification omitted: {phrase}")

    evidence = operations.get("evidenceRecord")
    require(isinstance(evidence, dict), "evidenceRecord must be an object")
    fields = set(unique_strings(evidence.get("requiredFields"),
                                "evidenceRecord.requiredFields", minimum=10))
    for required_field in (
        "operationId", "incidentReference", "sourceCommitSha", "operator",
        "reviewer", "previousMode", "newMode", "proxyMode",
        "affectedPolicyIds", "startedAt", "expiresAt", "verificationResults",
        "restoredAt", "openRisks",
    ):
        require(required_field in fields,
                f"evidence record field omitted: {required_field}")
    require(evidence.get("appendOnly") is True,
            "operation evidence must remain append-only")
    require(evidence.get("privacyClass") == "operational_sensitive_no_secrets",
            "operation evidence privacy class drift")

    ledger_readiness = evidence_contract.get("readiness")
    require(isinstance(ledger_readiness, dict), "ledger readiness must be an object")
    for flag in (
        "recordContractDefined", "exclusiveWriterImplemented",
        "ledgerValidatorImplemented", "duplicateOperationIdRejected",
        "privacyValidationImplemented",
    ):
        require(ledger_readiness.get(flag) is True,
                f"ledger foundation missing: {flag}")
    for flag in (
        "productionControlPlaneImplemented", "automaticModeExpiryImplemented",
        "productionEvidenceRecorded", "productionReady",
    ):
        require(ledger_readiness.get(flag) is False,
                f"ledger cannot claim unproven production capability: {flag}")

    readiness = operations.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "policyDefined", "runbookDefined", "safeModesDefined",
        "transitionGuardsDefined", "recoveryVerificationDefined",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    require(readiness.get("evidenceLedgerImplemented") is True,
            "implemented append-only operation ledger must be registered")
    for unproven in (
        "productionControlPlaneImplemented",
        "automaticExpiryImplemented",
        "sharedStoreImplemented",
        "trustedProxyDeploymentConfigured",
        "drillCompleted",
        "operatorReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven operations readiness cannot be true: {unproven}")

    runbook_path = ROOT / operations["canonicalRunbook"]
    require(runbook_path.is_file(), "rate-limit operations runbook missing")
    runbook = runbook_path.read_text(encoding="utf-8")
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"runbook missing heading: {heading}")
    for phrase in (
        "Production decision remains: **NO_GO**",
        "UNLIMITED_OR_FAIL_OPEN` is forbidden",
        "Every emergency mode expires automatically after no more than 60 minutes",
        "Emergency local fallback is permitted only for a route whose machine-readable policy already declares",
        "Never record raw IP addresses, tokens, account IDs or request content",
        "No emergency-mode or recovery drill has been completed",
    ):
        require(phrase in runbook, f"runbook missing binding phrase: {phrase}")

    refs = operations.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "rate-limit operations evidenceRefs invalid")
    expected_evidence = BASE_EVIDENCE | LEDGER_EVIDENCE
    require(set(refs) == expected_evidence, f"evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "operations policy cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-005"]
    require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "operation evidence foundation cannot make OPS-P0-005 READY")
    missing = gate.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-005 missingEvidence must be a list")
    require(any("production emergency control plane with automatic expiry" in item
                for item in missing),
            "production control-plane/expiry gap must remain explicit")

    print("Memory OS rate-limit operations validation PASS")
    print(f"safe operational modes: {sum(1 for value in EXPECTED_MODES.values() if value)}")
    print("append-only operation evidence ledger: IMPLEMENTED")
    print("production control plane: NOT_IMPLEMENTED")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"RATE-LIMIT OPERATIONS VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
