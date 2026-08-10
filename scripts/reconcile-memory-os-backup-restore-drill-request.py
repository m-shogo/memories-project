#!/usr/bin/env python3
"""Reconcile production-equivalent backup/restore drill planning authority.

This script never creates a drill request and never executes backup/restore work.
It only derives current planning admission state from append-only authorities,
updates bounded counters/readiness, and records the planning foundation in the
canonical OPS-P0-007 status while preserving all six production blockers.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
EVIDENCE_PREFIX = "production-equivalent backup/restore drill request admission is planning-only and fail-closed:"
REFS = (
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-drill-request-negative.py",
    "scripts/reconcile-memory-os-backup-restore-drill-request.py",
    ".github/workflows/backup-restore-drill-request.yml",
)


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def expected_decision(
    generation_count: int,
    eligible_pair_count: int,
    objective_count: int,
    request_count: int,
    executable_count: int,
) -> str:
    if generation_count < 2 or objective_count == 0:
        return "BLOCKED_NO_REGISTERED_GENERATION_OR_APPROVED_OBJECTIVE"
    if eligible_pair_count == 0:
        return "BLOCKED_NO_SEMANTICALLY_ELIGIBLE_DISTINCT_ENVIRONMENT_PAIR"
    if executable_count > 0:
        return "ADMITTED_REQUEST_AVAILABLE"
    if request_count > 0:
        return "AWAITING_CURRENT_EXECUTABLE_DRILL_REQUEST"
    return "AWAITING_REVIEWED_DRILL_REQUEST"


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_reconcile")
    eligibility = load_module(ELIGIBILITY_HELPER, "memory_os_restore_generation_eligibility_reconcile")

    generation_rows = generations.get("generations")
    generation_count = generations.get("registeredGenerationCount")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation registry rows invalid")
    require(isinstance(generation_count, int) and generation_count == len(generation_rows), "generation registry count drift")
    require(generations.get("appendOnly") is True and generations.get("productionEvidence") is False, "generation registry boundary drift")

    semantic = eligibility.derive(GEN_REGISTRY)
    require(semantic.get("registeredGenerationCount") == generation_count, "semantic eligibility registered count drift")
    eligible_count = semantic.get("preflightEligibleGenerationCount")
    unsuperseded_eligible_count = semantic.get("unsupersededPreflightEligibleGenerationCount")
    distinct_eligible_environment_count = semantic.get("distinctPreflightEligibleEnvironmentCount")
    eligible_pair_count = semantic.get("eligibleDirectedPairCount")
    for value, field in (
        (eligible_count, "preflightEligibleGenerationCount"),
        (unsuperseded_eligible_count, "unsupersededPreflightEligibleGenerationCount"),
        (distinct_eligible_environment_count, "distinctPreflightEligibleEnvironmentCount"),
        (eligible_pair_count, "eligibleDirectedPairCount"),
    ):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"semantic eligibility {field} invalid")
    require(eligible_count <= generation_count, "semantic eligible count cannot exceed registered count")
    require(unsuperseded_eligible_count <= eligible_count, "unsuperseded semantic eligible count drift")
    require(distinct_eligible_environment_count <= unsuperseded_eligible_count, "distinct semantic environment count drift")
    if distinct_eligible_environment_count < 2:
        require(eligible_pair_count == 0, "eligible directed pair requires two distinct semantic environments")

    objective_rows = objectives.get("records")
    objective_count = objectives.get("approvedObjectiveCount")
    require(isinstance(objective_rows, list) and all(isinstance(row, dict) for row in objective_rows), "recovery objective rows invalid")
    require(isinstance(objective_count, int) and objective_count == len(objective_rows), "recovery objective count drift")
    require(objectives.get("appendOnly") is True and objectives.get("productionEvidence") is False and objectives.get("productionReady") is False, "recovery objective boundary drift")

    requests = registry.get("requests")
    require(registry.get("appendOnly") is True, "drill request registry must remain append-only")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "drill request registry rows invalid")
    for row in requests:
        writer.validate_request(row, require_current=False)
    executable_count = sum(1 for row in requests if writer.request_currently_executable(row))
    request_count = len(requests)
    if generation_count < 2 or objective_count == 0:
        require(request_count == 0, "request history cannot exist before prerequisite authorities")
    if eligible_pair_count == 0:
        require(executable_count == 0, "semantic preflight block cannot have a current executable request")

    registry["registeredRequestCount"] = request_count
    registry["currentExecutableRequestCount"] = executable_count
    registry["productionEvidence"] = False
    registry["productionReady"] = False
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    state = contract.get("currentAdmissionState")
    readiness = contract.get("readiness")
    require(isinstance(state, dict) and isinstance(readiness, dict), "drill request contract authority state missing")
    state["registeredEnvironmentGenerationCount"] = generation_count
    state["preflightEligibleEnvironmentGenerationCount"] = eligible_count
    state["unsupersededPreflightEligibleEnvironmentGenerationCount"] = unsuperseded_eligible_count
    state["distinctPreflightEligibleEnvironmentCount"] = distinct_eligible_environment_count
    state["eligibleDirectedSourceTargetPairCount"] = eligible_pair_count
    state["approvedRecoveryObjectiveCount"] = objective_count
    state["registeredRequestCount"] = request_count
    state["currentExecutableRequestCount"] = executable_count
    state["admissionDecision"] = expected_decision(
        generation_count,
        eligible_pair_count,
        objective_count,
        request_count,
        executable_count,
    )
    state["productionEvidence"] = False
    state["productionReady"] = False
    state["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["negativeAdmissionSuiteImplemented"] = True
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["runbookDefined"] = True
    readiness["environmentGenerationAvailable"] = generation_count >= 2
    readiness["semanticallyEligibleDistinctEnvironmentPairAvailable"] = eligible_pair_count > 0
    readiness["approvedRecoveryObjectivesAvailable"] = objective_count > 0
    readiness["drillRequested"] = request_count > 0
    readiness["currentExecutableRequestAvailable"] = executable_count > 0
    readiness["drillExecuted"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "drill planning cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 authority arrays invalid")
    require_canonical_gaps(missing, Fail)

    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(
        existing,
        f"{EVIDENCE_PREFIX} registered environment generations={generation_count}, semantic preflight-eligible generations={eligible_count}, unsuperseded semantic preflight-eligible generations={unsuperseded_eligible_count}, distinct semantic preflight-eligible environments={distinct_eligible_environment_count}, eligible directed source-target pairs={eligible_pair_count}, approved recovery objectives={objective_count}, admitted planning requests={request_count}, currently executable requests={executable_count}, admissionDecision={state['admissionDecision']}; admission requires two distinct unsuperseded semantically restore-preflight-eligible registered production-equivalent generations from distinct environments, the current approved objective, PITR/WAL and exact object-version policies, all eight planned evidence domains, distinct Recovery Owner/Security/Operability approvals and mandatory stop conditions; registered generation count alone never creates planning authority, historical requests remain auditable after supersession but become non-executable, and request admission never executes a restore or creates production evidence",
    )
    for ref in REFS:
        require((ROOT / ref).is_file(), f"drill request authority artifact missing: {ref}")
        append_once(refs, ref)
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile drill request validator failed:\n{completed.stdout[-5000:]}{completed.stderr[-5000:]}")

    print("Memory OS backup/restore drill request authority reconciliation PASS")
    print(f"registered environment generations: {generation_count}")
    print(f"semantic preflight-eligible generations: {eligible_count}")
    print(f"unsuperseded semantic preflight-eligible generations: {unsuperseded_eligible_count}")
    print(f"distinct semantic preflight-eligible environments: {distinct_eligible_environment_count}")
    print(f"eligible directed source-target pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"registered planning requests: {request_count}")
    print(f"currently executable requests: {executable_count}")
    print(f"admission decision: {state['admissionDecision']}")
    print("registered generation count alone creates planning authority: false")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("restore executed: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
