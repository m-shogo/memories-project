#!/usr/bin/env python3
"""Validate production-equivalent backup/restore drill planning admission."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
GEN_RECOVERY_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
TYPED_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-negative.py"


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


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_writer_validator", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_negative() -> None:
    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"drill request negative suite failed:\n{completed.stdout[-5000:]}{completed.stderr[-5000:]}")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    generation_recovery = load(GEN_RECOVERY_CONTRACT)
    typed_contract = load(TYPED_CONTRACT)
    writer = load_writer()

    require(contract.get("schemaVersion") == "memory-os-backup-restore-drill-request-contract.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-backup-restore-drill-request.v1", "record schema drift")
    require(contract.get("appendOnly") is True, "request contract must remain append-only")
    path_refs = {
        "environmentGenerationRegistry": GEN_REGISTRY,
        "recoveryObjectivesRegistry": OBJECTIVES_REGISTRY,
        "requestRegistry": REGISTRY,
        "generationRecoveryContract": GEN_RECOVERY_CONTRACT,
        "typedNonResurrectionContract": TYPED_CONTRACT,
        "writer": WRITER,
        "validator": Path("scripts/validate-memory-os-backup-restore-drill-request.py"),
        "negativeAdmissionValidator": NEGATIVE,
        "reconcile": Path("scripts/reconcile-memory-os-backup-restore-drill-request.py"),
        "runbook": Path("docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md"),
        "workflow": Path(".github/workflows/backup-restore-drill-request.yml"),
    }
    for field, path in path_refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"contract ref drift: {field}")
        require((ROOT / expected).is_file(), f"contract artifact missing: {expected}")

    required_fields = contract.get("requiredRequestFields")
    required_domains = contract.get("requiredEvidenceDomains")
    required_stops = contract.get("requiredStopConditions")
    rules = contract.get("admissionRules")
    require(isinstance(required_fields, list) and len(required_fields) == len(set(required_fields)) and len(required_fields) >= 20, "required request fields incomplete")
    require(isinstance(required_domains, list) and len(required_domains) == 8 and len(required_domains) == len(set(required_domains)), "required evidence domains drift")
    require(isinstance(required_stops, list) and len(required_stops) >= 10 and len(required_stops) == len(set(required_stops)), "required stop conditions incomplete")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "admissionRules must remain fail-closed")

    environment_policy = contract.get("environmentPolicy")
    require(isinstance(environment_policy, dict), "environmentPolicy missing")
    require(environment_policy.get("class") == "PRODUCTION_EQUIVALENT_ISOLATED_RESTORE_DRILL", "environment class drift")
    require(environment_policy.get("productionTrafficAllowed") is False, "production traffic must remain forbidden")
    require(environment_policy.get("productionCredentialsAllowed") is False, "production credentials must remain forbidden")
    require(environment_policy.get("syntheticOrApprovedSanitizedDataOnly") is True, "data policy drift")
    require(environment_policy.get("automaticTrafficPromotionAllowed") is False, "automatic traffic promotion must remain forbidden")
    require(environment_policy.get("destructiveDownMigrationAllowed") is False, "destructive down migration must remain forbidden")

    execution = contract.get("executionBoundary")
    require(isinstance(execution, dict), "executionBoundary missing")
    require(execution.get("planningAuthorityOnly") is True, "request must remain planning authority only")
    require(execution.get("requestAloneMayExecuteDrill") is False, "request alone cannot execute drill")
    require(execution.get("requestMustBeRevalidatedImmediatelyBeforeExecution") is True, "execution-time revalidation required")
    for key in ("backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady"):
        require(execution.get(key) is False, f"executionBoundary must keep {key}=false")

    require(generation_recovery.get("typedNonResurrectionAdmissionContract") == str(TYPED_CONTRACT.relative_to(ROOT)), "generation recovery contract typed gate drift")
    typed_rules = typed_contract.get("candidateCoverageRule")
    require(isinstance(typed_rules, dict) and typed_rules.get("genericNonResurrectionPassAloneIsInsufficient") is True, "typed non-resurrection bypass guard missing")

    generation_rows = generations.get("generations")
    generation_count = generations.get("registeredGenerationCount")
    require(generations.get("appendOnly") is True and generations.get("productionEvidence") is False, "generation registry boundary drift")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation registry rows invalid")
    require(isinstance(generation_count, int) and generation_count == len(generation_rows), "generation registry count drift")

    objective_rows = objectives.get("records")
    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    require(objectives.get("appendOnly") is True and objectives.get("productionEvidence") is False and objectives.get("productionReady") is False, "recovery objective registry boundary drift")
    require(isinstance(objective_rows, list) and all(isinstance(row, dict) for row in objective_rows), "recovery objective rows invalid")
    require(isinstance(objective_count, int) and objective_count == len(objective_rows), "recovery objective count drift")
    if objective_count == 0:
        require(current_objective is None, "empty recovery objective registry cannot have currentObjectiveId")
    else:
        require(isinstance(current_objective, str) and sum(1 for row in objective_rows if row.get("objectiveId") == current_objective) == 1, "current recovery objective invalid")

    require(registry.get("schemaVersion") == "memory-os-backup-restore-drill-request-registry.v1", "request registry schema drift")
    require(registry.get("registryClass") == "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS", "request registry class drift")
    require(registry.get("appendOnly") is True, "request registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "request registry cannot promote production")
    requests = registry.get("requests")
    request_count = registry.get("registeredRequestCount")
    executable_count = registry.get("currentExecutableRequestCount")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "request registry records invalid")
    require(isinstance(request_count, int) and request_count == len(requests), "registeredRequestCount drift")
    request_ids: set[str] = set()
    tuples: set[tuple[Any, Any, Any]] = set()
    derived_executable = 0
    for row in requests:
        writer.validate_request(row, require_current=False)
        request_id = row.get("requestId")
        require(isinstance(request_id, str) and request_id not in request_ids, f"duplicate requestId: {request_id}")
        request_ids.add(request_id)
        key = (row.get("sourceEnvironmentGenerationId"), row.get("restoreTargetEnvironmentGenerationId"), row.get("recoveryObjectivesId"))
        require(key not in tuples, f"duplicate source/target/objective drill request tuple: {key}")
        tuples.add(key)
        if writer.request_currently_executable(row):
            derived_executable += 1
    require(isinstance(executable_count, int) and executable_count == derived_executable, "currentExecutableRequestCount drift")
    if generation_count < 2 or objective_count == 0:
        require(request_count == 0 and executable_count == 0, "drill request cannot exist without two registered generations and an approved objective")

    state = contract.get("currentAdmissionState")
    readiness = contract.get("readiness")
    require(isinstance(state, dict) and isinstance(readiness, dict), "contract authority state missing")
    require(state.get("registeredEnvironmentGenerationCount") == generation_count, "contract generation count drift")
    require(state.get("approvedRecoveryObjectiveCount") == objective_count, "contract objective count drift")
    require(state.get("registeredRequestCount") == request_count, "contract request count drift")
    require(state.get("currentExecutableRequestCount") == executable_count, "contract executable request count drift")
    if generation_count < 2 or objective_count == 0:
        expected_decision = "BLOCKED_NO_REGISTERED_GENERATION_OR_APPROVED_OBJECTIVE"
    elif executable_count > 0:
        expected_decision = "ADMITTED_REQUEST_AVAILABLE"
    elif request_count > 0:
        expected_decision = "AWAITING_CURRENT_EXECUTABLE_DRILL_REQUEST"
    else:
        expected_decision = "AWAITING_REVIEWED_DRILL_REQUEST"
    require(state.get("admissionDecision") == expected_decision, "contract admissionDecision drift")
    require(state.get("productionEvidence") is False and state.get("productionReady") is False and state.get("productionDecision") == "NO_GO", "contract production boundary drift")
    require(readiness.get("environmentGenerationAvailable") is (generation_count >= 2), "readiness environment generation drift")
    require(readiness.get("approvedRecoveryObjectivesAvailable") is (objective_count > 0), "readiness objective drift")
    require(readiness.get("drillRequested") is (request_count > 0), "readiness drillRequested drift")
    require(readiness.get("currentExecutableRequestAvailable") is (executable_count > 0), "readiness current executable request drift")
    require(readiness.get("drillExecuted") is False and readiness.get("productionReady") is False, "planning authority cannot claim execution/production readiness")

    run_negative()
    print("Memory OS production-equivalent backup/restore drill request validation PASS")
    print(f"registered environment generations: {generation_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"registered drill requests: {request_count}")
    print(f"currently executable requests: {executable_count}")
    print("historical admitted requests survive later generation/objective supersession: true")
    print("planning authority only: true")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
