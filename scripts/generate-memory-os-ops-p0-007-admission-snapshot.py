#!/usr/bin/env python3
"""Generate deterministic strict admission snapshot for OPS-P0-007 Backup/Restore."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REL = Path("contracts/operations/ops-p0-007-admission-snapshot.v1.json")
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
BLOCKER_HELPER_REL = Path("scripts/memory_os_backup_restore_blockers.py")
SNAPSHOT_VALIDATOR_REL = Path("scripts/validate-memory-os-ops-p0-007-admission-snapshot.py")
RECOVERY_OBJECTIVE_VALIDATOR_REL = Path("scripts/validate-memory-os-recovery-objectives.py")
DRILL_REQUEST_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-drill-request.py")
GEN_EVIDENCE_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-evidence.py")
TYPED_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-non-resurrection-admission.py")
OBJECTIVES_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
DRILL_REQUESTS_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
GEN_EVIDENCE_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
TYPED_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
OBJECTIVE_WRITER_REL = Path("scripts/register-memory-os-recovery-objectives.py")
DRILL_REQUEST_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
GEN_EVIDENCE_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
TYPED_WRITER_REL = Path("scripts/register-memory-os-backup-restore-non-resurrection-evidence.py")
OUTPUT = ROOT / OUTPUT_REL
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
BLOCKER_HELPER = ROOT / BLOCKER_HELPER_REL
SNAPSHOT_VALIDATOR = ROOT / SNAPSHOT_VALIDATOR_REL
RECOVERY_OBJECTIVE_VALIDATOR = ROOT / RECOVERY_OBJECTIVE_VALIDATOR_REL
DRILL_REQUEST_VALIDATOR = ROOT / DRILL_REQUEST_VALIDATOR_REL
GEN_EVIDENCE_VALIDATOR = ROOT / GEN_EVIDENCE_VALIDATOR_REL
TYPED_VALIDATOR = ROOT / TYPED_VALIDATOR_REL
OBJECTIVES = ROOT / OBJECTIVES_REL
DRILL_REQUESTS = ROOT / DRILL_REQUESTS_REL
GEN_EVIDENCE = ROOT / GEN_EVIDENCE_REL
TYPED = ROOT / TYPED_REL
STATUS = ROOT / STATUS_REL
OBJECTIVE_WRITER = ROOT / OBJECTIVE_WRITER_REL
DRILL_REQUEST_WRITER = ROOT / DRILL_REQUEST_WRITER_REL
GEN_EVIDENCE_WRITER = ROOT / GEN_EVIDENCE_WRITER_REL
TYPED_WRITER = ROOT / TYPED_WRITER_REL
GEN_BLOCKER = "TWO_DISTINCT_SEMANTICALLY_ELIGIBLE_ENVIRONMENTS"
OBJECTIVE_BLOCKER = "CURRENT_APPROVED_RECOVERY_OBJECTIVE"


def require_exact_repo_file(path: Path, expected_relative: Path, label: str) -> None:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"strict snapshot authority missing or escapes repository: {label}") from exc
    if lexical != expected_relative or resolved != expected_relative or not path.is_file() or path.is_symlink():
        raise SystemExit(f"strict snapshot authority drift: {label}")


def enforce_runtime_authorities() -> None:
    for path, expected_relative, label in (
        (OUTPUT, OUTPUT_REL, "snapshot output"),
        (ELIGIBILITY_HELPER, ELIGIBILITY_HELPER_REL, "environment generation eligibility helper"),
        (BLOCKER_HELPER, BLOCKER_HELPER_REL, "backup/restore blocker helper"),
        (SNAPSHOT_VALIDATOR, SNAPSHOT_VALIDATOR_REL, "snapshot validator"),
        (RECOVERY_OBJECTIVE_VALIDATOR, RECOVERY_OBJECTIVE_VALIDATOR_REL, "recovery objective admission validator"),
        (DRILL_REQUEST_VALIDATOR, DRILL_REQUEST_VALIDATOR_REL, "reviewed drill request admission validator"),
        (GEN_EVIDENCE_VALIDATOR, GEN_EVIDENCE_VALIDATOR_REL, "generation recovery evidence admission validator"),
        (TYPED_VALIDATOR, TYPED_VALIDATOR_REL, "typed non-resurrection admission validator"),
        (OBJECTIVES, OBJECTIVES_REL, "recovery objective registry"),
        (DRILL_REQUESTS, DRILL_REQUESTS_REL, "restore drill request registry"),
        (GEN_EVIDENCE, GEN_EVIDENCE_REL, "generation recovery evidence registry"),
        (TYPED, TYPED_REL, "typed non-resurrection registry"),
        (STATUS, STATUS_REL, "production operability status"),
        (OBJECTIVE_WRITER, OBJECTIVE_WRITER_REL, "recovery objective writer"),
        (DRILL_REQUEST_WRITER, DRILL_REQUEST_WRITER_REL, "restore drill request writer"),
        (GEN_EVIDENCE_WRITER, GEN_EVIDENCE_WRITER_REL, "generation recovery evidence writer"),
        (TYPED_WRITER, TYPED_WRITER_REL, "typed non-resurrection writer"),
    ):
        require_exact_repo_file(path, expected_relative, label)


def atomic_write_text(path: Path, text: str) -> None:
    relative = path.relative_to(ROOT)
    if not path.parent.is_dir():
        raise SystemExit(f"strict snapshot authority parent missing: {relative.parent}")
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


def load(path: Path) -> dict[str, Any]:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"generated strict snapshot invalid: cannot resolve canonical authority: {path}") from exc
    if relative != resolved or not path.is_file() or path.is_symlink():
        raise SystemExit(f"generated strict snapshot invalid: authority escapes canonical repository path: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"generated strict snapshot invalid: cannot load {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"generated strict snapshot invalid: root must be object: {relative}")
    return value


def load_module(path: Path, name: str):
    enforce_runtime_authorities()
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"cannot resolve canonical authority module: {path}") from exc
    if relative != resolved or not path.is_file() or path.is_symlink():
        raise SystemExit(f"authority module escapes canonical repository path: {relative}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load authority module: {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_registry(module, registry: dict[str, Any], label: str) -> list[dict[str, Any]]:
    validator = getattr(module, "validate_registry_for_append", None)
    failure_type = getattr(module, "Fail", RuntimeError)
    if not callable(validator) or not isinstance(failure_type, type) or not issubclass(failure_type, BaseException):
        raise SystemExit(f"{label} canonical registry validator interface invalid")
    try:
        rows = validator(registry)
    except failure_type as exc:
        raise SystemExit(f"{label} canonical registry authority invalid: {exc}") from exc
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise SystemExit(f"{label} canonical registry validator returned invalid rows")
    return rows


def run_canonical_validator(path: Path, module_name: str, label: str) -> None:
    module = load_module(path, module_name)
    validator = getattr(module, "main", None)
    failure_type = getattr(module, "Fail", RuntimeError)
    if not callable(validator) or not isinstance(failure_type, type) or not issubclass(failure_type, BaseException):
        raise SystemExit(f"{label} canonical admission validator interface invalid")
    try:
        result = validator()
    except failure_type as exc:
        raise SystemExit(f"{label} canonical admission authority invalid: {exc}") from exc
    if not isinstance(result, int) or isinstance(result, bool) or result != 0:
        raise SystemExit(f"{label} canonical admission validator returned invalid result: {result}")


def run_full_admission_validators() -> None:
    enforce_runtime_authorities()
    for path, module_name, label in (
        (RECOVERY_OBJECTIVE_VALIDATOR, "memory_os_objective_admission_ops_p0_007_snapshot", "recovery objective"),
        (DRILL_REQUEST_VALIDATOR, "memory_os_drill_request_admission_ops_p0_007_snapshot", "reviewed drill request"),
        (GEN_EVIDENCE_VALIDATOR, "memory_os_generation_evidence_admission_ops_p0_007_snapshot", "generation recovery evidence"),
        (TYPED_VALIDATOR, "memory_os_typed_non_resurrection_admission_ops_p0_007_snapshot", "typed non-resurrection"),
    ):
        run_canonical_validator(path, module_name, label)


def validate_generated_snapshot() -> None:
    enforce_runtime_authorities()
    module = load_module(SNAPSHOT_VALIDATOR, "memory_os_ops_p0_007_snapshot_post_write_validator")
    validator = getattr(module, "main", None)
    failure_type = getattr(module, "Fail", RuntimeError)
    if not callable(validator) or not isinstance(failure_type, type) or not issubclass(failure_type, BaseException):
        raise SystemExit("strict snapshot validator interface invalid")
    try:
        result = validator()
    except failure_type as exc:
        raise SystemExit(f"generated strict snapshot invalid: {exc}") from exc
    if not isinstance(result, int) or isinstance(result, bool) or result != 0:
        raise SystemExit(f"generated strict snapshot validator returned invalid result: {result}")


def load_helper():
    return load_module(ELIGIBILITY_HELPER, "memory_os_generation_eligibility_ops_p0_007_snapshot")


CANONICAL_EXECUTION_HELPERS = (
    require_exact_repo_file,
    enforce_runtime_authorities,
    atomic_write_text,
    load,
    load_module,
    validate_registry,
    run_canonical_validator,
    run_full_admission_validators,
    validate_generated_snapshot,
    load_helper,
)


def enforce_execution_authority(
    canonical_helpers: tuple[Any, ...] = CANONICAL_EXECUTION_HELPERS,
    canonical_runtime_guard=enforce_runtime_authorities,
) -> None:
    if enforce_runtime_authorities is not canonical_runtime_guard:
        raise SystemExit("strict snapshot generator runtime authority guard drift")
    current_helpers = (
        require_exact_repo_file,
        enforce_runtime_authorities,
        atomic_write_text,
        load,
        load_module,
        validate_registry,
        run_canonical_validator,
        run_full_admission_validators,
        validate_generated_snapshot,
        load_helper,
    )
    if current_helpers != canonical_helpers:
        raise SystemExit("strict snapshot generator execution helper drift")
    enforce_runtime_authorities()


def main(canonical_execution_guard=enforce_execution_authority) -> int:
    if enforce_execution_authority is not canonical_execution_guard:
        raise SystemExit("strict snapshot generator execution guard drift")
    enforce_execution_authority()
    run_full_admission_validators()
    helper = load_helper()
    blocker_helper = load_module(BLOCKER_HELPER, "memory_os_backup_restore_blockers_ops_p0_007_snapshot")
    eligibility = helper.derive()
    objectives = load(OBJECTIVES)
    requests = load(DRILL_REQUESTS)
    generation_evidence = load(GEN_EVIDENCE)
    typed = load(TYPED)
    status = load(STATUS)

    objective_writer = load_module(OBJECTIVE_WRITER, "memory_os_objective_writer_ops_p0_007_snapshot")
    request_writer = load_module(DRILL_REQUEST_WRITER, "memory_os_drill_request_writer_ops_p0_007_snapshot")
    generation_writer = load_module(GEN_EVIDENCE_WRITER, "memory_os_generation_evidence_writer_ops_p0_007_snapshot")
    typed_writer = load_module(TYPED_WRITER, "memory_os_typed_non_resurrection_writer_ops_p0_007_snapshot")
    validate_registry(objective_writer, objectives, "recovery objective")
    validate_registry(request_writer, requests, "restore drill request")
    validate_registry(generation_writer, generation_evidence, "generation recovery evidence")
    validate_registry(typed_writer, typed, "typed non-resurrection")

    objective_count = objectives.get("approvedObjectiveCount")
    current_objective = objectives.get("currentObjectiveId")
    request_count = requests.get("registeredRequestCount")
    current_request_count = requests.get("currentExecutableRequestCount")
    generation_evidence_count = generation_evidence.get("registeredEvidenceCount")
    drill_bound_count = generation_evidence.get("drillRequestBoundEvidenceCount")
    candidate_count = generation_evidence.get("productionEquivalentRecoveryCandidateCount")
    typed_complete = typed.get("completeRecordCount")
    numeric = {
        "approvedRecoveryObjectiveCount": objective_count,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "generationRecoveryEvidenceCount": generation_evidence_count,
        "drillRequestBoundGenerationRecoveryEvidenceCount": drill_bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
    }
    for field, value in numeric.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SystemExit(f"{field} invalid")
    if drill_bound_count != generation_evidence_count:
        raise SystemExit("unbound generation recovery evidence exists")
    if current_request_count > request_count:
        raise SystemExit("current drill request count exceeds history")
    if candidate_count > generation_evidence_count:
        raise SystemExit("candidate count exceeds generation evidence")

    ops7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    if not isinstance(ops7, dict):
        raise SystemExit("OPS-P0-007 status missing")
    missing = ops7.get("missingEvidence")
    require_canonical_gaps = getattr(blocker_helper, "require_canonical_gaps", None)
    canonical_gaps = getattr(blocker_helper, "CANONICAL_GAPS", None)
    if not callable(require_canonical_gaps) or not isinstance(canonical_gaps, tuple) or len(canonical_gaps) != 6:
        raise SystemExit("canonical OPS-P0-007 blocker authority invalid")
    try:
        require_canonical_gaps(missing, RuntimeError)
    except RuntimeError as exc:
        raise SystemExit(f"canonical OPS-P0-007 blocker authority invalid: {exc}") from exc
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("production decision must remain NO_GO")

    strict_blockers: list[str] = []
    if eligibility["eligibleDirectedPairCount"] == 0:
        strict_blockers.append(GEN_BLOCKER)
    objective_available = objective_count > 0 and isinstance(current_objective, str) and bool(current_objective)
    if not objective_available:
        strict_blockers.append(OBJECTIVE_BLOCKER)

    if strict_blockers:
        stage = "PREREQUISITES_BLOCKED"
        next_action = "produce and independently review two distinct semantically eligible non-production environment generations; independently approve explicit recovery objectives without AI-selected defaults"
    elif current_request_count == 0:
        stage = "READY_FOR_REVIEWED_DRILL_REQUEST"
        next_action = "submit one external planning-only restore drill request for human review using an eligible directed generation pair and the current approved objective"
    elif generation_evidence_count == 0:
        stage = "READY_FOR_ISOLATED_RESTORE_EVIDENCE"
        next_action = "immediately revalidate the current reviewed drill request before isolated execution, then register exact request-bound generation recovery evidence"
    elif typed_complete == 0 or candidate_count == 0:
        stage = "READY_FOR_TYPED_NON_RESURRECTION_EVIDENCE"
        next_action = "bind all eight typed non-resurrection domains with independent security and operability review before any final recovery candidate"
    else:
        stage = "RECOVERY_CANDIDATE_AVAILABLE_PRODUCTION_STILL_NO_GO"
        next_action = "retain NO_GO until the canonical six production backup/restore blockers are genuinely closed and a separate human production promotion decision is made"

    document = {
        "schemaVersion": "memory-os-ops-p0-007-admission-snapshot.v1",
        "deterministic": True,
        "areaId": "OPS-P0-007",
        "stage": stage,
        "strictPrerequisiteBlockers": strict_blockers,
        "strictPrerequisiteBlockerCount": len(strict_blockers),
        "registeredEnvironmentGenerationCount": eligibility["registeredGenerationCount"],
        "preflightEligibleGenerationCount": eligibility["preflightEligibleGenerationCount"],
        "unsupersededPreflightEligibleGenerationCount": eligibility["unsupersededPreflightEligibleGenerationCount"],
        "distinctPreflightEligibleEnvironmentCount": eligibility["distinctPreflightEligibleEnvironmentCount"],
        "eligibleDirectedRestorePairCount": eligibility["eligibleDirectedPairCount"],
        "approvedRecoveryObjectiveCount": objective_count,
        "currentRecoveryObjectiveId": current_objective,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_request_count,
        "generationRecoveryEvidenceCount": generation_evidence_count,
        "drillRequestBoundGenerationRecoveryEvidenceCount": drill_bound_count,
        "completeTypedNonResurrectionRecordCount": typed_complete,
        "finalProductionEquivalentRecoveryCandidateCount": candidate_count,
        "canonicalMissingEvidenceCount": len(canonical_gaps),
        "downstreamRequirements": [
            "submit one externally reviewed planning-only restore drill request bound to an eligible source/target generation pair and the current approved recovery objective",
            "revalidate the drill request immediately before any isolated restore execution",
            "admit request-bound generation recovery evidence with exact backup/manifest/restore hashes and measured approved objectives",
            "bind all eight typed non-resurrection domains with independent security and operability review",
            "retain the canonical six production backup/restore blockers until genuine production-shaped evidence closes them",
            "make any production promotion as a separate human decision",
        ],
        "nextAction": next_action,
        "requestCreated": False,
        "restoreExecuted": False,
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    }
    enforce_execution_authority()
    previous = OUTPUT.read_bytes()
    output_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(OUTPUT, output_text)
        validate_generated_snapshot()
    except (Exception, SystemExit):
        atomic_write_text(OUTPUT, previous.decode("utf-8"))
        raise
    print("Memory OS OPS-P0-007 strict admission snapshot generated")
    print(f"stage: {stage}")
    print(f"strict prerequisite blockers: {len(strict_blockers)}")
    print(f"eligible directed restore pairs: {eligibility['eligibleDirectedPairCount']}")
    print(f"canonical blockers: {len(canonical_gaps)}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
