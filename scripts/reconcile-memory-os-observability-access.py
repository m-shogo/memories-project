#!/usr/bin/env python3
"""Register observability retention/access policy without claiming enforcement."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = ROOT / "contracts/operations/observability-event-contract.v1.json"
ACCESS_PATH = ROOT / "contracts/operations/observability-retention-access-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-observability-access.py"

OLD_GAP = "log retention and access policy configured"
NEW_EXISTING = (
    "binding privacy-first observability retention tiers for 14-day hot, 90-day warm and 365-day reviewed incident evidence",
    "least-privilege log access roles with separation between on-call, incident command, security review and observability administration",
    "default-denied 60-minute break-glass and reviewed export policies with append-only access audit requirements",
    "canonical access, export, retention-expiry and sink-health response runbook",
)
NEW_GAPS = (
    "production log backend retention enforcement, expiry verification and ingestion-freshness monitoring",
    "production identity-group assignment, append-only access-audit sink, periodic access review and tested break-glass/export workflows",
)
NEW_REFS = (
    "contracts/operations/observability-retention-access-contract.v1.json",
    "docs/runbooks/memory-os-observability-access.md",
    "scripts/validate-memory-os-observability-access.py",
    "scripts/reconcile-memory-os-observability-access.py",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def validate_current_authority() -> None:
    completed = subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            "canonical observability access authority is invalid before reconcile")


def commit_validated_pair(event: dict[str, Any], status: dict[str, Any]) -> None:
    original_event = EVENT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        EVENT_PATH.write_bytes(render(event))
        STATUS_PATH.write_bytes(render(status))
        completed = subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=False)
        require(completed.returncode == 0,
                "reconciled observability access authority failed validation")
    except BaseException:
        EVENT_PATH.write_bytes(original_event)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    validate_current_authority()
    event = load(EVENT_PATH)
    access = load(ACCESS_PATH)
    readiness = access.get("readiness")
    require(isinstance(readiness, dict), "access readiness must be an object")
    for foundation in (
        "retentionPolicyDefined",
        "accessRolesDefined",
        "breakGlassPolicyDefined",
        "exportPolicyDefined",
        "sinkHealthRequirementsDefined",
        "runbookDefined",
    ):
        require(readiness.get(foundation) is True,
                f"access foundation not validated: {foundation}")
    for unproven in (
        "productionBackendConfigured",
        "identityGroupsConfigured",
        "accessAuditConfigured",
        "retentionEnforced",
        "breakGlassTested",
        "exportTested",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven access readiness cannot be true: {unproven}")

    retention = event.get("retention")
    require(isinstance(retention, dict), "event retention must be an object")
    changed = False
    expected_retention = {
        "policyDefined": True,
        "policyContract": "contracts/operations/observability-retention-access-contract.v1.json",
        "backendConfigured": False,
        "enforcementVerified": False,
        "note": (
            "Retention and access policy is defined in the dedicated privacy-first "
            "contract, but no production log backend, identity groups, access-audit "
            "sink, break-glass workflow or expiry verification is configured. "
            "OPS-P0-003 remains PARTIAL."
        ),
    }
    for key, value in expected_retention.items():
        if retention.get(key) != value:
            retention[key] = value
            changed = True

    expected_access = {
        "policyDefined": True,
        "policyContract": "contracts/operations/observability-retention-access-contract.v1.json",
        "identityGroupsConfigured": False,
        "accessAuditConfigured": False,
        "breakGlassTested": False,
        "exportTested": False,
    }
    access_policy = event.get("accessPolicy")
    if access_policy != expected_access:
        event["accessPolicy"] = expected_access
        changed = True

    alert_routing = event.get("alertRouting")
    require(isinstance(alert_routing, dict), "event alertRouting must be an object")
    require(alert_routing.get("routingConfigured") is False,
            "log alert routing remains unconfigured")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "access policy cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-003"]
    require(len(matches) == 1, "OPS-P0-003 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "access policy cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-003 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-003 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-003 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    if OLD_GAP in missing:
        missing.remove(OLD_GAP)
        changed = True
    for item in NEW_GAPS:
        changed = append_once(missing, item) or changed
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"observability access evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    for required_gap in (
        "production log backend retention enforcement",
        "production identity-group assignment",
        "real alert routing",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-003 gap disappeared: {required_gap}")
    require(gate.get("status") == "PARTIAL", "OPS-P0-003 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Observability access authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_validated_pair(event, status)
    print("Registered observability retention/access policy; enforcement remains NOT_CONFIGURED and OPS-P0-003 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"OBSERVABILITY ACCESS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
