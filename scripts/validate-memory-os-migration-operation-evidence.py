#!/usr/bin/env python3
"""Validate the migration operation evidence contract and ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from migration_operation_evidence_lib import (
    CONTRACT_PATH,
    LIFECYCLE_PATH,
    ROOT,
    EvidenceValidationError,
    expected_filename,
    load_json,
    validate_record,
)

LEDGER = ROOT / "docs/evidence/migration-operations"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_REFS = {
    "contracts/operations/migration-operation-evidence-contract.v1.json",
    "scripts/migration_operation_evidence_lib.py",
    "scripts/create-memory-os-migration-operation-evidence.py",
    "scripts/validate-memory-os-migration-operation-evidence.py",
    "scripts/reconcile-memory-os-migration-operation-evidence.py",
    "docs/evidence/migration-operations/README.md",
    "docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json",
    ".github/workflows/migration-operation-evidence.yml",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceValidationError(message)


def main() -> int:
    contract = load_json(CONTRACT_PATH)
    lifecycle = load_json(LIFECYCLE_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-migration-operation-evidence.v1",
            "migration operation contract schemaVersion drift")
    require(contract.get("recordSchemaVersion") ==
            "memory-os-migration-operation-record.v1",
            "migration operation record schemaVersion drift")
    require(contract.get("sourceLifecycleContract") ==
            "contracts/operations/migration-lifecycle-contract.v1.json",
            "source lifecycle contract path drift")
    require(contract.get("ledgerDirectory") ==
            "docs/evidence/migration-operations",
            "ledger directory drift")
    require(contract.get("writer") ==
            "scripts/create-memory-os-migration-operation-evidence.py",
            "writer path drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-migration-operation-evidence.py",
            "validator path drift")
    require(contract.get("reconcile") ==
            "scripts/reconcile-memory-os-migration-operation-evidence.py",
            "reconcile path drift")
    require(contract.get("workflow") ==
            ".github/workflows/migration-operation-evidence.yml",
            "workflow path drift")
    require(set(contract.get("requiredFields", [])) >=
            set(lifecycle["evidenceRecord"]["requiredFields"]),
            "migration operation contract omits lifecycle evidence fields")
    guards = contract.get("appendOnlyGuards", {})
    require(guards.get("exclusiveCreateRequired") is True,
            "exclusive create guard missing")
    require(guards.get("existingMigrationRunIdCannotBeOverwritten") is True,
            "overwrite guard missing")
    require(guards.get("canonicalLedgerMustValidateBeforeAppend") is True,
            "canonical ledger pre-append validation guard missing")
    require(guards.get("canonicalLedgerMustValidateAfterAppend") is True,
            "canonical ledger post-append validation guard missing")
    require(guards.get("postAppendValidationFailureMustRemoveNewRecord") is True,
            "post-append rollback guard missing")
    require(contract.get("privacy", {}).get("containsSecretsMustBeFalse") is True,
            "containsSecrets privacy guard missing")
    require(contract.get("resultPolicy", {}).get(
            "productionRecordIsNotProductionReadinessEvidence") is True,
            "production evidence boundary missing")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "migration evidenceRefs invalid")
    require(set(refs) == EXPECTED_REFS,
            f"migration operation evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"migration evidence path missing: {ref}")

    records = []
    if LEDGER.is_dir():
        for path in sorted(LEDGER.glob("mgr_*.json")):
            record = load_json(path)
            validate_record(record)
            require(path.name == expected_filename(record),
                    f"record filename does not match migrationRunId: {path.name}")
            records.append(record)
    run_ids = [record["migrationRunId"] for record in records]
    require(len(run_ids) == len(set(run_ids)),
            "migration ledger contains duplicate migrationRunId values")

    template = load_json(
        ROOT / "docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json"
    )
    validate_record(template)

    status = load_json(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "migration ledger cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-001"), None)
    require(isinstance(gate, dict), "OPS-P0-001 missing")
    require(gate.get("status") != "READY",
            "operation ledger alone cannot make OPS-P0-001 READY")

    print("Memory OS migration operation evidence validation PASS")
    print(f"committed records: {len(records)}")
    print(f"OPS-P0-001 status: {gate.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceValidationError as exc:
        print(f"MIGRATION OPERATION EVIDENCE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
