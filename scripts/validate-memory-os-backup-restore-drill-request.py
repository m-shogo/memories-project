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
CONTRACT_REL = Path("contracts/operations/backup-restore-drill-request-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
OBJECTIVES_REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
GEN_RECOVERY_CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
TYPED_CONTRACT_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
EXPECTED_LOCK_REL = Path("contracts/operations/.backup-restore-drill-request.lock")
NEGATIVE_REL = Path("scripts/validate-memory-os-backup-restore-drill-request-negative.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
OBJECTIVES_REGISTRY = ROOT / OBJECTIVES_REGISTRY_REL
GEN_RECOVERY_CONTRACT = ROOT / GEN_RECOVERY_CONTRACT_REL
TYPED_CONTRACT = ROOT / TYPED_CONTRACT_REL
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
WRITER = ROOT / WRITER_REL
EXPECTED_LOCK = ROOT / EXPECTED_LOCK_REL
NEGATIVE = ROOT / NEGATIVE_REL


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


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def require_canonical_lock_path(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        parent = path.parent.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} parent missing or escapes repository") from exc
    require(lexical == expected_relative, f"{field} authority drift")
    require(parent == expected_relative.parent, f"{field} parent authority drift")
    require(not path.is_symlink(), f"{field} must not be symlink")
    if path.exists():
        require(path.is_file(), f"{field} must be a file when materialized")
        try:
            resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise Fail(f"{field} materialized path escapes repository") from exc
        require(resolved == expected_relative, f"{field} materialized authority drift")
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "drill request contract"),
        (REGISTRY, REGISTRY_REL, "drill request registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (OBJECTIVES_REGISTRY, OBJECTIVES_REGISTRY_REL, "recovery objectives registry"),
        (GEN_RECOVERY_CONTRACT, GEN_RECOVERY_CONTRACT_REL, "generation recovery contract"),
        (TYPED_CONTRACT, TYPED_CONTRACT_REL, "typed non-resurrection contract"),
        (ELIGIBILITY_HELPER, ELIGIBILITY_HELPER_REL, "semantic generation eligibility helper"),
        (WRITER, WRITER_REL, "drill request writer"),
        (NEGATIVE, NEGATIVE_REL, "drill request negative validator"),
    ):
        require_exact_repo_file(path, expected, field)
    require_canonical_lock_path(EXPECTED_LOCK, EXPECTED_LOCK_REL, "drill request append lock")


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_module(path: Path, name: str):
    relative = repo_relative(path)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    return module


def run_negative() -> None:
    require_exact_repo_file(NEGATIVE, NEGATIVE_REL, "drill request negative validator")
    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"drill request negative suite failed:\n{completed.stdout[-5000:]}{completed.stderr[-5000:]}")


CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
CANONICAL_MODULE_FROM_SPEC = importlib.util.module_from_spec


def enforce_execution_transport(
    canonical_subprocess_run=CANONICAL_SUBPROCESS_RUN,
    canonical_spec_from_file_location=CANONICAL_SPEC_FROM_FILE_LOCATION,
    canonical_module_from_spec=CANONICAL_MODULE_FROM_SPEC,
) -> None:
    if subprocess.run is not canonical_subprocess_run:
        raise Fail("drill request subprocess execution transport drift")
    if importlib.util.spec_from_file_location is not canonical_spec_from_file_location:
        raise Fail("drill request import spec transport drift")
    if importlib.util.module_from_spec is not canonical_module_from_spec:
        raise Fail("drill request module loader transport drift")


CANONICAL_EXECUTION_GUARD = enforce_execution_transport


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


def main(canonical_execution_guard=CANONICAL_EXECUTION_GUARD) -> int:
    if enforce_execution_transport is not canonical_execution_guard:
        raise Fail("drill request execution guard drift")
    enforce_execution_transport()
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES_REGISTRY)
    generation_recovery = load(GEN_RECOVERY_CONTRACT)
    typed_contract = load(TYPED_CONTRACT)
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_validator")
    eligibility = load_module(ELIGIBILITY_HELPER, "memory_os_restore_generation_eligibility_validator")

    writer_authorities = (
        ("CONTRACT", "CANONICAL_CONTRACT", CONTRACT, "restore drill request contract"),
        ("REGISTRY", "CANONICAL_REGISTRY", REGISTRY, "restore drill request registry"),
        ("GEN_REGISTRY", "CANONICAL_GEN_REGISTRY", GEN_REGISTRY, "environment generation registry"),
        ("OBJECTIVES_REGISTRY", "CANONICAL_OBJECTIVES_REGISTRY", OBJECTIVES_REGISTRY, "recovery objectives registry"),
    )
    for runtime_name, canonical_name, expected_path, field in writer_authorities:
        runtime_path = getattr(writer, runtime_name, None)
        canonical_path = getattr(writer, canonical_name, None)
        require(runtime_path == expected_path, f"writer runtime authority drift: {runtime_name}")
        require(canonical_path == expected_path, f"writer canonical authority drift: {canonical_name}")
        writer.require_canonical_runtime_authority(runtime_path, canonical_path, field)
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "drill request writer append lock authority drift")
    require_canonical_lock_path(writer_lock, EXPECTED_LOCK_REL, "writer drill request append lock")
    require(writer_lock.parent == REGISTRY.parent, "drill request append lock must share registry authority directory")

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
        candidate = path if path.is_absolute() else ROOT / path
        expected = str(require_repo_file(candidate, f"contract artifact missing: {path}"))
        require(contract.get(field) == expected, f"contract ref drift: {field}")

    required_fields = contract.get("requiredRequestFields")
    required_domains = contract.get("requiredEvidenceDomains")
    required_stops = contract.get("requiredStopConditions")
    rules = contract.get("admissionRules")
    require(isinstance(required_fields, list) and len(required_fields) == len(set(required_fields)) and len(required_fields) >= 20, "required request fields incomplete")
    require(isinstance(required_domains, list) and len(required_domains) == 8 and len(required_domains) == len(set(required_domains)), "required evidence domains drift")
    require(isinstance(required_stops, list) and len(required_stops) >= 10 and len(required_stops) == len(set(required_stops)), "required stop conditions incomplete")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "admissionRules must remain fail-closed")
    require(rules.get("registeredGenerationCountIsNotSemanticEligibility") is True, "registered generation count must remain distinct from semantic eligibility")

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

    require(generation_recovery.get("typedNonResurrectionAdmissionContract") == str(repo_relative(TYPED_CONTRACT)), "generation recovery contract typed gate drift")
    typed_rules = typed_contract.get("candidateCoverageRule")
    require(isinstance(typed_rules, dict) and typed_rules.get("genericNonResurrectionPassAloneIsInsufficient") is True, "typed non-resurrection bypass guard missing")

    generation_rows = generations.get("generations")
    generation_count = generations.get("registeredGenerationCount")
    require(generations.get("appendOnly") is True and generations.get("productionEvidence") is False, "generation registry boundary drift")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation registry rows invalid")
    require(isinstance(generation_count, int) and not isinstance(generation_count, bool) and generation_count == len(generation_rows), "generation registry count drift")

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
    current_objective = objectives.get("currentObjectiveId")
    require(objectives.get("appendOnly") is True and objectives.get("productionEvidence") is False and objectives.get("productionReady") is False, "recovery objective registry boundary drift")
    require(isinstance(objective_rows, list) and all(isinstance(row, dict) for row in objective_rows), "recovery objective rows invalid")
    require(isinstance(objective_count, int) and not isinstance(objective_count, bool) and objective_count == len(objective_rows), "recovery objective count drift")
    if objective_count == 0:
        require(current_objective is None, "empty recovery objective registry cannot have currentObjectiveId")
        current_objective_available = False
    else:
        require(isinstance(current_objective, str) and sum(1 for row in objective_rows if row.get("objectiveId") == current_objective) == 1, "current recovery objective invalid")
        current_objective_available = True

    require(registry.get("schemaVersion") == "memory-os-backup-restore-drill-request-registry.v1", "request registry schema drift")
    require(registry.get("registryClass") == "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS", "request registry class drift")
    require(registry.get("appendOnly") is True, "request registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "request registry cannot promote production")
    requests = registry.get("requests")
    request_count = registry.get("registeredRequestCount")
    executable_count = registry.get("currentExecutableRequestCount")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "request registry records invalid")
    require(isinstance(request_count, int) and not isinstance(request_count, bool) and request_count == len(requests), "registeredRequestCount drift")
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
    require(isinstance(executable_count, int) and not isinstance(executable_count, bool) and executable_count == derived_executable, "currentExecutableRequestCount drift")
    if generation_count < 2 or not current_objective_available:
        require(request_count == 0 and executable_count == 0, "drill request cannot exist without two registered generations and a current approved objective")
    if eligible_pair_count == 0 or not current_objective_available:
        require(executable_count == 0, "current executable request requires semantic preflight eligibility and a current approved recovery objective")

    state = contract.get("currentAdmissionState")
    readiness = contract.get("readiness")
    require(isinstance(state, dict) and isinstance(readiness, dict), "contract authority state missing")
    state_counts = (
        "registeredEnvironmentGenerationCount",
        "preflightEligibleEnvironmentGenerationCount",
        "unsupersededPreflightEligibleEnvironmentGenerationCount",
        "distinctPreflightEligibleEnvironmentCount",
        "eligibleDirectedSourceTargetPairCount",
        "approvedRecoveryObjectiveCount",
        "registeredRequestCount",
        "currentExecutableRequestCount",
    )
    for field in state_counts:
        value = state.get(field)
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"contract {field} must be a non-boolean count")
    require(state.get("registeredEnvironmentGenerationCount") == generation_count, "contract generation count drift")
    require(state.get("preflightEligibleEnvironmentGenerationCount") == eligible_count, "contract semantic eligible count drift")
    require(state.get("unsupersededPreflightEligibleEnvironmentGenerationCount") == unsuperseded_eligible_count, "contract unsuperseded semantic eligible count drift")
    require(state.get("distinctPreflightEligibleEnvironmentCount") == distinct_eligible_environment_count, "contract distinct semantic environment count drift")
    require(state.get("eligibleDirectedSourceTargetPairCount") == eligible_pair_count, "contract eligible source-target pair count drift")
    require(state.get("approvedRecoveryObjectiveCount") == objective_count, "contract objective count drift")
    require(state.get("registeredRequestCount") == request_count, "contract request count drift")
    require(state.get("currentExecutableRequestCount") == executable_count, "contract executable request count drift")
    decision = expected_decision(generation_count, eligible_pair_count, current_objective_available, request_count, executable_count)
    require(state.get("admissionDecision") == decision, "contract admissionDecision drift")
    require(state.get("productionEvidence") is False and state.get("productionReady") is False and state.get("productionDecision") == "NO_GO", "contract production boundary drift")
    require(readiness.get("environmentGenerationAvailable") is (generation_count >= 2), "readiness registered environment generation drift")
    require(readiness.get("semanticallyEligibleDistinctEnvironmentPairAvailable") is (eligible_pair_count > 0), "readiness semantic environment pair drift")
    require(readiness.get("approvedRecoveryObjectivesAvailable") is current_objective_available, "readiness current objective drift")
    require(readiness.get("drillRequested") is (request_count > 0), "readiness drillRequested drift")
    require(readiness.get("currentExecutableRequestAvailable") is (executable_count > 0), "readiness current executable request drift")
    require(readiness.get("drillExecuted") is False and readiness.get("productionReady") is False, "planning authority cannot claim execution/production readiness")

    run_negative()
    print("Memory OS production-equivalent backup/restore drill request validation PASS")
    print("drill request validator canonical runtime authorities enforced: true")
    print("drill request execution transport substitution accepted: false")
    print("ephemeral append lock may be absent but path authority remains canonical: true")
    print(f"registered environment generations: {generation_count}")
    print(f"semantic preflight-eligible generations: {eligible_count}")
    print(f"unsuperseded semantic preflight-eligible generations: {unsuperseded_eligible_count}")
    print(f"distinct semantic preflight-eligible environments: {distinct_eligible_environment_count}")
    print(f"eligible directed source-target pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"current approved recovery objective available: {str(current_objective_available).lower()}")
    print(f"registered drill requests: {request_count}")
    print(f"currently executable requests: {executable_count}")
    print(f"admission decision: {decision}")
    print("writer canonical runtime authorities validated without evidence rows: true")
    print("writer append lock authority canonical: true")
    print("boolean registry/contract aggregate counts accepted: false")
    print("registered generation or historical objective count alone creates planning authority: false")
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
