#!/usr/bin/env python3
"""Register rate-limit operations policy without claiming control-plane readiness."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-operations.py"

OLD_GAP = "operational disable/rollback runbook"
STALE_LEDGER_GAP = "production emergency control plane with automatic expiry and append-only operation evidence ledger"
NEW_EXISTING = (
    "binding emergency-operation policy that forbids unlimited/fail-open public traffic and permits only normal bounded, strict local emergency or route fail-closed modes",
    "trusted-proxy disablement procedure for uncertain deployment ownership",
    "canonical activation, rollback, shared-store recovery and no-business-mutation verification runbook",
)
NEW_GAPS = (
    "production emergency control plane with automatic expiry",
    "completed emergency-mode, shared-store recovery and trusted-proxy disablement drills",
)
NEW_REFS = (
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "docs/runbooks/memory-os-rate-limit-operations.md",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/reconcile-memory-os-rate-limit-operations.py",
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


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def validate_written_authority() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0,
            f"rate-limit operations post-write validation failed:\n{completed.stdout[-4000:]}")


def transactional_write(policy: dict[str, Any], status: dict[str, Any]) -> None:
    originals = {
        POLICY_PATH: POLICY_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        POLICY_PATH.write_text(
            json.dumps(policy, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validate_written_authority()
    except Exception:
        for path, original in originals.items():
            path.write_bytes(original)
        raise


def main() -> int:
    policy = load(POLICY_PATH)
    operations = load(OPERATIONS_PATH)
    readiness = operations.get("readiness")
    require(isinstance(readiness, dict), "operations readiness must be an object")
    for foundation in (
        "policyDefined", "runbookDefined", "safeModesDefined",
        "transitionGuardsDefined", "recoveryVerificationDefined",
        "evidenceLedgerImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"operations foundation not validated: {foundation}")
    for unproven in (
        "productionControlPlaneImplemented", "automaticExpiryImplemented",
        "sharedStoreImplemented", "trustedProxyDeploymentConfigured",
        "drillCompleted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven operations readiness cannot be true: {unproven}")

    changed = False
    expected_operations = {
        "policyDefined": True,
        "policyContract": "contracts/operations/rate-limit-operations-contract.v1.json",
        "productionControlPlaneImplemented": False,
        "automaticExpiryImplemented": False,
        "evidenceLedgerImplemented": True,
        "drillCompleted": False,
    }
    if policy.get("operations") != expected_operations:
        policy["operations"] = expected_operations
        changed = True

    refs = policy.get("evidenceRefs")
    require(isinstance(refs, list), "primary rate-limit evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"rate-limit operations evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    store = policy.get("store")
    require(isinstance(store, dict), "primary store contract must be an object")
    require(store.get("distributedEnforcementImplemented") is False,
            "distributed shared store remains unimplemented")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "operations policy cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-005"]
    require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "operations policy cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-005 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-005 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-005 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    for stale_gap in (OLD_GAP, STALE_LEDGER_GAP):
        if stale_gap in missing:
            missing.remove(stale_gap)
            changed = True
    for item in NEW_GAPS:
        changed = append_once(missing, item) or changed
    for ref in NEW_REFS:
        changed = append_once(status_refs, ref) or changed

    for required_gap in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration owned per deployment",
        "load-calibrated limits",
        "production emergency control plane",
        "completed emergency-mode",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-005 gap disappeared: {required_gap}")
    require(not any("append-only operation evidence ledger" in item for item in missing),
            "implemented operation ledger cannot remain a missing-evidence blocker")
    require(gate.get("status") == "PARTIAL", "OPS-P0-005 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Rate-limit operations authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    transactional_write(policy, status)
    print("Registered rate-limit operations policy; OPS-P0-005 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RATE-LIMIT OPERATIONS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
