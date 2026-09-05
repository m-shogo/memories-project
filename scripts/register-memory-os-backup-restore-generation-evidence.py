#!/usr/bin/env python3
"""Append one reviewed, drill-request-bound backup/restore evidence record."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
REGISTRY = CANONICAL_REGISTRY
CANONICAL_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_REGISTRY = CANONICAL_GEN_REGISTRY
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
CANONICAL_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
OBJECTIVES_REGISTRY = CANONICAL_OBJECTIVES_REGISTRY
OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
CANONICAL_DRILL_REQUEST_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REQUEST_CONTRACT = CANONICAL_DRILL_REQUEST_CONTRACT
CANONICAL_DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
DRILL_REQUEST_REGISTRY = CANONICAL_DRILL_REQUEST_REGISTRY
DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
CANONICAL_NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
NON_RESURRECTION_CONTRACT = CANONICAL_NON_RESURRECTION_CONTRACT
CANONICAL_NON_RESURRECTION_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
NON_RESURRECTION_REGISTRY = CANONICAL_NON_RESURRECTION_REGISTRY
NON_RESURRECTION_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_ID = re.compile(r"^brge_[a-z0-9][a-z0-9_-]{7,63}$")
REQUEST_ID = re.compile(r"^brrq_[a-z0-9][a-z0-9_-]{7,63}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def domain_validation_failure(exc: BaseException) -> bool:
    """Recognize only explicit domain validation failures across dynamic modules."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RuntimeError) and current.__class__.__name__ == "Fail":
            return True
        current = current.__cause__ or current.__context__
    return False


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    """Contain canonical runtime authority without breaking isolated test registries."""
    if path == canonical:
        canonical_repo_file(path, field)


def require_cli_authorities() -> None:
    """Pin actual generation-evidence append to canonical upstream and review authorities."""
    for actual, canonical, field in (
        (CONTRACT, ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json", "generation evidence contract"),
        (REGISTRY, CANONICAL_REGISTRY, "generation evidence registry"),
        (GEN_REGISTRY, CANONICAL_GEN_REGISTRY, "environment generation registry"),
        (GEN_WRITER, ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py", "environment generation writer"),
        (OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry"),
        (OBJECTIVES_WRITER, ROOT / "scripts/register-memory-os-recovery-objectives.py", "recovery objectives writer"),
        (DRILL_REQUEST_CONTRACT, CANONICAL_DRILL_REQUEST_CONTRACT, "restore drill request contract"),
        (DRILL_REQUEST_REGISTRY, CANONICAL_DRILL_REQUEST_REGISTRY, "restore drill request registry"),
        (DRILL_REQUEST_WRITER, ROOT / "scripts/request-memory-os-backup-restore-drill.py", "restore drill request writer"),
        (NON_RESURRECTION_CONTRACT, CANONICAL_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract"),
        (NON_RESURRECTION_REGISTRY, CANONICAL_NON_RESURRECTION_REGISTRY, "typed non-resurrection registry"),
        (NON_RESURRECTION_WRITER, ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py", "typed non-resurrection writer"),
        (INDEPENDENT_REVIEW_VALIDATOR, ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py", "generation independent-review validator"),
    ):
        require(actual == canonical, f"{field} must use canonical authority")
        canonical_repo_file(actual, field)
    canonical_lock = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
    require(LOCK == canonical_lock, "generation evidence append lock must use canonical authority")
    require(LOCK.parent == CANONICAL_REGISTRY.parent, "generation evidence append lock must share canonical registry directory")


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def repo_ref(value: Any, field: str, required: bool = True) -> str | None:
    if value is None and not required:
        return None
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
        raise Fail(f"{field} evidence path missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def generation_by_id(generations: list[Any], generation_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(generation_id, str) and generation_id, f"{field} required")
    matches = [row for row in generations if isinstance(row, dict) and row.get("generationId") == generation_id]
    require(len(matches) == 1, f"{field} is not a unique registered generation")
    return matches[0]


def load_generation_writer():
    writer = canonical_repo_file(GEN_WRITER, "environment generation writer")
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_generation_evidence", writer)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_objectives_writer():
    writer = canonical_repo_file(OBJECTIVES_WRITER, "recovery objectives writer")
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_writer_for_generation_evidence", writer)
    require(spec is not None and spec.loader is not None, "cannot load recovery objectives writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def objective_for_record(record: dict[str, Any]) -> dict[str, Any] | None:
    require_canonical_runtime_authority(OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry")
    registry = load(OBJECTIVES_REGISTRY)
    if OBJECTIVES_REGISTRY == CANONICAL_OBJECTIVES_REGISTRY:
        objectives_writer = load_objectives_writer()
        try:
            rows = objectives_writer.validate_registry_for_append(registry)
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail(f"recovery objectives registry authority invalid: {exc}") from exc
            raise
    else:
        require(registry.get("schemaVersion") == "memory-os-recovery-objectives-registry.v1", "recovery objectives registry schema drift")
        require(registry.get("appendOnly") is True, "recovery objectives registry must remain append-only")
        require(
            registry.get("productionEvidence") is False and registry.get("productionReady") is False,
            "recovery objectives registry production boundary drift",
        )
        rows = registry.get("records")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "recovery objectives registry invalid")
        approved_count = registry.get("approvedObjectiveCount")
        require(valid_count(approved_count) and approved_count == len(rows), "recovery objectives registry approvedObjectiveCount drift")
        objective_ids = [row.get("objectiveId") for row in rows]
        require(
            all(isinstance(value, str) and value for value in objective_ids)
            and len(objective_ids) == len(set(objective_ids)),
            "recovery objectives registry objectiveId authority invalid",
        )
        current_objective_id = registry.get("currentObjectiveId")
        if rows:
            require(current_objective_id == objective_ids[-1], "recovery objectives registry currentObjectiveId drift")
        else:
            require(current_objective_id is None, "empty recovery objectives registry must not declare currentObjectiveId")

    objective_id = record.get("recoveryObjectivesId")
    measurements = (
        record.get("measuredRpoSeconds"),
        record.get("measuredRtoSeconds"),
        record.get("measuredObjectDatabaseSkewSeconds"),
    )
    if objective_id is None:
        require(all(value is None for value in measurements), "recovery measurements require an approved recoveryObjectivesId")
        return None
    require(isinstance(objective_id, str) and objective_id, "recoveryObjectivesId invalid")
    matches = [row for row in rows if row.get("objectiveId") == objective_id]
    require(len(matches) == 1, "recoveryObjectivesId is not uniquely registered")
    objective = matches[0]
    for value, field in zip(measurements, ("measuredRpoSeconds", "measuredRtoSeconds", "measuredObjectDatabaseSkewSeconds")):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field} invalid")
    return objective


def measurements_meet_objective(record: dict[str, Any], objective: dict[str, Any] | None) -> bool:
    if objective is None:
        return False
    return (
        record.get("measuredRpoSeconds") <= objective.get("rpoSeconds", -1)
        and record.get("measuredRtoSeconds") <= objective.get("rtoSeconds", -1)
        and record.get("measuredObjectDatabaseSkewSeconds") <= objective.get("maximumObjectDatabaseSkewSeconds", -1)
    )


def load_drill_writer():
    require_canonical_runtime_authority(DRILL_REQUEST_CONTRACT, CANONICAL_DRILL_REQUEST_CONTRACT, "restore drill request contract")
    writer = canonical_repo_file(DRILL_REQUEST_WRITER, "restore drill request writer")
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_writer_for_generation_evidence", writer)
    require(spec is not None and spec.loader is not None, "cannot load restore drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CONTRACT = DRILL_REQUEST_CONTRACT
    module.GEN_REGISTRY = GEN_REGISTRY
    module.OBJECTIVES_REGISTRY = OBJECTIVES_REGISTRY
    return module


def load_non_resurrection_writer():
    require_canonical_runtime_authority(NON_RESURRECTION_CONTRACT, CANONICAL_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract")
    writer = canonical_repo_file(NON_RESURRECTION_WRITER, "typed non-resurrection writer")
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_writer_for_generation_evidence", writer)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CONTRACT = NON_RESURRECTION_CONTRACT
    return module


def load_independent_review_validator():
    validator = canonical_repo_file(INDEPENDENT_REVIEW_VALIDATOR, "generation independent-review validator")
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_for_candidate", validator)
    require(spec is not None and spec.loader is not None, "cannot load generation independent-review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT, "generation independent-review contract authority drift")
    require(getattr(module, "REGISTRY", None) == CANONICAL_REGISTRY, "generation independent-review registry authority drift")
    require(callable(getattr(module, "candidate_reviews_approved", None)), "generation independent-review candidate authority missing")
    return module


def validate_upstream_authorities_for_append() -> None:
    """Validate canonical upstream append-only authorities even when evidence is empty."""
    if GEN_REGISTRY == CANONICAL_GEN_REGISTRY:
        try:
            load_generation_writer().validate_registry_for_append(load(GEN_REGISTRY))
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail(f"environment generation registry authority invalid: {exc}") from exc
            raise
    if OBJECTIVES_REGISTRY == CANONICAL_OBJECTIVES_REGISTRY:
        try:
            load_objectives_writer().validate_registry_for_append(load(OBJECTIVES_REGISTRY))
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail(f"recovery objectives registry authority invalid: {exc}") from exc
            raise
    if DRILL_REQUEST_REGISTRY == CANONICAL_DRILL_REQUEST_REGISTRY:
        try:
            load_drill_writer().validate_registry_for_append(load(DRILL_REQUEST_REGISTRY))
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail(f"restore drill request registry authority invalid: {exc}") from exc
            raise


def drill_request_for_record(record: dict[str, Any], *, require_current: bool) -> dict[str, Any]:
    require_canonical_runtime_authority(DRILL_REQUEST_REGISTRY, CANONICAL_DRILL_REQUEST_REGISTRY, "restore drill request registry")
    request_id = record.get("drillRequestId")
    require(isinstance(request_id, str) and REQUEST_ID.fullmatch(request_id), "drillRequestId invalid")
    registry = load(DRILL_REQUEST_REGISTRY)
    drill_writer = load_drill_writer()
    if DRILL_REQUEST_REGISTRY == CANONICAL_DRILL_REQUEST_REGISTRY:
        try:
            rows = drill_writer.validate_registry_for_append(registry)
        except Exception as exc:
            if domain_validation_failure(exc):
                raise Fail(f"restore drill request registry authority invalid: {exc}") from exc
            raise
    else:
        require(registry.get("schemaVersion") == "memory-os-backup-restore-drill-request-registry.v1", "drill request registry schema drift")
        require(registry.get("appendOnly") is True, "drill request registry must remain append-only")
        require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "drill request registry production boundary drift")
        rows = registry.get("requests")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "drill request registry rows invalid")
        registered_count = registry.get("registeredRequestCount")
        current_count = registry.get("currentExecutableRequestCount")
        require(
            isinstance(registered_count, int) and not isinstance(registered_count, bool) and registered_count == len(rows),
            "drill request registry registeredRequestCount drift",
        )
        require(isinstance(current_count, int) and not isinstance(current_count, bool), "drill request registry currentExecutableRequestCount invalid")

        current_executable = 0
        for index, row in enumerate(rows):
            try:
                drill_writer.validate_request(row, require_current=False)
            except Exception as exc:
                if domain_validation_failure(exc):
                    raise Fail(f"drill request registry requests[{index}] historical authority invalid") from exc
                raise
            try:
                drill_writer.validate_request(row, require_current=True)
            except Exception as exc:
                if domain_validation_failure(exc):
                    continue
                raise
            current_executable += 1
        require(current_count == current_executable, "drill request registry currentExecutableRequestCount drift")

    matches = [row for row in rows if row.get("requestId") == request_id]
    require(len(matches) == 1, "drillRequestId is not uniquely registered")
    request = matches[0]
    drill_writer.validate_request(request, require_current=require_current)
    require(request.get("sourceEnvironmentGenerationId") == record.get("sourceEnvironmentGenerationId"), "drill request source generation mismatch")
    require(request.get("sourceEnvironmentManifestSha256") == record.get("sourceEnvironmentManifestSha256"), "drill request source manifest mismatch")
    require(request.get("restoreTargetEnvironmentGenerationId") == record.get("restoreTargetGenerationId"), "drill request restore target generation mismatch")
    require(request.get("restoreTargetManifestSha256") == record.get("restoreTargetManifestSha256"), "drill request restore target manifest mismatch")
    require(request.get("recoveryObjectivesId") == record.get("recoveryObjectivesId"), "drill request recovery objective mismatch")
    return request


def drill_request_current(record: dict[str, Any]) -> bool:
    try:
        drill_request_for_record(record, require_current=True)
    except Exception as exc:
        if domain_validation_failure(exc):
            return False
        raise
    return True


def independent_reviews_satisfied(record: dict[str, Any]) -> bool:
    security = record.get("securityReviewRef")
    operability = record.get("operabilityReviewRef")
    if not isinstance(security, str) or not isinstance(operability, str) or security == operability:
        return False
    canonical_runtime = (
        REGISTRY == CANONICAL_REGISTRY
        and GEN_REGISTRY == CANONICAL_GEN_REGISTRY
        and OBJECTIVES_REGISTRY == CANONICAL_OBJECTIVES_REGISTRY
        and DRILL_REQUEST_REGISTRY == CANONICAL_DRILL_REQUEST_REGISTRY
    )
    if not canonical_runtime:
        return True
    try:
        return load_independent_review_validator().candidate_reviews_approved(record) is True
    except Exception as exc:
        if domain_validation_failure(exc):
            return False
        raise


def base_candidate(record: dict[str, Any]) -> bool:
    """Return whether generation evidence satisfies every pre-overlay candidate gate."""
    objective = objective_for_record(record)
    require_canonical_runtime_authority(OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry")
    objectives_registry = load(OBJECTIVES_REGISTRY)
    current_objective_id = objectives_registry.get("currentObjectiveId")
    return (
        drill_request_current(record)
        and objective is not None
        and record.get("recoveryObjectivesId") == current_objective_id
        and measurements_meet_objective(record, objective)
        and record.get("evidenceComplete") is True
        and record.get("isolatedRestoreVerified") is True
        and record.get("postgresPitrVerified") is True
        and record.get("independentObjectRetentionVerified") is True
        and record.get("tlsVerified") is True
        and record.get("restoreOnlyCredentialSeparationVerified") is True
        and record.get("databaseObjectRecoveryCoherenceVerified") is True
        and record.get("nonResurrectionVerification") == "PASS"
        and independent_reviews_satisfied(record)
        and not record.get("unresolvedFindings")
    )


def typed_non_resurrection_covered(evidence_id: Any) -> bool:
    """Fail closed unless one complete typed overlay covers this generation record."""
    if not isinstance(evidence_id, str) or not evidence_id:
        return False
    try:
        require_canonical_runtime_authority(NON_RESURRECTION_CONTRACT, CANONICAL_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract")
        require_canonical_runtime_authority(NON_RESURRECTION_REGISTRY, CANONICAL_NON_RESURRECTION_REGISTRY, "typed non-resurrection registry")
        contract = load(NON_RESURRECTION_CONTRACT)
        registry = load(NON_RESURRECTION_REGISTRY)
    except Fail:
        return False
    required_domains = contract.get("requiredDomains")
    if not isinstance(required_domains, list) or len(required_domains) != 8 or len(required_domains) != len(set(required_domains)):
        return False
    if registry.get("schemaVersion") != "memory-os-backup-restore-non-resurrection-admission-registry.v1":
        return False
    if registry.get("appendOnly") is not True or registry.get("productionEvidence") is not False or registry.get("productionReady") is not False:
        return False
    rows = registry.get("records")
    if not isinstance(rows, list):
        return False
    matches = [row for row in rows if isinstance(row, dict) and row.get("generationEvidenceId") == evidence_id]
    if len(matches) != 1:
        return False
    row = matches[0]

    if NON_RESURRECTION_REGISTRY == CANONICAL_NON_RESURRECTION_REGISTRY:
        try:
            overlay_writer = load_non_resurrection_writer()
            overlay_writer.REGISTRY = NON_RESURRECTION_REGISTRY
            overlay_writer.GEN_EVIDENCE_REGISTRY = REGISTRY

            generation_registry = load(REGISTRY)
            generation_rows = generation_registry.get("records")
            require(
                isinstance(generation_rows, list) and all(isinstance(candidate_row, dict) for candidate_row in generation_rows),
                "generation evidence registry records invalid for typed candidate derivation",
            )

            def candidate_complete_against_bound_authority(candidate_row: dict[str, Any]) -> bool:
                generation_evidence_id = candidate_row.get("generationEvidenceId")
                bound_matches = [
                    generation_row
                    for generation_row in generation_rows
                    if generation_row.get("evidenceId") == generation_evidence_id
                ]
                require(len(bound_matches) == 1, "typed candidate generation evidence binding is not unique")
                return candidate_row.get("evidenceComplete") is True and base_candidate(bound_matches[0])

            overlay_writer.candidate_complete = candidate_complete_against_bound_authority
            validated_rows = overlay_writer.validate_registry_for_append(registry)
            validated_matches = [
                candidate_row
                for candidate_row in validated_rows
                if candidate_row.get("generationEvidenceId") == evidence_id
            ]
            if len(validated_matches) != 1:
                return False
            row = validated_matches[0]
        except Exception as exc:
            if domain_validation_failure(exc):
                return False
            raise

    if row.get("evidenceComplete") is not True:
        return False
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        if row.get(field) is not False:
            return False
    if row.get("unresolvedFindings") != []:
        return False
    security = row.get("securityReviewRef")
    operability = row.get("operabilityReviewRef")
    if not isinstance(security, str) or not isinstance(operability, str) or security == operability:
        return False
    domains = row.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(required_domains):
        return False
    for name in required_domains:
        entry = domains.get(name)
        if not isinstance(entry, dict) or set(entry) != {"result", "evidenceRef"}:
            return False
        if entry.get("result") != "PASS" or not isinstance(entry.get("evidenceRef"), str):
            return False
    return True


def candidate(record: dict[str, Any]) -> bool:
    """Final production-equivalent recovery candidate predicate."""
    return base_candidate(record) and typed_non_resurrection_covered(record.get("evidenceId"))


def validate_record(record: dict[str, Any], *, require_current_drill_request: bool = True) -> None:
    """Validate a recovery evidence record.

    Registration uses the default current-request gate. Canonical history audits
    pass `False` so a once-admitted immutable evidence row stays auditable after
    later generation/objective supersession; it simply stops being a current
    production-equivalent recovery candidate.
    """
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(contract.get("recoveryObjectivesRegistry") == str(CANONICAL_OBJECTIVES_REGISTRY.relative_to(ROOT)), "recoveryObjectivesRegistry ref drift")
    require(contract.get("drillRequestContract") == str(CANONICAL_DRILL_REQUEST_CONTRACT.relative_to(ROOT)), "drillRequestContract ref drift")
    require(contract.get("drillRequestRegistry") == str(CANONICAL_DRILL_REQUEST_REGISTRY.relative_to(ROOT)), "drillRequestRegistry ref drift")
    require(contract.get("typedNonResurrectionAdmissionContract") == str(CANONICAL_NON_RESURRECTION_CONTRACT.relative_to(ROOT)), "typed non-resurrection contract ref drift")
    require(contract.get("typedNonResurrectionAdmissionRegistry") == str(CANONICAL_NON_RESURRECTION_REGISTRY.relative_to(ROOT)), "typed non-resurrection registry ref drift")
    require(contract.get("independentReviewValidator") == str(INDEPENDENT_REVIEW_VALIDATOR.relative_to(ROOT)), "independent review validator ref drift")
    require(
        contract.get("recordRules", {}).get("registryMustRevalidateAfterAppendAndRollbackOnFailure") is True,
        "generation evidence transactional append authority drift",
    )
    require_canonical_runtime_authority(OBJECTIVES_REGISTRY, CANONICAL_OBJECTIVES_REGISTRY, "recovery objectives registry")
    require_canonical_runtime_authority(DRILL_REQUEST_CONTRACT, CANONICAL_DRILL_REQUEST_CONTRACT, "restore drill request contract")
    require_canonical_runtime_authority(DRILL_REQUEST_REGISTRY, CANONICAL_DRILL_REQUEST_REGISTRY, "restore drill request registry")
    require_canonical_runtime_authority(NON_RESURRECTION_CONTRACT, CANONICAL_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract")
    require_canonical_runtime_authority(NON_RESURRECTION_REGISTRY, CANONICAL_NON_RESURRECTION_REGISTRY, "typed non-resurrection registry")
    canonical_repo_file(OBJECTIVES_WRITER, "recovery objectives writer")
    canonical_repo_file(DRILL_REQUEST_WRITER, "restore drill request writer")
    canonical_repo_file(NON_RESURRECTION_WRITER, "typed non-resurrection writer")
    canonical_repo_file(INDEPENDENT_REVIEW_VALIDATOR, "generation independent-review validator")
    require(isinstance(record.get("evidenceId"), str) and EVIDENCE_ID.fullmatch(record["evidenceId"]), "evidenceId invalid")
    source_commit = record.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source_commit + "^{commit}") == "", "sourceCommitSha does not exist")

    generation_registry = load(GEN_REGISTRY)
    generations = generation_registry.get("generations")
    require(isinstance(generations, list) and generations, "no production-equivalent environment generation is registered")
    source_generation = generation_by_id(generations, record.get("sourceEnvironmentGenerationId"), "sourceEnvironmentGenerationId")
    target_generation = generation_by_id(generations, record.get("restoreTargetGenerationId"), "restoreTargetGenerationId")
    require(record.get("sourceEnvironmentManifestSha256") == source_generation.get("environmentManifestSha256"), "source environment manifest digest mismatch")
    require(record.get("restoreTargetManifestSha256") == target_generation.get("environmentManifestSha256"), "restore target environment manifest digest mismatch")
    require(source_commit == target_generation.get("sourceCommitSha"), "sourceCommitSha must match restore target generation source commit")

    for field in (
        "sourceEnvironmentManifestSha256", "restoreTargetManifestSha256", "backupArtifactSha256",
        "backupManifestSha256", "databaseRecoveryPointDigest", "objectRecoveryPointDigest",
        "restoreEvidenceBundleSha256", "restoredBackupArtifactSha256",
    ):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} invalid")
    require(record["restoredBackupArtifactSha256"] == record["backupArtifactSha256"], "restore must reference the exact backup artifact digest")

    for field in (
        "isolatedRestoreVerified", "postgresPitrVerified", "independentObjectRetentionVerified", "tlsVerified",
        "restoreOnlyCredentialSeparationVerified", "databaseObjectRecoveryCoherenceVerified", "evidenceComplete",
    ):
        require(isinstance(record.get(field), bool), f"{field} must be boolean")
    require(record.get("nonResurrectionVerification") in {"PASS", "FAIL", "NOT_RUN"}, "nonResurrectionVerification invalid")
    objective_for_record(record)
    drill_request_for_record(record, require_current=require_current_drill_request)

    source_id = record["sourceEnvironmentGenerationId"]
    target_id = record["restoreTargetGenerationId"]
    material_ref = repo_ref(record.get("materialDeltaReviewRef"), "materialDeltaReviewRef", required=False)
    if source_id != target_id:
        require(material_ref is not None, "cross-generation restore requires materialDeltaReviewRef")
    security_ref = repo_ref(record.get("securityReviewRef"), "securityReviewRef", required=False)
    operability_ref = repo_ref(record.get("operabilityReviewRef"), "operabilityReviewRef", required=False)
    if security_ref is not None and operability_ref is not None:
        require(security_ref != operability_ref, "security and operability reviews must be distinct")

    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL findings block registry admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}] status invalid")

    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password",
        "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@", "latest",
    ):
        require(forbidden not in serialized, f"record contains forbidden recovery material: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validate_upstream_authorities_for_append()
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry records invalid")

    count = registry.get("registeredEvidenceCount")
    bound_count = registry.get("drillRequestBoundEvidenceCount")
    backup_count = registry.get("completeGenerationBoundBackupCount")
    restore_count = registry.get("completeGenerationBoundRestoreCount")
    candidate_count = registry.get("productionEquivalentRecoveryCandidateCount")
    require(valid_count(count) and count == len(rows), "registeredEvidenceCount drift")
    require(all(valid_count(value) for value in (bound_count, backup_count, restore_count, candidate_count)), "registry derived counts invalid")

    ids: set[str] = set()
    for index, row in enumerate(rows):
        evidence_id = row.get("evidenceId")
        require(isinstance(evidence_id, str) and evidence_id and evidence_id not in ids, f"registry records[{index}] evidenceId authority invalid")
        ids.add(evidence_id)
        validate_record(row, require_current_drill_request=False)

    derived_bound = len(rows)
    derived_backup = sum(1 for row in rows if row.get("evidenceComplete") is True)
    derived_restore = sum(
        1
        for row in rows
        if row.get("evidenceComplete") is True
        and row.get("isolatedRestoreVerified") is True
        and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256")
    )
    derived_candidates = sum(1 for row in rows if candidate(row))
    require(bound_count == derived_bound == count, "drillRequestBoundEvidenceCount drift")
    require(backup_count == derived_backup, "completeGenerationBoundBackupCount drift")
    require(restore_count == derived_restore, "completeGenerationBoundRestoreCount drift")
    require(candidate_count == derived_candidates, "productionEquivalentRecoveryCandidateCount drift")
    require(0 <= candidate_count <= restore_count <= backup_count <= bound_count <= count, "registry count ordering invalid")
    return rows


def atomic_write(value: dict[str, Any], mode: int) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".backup-restore-generation.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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


def atomic_restore(payload: bytes, mode: int) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".backup-restore-generation-rollback.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
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
        with REGISTRY.open("rb") as handle:
            original = handle.read()
            original_mode = stat.S_IMODE(os.fstat(handle.fileno()).st_mode)
    except OSError as exc:
        raise Fail("cannot snapshot generation evidence registry before append") from exc
    atomic_write(value, original_mode)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        atomic_restore(original, original_mode)
        raise


def main() -> int:
    require_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    input_path = Path(args.record).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input recovery evidence record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    validate_record(record, require_current_drill_request=True)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("backup/restore generation evidence registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["evidenceId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        rows = validate_registry_for_append(registry)
        require(all(row.get("evidenceId") != record["evidenceId"] for row in rows), "evidenceId already registered")
        rows.append(record)
        registry["registeredEvidenceCount"] = len(rows)
        registry["drillRequestBoundEvidenceCount"] = sum(1 for row in rows if isinstance(row.get("drillRequestId"), str))
        registry["completeGenerationBoundBackupCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True)
        registry["completeGenerationBoundRestoreCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True and row.get("isolatedRestoreVerified") is True and row.get("restoredBackupArtifactSha256") == row.get("backupArtifactSha256"))
        registry["productionEquivalentRecoveryCandidateCount"] = sum(1 for row in rows if candidate(row))
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        registry["limitations"] = [
            "generation-bound recovery evidence remains non-production evidence",
            "every admitted recovery evidence row must bind an already admitted restore drill request with the same source generation, restore target generation and recovery objective",
            "new evidence registration requires that drill request to still be currently executable; later supersession preserves historical evidence but removes current candidate eligibility",
            "a generation record can satisfy all pre-overlay recovery controls without becoming a production-equivalent recovery candidate until complete typed non-resurrection evidence is separately registered",
            "historical evidence remains valid against the approved objective ID recorded at execution time, but only evidence bound to the current objective ID and a currently executable drill request can become a current production-equivalent recovery candidate",
            "failed RPO/RTO/object-database-skew measurements remain admissible evidence but cannot become production-equivalent recovery candidates",
            "production-equivalent recovery candidates require current approved recovery objectives, a current drill request, all fail-closed controls, complete typed non-resurrection coverage and typed append-only independent Security/Operability reviews",
            "this registry never establishes application production readiness"
        ]
        write_registry_transactionally(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered generation-bound backup/restore evidence: {record['evidenceId']}")
    print(f"drill request bound: {record['drillRequestId']}")
    print(f"drill request currently executable: {str(drill_request_current(record)).lower()}")
    print(f"pre-overlay recovery gates complete: {str(base_candidate(record)).lower()}")
    print(f"typed non-resurrection coverage present: {str(typed_non_resurrection_covered(record['evidenceId'])).lower()}")
    print(f"production-equivalent recovery candidate: {str(candidate(record)).lower()}")
    print("production evidence: false")
    print("application production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION EVIDENCE REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
