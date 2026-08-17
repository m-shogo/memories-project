#!/usr/bin/env python3
"""Register the append-only migration operation evidence foundation."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/migration-operation-evidence-contract.v1.json"
LIFECYCLE_PATH = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
POST_WRITE_VALIDATORS = (
    ROOT / "scripts/validate-memory-os-migration-operation-evidence.py",
    ROOT / "scripts/validate-memory-os-migration-lifecycle.py",
    ROOT / "scripts/validate-memory-os-operability.py",
)

EVIDENCE_REFS = (
    "contracts/operations/migration-operation-evidence-contract.v1.json",
    "scripts/migration_operation_evidence_lib.py",
    "scripts/create-memory-os-migration-operation-evidence.py",
    "scripts/validate-memory-os-migration-operation-evidence.py",
    "scripts/reconcile-memory-os-migration-operation-evidence.py",
    "docs/evidence/migration-operations/README.md",
    "docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json",
    ".github/workflows/migration-operation-evidence.yml",
)
NEW_EXISTING = (
    "append-only migration operation evidence ledger with canonical before/after migration prefixes, exact source SHA, opaque recovery-point reference and distinct operator/reviewer identities",
    "exclusive-create writer preventing overwrite of an existing migrationRunId and fail-closed validator shared by writer and CI",
    "step-result and recovery-decision consistency checks with Production confirmation separated from migration approval or readiness",
)
RECOVERY_GAPS = (
    "production recovery-point creation and automated restore usability verification before migration mutation",
    "completed production-shaped migration rehearsal with lock, statement-timeout, runtime and mixed-version budgets",
    "isolated restore linkage and promotion decision for destructive contract migrations",
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


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def normalize_contract(contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("schemaVersion") ==
            "memory-os-migration-operation-evidence.v1",
            "migration operation contract schema drift")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "migration operation readiness missing")
    for field in (
        "contractDefined", "writerImplemented", "validatorImplemented",
        "exclusiveCreateSelfTestImplemented", "canonicalSequenceBindingImplemented",
    ):
        readiness[field] = True
    readiness["productionRecoveryPointVerificationImplemented"] = False
    readiness["productionReady"] = False
    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list), "migration operation evidenceRefs must be a list")
    for ref in EVIDENCE_REFS:
        require((ROOT / ref).is_file(), f"migration operation evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
    contract["evidenceRefs"] = unique(refs)
    return contract


def normalize_lifecycle(lifecycle: dict[str, Any]) -> dict[str, Any]:
    require(lifecycle.get("schemaVersion") == "memory-os-migration-lifecycle.v1",
            "migration lifecycle schema drift")
    readiness = lifecycle.get("readiness")
    require(isinstance(readiness, dict), "migration lifecycle readiness missing")
    readiness["operatorEvidenceRecordImplemented"] = True
    readiness["isolatedRestoreLinked"] = False
    readiness["mixedVersionCompatibilityProven"] = False
    readiness["productionShapedRehearsalCompleted"] = False
    readiness["ready"] = False
    refs = lifecycle.get("evidenceRefs")
    require(isinstance(refs, list), "migration lifecycle evidenceRefs must be a list")
    for ref in EVIDENCE_REFS:
        if ref not in refs:
            refs.append(ref)
    lifecycle["evidenceRefs"] = unique(refs)
    note = str(readiness.get("note", ""))
    if "append-only operator evidence ledger" not in note:
        readiness["note"] = (
            "The canonical migration sequence, clean PostgreSQL 16 dry-run, binding lifecycle/runbook and append-only operator evidence ledger exist. "
            "Production recovery-point verification, mixed-version release proof, isolated restore linkage and production-shaped rehearsal remain required, so OPS-P0-001 stays PARTIAL."
        )
    return lifecycle


def normalize_status(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO",
            "migration evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-001"), None)
    require(isinstance(gate, dict), "OPS-P0-001 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-001 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-001 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-001 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-001 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
    missing[:] = [item for item in missing
                  if not (isinstance(item, str) and
                          "append-only operator evidence record" in item.lower())]
    for item in RECOVERY_GAPS:
        if item not in missing:
            missing.append(item)
    for ref in EVIDENCE_REFS:
        if ref not in refs:
            refs.append(ref)
    gate["existingEvidence"] = unique(existing)
    gate["missingEvidence"] = unique(missing)
    gate["evidenceRefs"] = unique(refs)

    lowered = [str(item).lower() for item in gate["missingEvidence"]]
    for label, terms in {
        "recovery point": ("recovery-point", "restore"),
        "production rehearsal": ("production-shaped", "rehearsal"),
        "mixed version": ("mixed-version",),
        "isolated restore": ("isolated", "restore"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required OPS-P0-001 gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL",
            "migration evidence changed OPS-P0-001 readiness")
    return status


def run_validator(path: Path) -> None:
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    completed = subprocess.run(["python", str(path)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            f"reconciled migration operation authority failed validation: {path.name}")


def commit_validated_triple(
    contract: dict[str, Any],
    lifecycle: dict[str, Any],
    status: dict[str, Any],
) -> None:
    originals = {
        CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
        LIFECYCLE_PATH: LIFECYCLE_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        CONTRACT_PATH.write_bytes(render(contract))
        LIFECYCLE_PATH.write_bytes(render(lifecycle))
        STATUS_PATH.write_bytes(render(status))
        for validator in POST_WRITE_VALIDATORS:
            run_validator(validator)
    except BaseException:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current_contract = load(CONTRACT_PATH)
    current_lifecycle = load(LIFECYCLE_PATH)
    current_status = load(STATUS_PATH)
    candidate_contract = normalize_contract(copy.deepcopy(current_contract))
    candidate_lifecycle = normalize_lifecycle(copy.deepcopy(current_lifecycle))
    candidate_status = normalize_status(copy.deepcopy(current_status))
    candidate_status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()

    left_status = copy.deepcopy(current_status)
    right_status = copy.deepcopy(candidate_status)
    left_status.pop("asOf", None)
    right_status.pop("asOf", None)
    changed = (
        current_contract != candidate_contract or
        current_lifecycle != candidate_lifecycle or
        left_status != right_status
    )
    if args.check:
        require(not changed, "migration operation authority is not normalized")
        print("Memory OS migration operation authority normalization check PASS")
        return 0
    if not changed:
        print("Memory OS migration operation authority already normalized")
        return 0

    commit_validated_triple(candidate_contract, candidate_lifecycle, candidate_status)
    print("Normalized migration operation contract, lifecycle and OPS-P0-001 authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"MIGRATION OPERATION EVIDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
