#!/usr/bin/env python3
"""Register the append-only migration operation evidence foundation."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/migration-operation-evidence-contract.v1.json")
LIFECYCLE_REL = Path("contracts/operations/migration-lifecycle-contract.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
OPERATION_VALIDATOR_REL = Path("scripts/validate-memory-os-migration-operation-evidence.py")
LIFECYCLE_VALIDATOR_REL = Path("scripts/validate-memory-os-migration-lifecycle.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/migration-operation-evidence.yml")
LIB_REL = Path("scripts/migration_operation_evidence_lib.py")
WRITER_REL = Path("scripts/create-memory-os-migration-operation-evidence.py")
CONTRACT_PATH = ROOT / CONTRACT_REL
LIFECYCLE_PATH = ROOT / LIFECYCLE_REL
STATUS_PATH = ROOT / STATUS_REL
OPERATION_VALIDATOR = ROOT / OPERATION_VALIDATOR_REL
LIFECYCLE_VALIDATOR = ROOT / LIFECYCLE_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL
LIB_PATH = ROOT / LIB_REL
WRITER_PATH = ROOT / WRITER_REL
EXPECTED_POST_WRITE_VALIDATORS = (
    OPERATION_VALIDATOR,
    LIFECYCLE_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
POST_WRITE_VALIDATORS = EXPECTED_POST_WRITE_VALIDATORS

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
STRONGER_LIFECYCLE_FIELDS = (
    "isolatedRestoreLinked",
    "mixedVersionCompatibilityProven",
    "productionShapedRehearsalCompleted",
    "ready",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    require(
        POST_WRITE_VALIDATORS == EXPECTED_POST_WRITE_VALIDATORS,
        "migration operation post-write validator chain authority drift",
    )
    for path, relative, field in (
        (CONTRACT_PATH, CONTRACT_REL, "migration operation contract"),
        (LIFECYCLE_PATH, LIFECYCLE_REL, "migration lifecycle contract"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (OPERATION_VALIDATOR, OPERATION_VALIDATOR_REL, "migration operation validator"),
        (LIFECYCLE_VALIDATOR, LIFECYCLE_VALIDATOR_REL, "migration lifecycle validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "migration operation workflow"),
        (LIB_PATH, LIB_REL, "migration operation evidence library"),
        (WRITER_PATH, WRITER_REL, "migration operation writer"),
    ):
        require_exact_repo_file(path, relative, field)


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


def atomic_replace_bytes(path: Path, payload: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def run_validator(path: Path, *, phase: str) -> None:
    enforce_runtime_authorities()
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    completed = subprocess.run(["python", str(path)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            f"{phase} migration operation authority failed validation: {path.name}")


def validate_current_authority() -> None:
    enforce_runtime_authorities()
    for validator in POST_WRITE_VALIDATORS:
        run_validator(validator, phase="current")


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
    for field in ("productionRecoveryPointVerificationImplemented", "productionReady"):
        require(isinstance(readiness.get(field), bool),
                f"migration operation readiness.{field} must be boolean")
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
    for field in STRONGER_LIFECYCLE_FIELDS:
        require(isinstance(readiness.get(field), bool),
                f"migration lifecycle readiness.{field} must be boolean")
    refs = lifecycle.get("evidenceRefs")
    require(isinstance(refs, list), "migration lifecycle evidenceRefs must be a list")
    for ref in EVIDENCE_REFS:
        if ref not in refs:
            refs.append(ref)
    lifecycle["evidenceRefs"] = unique(refs)
    note = str(readiness.get("note", ""))
    stronger_authority_present = any(readiness[field] for field in STRONGER_LIFECYCLE_FIELDS)
    if "append-only operator evidence ledger" not in note and not stronger_authority_present:
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
        atomic_replace_bytes(CONTRACT_PATH, render(contract))
        atomic_replace_bytes(LIFECYCLE_PATH, render(lifecycle))
        atomic_replace_bytes(STATUS_PATH, render(status))
        for validator in POST_WRITE_VALIDATORS:
            run_validator(validator, phase="reconciled")
    except BaseException:
        for path, payload in originals.items():
            atomic_replace_bytes(path, payload)
        raise


def main() -> int:
    enforce_runtime_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    validate_current_authority()
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
