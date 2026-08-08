#!/usr/bin/env python3
"""Validate deterministic P0 admission inventory against canonical registries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


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
    inventory = load(INVENTORY)
    status = load(STATUS)
    require(inventory.get("schemaVersion") == "memory-os-operability-admission-inventory.v1", "inventory schema drift")
    require(inventory.get("deterministic") is True, "inventory must remain deterministic")
    require(inventory.get("productionEvidence") is False and inventory.get("productionReady") is False, "inventory cannot promote production")
    require(inventory.get("productionDecision") == "NO_GO" and status.get("productionDecision") == "NO_GO", "production decision drift")
    rows = inventory.get("areas")
    require(isinstance(rows, list) and len(rows) == 9, "inventory must contain P0-001 through P0-009")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    require(ids == [f"OPS-P0-{number:03d}" for number in range(1, 10)], f"inventory area order/set drift: {ids}")
    status_rows = {row.get("id"): row for row in status.get("areas", []) if isinstance(row, dict)}
    inventory_rows = {row.get("id"): row for row in rows if isinstance(row, dict)}
    for row in rows:
        area_id = row["id"]
        require(row.get("productionEvidence") is False and row.get("productionReady") is False, f"{area_id} inventory cannot promote production")
        require(isinstance(row.get("foundationImplemented"), bool), f"{area_id}.foundationImplemented invalid")
        require(isinstance(row.get("admittedEvidenceCount"), int) and row["admittedEvidenceCount"] >= 0, f"{area_id}.admittedEvidenceCount invalid")
        require(isinstance(row.get("nextGate"), str) and row["nextGate"], f"{area_id}.nextGate missing")
        source = status_rows.get(area_id)
        require(isinstance(source, dict), f"status row missing: {area_id}")
        require(row.get("status") == source.get("status"), f"{area_id}.status drift")
        require(row.get("blocking") == source.get("blocking"), f"{area_id}.blocking drift")
        missing = source.get("missingEvidence")
        require(isinstance(missing, list), f"{area_id}.missingEvidence invalid")
        require(row.get("missingEvidenceCount") == len(missing), f"{area_id}.missingEvidenceCount drift")

    generations = load(ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    recovery_objectives = load(ROOT / "contracts/operations/recovery-objectives-registry.v1.json")
    backup_binding = load(ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load(ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    non_resurrection_contract = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
    non_resurrection_registry = load(ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")

    generation_count = generations.get("registeredGenerationCount")
    objective_count = recovery_objectives.get("approvedObjectiveCount")
    require(isinstance(generation_count, int) and generation_count >= 0, "environment generation count invalid")
    require(isinstance(objective_count, int) and objective_count >= 0, "recovery objective count invalid")
    require(inventory.get("productionEquivalentEnvironmentGenerationCount") == generation_count, "environment generation count drift")
    require(inventory.get("approvedRecoveryObjectiveCount") == objective_count, "approved recovery objective count drift")

    typed_record_count = non_resurrection_registry.get("registeredRecordCount")
    typed_complete_count = non_resurrection_registry.get("completeRecordCount")
    typed_covered_count = non_resurrection_registry.get("candidateCoveredCount")
    require(all(isinstance(value, int) and value >= 0 for value in (typed_record_count, typed_complete_count, typed_covered_count)), "typed non-resurrection registry counts invalid")
    require(typed_covered_count <= typed_complete_count <= typed_record_count, "typed non-resurrection registry count ordering invalid")
    require(non_resurrection_registry.get("productionEvidence") is False and non_resurrection_registry.get("productionReady") is False, "typed non-resurrection registry cannot promote production")
    require(inventory.get("typedNonResurrectionRecordCount") == typed_record_count, "inventory typed record count drift")
    require(inventory.get("completeTypedNonResurrectionRecordCount") == typed_complete_count, "inventory complete typed record count drift")

    typed_boundary = non_resurrection_contract.get("currentBoundary")
    require(isinstance(typed_boundary, dict), "typed non-resurrection currentBoundary missing")
    pending_typed = typed_boundary.get("preOverlayEligiblePendingTypedCoverageCount")
    final_candidate_count = backup_recovery.get("productionEquivalentRecoveryCandidateCount")
    require(isinstance(pending_typed, int) and pending_typed >= 0, "pending typed coverage count invalid")
    require(isinstance(final_candidate_count, int) and final_candidate_count >= 0, "final recovery candidate count invalid")
    require(typed_boundary.get("productionEquivalentRecoveryCandidateCount") == final_candidate_count, "typed boundary final candidate count drift")
    require(typed_boundary.get("candidateCoveredCount") == typed_covered_count, "typed boundary covered candidate count drift")
    require(final_candidate_count == typed_covered_count, "final recovery candidate must equal complete typed coverage of pre-overlay eligible records")
    require(typed_boundary.get("productionEvidence") is False and typed_boundary.get("productionReady") is False, "typed boundary cannot promote production")
    require(typed_boundary.get("productionDecision") == "NO_GO", "typed boundary production decision drift")

    backup_boundary = backup_binding.get("currentBoundary")
    require(isinstance(backup_boundary, dict), "backup generation boundary missing")
    backup_row = inventory_rows.get("OPS-P0-007")
    require(isinstance(backup_row, dict), "OPS-P0-007 inventory row missing")
    require(backup_row.get("authority") == "contracts/operations/backup-restore-generation-evidence-contract.v1.json", "OPS-P0-007 authority drift")
    require(backup_row.get("secondaryAuthority") == "contracts/operations/backup-restore-generation-binding-contract.v1.json", "OPS-P0-007 secondary authority drift")
    require(backup_row.get("tertiaryAuthority") == "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json", "OPS-P0-007 typed authority drift")
    require(backup_row.get("foundationImplemented") is True, "OPS-P0-007 admission foundation incomplete")
    deps = backup_row.get("dependencyCounts")
    require(isinstance(deps, dict), "OPS-P0-007 dependencyCounts missing")
    expected_dependencies = {
        "environmentGenerations": generation_count,
        "approvedRecoveryObjectives": objective_count,
        "generationBoundBackups": backup_boundary.get("generationBoundBackupCount"),
        "generationBoundRestores": backup_boundary.get("generationBoundRestoreCount"),
        "typedNonResurrectionRecords": typed_record_count,
        "completeTypedNonResurrectionRecords": typed_complete_count,
        "preOverlayEligiblePendingTypedCoverage": pending_typed,
        "typedCoveredRecoveryCandidates": typed_covered_count,
        "productionEquivalentRecoveryCandidates": final_candidate_count,
    }
    require(deps == expected_dependencies, f"OPS-P0-007 dependencyCounts drift: {deps}")
    require(backup_row.get("admittedEvidenceCount") == backup_boundary.get("generationBoundRestoreCount"), "OPS-P0-007 admitted restore count drift")
    require("all eight typed non-resurrection domains" in backup_row.get("nextGate", ""), "OPS-P0-007 nextGate must preserve typed non-resurrection requirement")

    if typed_record_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot exist without typed non-resurrection record")
    if generation_count == 0 or objective_count == 0:
        require(final_candidate_count == 0, "final recovery candidate cannot exist without generation and approved objectives")

    print("Memory OS operability admission inventory validation PASS")
    print("P0 areas: 9")
    print(f"production-equivalent generations: {generation_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"typed non-resurrection records: {typed_record_count}")
    print(f"final recovery candidates: {final_candidate_count}")
    print("generic non-resurrection PASS bypass: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY ADMISSION INVENTORY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
