#!/usr/bin/env python3
"""Register backup/restore policy foundations without claiming configuration."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/backup-restore-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"

NEW_EXISTING = (
    "binding backup, PITR, object-version retention and isolated-restore policy with object versioning explicitly separated from backup completion",
    "four protected recovery domains covering canonical PostgreSQL state, exact object versions, release metadata and incident/deletion evidence",
    "nine-phase isolated restore lifecycle with mandatory authority, integrity, idempotency and non-resurrection verification",
    "promotion guards that block routing on cross-tenant visibility, resurrection, recovery-point incoherence, missing artifacts, unmeasured objectives or incomplete checks",
    "canonical backup/restore runbook and fail-closed policy validator",
)
NEW_REFS = (
    "contracts/operations/backup-restore-contract.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "docs/runbooks/memory-os-backup-restore.md",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/reconcile-memory-os-backup-restore.py",
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


def main() -> int:
    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "backup readiness must be an object")
    for foundation in (
        "policyDefined", "protectedDomainsDefined", "restoreLifecycleDefined",
        "mandatoryVerificationDefined", "promotionGuardsDefined",
        "evidenceRecordDefined", "runbookDefined",
    ):
        require(readiness.get(foundation) is True,
                f"backup policy foundation not validated: {foundation}")
    for unproven in (
        "rpoDefined", "rtoDefined", "postgresBackupConfigured",
        "postgresPitrConfigured", "objectIndependentRetentionConfigured",
        "backupMonitoringConfigured", "isolatedRestoreEnvironmentImplemented",
        "nonResurrectionAutomationImplemented", "restoreDrillCompleted",
        "productionPromotionRehearsed", "independentReviewCompleted", "ready",
    ):
        require(readiness.get(unproven) is False,
                f"unproven backup readiness cannot be true: {unproven}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "backup reconcile requires productionDecision NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") in {
        "NOT_IMPLEMENTED_OR_PROVEN", "PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"
    }, "backup reconcile cannot modify the current status")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-007 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence must be a list")
    if refs is None:
        refs = []
        gate["evidenceRefs"] = refs
    require(isinstance(refs, list), "OPS-P0-007 evidenceRefs must be a list")
    require_canonical_gaps(missing, ReconcileFailure)

    changed = False
    if gate.get("status") == "NOT_IMPLEMENTED_OR_PROVEN":
        gate["status"] = "PARTIAL_FOUNDATIONS_ONLY"
        changed = True
    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"backup evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    # Canonical production blockers are exclusively owned by
    # reconcile-memory-os-backup-authority.py. This policy-foundation layer may
    # add policy evidence, but it cannot manufacture, rewrite or duplicate gaps.
    require_canonical_gaps(missing, ReconcileFailure)
    require(gate.get("status") != "READY",
            "policy foundations cannot make OPS-P0-007 READY")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Backup/restore policy foundation already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Registered backup/restore policy foundations; canonical production blockers unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"BACKUP RESTORE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
