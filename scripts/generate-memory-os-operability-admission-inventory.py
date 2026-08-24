#!/usr/bin/env python3
"""Generate a deterministic inventory of P0 admission authorities and admitted evidence."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
INVENTORY_VALIDATOR = ROOT / "scripts" / "validate-memory-os-operability-admission-inventory.py"


def require_generator_authority_identity() -> None:
    authorities = (
        (OUTPUT, Path("contracts/operations/operability-admission-inventory.v1.json"), "operability inventory output"),
        (STATUS, Path("contracts/operations/production-operability-status.json"), "production operability status"),
        (INVENTORY_VALIDATOR, Path("scripts/validate-memory-os-operability-admission-inventory.py"), "operability inventory validator"),
    )
    root = ROOT.resolve()
    for path, expected, label in authorities:
        try:
            lexical = path.relative_to(ROOT)
            resolved = path.resolve(strict=True).relative_to(root)
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise SystemExit(f"canonical {label} missing or escapes repository") from exc
        if lexical != expected or resolved != expected or not path.is_file():
            raise SystemExit(f"canonical {label} path drift: {lexical}")


def atomic_write_text(path: Path, text: str) -> None:
    relative = path.relative_to(ROOT)
    if not path.parent.is_dir():
        raise SystemExit(f"authority parent missing: {relative.parent}")
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise SystemExit(f"cannot atomically write {relative}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {relative}")
    return value


def exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def exact_success(result: Any, label: str) -> None:
    if not isinstance(result, int) or isinstance(result, bool) or result != 0:
        raise SystemExit(f"{label} invalid: validator exit {result}")


def canonical_registry_validator(script_name: str, module_name: str):
    path = ROOT / "scripts" / script_name
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"canonical registry validator missing or escapes repository: {script_name}") from exc
    if resolved != Path("scripts") / script_name or not path.is_file():
        raise SystemExit(f"canonical registry validator path drift: {script_name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load canonical registry validator: {script_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_registry_for_append", None)
    if not callable(validator):
        raise SystemExit(f"canonical registry validator missing validate_registry_for_append: {script_name}")
    return validator


def require_canonical_registry(script_name: str, module_name: str, registry: dict[str, Any], label: str) -> None:
    validator = canonical_registry_validator(script_name, module_name)
    try:
        validator(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise SystemExit(f"{label} invalid: {exc}") from exc
        raise


def canonical_human_tabletop_count() -> int:
    script_name = "validate-memory-os-incident-human-tabletops.py"
    path = ROOT / "scripts" / script_name
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"canonical human tabletop validator missing or escapes repository: {script_name}") from exc
    if resolved != Path("scripts") / script_name or not path.is_file():
        raise SystemExit(f"canonical human tabletop validator path drift: {script_name}")
    spec = importlib.util.spec_from_file_location("memory_os_human_tabletop_inventory_generator_authority", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load canonical human tabletop validator: {script_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_ledger", None)
    if not callable(validator):
        raise SystemExit(f"canonical human tabletop validator missing validate_ledger: {script_name}")
    try:
        scenarios = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise SystemExit(f"human incident tabletop ledger invalid: {exc}") from exc
        raise
    if not isinstance(scenarios, set) or not all(isinstance(scenario, str) for scenario in scenarios):
        raise SystemExit("canonical human tabletop validator result invalid")
    return len(scenarios)


def require_canonical_load_authority() -> None:
    script_name = "validate-memory-os-load.py"
    path = ROOT / "scripts" / script_name
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"canonical load validator missing or escapes repository: {script_name}") from exc
    if resolved != Path("scripts") / script_name or not path.is_file():
        raise SystemExit(f"canonical load validator path drift: {script_name}")
    spec = importlib.util.spec_from_file_location("memory_os_load_inventory_generator_authority", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load canonical load validator: {script_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "main", None)
    if not callable(validator):
        raise SystemExit(f"canonical load validator missing main: {script_name}")
    result = validator()
    exact_success(result, "canonical load authority")


def require_canonical_command_authority(script_name: str, module_name: str, label: str) -> None:
    path = ROOT / "scripts" / script_name
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"canonical command validator missing or escapes repository: {script_name}") from exc
    if resolved != Path("scripts") / script_name or not path.is_file():
        raise SystemExit(f"canonical command validator path drift: {script_name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load canonical command validator: {script_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "main", None)
    if not callable(validator):
        raise SystemExit(f"canonical command validator missing main: {script_name}")
    try:
        result = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise SystemExit(f"{label} invalid: {exc}") from exc
        raise
    exact_success(result, label)


def validate_generated_inventory() -> None:
    try:
        resolved = INVENTORY_VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit("canonical inventory validator missing or escapes repository") from exc
    expected = Path("scripts") / INVENTORY_VALIDATOR.name
    if resolved != expected or not INVENTORY_VALIDATOR.is_file():
        raise SystemExit("canonical inventory validator path drift")
    spec = importlib.util.spec_from_file_location(
        "memory_os_operability_inventory_generator_postwrite_validator",
        INVENTORY_VALIDATOR,
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load canonical inventory validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "main", None)
    if not callable(validator):
        raise SystemExit("canonical inventory validator missing main")
    try:
        result = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ in {"Fail", "Failure", "RegistrationFailure"}:
            raise SystemExit(f"generated inventory invalid: {exc}") from exc
        raise
    exact_success(result, "generated inventory")


def p0_status(status: dict[str, Any], area_id: str) -> dict[str, Any]:
    rows = status.get("areas")
    if not isinstance(rows, list):
        raise SystemExit("operability status areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == area_id]
    if len(matches) != 1:
        raise SystemExit(f"status area missing/duplicate: {area_id}")
    return matches[0]


def main() -> int:
    require_generator_authority_identity()
    status = load("contracts/operations/production-operability-status.json")
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("inventory generation refuses productionDecision != NO_GO")

    migration = load("contracts/operations/migration-production-shaped-admission-registry.v1.json")
    incident_contact = load("contracts/operations/incident-contact-routing-admission-registry.v1.json")
    observability = load("contracts/operations/observability-stack-deployment-registry.v1.json")
    rate_runtime = load("contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json")
    load_contract = load("contracts/operations/load-test-scenario-contract.v1.json")
    soak_review = load("contracts/operations/sustained-soak-independent-review-registry.v1.json")
    generations = load("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    recovery_objectives = load("contracts/operations/recovery-objectives-registry.v1.json")
    backup_binding = load("contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    backup_non_resurrection_contract = load("contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
    backup_non_resurrection = load("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
    backup_drill_request_contract = load("contracts/operations/backup-restore-drill-request-contract.v1.json")
    backup_drill_requests = load("contracts/operations/backup-restore-drill-request-registry.v1.json")
    backup_drill_preflight = load("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
    backup_promotion_reviews = load("contracts/operations/backup-restore-promotion-review-registry.v1.json")
    releases = load("contracts/operations/release-baseline-registry.v1.json")
    release_pairs = load("contracts/operations/release-compatibility-pair-registry.v1.json")
    clients = load("contracts/operations/client-baseline-registry.v1.json")
    parsers = load("contracts/operations/parser-artifact-registry.v1.json")
    failure_drills = load("contracts/operations/production-shaped-failure-drill-registry.v1.json")

    require_canonical_registry(
        "register-memory-os-production-equivalent-environment-generation.py",
        "memory_os_environment_generation_inventory_generator_authority",
        generations,
        "environment generation registry",
    )
    require_canonical_registry(
        "register-memory-os-recovery-objectives.py",
        "memory_os_recovery_objective_inventory_generator_authority",
        recovery_objectives,
        "recovery objective registry",
    )
    require_canonical_registry(
        "request-memory-os-backup-restore-drill.py",
        "memory_os_drill_request_inventory_generator_authority",
        backup_drill_requests,
        "drill request registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-generation-evidence.py",
        "memory_os_generation_evidence_inventory_generator_authority",
        backup_recovery,
        "generation recovery evidence registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-non-resurrection-evidence.py",
        "memory_os_typed_non_resurrection_inventory_generator_authority",
        backup_non_resurrection,
        "typed non-resurrection registry",
    )
    require_canonical_registry(
        "register-memory-os-backup-restore-promotion-review.py",
        "memory_os_promotion_review_inventory_generator_authority",
        backup_promotion_reviews,
        "human promotion review registry",
    )
    require_canonical_registry(
        "register-memory-os-migration-production-shaped-admission.py",
        "memory_os_migration_production_inventory_generator_authority",
        migration,
        "migration production-shaped admission registry",
    )
    require_canonical_registry(
        "register-memory-os-incident-contact-routing.py",
        "memory_os_incident_contact_inventory_generator_authority",
        incident_contact,
        "incident contact routing registry",
    )
    require_canonical_registry(
        "register-memory-os-observability-stack-deployment.py",
        "memory_os_observability_stack_inventory_generator_authority",
        observability,
        "observability stack deployment registry",
    )
    require_canonical_registry(
        "validate-memory-os-rate-limit-distributed-runtime.py",
        "memory_os_rate_runtime_inventory_generator_authority",
        rate_runtime,
        "rate-limit distributed runtime registry",
    )
    require_canonical_registry(
        "register-memory-os-sustained-soak-independent-review.py",
        "memory_os_sustained_soak_inventory_generator_authority",
        soak_review,
        "sustained-soak independent review registry",
    )
    require_canonical_registry(
        "register-memory-os-release-baseline.py",
        "memory_os_release_baseline_inventory_generator_authority",
        releases,
        "release baseline registry",
    )
    require_canonical_registry(
        "register-memory-os-release-compatibility-pair.py",
        "memory_os_release_pair_inventory_generator_authority",
        release_pairs,
        "release compatibility pair registry",
    )
    require_canonical_registry(
        "register-memory-os-client-baseline.py",
        "memory_os_client_baseline_inventory_generator_authority",
        clients,
        "client baseline registry",
    )
    require_canonical_registry(
        "register-memory-os-parser-artifact.py",
        "memory_os_parser_artifact_inventory_generator_authority",
        parsers,
        "parser artifact registry",
    )
    require_canonical_registry(
        "register-memory-os-production-shaped-failure-drill.py",
        "memory_os_failure_drill_inventory_generator_authority",
        failure_drills,
        "production-shaped failure drill registry",
    )

    human_tabletop_count = canonical_human_tabletop_count()
    require_canonical_load_authority()
    for script_name, module_name, label in (
        (
            "validate-memory-os-backup-restore-generation-binding.py",
            "memory_os_backup_generation_binding_inventory_generator_authority",
            "backup/restore generation binding authority",
        ),
        (
            "validate-memory-os-recovery-objectives.py",
            "memory_os_recovery_objectives_inventory_generator_authority",
            "backup/restore recovery objective admission authority",
        ),
        (
            "validate-memory-os-backup-restore-drill-request.py",
            "memory_os_backup_drill_request_inventory_generator_authority",
            "backup/restore drill request derived authority",
        ),
        (
            "validate-memory-os-backup-restore-drill-preflight.py",
            "memory_os_backup_drill_preflight_inventory_generator_authority",
            "backup/restore drill preflight authority",
        ),
        (
            "validate-memory-os-backup-restore-generation-evidence.py",
            "memory_os_backup_generation_evidence_inventory_generator_authority",
            "backup/restore generation recovery evidence admission authority",
        ),
        (
            "validate-memory-os-backup-restore-non-resurrection-admission.py",
            "memory_os_backup_non_resurrection_inventory_generator_authority",
            "backup/restore typed non-resurrection authority",
        ),
        (
            "validate-memory-os-backup-restore-promotion-review.py",
            "memory_os_backup_promotion_review_inventory_generator_authority",
            "backup/restore human promotion review authority",
        ),
    ):
        require_canonical_command_authority(script_name, module_name, label)
    load_ready = load_contract.get("readiness")
    if not isinstance(load_ready, dict):
        raise SystemExit("load readiness missing")
    backup_boundary = backup_binding.get("currentBoundary")
    if not isinstance(backup_boundary, dict):
        raise SystemExit("backup generation boundary missing")
    non_resurrection_boundary = backup_non_resurrection_contract.get("currentBoundary")
    if not isinstance(non_resurrection_boundary, dict):
        raise SystemExit("backup typed non-resurrection boundary missing")
    drill_request_state = backup_drill_request_contract.get("currentAdmissionState")
    if not isinstance(drill_request_state, dict):
        raise SystemExit("backup drill request admission state missing")
    preflight_state = backup_drill_preflight.get("currentState")
    if not isinstance(preflight_state, dict):
        raise SystemExit("backup drill preflight state missing")

    promotion_rows = backup_promotion_reviews.get("records")
    promotion_count = backup_promotion_reviews.get("registeredReviewCount")
    if backup_promotion_reviews.get("schemaVersion") != "memory-os-backup-restore-promotion-review-registry.v1":
        raise SystemExit("backup promotion review registry schema drift")
    if backup_promotion_reviews.get("appendOnly") is not True:
        raise SystemExit("backup promotion review registry must remain append-only")
    if any(backup_promotion_reviews.get(field) is not False for field in ("productionTrafficChanged", "productionEvidence", "productionReady")):
        raise SystemExit("backup promotion review registry cannot promote production")
    if not isinstance(promotion_rows, list) or not all(isinstance(row, dict) for row in promotion_rows):
        raise SystemExit("backup promotion review registry rows invalid")
    if not valid_count(promotion_count) or promotion_count != len(promotion_rows):
        raise SystemExit("backup promotion review registry count drift")
    current_promotion_decision_id = backup_promotion_reviews.get("currentDecisionId")
    if current_promotion_decision_id is not None:
        current_matches = [row for row in promotion_rows if row.get("decisionId") == current_promotion_decision_id]
        if len(current_matches) != 1:
            raise SystemExit("backup promotion review currentDecisionId authority drift")

    generation_count = generations.get("registeredGenerationCount")
    objective_count = recovery_objectives.get("approvedObjectiveCount")
    release_pair_count = release_pairs.get("approvedPairCount")
    if not valid_count(generation_count):
        raise SystemExit("registered environment generation count invalid")
    if not valid_count(objective_count):
        raise SystemExit("approved recovery objective count invalid")
    if not valid_count(release_pair_count):
        raise SystemExit("approved release pair count invalid")
    soak_approved_criteria_count = soak_review.get("approvedLeakStabilityCriteriaCount")
    soak_passing_review_count = soak_review.get("passingIndependentReviewCount")
    soak_leak_proof = soak_review.get("leakProof")
    typed_record_count = backup_non_resurrection.get("registeredRecordCount")
    typed_complete_count = backup_non_resurrection.get("completeRecordCount")
    typed_covered_count = backup_non_resurrection.get("candidateCoveredCount")
    pending_typed_count = non_resurrection_boundary.get("preOverlayEligiblePendingTypedCoverageCount")
    drill_request_count = backup_drill_requests.get("registeredRequestCount")
    executable_drill_request_count = backup_drill_requests.get("currentExecutableRequestCount")
    generation_evidence_count = backup_recovery.get("registeredEvidenceCount")
    drill_bound_generation_evidence_count = backup_recovery.get("drillRequestBoundEvidenceCount")
    final_recovery_candidate_count = backup_recovery.get("productionEquivalentRecoveryCandidateCount")
    generation_bound_backup_count = backup_boundary.get("generationBoundBackupCount")
    generation_bound_restore_count = backup_boundary.get("generationBoundRestoreCount")
    preflight_eligible_generation_count = preflight_state.get("preflightEligibleGenerationCount")
    unsuperseded_generation_count = preflight_state.get("unsupersededGenerationCount")
    unsuperseded_preflight_eligible_generation_count = preflight_state.get("unsupersededPreflightEligibleGenerationCount")
    distinct_unsuperseded_preflight_eligible_environment_count = preflight_state.get("distinctUnsupersededPreflightEligibleEnvironmentCount")
    eligible_pair_count = preflight_state.get("eligibleDirectedSourceTargetPairCount")
    preflight_eligible = preflight_state.get("eligibleToSubmitReviewedDrillRequest")
    preflight_decision = preflight_state.get("preflightDecision")
    independent_evidence_review_completed = backup_boundary.get("independentReviewCompleted")
    human_promotion_review_completed = current_promotion_decision_id is not None
    human_promotion_authorized = False

    for value, field in (
        (soak_approved_criteria_count, "approved leak/stability criteria"),
        (soak_passing_review_count, "passing independent sustained-soak review"),
        (typed_record_count, "typed non-resurrection record"),
        (typed_complete_count, "complete typed non-resurrection"),
        (typed_covered_count, "typed candidate coverage"),
        (pending_typed_count, "pending typed coverage"),
        (drill_request_count, "backup/restore drill request"),
        (executable_drill_request_count, "current executable backup/restore drill request"),
        (generation_evidence_count, "generation recovery evidence"),
        (drill_bound_generation_evidence_count, "drill-request-bound generation recovery evidence"),
        (final_recovery_candidate_count, "final production-equivalent recovery candidate"),
        (generation_bound_backup_count, "generation-bound backup"),
        (generation_bound_restore_count, "generation-bound restore"),
        (preflight_eligible_generation_count, "preflight-eligible environment generation"),
        (unsuperseded_generation_count, "unsuperseded environment generation"),
        (unsuperseded_preflight_eligible_generation_count, "unsuperseded preflight-eligible environment generation"),
        (distinct_unsuperseded_preflight_eligible_environment_count, "distinct unsuperseded preflight-eligible environment"),
        (eligible_pair_count, "eligible restore drill source-target pair"),
    ):
        if not valid_count(value):
            raise SystemExit(f"{field} count invalid")
    for value, field in (
        (soak_leak_proof, "sustained-soak leak proof"),
        (independent_evidence_review_completed, "independent evidence review completed"),
        (human_promotion_review_completed, "human production-promotion review completed"),
        (human_promotion_authorized, "human production-promotion authorized"),
    ):
        if not isinstance(value, bool):
            raise SystemExit(f"{field} invalid")
    if soak_leak_proof and soak_passing_review_count == 0:
        raise SystemExit("sustained-soak leak proof cannot exist without a passing independent review")
    if soak_passing_review_count > soak_approved_criteria_count:
        raise SystemExit("passing sustained-soak review count exceeds approved criteria authority")
    if human_promotion_authorized and not human_promotion_review_completed:
        raise SystemExit("production promotion cannot be authorized without completed human promotion review")
    if not isinstance(preflight_eligible, bool):
        raise SystemExit("restore drill preflight eligibility invalid")
    if not isinstance(preflight_decision, str) or not preflight_decision:
        raise SystemExit("restore drill preflight decision invalid")
    if not (typed_covered_count <= typed_complete_count <= typed_record_count):
        raise SystemExit("typed non-resurrection count ordering invalid")
    if executable_drill_request_count > drill_request_count:
        raise SystemExit("drill request executable count exceeds request history")
    if drill_bound_generation_evidence_count != generation_evidence_count:
        raise SystemExit("every generation recovery evidence row must be drill-request-bound")
    if generation_bound_restore_count > generation_bound_backup_count:
        raise SystemExit("generation-bound restore count exceeds generation-bound backup count")
    if final_recovery_candidate_count > generation_evidence_count:
        raise SystemExit("final recovery candidate count exceeds generation recovery evidence history")
    if drill_request_state.get("registeredRequestCount") != drill_request_count:
        raise SystemExit("drill request contract/registry request count drift")
    if drill_request_state.get("currentExecutableRequestCount") != executable_drill_request_count:
        raise SystemExit("drill request contract/registry executable count drift")
    if drill_request_state.get("preflightEligibleEnvironmentGenerationCount") != preflight_eligible_generation_count:
        raise SystemExit("drill request/preflight semantic generation count drift")
    if drill_request_state.get("unsupersededPreflightEligibleEnvironmentGenerationCount") != unsuperseded_preflight_eligible_generation_count:
        raise SystemExit("drill request/preflight unsuperseded semantic generation count drift")
    if drill_request_state.get("productionEvidence") is not False or drill_request_state.get("productionReady") is not False:
        raise SystemExit("drill request authority cannot promote production")
    if preflight_state.get("registeredGenerationCount") != generation_count:
        raise SystemExit("restore drill preflight generation count drift")
    if preflight_state.get("approvedRecoveryObjectiveCount") != objective_count:
        raise SystemExit("restore drill preflight objective count drift")
    if preflight_state.get("reviewedDrillRequestCount") != drill_request_count:
        raise SystemExit("restore drill preflight request count drift")
    if preflight_state.get("currentExecutableDrillRequestCount") != executable_drill_request_count:
        raise SystemExit("restore drill preflight executable request count drift")
    if any(preflight_state.get(field) is not False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")):
        raise SystemExit("restore drill preflight execution/production boundary drift")
    if preflight_state.get("productionDecision") != "NO_GO":
        raise SystemExit("restore drill preflight production decision drift")

    local_soak_complete = bool(load_ready.get("localLongSoakRunCount", 0) >= 2 and load_ready.get("localSustainedSoakEvidence") is True)
    if preflight_decision == "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS":
        backup_next_gate = "register two distinct reviewed production-equivalent environment generations that independently revalidate as unsuperseded and semantically restore-preflight eligible; then approve explicit recovery objectives before submitting any restore drill request"
    elif preflight_decision == "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE":
        backup_next_gate = "approve explicit RPO, RTO and maximum object/database skew for the current recovery objective; then submit a planning-only cross-environment restore drill request for review"
    elif preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION":
        backup_next_gate = "submit an external reviewed planning-only restore drill request bound to one eligible source/target generation pair and the current recovery objective; do not execute from preflight alone"
    elif preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST":
        backup_next_gate = "immediately revalidate the existing reviewed drill request before any isolated restore execution, then admit request-bound generation recovery evidence and all eight typed non-resurrection domains"
    else:
        raise SystemExit(f"unknown restore drill preflight decision: {preflight_decision}")

    areas: list[dict[str, Any]] = [
        {
            "id": "OPS-P0-001",
            "authority": "contracts/operations/migration-production-shaped-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/migration-production-shaped-admission-contract.v1.json",
                "contracts/operations/migration-production-shaped-admission-registry.v1.json",
                "scripts/register-memory-os-migration-production-shaped-admission.py",
                "scripts/validate-memory-os-migration-production-shaped-admission.py",
                ".github/workflows/migration-production-shaped-admission.yml",
            )),
            "admittedEvidenceCount": migration.get("admittedRehearsalCount", 0),
            "dependencyCounts": {
                "approvedReleases": releases.get("approvedReleaseCount", 0),
                "approvedReleasePairs": release_pair_count,
                "environmentGenerations": generation_count,
            },
            "nextGate": "registered production-equivalent generation plus an approved predecessor/successor release pair before production-shaped migration rehearsal admission",
        },
        {
            "id": "OPS-P0-002",
            "authority": "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
            "secondaryAuthority": "contracts/operations/incident-contact-routing-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
                "scripts/register-memory-os-incident-human-tabletop.py",
                "contracts/operations/incident-contact-routing-admission-contract.v1.json",
                "scripts/register-memory-os-incident-contact-routing.py",
            )),
            "admittedEvidenceCount": human_tabletop_count,
            "requiredEvidenceCount": 6,
            "secondaryAdmittedEvidenceCount": incident_contact.get("admittedRoutingCount", 0),
            "dependencyCounts": {"observabilityStacks": observability.get("admittedStackCount", 0)},
            "nextGate": "human-led completion of six canonical tabletop scenarios; configured contact routing additionally requires an admitted observability stack",
        },
        {
            "id": "OPS-P0-003",
            "authority": "contracts/operations/observability-stack-deployment-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/observability-stack-deployment-contract.v1.json"),
            "admittedEvidenceCount": observability.get("admittedStackCount", 0),
            "nextGate": "admit integrated structured-log backend, retention deletion, access audit and review evidence",
        },
        {
            "id": "OPS-P0-004",
            "authority": "contracts/operations/observability-stack-deployment-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/observability-stack-deployment-contract.v1.json"),
            "admittedEvidenceCount": observability.get("admittedStackCount", 0),
            "nextGate": "admit real metrics scrape/backend/dashboard/paging delivery and response evidence",
        },
        {
            "id": "OPS-P0-005",
            "authority": "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
                "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
                "scripts/register-memory-os-rate-limit-distributed-runtime.py",
            )),
            "admittedEvidenceCount": rate_runtime.get("admittedRuntimeCount", 0),
            "nextGate": "admit shared-store/trusted-proxy multi-instance runtime with restart continuity and runtime-observed emergency expiry drills",
        },
        {
            "id": "OPS-P0-006",
            "authority": "contracts/operations/load-test-scenario-contract.v1.json",
            "secondaryAuthority": "contracts/operations/sustained-soak-independent-review-registry.v1.json",
            "foundationImplemented": True,
            "admittedEvidenceCount": load_ready.get("localLongSoakRunCount", 0),
            "requiredEvidenceCount": 2,
            "approvedLeakStabilityCriteriaCount": soak_approved_criteria_count,
            "passingIndependentReviewCount": soak_passing_review_count,
            "leakProof": soak_leak_proof,
            "dependencyCounts": {
                "environmentGenerations": generation_count,
                "localSustainedSoakEvidence": local_soak_complete,
                "repeatableLocalDegradationSignalObserved": bool(load_ready.get("repeatableLocalDegradationSignalObserved")),
                "approvedLeakStabilityCriteria": soak_approved_criteria_count,
                "passingIndependentReviews": soak_passing_review_count,
            },
            "nextGate": (
                "local repeated 60-minute soak and descriptive trend review are complete; next require independent leak/stability criteria plus generation-bound production-equivalent capacity, dependency and host-failure evidence"
                if local_soak_complete
                else "complete two independent 60-minute LOCAL_LONG_SOAK results plus descriptive trend review before production-equivalent capacity/host-failure admission"
            ),
        },
        {
            "id": "OPS-P0-007",
            "authority": "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
            "secondaryAuthority": "contracts/operations/backup-restore-generation-binding-contract.v1.json",
            "tertiaryAuthority": "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
            "quaternaryAuthority": "contracts/operations/backup-restore-drill-request-contract.v1.json",
            "quinaryAuthority": "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
                "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
                "contracts/operations/recovery-objectives-admission-contract.v1.json",
                "contracts/operations/recovery-objectives-registry.v1.json",
                "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
                "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
                "contracts/operations/backup-restore-drill-request-contract.v1.json",
                "contracts/operations/backup-restore-drill-request-registry.v1.json",
                "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
                "contracts/operations/backup-restore-promotion-review-registry.v1.json",
                "docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md",
                "scripts/register-memory-os-backup-restore-generation-evidence.py",
                "scripts/validate-memory-os-backup-restore-generation-evidence.py",
                "scripts/validate-memory-os-recovery-objectives.py",
                "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
                "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
                "scripts/request-memory-os-backup-restore-drill.py",
                "scripts/validate-memory-os-backup-restore-drill-request.py",
                "scripts/reconcile-memory-os-backup-restore-drill-request.py",
                "scripts/validate-memory-os-backup-restore-drill-preflight.py",
                "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
                "scripts/register-memory-os-backup-restore-promotion-review.py",
                ".github/workflows/backup-restore-generation-evidence.yml",
                ".github/workflows/recovery-objectives-admission.yml",
                ".github/workflows/backup-restore-non-resurrection-admission.yml",
                ".github/workflows/backup-restore-drill-request.yml",
                ".github/workflows/backup-restore-drill-preflight.yml",
                ".github/workflows/backup-restore-promotion-review.yml",
            )),
            "admittedEvidenceCount": generation_bound_restore_count,
            "preflightDecision": preflight_decision,
            "preflightEligible": preflight_eligible,
            "independentEvidenceReviewCompleted": independent_evidence_review_completed,
            "humanProductionPromotionReviewCompleted": human_promotion_review_completed,
            "humanProductionPromotionAuthorized": human_promotion_authorized,
            "dependencyCounts": {
                "environmentGenerations": generation_count,
                "preflightEligibleEnvironmentGenerations": preflight_eligible_generation_count,
                "unsupersededEnvironmentGenerations": unsuperseded_generation_count,
                "unsupersededPreflightEligibleEnvironmentGenerations": unsuperseded_preflight_eligible_generation_count,
                "distinctUnsupersededPreflightEligibleEnvironments": distinct_unsuperseded_preflight_eligible_environment_count,
                "eligibleDirectedRestorePairs": eligible_pair_count,
                "approvedRecoveryObjectives": objective_count,
                "reviewedRestoreDrillRequests": drill_request_count,
                "currentExecutableRestoreDrillRequests": executable_drill_request_count,
                "generationRecoveryEvidenceRecords": generation_evidence_count,
                "drillRequestBoundGenerationEvidence": drill_bound_generation_evidence_count,
                "generationBoundBackups": generation_bound_backup_count,
                "generationBoundRestores": generation_bound_restore_count,
                "typedNonResurrectionRecords": typed_record_count,
                "completeTypedNonResurrectionRecords": typed_complete_count,
                "preOverlayEligiblePendingTypedCoverage": pending_typed_count,
                "typedCoveredRecoveryCandidates": typed_covered_count,
                "productionEquivalentRecoveryCandidates": final_recovery_candidate_count,
            },
            "nextGate": backup_next_gate,
        },
        {
            "id": "OPS-P0-008",
            "authority": "contracts/operations/release-compatibility-pair-contract.v1.json",
            "secondaryAuthority": "contracts/operations/compatibility-admission-gaps.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/release-compatibility-pair-contract.v1.json",
                "contracts/operations/release-compatibility-pair-registry.v1.json",
                "scripts/register-memory-os-release-compatibility-pair.py",
                "scripts/validate-memory-os-release-compatibility-pair.py",
                "scripts/reconcile-memory-os-release-compatibility-pair.py",
                ".github/workflows/release-compatibility-pair.yml",
            )),
            "admittedEvidenceCount": release_pair_count,
            "dependencyCounts": {
                "approvedReleases": releases.get("approvedReleaseCount", 0),
                "approvedRollbackPairs": release_pair_count,
                "approvedClients": clients.get("approvedClientBaselineCount", 0),
                "reviewedParserArtifacts": parsers.get("reviewedArtifactCount", 0),
            },
            "nextGate": "approve two release baselines and their rolling/rollback compatibility pair, then admit an immutable client baseline and reviewed retained parser artifact before production release compatibility; candidate/local execution remains separate non-release evidence",
        },
        {
            "id": "OPS-P0-009",
            "authority": "contracts/operations/production-shaped-failure-drill-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/production-shaped-failure-drill-contract.v1.json"),
            "admittedEvidenceCount": failure_drills.get("registeredDrillCount", 0),
            "requiredEvidenceCount": 4,
            "dependencyCounts": {
                "environmentGenerations": generation_count,
                "approvedReleasePairs": release_pair_count,
            },
            "nextGate": "generation-bound multi-instance, object-store, PostgreSQL failover and parser durable-spool restart drills; mixed-version failure evidence additionally requires an approved release pair",
        },
    ]

    for row in areas:
        source = p0_status(status, row["id"])
        row["status"] = source.get("status")
        row["blocking"] = source.get("blocking")
        row["missingEvidenceCount"] = len(source.get("missingEvidence", [])) if isinstance(source.get("missingEvidence"), list) else None
        row["productionEvidence"] = False
        row["productionReady"] = False

    document = {
        "schemaVersion": "memory-os-operability-admission-inventory.v1",
        "deterministic": True,
        "areas": areas,
        "productionEquivalentEnvironmentGenerationCount": generation_count,
        "approvedLeakStabilityCriteriaCount": soak_approved_criteria_count,
        "passingIndependentSustainedSoakReviewCount": soak_passing_review_count,
        "sustainedSoakLeakProof": soak_leak_proof,
        "backupRestorePreflightEligibleEnvironmentGenerationCount": preflight_eligible_generation_count,
        "backupRestoreUnsupersededEnvironmentGenerationCount": unsuperseded_generation_count,
        "backupRestoreUnsupersededPreflightEligibleEnvironmentGenerationCount": unsuperseded_preflight_eligible_generation_count,
        "backupRestoreDistinctUnsupersededPreflightEligibleEnvironmentCount": distinct_unsuperseded_preflight_eligible_environment_count,
        "backupRestoreEligibleDirectedPairCount": eligible_pair_count,
        "backupRestoreDrillPreflightEligible": preflight_eligible,
        "backupRestoreDrillPreflightDecision": preflight_decision,
        "approvedRecoveryObjectiveCount": objective_count,
        "reviewedBackupRestoreDrillRequestCount": drill_request_count,
        "currentExecutableBackupRestoreDrillRequestCount": executable_drill_request_count,
        "generationRecoveryEvidenceRecordCount": generation_evidence_count,
        "drillRequestBoundGenerationEvidenceCount": drill_bound_generation_evidence_count,
        "approvedReleaseCompatibilityPairCount": release_pair_count,
        "typedNonResurrectionRecordCount": typed_record_count,
        "completeTypedNonResurrectionRecordCount": typed_complete_count,
        "backupRestoreIndependentEvidenceReviewCompleted": independent_evidence_review_completed,
        "humanProductionPromotionReviewCompleted": human_promotion_review_completed,
        "humanProductionPromotionAuthorized": human_promotion_authorized,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "notes": [
            "foundationImplemented means the admission path exists; it does not mean runtime or production evidence exists",
            "admittedEvidenceCount is derived only from canonical append-only registries or accepted human tabletop ledger files",
            "candidate/local evidence is not counted as production admission unless its owning authority explicitly admits it",
            "local repeated soak evidence is tracked separately from human-approved leak/stability criteria, independent review, leak proof and production-shaped soak evidence",
            "recovery-objective values are never defaulted by this inventory; zero approved objectives means RPO/RTO/skew remain intentionally undefined",
            "registered production-equivalent generations are inventory only; restore planning additionally requires independent semantic preflight eligibility, unsuperseded state and a distinct-environment eligible directed pair",
            "restore drill preflight is read-only: READY authorizes only external reviewed request submission and BLOCKED never creates missing generations or recovery objectives",
            "backup/restore drill requests are planning authority only; historical requests remain auditable after supersession while current executable count requires immediate generation/objective revalidation",
            "every generation recovery evidence record must remain bound to one admitted restore drill request; an unbound record is an inventory validation failure",
            "a generic generation recovery nonResurrectionVerification PASS cannot create a final recovery candidate; complete typed coverage of all eight non-resurrection domains is independently required",
            "candidate-level independent evidence review is separate from human production-promotion review; human promotion review completion is sourced only from the append-only promotion-review registry and never authorizes production automatically",
            "candidate/local mixed-version execution remains separate from the approved release-pair registry and can never create an approved predecessor/successor pair"
        ]
    }
    output_before = OUTPUT.read_bytes() if OUTPUT.exists() else None
    output_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    atomic_write_text(OUTPUT, output_text)
    try:
        validate_generated_inventory()
    except BaseException:
        if output_before is None:
            OUTPUT.unlink(missing_ok=True)
        else:
            atomic_write_text(OUTPUT, output_before.decode("utf-8"))
        raise
    print("Memory OS operability admission inventory generated")
    print(f"P0 areas inventoried: {len(areas)}")
    print(f"production-equivalent generations: {document['productionEquivalentEnvironmentGenerationCount']}")
    print(f"approved leak/stability criteria: {soak_approved_criteria_count}")
    print(f"passing independent sustained-soak reviews: {soak_passing_review_count}")
    print(f"sustained-soak leak proof: {str(soak_leak_proof).lower()}")
    print(f"restore preflight semantic/unsuperseded-semantic generations: {preflight_eligible_generation_count}/{unsuperseded_preflight_eligible_generation_count}")
    print(f"restore preflight distinct semantic unsuperseded environments: {distinct_unsuperseded_preflight_eligible_environment_count}")
    print(f"restore preflight decision: {preflight_decision}")
    print(f"restore preflight eligible pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"reviewed backup/restore drill requests: {drill_request_count}")
    print(f"currently executable backup/restore drill requests: {executable_drill_request_count}")
    print(f"generation/drill-bound recovery evidence: {generation_evidence_count}/{drill_bound_generation_evidence_count}")
    print(f"typed non-resurrection records: {typed_record_count}")
    print(f"final recovery candidates: {final_recovery_candidate_count}")
    print(f"candidate evidence review/human promotion review/authorization: {str(independent_evidence_review_completed).lower()}/{str(human_promotion_review_completed).lower()}/{str(human_promotion_authorized).lower()}")
    print(f"approved release compatibility pairs: {release_pair_count}")
    print(f"local repeated soak complete: {str(local_soak_complete).lower()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
