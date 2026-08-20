#!/usr/bin/env python3
"""Reconcile explicitly approved recovery objectives without inventing values."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/recovery-objectives-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-recovery-objectives.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-recovery-objectives.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL
EVIDENCE_PREFIX = "recovery objectives approval is append-only:"
REFS = (
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/reconcile-memory-os-recovery-objectives.py",
    ".github/workflows/recovery-objectives-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    canonical_contract = CONTRACT == ROOT / CONTRACT_REL
    canonical_status = STATUS == ROOT / STATUS_REL
    require(canonical_contract is canonical_status, "recovery objective fixture boundary must replace contract and status together")
    if canonical_contract:
        require_exact_repo_file(CONTRACT, CONTRACT_REL, "recovery objective contract")
        require_exact_repo_file(REGISTRY, REGISTRY_REL, "recovery objective registry")
        require_exact_repo_file(WRITER, WRITER_REL, "recovery objective writer")
        require_exact_repo_file(VALIDATOR, VALIDATOR_REL, "recovery objective validator")
        require_exact_repo_file(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
        require_exact_repo_file(STATUS, STATUS_REL, "production operability status")


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise Fail(f"cannot write {relative}: {exc}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer():
    if CONTRACT == ROOT / CONTRACT_REL and STATUS == ROOT / STATUS_REL:
        require_exact_repo_file(WRITER, WRITER_REL, "recovery objective writer")
    else:
        require_repo_file(WRITER, "recovery objective writer missing")
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_reconcile_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective writer")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load recovery objective writer: {exc}") from exc
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_validator(path: Path, label: str) -> None:
    relative = require_repo_file(path, f"{label} missing")
    completed = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"post-reconcile {label} failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}",
    )


def main() -> int:
    enforce_runtime_authorities()
    original_contract_text = read_text(CONTRACT)
    original_status_text = read_text(STATUS)
    registry = load(REGISTRY)
    contract = load(CONTRACT)
    status = load(STATUS)
    writer = load_writer()

    # Reconciliation may update derived contract/status projections only from
    # an already-valid append-only human approval registry. Reuse the direct
    # writer validator before reading or projecting counters so schema,
    # production-boundary, duplicate/supersession, and current-pointer
    # corruption can never be normalized by reconcile.
    try:
        rows = writer.validate_registry_for_append(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ != "Fail":
            raise
        raise Fail(f"append-only recovery objective authority invalid before reconcile: {exc}") from exc

    count = registry.get("approvedObjectiveCount")
    current_id = registry.get("currentObjectiveId")
    require(isinstance(count, int) and not isinstance(count, bool) and count >= 0 and len(rows) == count, "recovery objective registry count drift")
    require(current_id == (rows[-1].get("objectiveId") if rows else None), "current objective drift")
    if count == 0:
        require(current_id is None, "empty objective registry requires null currentObjectiveId")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority missing")
    authority["approvedObjectiveCount"] = count
    authority["currentObjectiveId"] = current_id
    authority["rpoDefined"] = count > 0
    authority["rtoDefined"] = count > 0
    authority["objectDatabaseSkewDefined"] = count > 0
    authority["productionEvidence"] = False
    authority["productionReady"] = False
    authority["productionDecision"] = "NO_GO"

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True,
            "recovery objectives cannot advance OPS-P0-007 readiness")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 evidence arrays missing")
    require_canonical_gaps(missing, Fail)
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    if count == 0:
        evidence = f"{EVIDENCE_PREFIX} approval registry exists but contains 0 records, so RPO/RTO/object-database skew remain intentionally undefined and restore evidence is forbidden from inventing targets"
    else:
        evidence = f"{EVIDENCE_PREFIX} {count} reviewed objective record(s) exist and current objectiveId={current_id}; measured restore evidence must bind this exact objective and satisfy its RPO/RTO/skew targets, while objective approval itself is not production evidence"
    append_once(existing, evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"recovery objective authority ref missing: {ref}")
        append_once(refs, ref)
    require_canonical_gaps(gate.get("missingEvidence"), Fail)
    require(status.get("productionDecision") == "NO_GO", "productionDecision changed unexpectedly")

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    status_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        write_text(STATUS, status_text)
        run_validator(VALIDATOR, "recovery objective validator")
        run_validator(OPERABILITY_VALIDATOR, "aggregate operability validator")
    except Exception:
        write_text(CONTRACT, original_contract_text)
        write_text(STATUS, original_status_text)
        raise

    print("Memory OS recovery objectives reconciliation PASS")
    print(f"approved objective records: {count}")
    print(f"current objective: {current_id or 'none'}")
    print("corrupt append-only objective registry auto-healed by reconcile: false")
    print("failed post-validation leaves objective/status mutation behind: false")
    print("aggregate operability validated inside transaction: true")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES RECONCILE FAILED: {exc}")
        raise SystemExit(1)
