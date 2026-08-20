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
OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
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


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
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


def load_module(path: Path, name: str):
    relative = require_repo_file(path, f"module missing: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def expected_decision(
    generation_count: int,
    eligible_pair_count: int,
    current_objective_available: bool,
    request_count: int,
    executable_count: int,
) -> str:
    if generation_count < 2 or not current_objective_available:
        return "BLOCKED_NO_REGISTERED_GENERATION_OR_APPROVED_OBJECTIVE"
    if eligible_pair_count == 0:
        return "BLOCKED_NO_SEMANTICALLY_ELIGIBLE_DISTINCT_ENVIRONMENT_PAIR"
    if executable_count > 0:
        return "ADMITTED_REQUEST_AVAILABLE"
    if request_count > 0:
        return "AWAITING_CURRENT_EXECUTABLE_DRILL_REQUEST"
    return "AWAITING_REVIEWED_DRILL_REQUEST"


def main() -> int:
    for path, message in (
        (CONTRACT, "drill request contract missing"),
        (REGISTRY, "drill request registry missing"),
        (GEN_REGISTRY, "environment generation registry missing"),
        (OBJECTIVES_REGISTRY, "recovery objectives registry missing"),
        (STATUS, "operability status missing"),
        (VALIDATOR, "drill request validator missing"),
        (OPERABILITY_VALIDATOR, "operability validator missing"),
        (WRITER, "drill request writer missing"),
        (ELIGIBILITY_HELPER, "semantic generation eligibility helper missing"),
        (OBJECTIVES_WRITER, "recovery objectives writer missing"),
    ):
        require_repo_file(path, message)

    original_contract_text = read_text(CONTRACT)
    original_registry_text = read_text(REGISTRY)
    original_status_text = read_text(STATUS)

    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    status = load(STATUS)
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_reconcile")
    eligibility = load_module(ELIGIBILITY_HELPER, "memory_os_restore_generation_eligibility_reconcile")
    objectives_writer = load_module(OBJECTIVES_WRITER, "memory_os_recovery_objectives_writer_reconcile")

    generation_rows = generations.get("generations")
    generation_count = generations.get("registeredGenerationCount")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation registry rows invalid")
    require(isinstance(generation_count, int) and not isinstance(generation_count, bool) and generation_count == len(generation_rows), "generation registry count drift")
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

    try:
        objective_rows = objectives_writer.validate_registry_for_append(objectives)
    except objectives_writer.Fail as exc:
        raise Fail(f"recovery objectives registry authority invalid: {exc}") from exc
    objective_count = objectives.get("approvedObjectiveCount")
    current_objective_id = objectives.get("currentObjectiveId")
    require(isinstance(objective_count, int) and not isinstance(objective_count, bool) and objective_count == len(objective_rows), "recovery objective count drift")
    if objective_count == 0:
        require(current_objective_id is None, "empty recovery objective registry cannot declare a current objective")
        current_objective_available = False
    else:
        require(current_objective_id == objective_rows[-1].get("objectiveId"), "currentObjectiveId must equal latest append-only recovery objective")
        current_objective_available = True

    require(registry.get("schemaVersion") == "memory-os-backup-restore-drill-request-registry.v1", "drill request registry schema drift")
    require(registry.get("registryClass") == "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS", "drill request registry class drift")
    require(registry.get("appendOnly") is True, "drill request registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "drill request registry production boundary drift")
    requests = registry.get("requests")
    registered_request_count = registry.get("registeredRequestCount")
    current_executable_count = registry.get("currentExecutableRequestCount")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "drill request registry rows invalid")
    require(
        isinstance(registered_request_count, int)
        and not isinstance(registered_request_count, bool)
        and registered_request_count == len(requests),
        "registeredRequestCount drift",
    )
    request_ids: set[str] = set()
    request_tuples: set[tuple[Any, Any, Any]] = set()
    for row in requests:
        writer.validate_request(row, require_current=False)
        request_id = row.get("requestId")
        require(isinstance(request_id, str) and request_id and request_id not in request_ids, f"duplicate requestId: {request_id}")
        request_ids.add(request_id)
        request_tuple = (
            row.get("sourceEnvironmentGenerationId"),
            row.get("restoreTargetEnvironmentGenerationId"),
            row.get("recoveryObjectivesId"),
        )
        require(request_tuple not in request_tuples, f"duplicate source/target/objective drill request tuple: {request_tuple}")
        request_tuples.add(request_tuple)
    executable_count = sum(1 for row in requests if writer.request_currently_executable(row))
    request_count = len(requests)
    require(
        isinstance(current_executable_count, int)
        and not isinstance(current_executable_count, bool)
        and current_executable_count == executable_count,
        "currentExecutableRequestCount drift",
    )
    if generation_count < 2 or objective_count == 0:
        require(request_count == 0, "request history cannot exist before prerequisite authorities")
    if eligible_pair_count == 0 or not current_objective_available:
        require(executable_count == 0, "current executable request requires semantic preflight eligibility and a current approved recovery objective")

    state = contract.get("currentAdmissionState")
    readiness = contract.get("readiness")
    require(isinstance(state, dict) and isinstance(readiness, dict), "drill request contract authority state missing")

    require(status.get("productionDecision") == "NO_GO", "drill planning cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-007 authority arrays invalid")
    require_canonical_gaps(missing, Fail)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"drill request authority artifact missing: {ref}")

    registry["registeredRequestCount"] = request_count
    registry["currentExecutableRequestCount"] = executable_count
    registry["productionEvidence"] = False
    registry["productionReady"] = False

    state["registeredEnvironmentGenerationCount"] = generation_count
    state["preflightEligibleEnvironmentGenerationCount"] = eligible_count
    state["unsupersededPreflightEligibleEnvironmentGenerationCount"] = unsuperseded_eligible_count
    state["distinctPreflightEligibleEnvironmentCount"] = distinct_eligible_environment_count
    state["eligibleDirectedSourceTargetPairCount"] = eligible_pair_count
    state["approvedRecoveryObjectiveCount"] = objective_count
    state["registeredRequestCount"] = request_count
    state["currentExecutableRequestCount"] = executable_count
    state["admissionDecision"] = expected_decision(generation_count, eligible_pair_count, current_objective_available, request_count, executable_count)
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
    readiness["approvedRecoveryObjectivesAvailable"] = current_objective_available
    readiness["drillRequested"] = request_count > 0
    readiness["currentExecutableRequestAvailable"] = executable_count > 0
    readiness["drillExecuted"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    append_once(
        existing,
        f"{EVIDENCE_PREFIX} registered environment generations={generation_count}, semantic preflight-eligible generations={eligible_count}, unsuperseded semantic preflight-eligible generations={unsuperseded_eligible_count}, distinct semantic preflight-eligible environments={distinct_eligible_environment_count}, eligible directed source-target pairs={eligible_pair_count}, approved recovery objectives={objective_count}, current approved objective available={str(current_objective_available).lower()}, admitted planning requests={request_count}, currently executable requests={executable_count}, admissionDecision={state['admissionDecision']}; admission requires two distinct unsuperseded semantically restore-preflight-eligible registered production-equivalent generations from distinct environments, the current approved objective, PITR/WAL and exact object-version policies, all eight planned evidence domains, distinct Recovery Owner/Security/Operability approvals and mandatory stop conditions; registered generation count or historical objective count alone never creates planning authority, historical requests remain auditable after supersession but become non-executable, and request admission never executes a restore or creates production evidence",
    )
    for ref in REFS:
        append_once(refs, ref)

    try:
        write_text(REGISTRY, json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
        write_text(CONTRACT, json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
        write_text(STATUS, json.dumps(status, indent=2, ensure_ascii=False) + "\n")
        completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0, f"post-reconcile drill request validator failed:\n{completed.stdout[-5000:]}{completed.stderr[-5000:]}")
        operability = subprocess.run([sys.executable, str(OPERABILITY_VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(operability.returncode == 0, f"post-reconcile operability validator failed:\n{operability.stdout[-5000:]}{operability.stderr[-5000:]}")
    except Exception:
        write_text(REGISTRY, original_registry_text)
        write_text(CONTRACT, original_contract_text)
        write_text(STATUS, original_status_text)
        raise

    print("Memory OS backup/restore drill request authority reconciliation PASS")
    print(f"registered environment generations: {generation_count}")
    print(f"semantic preflight-eligible generations: {eligible_count}")
    print(f"unsuperseded semantic preflight-eligible generations: {unsuperseded_eligible_count}")
    print(f"distinct semantic preflight-eligible environments: {distinct_eligible_environment_count}")
    print(f"eligible directed source-target pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"current approved recovery objective available: {str(current_objective_available).lower()}")
    print(f"registered planning requests: {request_count}")
    print(f"currently executable requests: {executable_count}")
    print(f"admission decision: {state['admissionDecision']}")
    print("authority paths contained inside repository: true")
    print("invalid UTF-8 authority accepted: false")
    print("failed post-validation leaves registry/contract/status mutation behind: false")
    print("boolean generation/objective aggregate counts accepted: false")
    print("corrupt drill-request aggregate authority auto-healed: false")
    print("recovery objective append-only authority validated through canonical writer: true")
    print("aggregate operability validation is inside reconciliation transaction: true")
    print("registered generation or historical objective count alone creates planning authority: false")
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
