#!/usr/bin/env python3
"""Reconcile migration rehearsal evidence infrastructure into canonical operability authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
REGISTRY_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
RECOVERY_VALIDATOR = ROOT / "scripts/memory_os_migration_recovery_point.py"
LOCAL_RESTORE = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
WORKFLOW = ROOT / ".github/workflows/migration-evidence-registry.yml"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
LIFECYCLE_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-lifecycle.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "append-only privacy-safe migration rehearsal evidence registry is implemented with an external-record writer, exact source-commit and canonical migration-sequence binding, distinct operator/reviewer pseudonyms, lock and statement budgets, an opaque SHA-256 recovery-artifact reference, and a separately validated local logical-restore capability authority; arbitrary repository files can no longer satisfy recovery evidence, while the actual rehearsal recovery artifact is still not restored by this registry and registrations remain non-production evidence"
)
REFS = (
    "contracts/operations/migration-evidence-registry-contract.v1.json",
    "contracts/operations/migration-evidence-registry.v1.json",
    "scripts/register-memory-os-migration-rehearsal-evidence.py",
    "scripts/validate-memory-os-migration-evidence-registry.py",
    "scripts/memory_os_migration_recovery_point.py",
    "scripts/reconcile-memory-os-migration-evidence-registry.py",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    ".github/workflows/migration-evidence-registry.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    for path in (
        REGISTRY, WRITER, REGISTRY_VALIDATOR, RECOVERY_VALIDATOR, LOCAL_RESTORE,
        WORKFLOW, LIFECYCLE_VALIDATOR,
    ):
        require(path.is_file(), f"migration evidence foundation missing: {path.relative_to(ROOT)}")

    registry = load(REGISTRY)
    contract = load(REGISTRY_CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "registry contract authority missing")
    records = registry.get("records")
    require(isinstance(records, list), "migration evidence records missing")
    count = registry.get("rehearsalEvidenceCount")
    passing = registry.get("passingRehearsalCount")
    pe_count = registry.get("productionEquivalentRehearsalCount")
    require(isinstance(count, int) and count == len(records), "rehearsal count drift")
    require(isinstance(passing, int) and 0 <= passing <= count, "passing count drift")
    require(isinstance(pe_count, int) and 0 <= pe_count <= count, "production-equivalent count drift")
    current["rehearsalEvidenceCount"] = count
    current["passingRehearsalCount"] = passing
    current["productionEquivalentRehearsalCount"] = pe_count
    current["productionMigrationEvidenceCount"] = 0
    current["productionEvidence"] = False
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    for flag in (
        "registryImplemented", "writerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "operatorEvidenceRecordImplemented",
        "typedRecoveryArtifactReferenceImplemented", "localRestoreCapabilityBound",
    ):
        readiness[flag] = True
    for flag in (
        "productionEquivalentRestoreCapabilityConfigured", "actualRecoveryArtifactRestoreLinked",
        "productionShapedRehearsalCompleted", "independentReviewCompleted", "productionReady",
    ):
        readiness[flag] = False
    write(REGISTRY_CONTRACT, contract)

    lifecycle = load(LIFECYCLE)
    lifecycle_readiness = lifecycle.get("readiness")
    require(isinstance(lifecycle_readiness, dict), "migration lifecycle readiness missing")
    lifecycle_readiness["operatorEvidenceRecordImplemented"] = True
    lifecycle_readiness["productionShapedRehearsalCompleted"] = False
    lifecycle_readiness["isolatedRestoreLinked"] = False
    lifecycle_readiness["mixedVersionCompatibilityProven"] = False
    lifecycle_readiness["ready"] = False
    lifecycle_readiness["note"] = (
        "The append-only non-production operator evidence registry now requires a typed SHA-256 recovery-artifact reference and separately validated local logical-restore capability. The registry still does not restore the actual rehearsal recovery artifact, and production-shaped migration rehearsal, mixed-version deployment proof, production-equivalent restore capability and destructive-contract restore linkage remain required."
    )
    evidence_refs = lifecycle.get("evidenceRefs")
    require(isinstance(evidence_refs, list), "migration lifecycle evidenceRefs missing")
    for ref in REFS:
        append_once(evidence_refs, ref)
    write(LIFECYCLE, lifecycle)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-001"), None)
    require(isinstance(gate, dict), "OPS-P0-001 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-001 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-001 arrays missing")
    append_once(existing, EVIDENCE)
    old_values = {
        "automated recovery-point verification and append-only operator evidence record",
        "automated recovery-point verification bound to an actual isolated recovery artifact",
    }
    replacement = "restore of the actual migration rehearsal recovery artifact, bound to the target recovery point and independently verified; local restore capability proof alone is insufficient"
    next_missing: list[Any] = []
    for item in missing:
        if item in old_values:
            if replacement not in next_missing:
                next_missing.append(replacement)
        elif item not in next_missing:
            next_missing.append(item)
    if replacement not in next_missing:
        next_missing.append(replacement)
    gate["missingEvidence"] = next_missing
    for ref in REFS:
        append_once(refs, ref)
    write(STATUS, status)

    subprocess.run(["python", str(REGISTRY_VALIDATOR)], cwd=ROOT, check=True)
    subprocess.run(["python", str(LIFECYCLE_VALIDATOR)], cwd=ROOT, check=True)

    print("Memory OS migration evidence registry reconciliation PASS")
    print(f"registered rehearsals: {count}")
    print("typed recovery artifact reference: implemented")
    print("local restore capability binding: implemented")
    print("actual recovery artifact restore linkage: false")
    print("production-shaped rehearsal: false")
    print("OPS-P0-001: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION EVIDENCE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
