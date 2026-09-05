#!/usr/bin/env python3
"""Append one reviewed production-equivalent backup/restore drill planning request."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
CONTRACT = CANONICAL_CONTRACT
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
REGISTRY = CANONICAL_REGISTRY
CANONICAL_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_REGISTRY = CANONICAL_GEN_REGISTRY
CANONICAL_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
OBJECTIVES_REGISTRY = CANONICAL_OBJECTIVES_REGISTRY
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
LOCK = ROOT / "contracts/operations/.backup-restore-drill-request.lock"
REQUEST_ID = re.compile(r"^brrq_[a-z0-9][a-z0-9_-]{7,63}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
APPROVAL_SCHEMA = "memory-os-backup-restore-drill-request-approval.v2"
APPROVAL_ROLES = {
    "recoveryOwner": "RECOVERY_OWNER",
    "securityReview": "SECURITY",
    "operabilityReview": "OPERABILITY",
}
APPROVAL_FIELDS = {
    "schemaVersion",
    "requestId",
    "requestRecordSha256",
    "reviewRole",
    "decision",
    "sourceEnvironmentGenerationId",
    "restoreTargetEnvironmentGenerationId",
    "recoveryObjectivesId",
    "approvedAt",
    "reviewerPseudonym",
    "productionTraffic",
    "productionCredentials",
    "automaticPromotion",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to its canonical repository file")
    return path


def require_canonical_runtime_authority(path: Path, canonical: Path, field: str) -> None:
    """Contain canonical runtime authority while permitting isolated test substitutions."""
    if ROOT == CANONICAL_ROOT and path == canonical:
        canonical_repo_file(path, field)


def require_cli_authorities() -> None:
    """Pin the actual append entrypoint to canonical production-planning authorities."""
    authorities = (
        (CONTRACT, CANONICAL_CONTRACT, "restore drill request contract"),
        (REGISTRY, CANONICAL_REGISTRY, "restore drill request registry"),
        (GEN_REGISTRY, CANONICAL_GEN_REGISTRY, "environment generation registry"),
        (OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry"),
        (ELIGIBILITY_HELPER, ROOT / "scripts/memory_os_environment_generation_eligibility.py", "environment generation eligibility helper"),
        (OBJECTIVES_WRITER, ROOT / "scripts/register-memory-os-recovery-objectives.py", "recovery objectives writer"),
    )
    require(ROOT == CANONICAL_ROOT, "drill request CLI repository root authority drift")
    for actual, canonical, field in authorities:
        require(actual == canonical, f"{field} must use canonical authority")
        canonical_repo_file(actual, field)
    canonical_lock = ROOT / "contracts/operations/.backup-restore-drill-request.lock"
    require(LOCK == canonical_lock, "restore drill request lock must use canonical authority")
    require(LOCK.parent == CANONICAL_REGISTRY.parent, "restore drill request lock must share canonical registry directory")


def canonical_request_sha256(record: dict[str, Any]) -> str:
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def approval_sha256(ref: str) -> str:
    try:
        payload = (ROOT / ref).read_bytes()
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"approval evidence cannot be hashed: {ref}") from exc
    return hashlib.sha256(payload).hexdigest()


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.as_posix() == value,
        f"{field} must be a canonical repository-relative path",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} path missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc


def load_eligibility_helper():
    helper = canonical_repo_file(ELIGIBILITY_HELPER, "environment generation eligibility helper")
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_for_restore_request", helper)
    require(spec is not None and spec.loader is not None, "cannot load environment generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_objectives_writer():
    helper = canonical_repo_file(OBJECTIVES_WRITER, "recovery objectives writer")
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_for_restore_request", helper)
    require(spec is not None and spec.loader is not None, "cannot load recovery objectives writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generations() -> list[dict[str, Any]]:
    """Return registered history only after the shared generation authority validates it."""
    require_canonical_runtime_authority(GEN_REGISTRY, CANONICAL_GEN_REGISTRY, "environment generation registry")
    registry = load(GEN_REGISTRY)
    helper = load_eligibility_helper()
    try:
        state = helper.derive_registry(registry)
    except helper.Fail as exc:
        raise Fail(f"environment generation registry authority invalid: {exc}") from exc
    rows = state.get("registeredRows")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "environment generation registry invalid")
    return rows


def generation_by_id(rows: list[dict[str, Any]], generation_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(generation_id, str) and generation_id, f"{field} required")
    matches = [row for row in rows if row.get("generationId") == generation_id]
    require(len(matches) == 1, f"{field} is not a unique registered generation")
    return matches[0]


def generation_is_unsuperseded(rows: list[dict[str, Any]], generation_id: str) -> bool:
    return not any(row.get("supersedesGenerationId") == generation_id for row in rows)


def require_preflight_eligible_generation(generation_id: str, field: str) -> None:
    helper = load_eligibility_helper()
    try:
        helper.eligible_generation_by_id(generation_id, registry_path=GEN_REGISTRY)
    except helper.Fail as exc:
        raise Fail(f"{field} is not an unsuperseded restore-preflight-eligible generation: {exc}") from exc


def objective_registry_state() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate objective history through its canonical append-only authority."""
    require_canonical_runtime_authority(OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry")
    registry = load(OBJECTIVES_REGISTRY)
    if ROOT == CANONICAL_ROOT and OBJECTIVES_REGISTRY == CANONICAL_OBJECTIVES_REGISTRY:
        helper = load_objectives_writer()
        try:
            rows = helper.validate_registry_for_append(registry)
        except helper.Fail as exc:
            raise Fail(f"recovery objectives registry authority invalid: {exc}") from exc
    else:
        rows = registry.get("records")
        count = registry.get("approvedObjectiveCount")
        require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False and registry.get("productionReady") is False, "recovery objective registry boundary drift")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "recovery objective registry invalid")
        require(isinstance(count, int) and not isinstance(count, bool) and count == len(rows), "recovery objective registry count drift")
    return registry, rows


def objective_by_id(objective_id: Any) -> dict[str, Any]:
    _, rows = objective_registry_state()
    require(isinstance(objective_id, str) and objective_id, "recoveryObjectivesId required")
    matches = [row for row in rows if row.get("objectiveId") == objective_id]
    require(len(matches) == 1, "recoveryObjectivesId is not uniquely registered")
    return matches[0]


def current_objective() -> dict[str, Any]:
    registry, rows = objective_registry_state()
    objective_id = registry.get("currentObjectiveId")
    require(isinstance(objective_id, str) and objective_id, "no current approved recovery objective")
    matches = [row for row in rows if row.get("objectiveId") == objective_id]
    require(len(matches) == 1, "currentObjectiveId is not uniquely registered")
    return matches[0]


def approval_document(ref: Any, field: str) -> dict[str, Any]:
    relative = repo_ref(ref, field)
    document = load(ROOT / relative)
    require(set(document) == APPROVAL_FIELDS, f"{field} approval field drift")
    require(document.get("schemaVersion") == APPROVAL_SCHEMA, f"{field} approval schemaVersion drift")
    parse_timestamp(document.get("approvedAt"), f"{field}.approvedAt")
    reviewer = document.get("reviewerPseudonym")
    require(isinstance(reviewer, str), f"{field} reviewerPseudonym required")
    canonical_reviewer = reviewer.strip()
    require(1 <= len(canonical_reviewer) <= 128 and reviewer == canonical_reviewer, f"{field} reviewerPseudonym must be canonical non-empty text")
    require(document.get("decision") == "APPROVED", f"{field} approval decision must be APPROVED")
    for boundary in ("productionTraffic", "productionCredentials", "automaticPromotion"):
        require(document.get(boundary) is False, f"{field} approval {boundary} must remain false")
    return document


def validate_request_approval(document: dict[str, Any], record: dict[str, Any], approval_key: str) -> str:
    field = f"approvalRefs.{approval_key}"
    require(document.get("reviewRole") == APPROVAL_ROLES[approval_key], f"{field} reviewRole mismatch")
    digest = document.get("requestRecordSha256")
    require(isinstance(digest, str) and DIGEST.fullmatch(digest), f"{field} requestRecordSha256 invalid")
    require(digest == canonical_request_sha256(record), f"{field} requestRecordSha256 binding mismatch")
    approved_at = parse_timestamp(document.get("approvedAt"), f"{field}.approvedAt")
    requested_at = parse_timestamp(record.get("requestedAt"), "requestedAt")
    require(approved_at >= requested_at, f"{field} approval predates the request")
    for approval_field, request_field in (("requestId", "requestId"), ("sourceEnvironmentGenerationId", "sourceEnvironmentGenerationId"), ("restoreTargetEnvironmentGenerationId", "restoreTargetEnvironmentGenerationId"), ("recoveryObjectivesId", "recoveryObjectivesId")):
        require(document.get(approval_field) == record.get(request_field), f"{field} {approval_field} binding mismatch")
    return str(document["reviewerPseudonym"])


def validate_request(record: dict[str, Any], *, require_current: bool = True) -> None:
    require_canonical_runtime_authority(CONTRACT, CANONICAL_CONTRACT, "restore drill request contract")
    contract = load(CONTRACT)
    required = set(contract.get("requiredRequestFields", []))
    require(required and set(record) == required, f"request field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "request schemaVersion drift")
    require(contract.get("approvalSchemaVersion") == APPROVAL_SCHEMA, "approval schema contract/writer drift")
    require(set(contract.get("requiredApprovalFields", [])) == APPROVAL_FIELDS, "approval field contract/writer drift")
    rules = contract.get("admissionRules")
    require(isinstance(rules, dict) and rules.get("approvalDocumentsMustBindCanonicalRequestRecordDigest") is True, "canonical request digest approval rule missing")
    require(rules.get("approvalDocumentsMustNotPredateRequest") is True, "approval chronology rule missing")
    require(rules.get("requestMustNotPredateSourceGenerationRegistration") is True, "source generation chronology rule missing")
    require(rules.get("requestMustNotPredateRestoreTargetGenerationRegistration") is True, "restore-target generation chronology rule missing")
    require(rules.get("requestMustNotPredateRecoveryObjectiveApproval") is True, "recovery objective chronology rule missing")
    require(rules.get("approvalReviewerPseudonymsMustBeCanonicalNonEmptyText") is True, "canonical reviewer pseudonym rule missing")
    require(rules.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True, "transactional request append authority missing")
    request_id = record.get("requestId")
    require(isinstance(request_id, str) and REQUEST_ID.fullmatch(request_id), "requestId invalid")
    requested_at = parse_timestamp(record.get("requestedAt"), "requestedAt")

    rows = generations()
    source = generation_by_id(rows, record.get("sourceEnvironmentGenerationId"), "sourceEnvironmentGenerationId")
    target = generation_by_id(rows, record.get("restoreTargetEnvironmentGenerationId"), "restoreTargetEnvironmentGenerationId")
    require(source.get("generationId") != target.get("generationId"), "source and restore-target generation IDs must differ")
    require(source.get("environmentId") != target.get("environmentId"), "source and restore-target environment IDs must differ")
    require(requested_at >= parse_timestamp(source.get("registeredAt"), "source generation registeredAt"), "request predates source generation registration")
    require(requested_at >= parse_timestamp(target.get("registeredAt"), "restore-target generation registeredAt"), "request predates restore-target generation registration")
    if require_current:
        require(generation_is_unsuperseded(rows, source["generationId"]), "source generation has been superseded")
        require(generation_is_unsuperseded(rows, target["generationId"]), "restore-target generation has been superseded")
        require_preflight_eligible_generation(source["generationId"], "sourceEnvironmentGenerationId")
        require_preflight_eligible_generation(target["generationId"], "restoreTargetEnvironmentGenerationId")
    for value, field in ((record.get("sourceEnvironmentManifestSha256"), "sourceEnvironmentManifestSha256"), (record.get("restoreTargetManifestSha256"), "restoreTargetManifestSha256")):
        require(isinstance(value, str) and DIGEST.fullmatch(value), f"{field} invalid")
    require(record["sourceEnvironmentManifestSha256"] == source.get("environmentManifestSha256"), "source environment manifest digest mismatch")
    require(record["restoreTargetManifestSha256"] == target.get("environmentManifestSha256"), "restore-target environment manifest digest mismatch")

    if require_current:
        objective = current_objective()
        require(record.get("recoveryObjectivesId") == objective.get("objectiveId"), "request must bind current approved recovery objective")
    else:
        objective = objective_by_id(record.get("recoveryObjectivesId"))
    require(requested_at >= parse_timestamp(objective.get("approvedAt"), "recovery objective approvedAt"), "request predates recovery objective approval")

    isolation = record.get("isolationPolicy")
    require(isinstance(isolation, dict) and set(isolation) == {"environmentClass", "networkIsolated", "productionRoutingForbidden", "syntheticOrApprovedSanitizedDataOnly"}, "isolationPolicy field drift")
    require(isolation.get("environmentClass") == "PRODUCTION_EQUIVALENT_ISOLATED_RESTORE_DRILL", "isolation environment class drift")
    require(isolation.get("networkIsolated") is True, "restore drill must be network isolated")
    require(isolation.get("productionRoutingForbidden") is True, "production routing must be forbidden")
    require(isolation.get("syntheticOrApprovedSanitizedDataOnly") is True, "restore drill data policy drift")

    database = record.get("databasePolicy")
    require(isinstance(database, dict) and set(database) == {"pitrRequired", "walContinuityRequired", "restoreIntoSeparateDatabaseRequired", "destructiveDownMigrationAllowed"}, "databasePolicy field drift")
    require(database.get("pitrRequired") is True and database.get("walContinuityRequired") is True, "PITR and WAL continuity are required")
    require(database.get("restoreIntoSeparateDatabaseRequired") is True, "isolated restore database required")
    require(database.get("destructiveDownMigrationAllowed") is False, "destructive down migration forbidden")

    object_policy = record.get("objectPolicy")
    require(isinstance(object_policy, dict) and set(object_policy) == {"independentRetentionRequired", "exactVersionRestoreRequired", "tlsRequired", "restoreOnlyCredentialsRequired", "deletionProtectionRequired", "immutabilityRequired"}, "objectPolicy field drift")
    for field in ("independentRetentionRequired", "exactVersionRestoreRequired", "tlsRequired", "restoreOnlyCredentialsRequired", "deletionProtectionRequired", "immutabilityRequired"):
        require(object_policy.get(field) is True, f"objectPolicy.{field} must be true")

    domains = record.get("requiredEvidenceDomains")
    required_domains = contract.get("requiredEvidenceDomains")
    require(isinstance(domains, list) and isinstance(required_domains, list), "requiredEvidenceDomains invalid")
    require(len(domains) == len(set(domains)) and set(domains) == set(required_domains), "requiredEvidenceDomains coverage drift")

    entry_refs = record.get("entryCriteriaRefs")
    require(isinstance(entry_refs, list) and len(entry_refs) >= 3 and len(entry_refs) == len(set(entry_refs)), "entryCriteriaRefs must contain at least three distinct refs")
    for index, ref in enumerate(entry_refs):
        repo_ref(ref, f"entryCriteriaRefs[{index}]")

    approvals = record.get("approvalRefs")
    require(isinstance(approvals, dict) and set(approvals) == set(APPROVAL_ROLES), "approvalRefs field drift")
    approval_values = [repo_ref(approvals[key], f"approvalRefs.{key}") for key in APPROVAL_ROLES]
    require(len(set(approval_values)) == 3, "recovery owner, security and operability approvals must be distinct")
    reviewers = [validate_request_approval(approval_document(approvals[key], f"approvalRefs.{key}"), record, key) for key in APPROVAL_ROLES]
    require(len(set(reviewers)) == 3, "recovery owner, security and operability reviewers must be distinct")

    stops = record.get("stopConditions")
    required_stops = contract.get("requiredStopConditions")
    require(isinstance(stops, list) and isinstance(required_stops, list), "stopConditions invalid")
    require(len(stops) == len(set(stops)) and set(required_stops).issubset(set(stops)), "required stop conditions missing")

    risks = record.get("openRisks")
    require(isinstance(risks, list), "openRisks must be list")
    risk_ids: set[str] = set()
    for index, risk in enumerate(risks):
        require(isinstance(risk, dict) and set(risk) == {"riskId", "severity", "status", "ownerRef"}, f"openRisks[{index}] field drift")
        risk_id = risk.get("riskId")
        require(isinstance(risk_id, str) and risk_id and risk_id not in risk_ids, f"openRisks[{index}].riskId invalid/duplicate")
        risk_ids.add(risk_id)
        require(risk.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL open risk blocks drill request admission")
        require(risk.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"openRisks[{index}].status invalid")
        repo_ref(risk.get("ownerRef"), f"openRisks[{index}].ownerRef")

    for field in ("productionTraffic", "productionCredentials", "automaticPromotion", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@", "latest"):
        require(forbidden not in serialized, f"request contains forbidden material: {forbidden}")


def request_currently_executable(record: dict[str, Any]) -> bool:
    try:
        validate_request(record, require_current=True)
    except Fail:
        return False
    return True


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate existing append-only request authority before any mutation."""
    require(registry.get("schemaVersion") == "memory-os-backup-restore-drill-request-registry.v1", "request registry schema drift")
    require(registry.get("registryClass") == "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS", "request registry class drift")
    require(registry.get("appendOnly") is True, "request registry must remain append-only")
    require(registry.get("productionEvidence") is False, "request registry productionEvidence must remain false")
    require(registry.get("productionReady") is False, "request registry productionReady must remain false")
    requests = registry.get("requests")
    require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "request registry records invalid")
    registered_count = registry.get("registeredRequestCount")
    executable_count = registry.get("currentExecutableRequestCount")
    require(isinstance(registered_count, int) and not isinstance(registered_count, bool), "registeredRequestCount must be a non-boolean integer")
    require(registered_count == len(requests), "registeredRequestCount drift")
    require(isinstance(executable_count, int) and not isinstance(executable_count, bool), "currentExecutableRequestCount must be a non-boolean integer")
    enforce_approval_digests = ROOT == CANONICAL_ROOT and REGISTRY == CANONICAL_REGISTRY
    digest_map = registry.get("approvalEvidenceDigestsByRequestId") if enforce_approval_digests else None
    if enforce_approval_digests:
        require(isinstance(digest_map, dict), "request approval evidence digest map invalid")
    request_ids: set[str] = set()
    tuples: set[tuple[Any, Any, Any]] = set()
    derived_executable = 0
    for row in requests:
        validate_request(row, require_current=False)
        request_id = row.get("requestId")
        require(isinstance(request_id, str) and request_id not in request_ids, f"duplicate requestId: {request_id}")
        request_ids.add(request_id)
        if enforce_approval_digests:
            approvals = row.get("approvalRefs")
            require(isinstance(approvals, dict) and set(approvals) == set(APPROVAL_ROLES), f"approvalRefs authority drift: {request_id}")
            refs = set(approvals.values())
            digests = digest_map.get(request_id) if isinstance(digest_map, dict) else None
            require(isinstance(digests, dict) and set(digests) == refs, f"approval evidence digest refs drift: {request_id}")
            for ref in refs:
                digest = digests.get(ref)
                require(isinstance(digest, str) and DIGEST.fullmatch(digest), f"approval evidence digest invalid: {request_id}")
                require(digest == approval_sha256(ref), f"approval evidence content drift: {request_id}: {ref}")
        key = (row.get("sourceEnvironmentGenerationId"), row.get("restoreTargetEnvironmentGenerationId"), row.get("recoveryObjectivesId"))
        require(key not in tuples, f"duplicate source/target/objective drill request tuple: {key}")
        tuples.add(key)
        if request_currently_executable(row):
            derived_executable += 1
    if enforce_approval_digests:
        require(isinstance(digest_map, dict) and set(digest_map) == request_ids, "request approval evidence digest request set drift")
    require(executable_count == derived_executable, "currentExecutableRequestCount drift")
    return requests


def registry_mode() -> int:
    try:
        return REGISTRY.stat().st_mode & 0o7777
    except OSError as exc:
        raise Fail("cannot snapshot backup/restore drill request registry mode before append") from exc


def atomic_write(value: dict[str, Any], mode: int | None = None) -> None:
    if mode is None:
        mode = registry_mode()
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-drill-request.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), mode)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def atomic_restore(payload: bytes, mode: int | None = None) -> None:
    if mode is None:
        mode = registry_mode()
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-drill-request-rollback.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def write_registry_transactionally(value: dict[str, Any]) -> None:
    try:
        original = REGISTRY.read_bytes()
        original_mode = registry_mode()
    except OSError as exc:
        raise Fail("cannot snapshot backup/restore drill request registry before append") from exc
    atomic_write(value, original_mode)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        atomic_restore(original, original_mode)
        raise


def main() -> int:
    require_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    input_path = Path(args.request).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("drill request input must be external to repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    validate_request(record, require_current=True)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("backup/restore drill request registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["requestId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        requests = validate_registry_for_append(registry)
        require(all(row.get("requestId") != record["requestId"] for row in requests), "requestId already registered")
        request_tuple = (record["sourceEnvironmentGenerationId"], record["restoreTargetEnvironmentGenerationId"], record["recoveryObjectivesId"])
        for row in requests:
            existing_tuple = (row.get("sourceEnvironmentGenerationId"), row.get("restoreTargetEnvironmentGenerationId"), row.get("recoveryObjectivesId"))
            require(existing_tuple != request_tuple, "source/target/objective tuple already has an admitted drill request")
        digest_map = registry.get("approvalEvidenceDigestsByRequestId")
        require(isinstance(digest_map, dict), "request approval evidence digest map invalid")
        require(record["requestId"] not in digest_map, "request approval digest authority already registered")
        approval_refs = record["approvalRefs"]
        digest_map[record["requestId"]] = {ref: approval_sha256(ref) for ref in approval_refs.values()}
        requests.append(record)
        registry["registeredRequestCount"] = len(requests)
        registry["currentExecutableRequestCount"] = sum(1 for row in requests if request_currently_executable(row))
        write_registry_transactionally(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered production-equivalent backup/restore drill request: {record['requestId']}")
    print("source/target semantically preflight eligible: true")
    print("request chronology bound to generation/objective authority: true")
    print("typed human approvals bound to canonical request digest: true")
    print("approval evidence content SHA-256 bound: true")
    print("approval chronology bound to request creation: true")
    print("planning authority only: true")
    print("execution-time revalidation required: true")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST FAILED: {exc}")
        raise SystemExit(1)
