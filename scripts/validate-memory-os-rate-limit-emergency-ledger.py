#!/usr/bin/env python3
"""Validate rate-limit emergency ledger structure and fail-closed promotion boundaries."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-emergency-ledger-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-emergency-ledger.v1.json"
POLICY = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
OPERATIONS = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-rate-limit-emergency-operation.py"
EVALUATOR = ROOT / "scripts/evaluate-memory-os-rate-limit-emergency-state.py"
WORKFLOW = ROOT / ".github/workflows/rate-limit-emergency-ledger.yml"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    policy = load(POLICY)
    operations = load(OPERATIONS)
    require(contract.get("schemaVersion") == "memory-os-rate-limit-emergency-ledger.v1", "contract schema drift")
    require(contract.get("sourceOperationsContract") == str(OPERATIONS.relative_to(ROOT)), "operations binding drift")
    require(contract.get("sourcePolicyContract") == str(POLICY.relative_to(ROOT)), "policy binding drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    require(contract.get("effectiveStateEvaluator") == str(EVALUATOR.relative_to(ROOT)), "evaluator binding drift")
    for path in (WRITER, EVALUATOR):
        require(path.is_file(), f"implementation missing: {path.relative_to(ROOT)}")
    require(contract.get("appendOnly") is True, "contract must remain append-only")
    require(contract.get("eventTypes") == ["ACTIVATE_INTENT", "EXPIRE_OBSERVED", "RESTORE_VERIFIED", "CLOSE_OPERATION"], "eventTypes drift")
    require(contract.get("runtimeModes") == ["NORMAL_CONFIGURED", "STRICT_LOCAL_EMERGENCY", "ROUTE_FAIL_CLOSED"], "runtimeModes drift")
    guards = contract.get("activationGuards")
    require(isinstance(guards, dict), "activation guards missing")
    require(guards.get("maximumDurationMinutes") == 60, "maximum duration drift")
    for key in (
        "operatorReviewerMustDiffer", "sourceCommitMustExist", "affectedPoliciesMustExist",
        "strictLocalEmergencyOnlyForPoliciesDeclaringEmergencyLocalFallback", "unlimitedOrFailOpenForbidden",
        "expiryRequired", "expiryMayNotBeExtendedInPlace", "newActivationRequiredForAdditionalTime",
        "rawIpTokenAccountRequestContentForbidden", "runtimeAppliedMustRemainFalseUntilControlPlaneIntegration",
        "productionEvidenceMustRemainFalseUntilRuntimeAndIndependentReviewExist",
    ):
        require(guards.get(key) is True, f"activation guard drift: {key}")
    rules = contract.get("effectiveStateRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "effective-state rules must remain fail-closed")
    boundary = contract.get("currentAuthority")
    require(isinstance(boundary, dict), "currentAuthority missing")

    require(registry.get("schemaVersion") == "memory-os-rate-limit-emergency-ledger-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    events = registry.get("events")
    require(isinstance(events, list), "registry events missing")
    require(registry.get("registeredEventCount") == len(events), "registeredEventCount drift")
    operation_ids: set[str] = set()
    event_ids: set[str] = set()
    production_operations: set[str] = set()
    runtime_applied = 0
    production_evidence = 0
    known_policies = {row.get("policyId"): row for row in policy.get("policies", []) if isinstance(row, dict)}
    allowed_transitions = {(row.get("from"), row.get("to")) for row in operations.get("allowedTransitions", []) if isinstance(row, dict)}
    for index, event in enumerate(events):
        require(isinstance(event, dict), f"events[{index}] invalid")
        event_id = event.get("eventId")
        operation_id = event.get("operationId")
        require(isinstance(event_id, str) and event_id not in event_ids, f"events[{index}] eventId invalid/duplicate")
        require(isinstance(operation_id, str) and operation_id, f"events[{index}] operationId missing")
        event_ids.add(event_id)
        operation_ids.add(operation_id)
        require(isinstance(event.get("sourceCommitSha"), str) and SHA40.fullmatch(event["sourceCommitSha"]) is not None, f"events[{index}] sourceCommitSha invalid")
        require(event.get("runtimeApplied") is False, f"events[{index}] cannot claim runtime applied")
        require(event.get("productionEvidence") is False, f"events[{index}] cannot claim production evidence")
        if event.get("environmentClass") == "PRODUCTION":
            production_operations.add(operation_id)
        runtime_applied += 1 if event.get("runtimeApplied") is True else 0
        production_evidence += 1 if event.get("productionEvidence") is True else 0
        if event.get("eventType") == "ACTIVATE_INTENT":
            require((event.get("previousMode"), event.get("requestedMode")) in allowed_transitions, f"events[{index}] transition not allowed")
            affected = event.get("affectedPolicyIds")
            require(isinstance(affected, list) and affected and len(affected) == len(set(affected)), f"events[{index}] affected policies invalid")
            require(all(item in known_policies for item in affected), f"events[{index}] unknown policy")
            if event.get("requestedMode") == "STRICT_LOCAL_EMERGENCY":
                require(all(known_policies[item].get("failureMode") == "fail_closed_emergency_local" for item in affected), f"events[{index}] invalid emergency-local policy")
            require(isinstance(event.get("environmentIdentityDigest"), str) and SHA256.fullmatch(event["environmentIdentityDigest"]) is not None, f"events[{index}] environment digest invalid")
    require(registry.get("registeredOperationCount") == len(operation_ids), "registeredOperationCount drift")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry cannot promote production")
    if "productionOperationCount" in registry:
        require(registry.get("productionOperationCount") == len(production_operations), "productionOperationCount drift")
    if "runtimeAppliedEventCount" in registry:
        require(registry.get("runtimeAppliedEventCount") == runtime_applied, "runtimeAppliedEventCount drift")
    if "productionEvidenceEventCount" in registry:
        require(registry.get("productionEvidenceEventCount") == production_evidence, "productionEvidenceEventCount drift")

    require(boundary.get("registeredEventCount") in {0, len(events)}, "contract event count drift")
    require(boundary.get("runtimeControlPlaneIntegrated") is False, "ledger cannot integrate runtime by claim")
    require(boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "production boundary drift")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for key in ("runtimeControlPlaneIntegrated", "productionEmergencyOperationRecorded", "completedRuntimeDrill", "independentReviewCompleted", "productionReady"):
        require(readiness.get(key) is False, f"ledger foundation cannot enable {key}")

    serialized = json.dumps(registry, ensure_ascii=False).lower()
    for forbidden in ("postgres://", "postgresql://", "authorization: bearer", "minioadmin", "raw_ip", "bearer_token", "account_id", "request_body"):
        require(forbidden not in serialized, f"registry contains forbidden material: {forbidden}")

    print("Memory OS rate-limit emergency ledger validation PASS")
    print(f"registered events: {len(events)}")
    print(f"registered operations: {len(operation_ids)}")
    print("runtime control plane integrated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE-LIMIT EMERGENCY LEDGER VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
