#!/usr/bin/env python3
"""Reconcile read-only production-equivalent restore drill preflight authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
VALIDATOR_MODULE = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "scripts/validate-memory-os-backup-restore-drill-preflight.py",
    "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
    ".github/workflows/backup-restore-drill-preflight.yml",
)
EVIDENCE_PREFIX = "production-equivalent restore drill preflight is read-only and fail-closed:"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_validator_module():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_preflight_validator_for_reconcile", VALIDATOR_MODULE)
    require(spec is not None and spec.loader is not None, "cannot load restore drill preflight validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    contract = load(CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REGISTRY)
    validator = load_validator_module()
    state = validator.derive_state(generations, objectives, drill_registry)

    canonical = contract.get("currentState")
    readiness = contract.get("readiness")
    require(isinstance(canonical, dict) and isinstance(readiness, dict), "preflight authority state missing")
    for field, value in state.items():
        canonical[field] = value
    canonical["requestCreated"] = False
    canonical["backupExecuted"] = False
    canonical["restoreExecuted"] = False
    canonical["productionTrafficChanged"] = False
    canonical["productionEvidence"] = False
    canonical["productionReady"] = False
    canonical["productionDecision"] = "NO_GO"

    pair_available = state["eligibleDirectedSourceTargetPairCount"] > 0
    objective_available = state["currentObjectiveId"] is not None
    readiness["contractDefined"] = True
    readiness["validatorImplemented"] = True
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["twoDistinctUnsupersededEnvironmentGenerationsAvailable"] = pair_available
    readiness["currentRecoveryObjectiveAvailable"] = objective_available
    readiness["eligibleSourceTargetPairAvailable"] = pair_available
    readiness["reviewedDrillRequestSubmissionEligible"] = state["eligibleToSubmitReviewedDrillRequest"]
    readiness["currentExecutableDrillRequestAvailable"] = state["currentExecutableDrillRequestCount"] > 0
    readiness["drillExecuted"] = False
    readiness["productionReady"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "preflight reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-007 authority arrays missing")
    require(len(missing) == 6, "canonical OPS-P0-007 six-blocker boundary drift")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    blockers = state["blockingPrerequisites"]
    blocker_text = ",".join(blockers) if blockers else "none"
    append_once(existing, (
        f"{EVIDENCE_PREFIX} registered/unsuperseded generations={state['registeredGenerationCount']}/{state['unsupersededGenerationCount']}, distinct unsuperseded environments={state['distinctUnsupersededEnvironmentCount']}, eligible directed source-target pairs={state['eligibleDirectedSourceTargetPairCount']}, approved recovery objectives={state['approvedRecoveryObjectiveCount']}, reviewed/current drill requests={state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}, blocking prerequisites={state['blockingPrerequisiteCount']}[{blocker_text}], decision={state['preflightDecision']}; READY authorizes only external reviewed request submission, never prerequisite/request creation, backup/restore execution, production traffic or promotion"
    ))
    for ref in REFS:
        require((ROOT / ref).is_file(), f"preflight evidence ref missing: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    for phrase in ("postgresql backup", "independent object", "rpo", "cross-cluster", "non-resurrection", "independent review"):
        require(phrase in joined, f"canonical OPS-P0-007 blocker disappeared: {phrase}")
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run([sys.executable, str(VALIDATOR_MODULE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile preflight validator failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")

    print("Memory OS production-equivalent restore drill preflight reconciliation PASS")
    print(f"preflight decision: {state['preflightDecision']}")
    print(f"blocking prerequisites ({state['blockingPrerequisiteCount']}): {blocker_text}")
    print(f"eligible directed source-target pairs: {state['eligibleDirectedSourceTargetPairCount']}")
    print(f"reviewed/current drill requests: {state['reviewedDrillRequestCount']}/{state['currentExecutableDrillRequestCount']}")
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
