#!/usr/bin/env python3
"""Reconcile read-only production-equivalent restore drill preflight authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
VALIDATOR_MODULE = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "scripts/validate-memory-os-backup-restore-drill-preflight.py",
    "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py",
    "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
    ".github/workflows/backup-restore-drill-preflight.yml",
)
EVIDENCE_PREFIX = "production-equivalent restore drill preflight is read-only and fail-closed:"


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


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise Fail(f"cannot write {relative}: {exc}") from exc


def load_validator_module():
    relative = require_repo_file(VALIDATOR_MODULE, "restore drill preflight validator missing")
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_preflight_validator_for_reconcile", VALIDATOR_MODULE)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_post_reconcile_validator(path: Path, label: str) -> None:
    relative = require_repo_file(path, f"{label} validator missing")
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
        f"post-reconcile {label} validator failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}",
    )


def main() -> int:
    original_contract_text = read_text(CONTRACT)
    original_status_text = read_text(STATUS)
    contract = load(CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REGISTRY)
    status = load(STATUS)
    validator = load_validator_module()

    # Validate every upstream append-only authority before deriving or mutating
    # preflight state. Reconcile must never turn corrupt source authority into a
    # canonical-looking derived contract, even transiently before rollback.
    validator.run_validator(validator.GEN_VALIDATOR, "environment generation")
    validator.run_validator(validator.OBJECTIVE_VALIDATOR, "recovery objectives")
    validator.run_validator(validator.DRILL_VALIDATOR, "restore drill request")
    state = validator.derive_state(generations, objectives, drill_registry)

    pair_available = state["eligibleDirectedSourceTargetPairCount"] > 0
    objective_available = state["currentObjectiveId"] is not None
    canonical = {
        **state,
        "requestCreated": False,
        "backupExecuted": False,
        "restoreExecuted": False,
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    }
    readiness = {
        "contractDefined": True,
        "validatorImplemented": True,
        "reconcileImplemented": True,
        "automaticWorkflowImplemented": True,
        "twoDistinctUnsupersededPreflightEligibleEnvironmentsAvailable": pair_available,
        "currentRecoveryObjectiveAvailable": objective_available,
        "eligibleSourceTargetPairAvailable": pair_available,
        "reviewedDrillRequestSubmissionEligible": state["eligibleToSubmitReviewedDrillRequest"],
        "currentExecutableDrillRequestAvailable": state["currentExecutableDrillRequestCount"] > 0,
        "drillExecuted": False,
        "productionReady": False,
    }
    require(set(canonical) == validator.STATE_FIELDS, "reconciled preflight currentState field drift")
    require(set(readiness) == validator.READINESS_FIELDS, "reconciled preflight readiness field drift")
    contract["currentState"] = canonical
    contract["readiness"] = readiness

    require(status.get("productionDecision") == "NO_GO", "preflight reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    require_canonical_gaps(missing, Fail)
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    blockers = state["blockingPrerequisites"]
    blocker_text = ",".join(blockers) if blockers else "none"
    append_once(existing, (
        f"{EVIDENCE_PREFIX} registered/preflight-eligible generations={state['registeredGenerationCount']}/{state['preflightEligibleGenerationCount']}, unsuperseded/preflight-eligible unsuperseded generations={state['unsupersededGenerationCount']}/{state['unsupersededPreflightEligibleGenerationCount']}, distinct semantic preflight-eligible unsuperseded environments={state['distinctUnsupersededPreflightEligibleEnvironmentCount']}, eligible directed source-target pairs={state['eligibleDirectedSourceTargetPairCount']}, approved recovery objectives={state['approvedRecoveryObjectiveCount']}, reviewed/current drill requests={state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}, blocking prerequisites={state['blockingPrerequisiteCount']}[{blocker_text}], decision={state['preflightDecision']}; registered generation inventory alone never creates restore-planning authority; READY authorizes only external reviewed request submission, never prerequisite/request creation, backup/restore execution, production traffic or promotion"
    ))
    for ref in REFS:
        require_repo_file(ROOT / ref, f"preflight evidence ref missing: {ref}")
        append_once(refs, ref)

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    status_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        write_text(STATUS, status_text)
        run_post_reconcile_validator(VALIDATOR_MODULE, "preflight")
        run_post_reconcile_validator(OPERABILITY_VALIDATOR, "operability")
    except Exception:
        write_text(CONTRACT, original_contract_text)
        write_text(STATUS, original_status_text)
        raise

    print("Memory OS production-equivalent restore drill preflight reconciliation PASS")
    print(f"registered/preflight-eligible generations: {state['registeredGenerationCount']}/{state['preflightEligibleGenerationCount']}")
    print(f"unsuperseded/preflight-eligible unsuperseded generations: {state['unsupersededGenerationCount']}/{state['unsupersededPreflightEligibleGenerationCount']}")
    print(f"distinct semantic preflight-eligible unsuperseded environments: {state['distinctUnsupersededPreflightEligibleEnvironmentCount']}")
    print(f"preflight decision: {state['preflightDecision']}")
    print(f"blocking prerequisites ({state['blockingPrerequisiteCount']}): {blocker_text}")
    print(f"eligible directed source-target pairs: {state['eligibleDirectedSourceTargetPairCount']}")
    print(f"reviewed/current drill requests: {state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}")
    print("preflight authority state canonicalized: true")
    print("upstream authority validated before reconcile mutation: true")
    print("preflight and aggregate operability validated inside transaction: true")
    print("failed post-validation leaves derived preflight/status mutation behind: false")
    print("registered generation inventory alone creates restore-planning authority: false")
    print("automatic prerequisite/request creation: false")
    print("restore executed: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
