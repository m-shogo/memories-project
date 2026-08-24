#!/usr/bin/env python3
"""Semantic validation for production-equivalent environment records."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
GEN_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,95}$")
DELTA_ID = re.compile(r"^[A-Z0-9._-]{3,64}$")
TOP_LEVEL_FIELDS = {
    "schemaVersion", "environmentId", "generationId", "status", "topology",
    "postgresql", "objectStorage", "queueWorkers", "network", "identityAndSecrets",
    "backupRestore", "materialDeltas", "evidenceBoundary",
}
STATUSES = {"PLANNED", "PROVISIONED_UNVALIDATED", "VALIDATION_IN_PROGRESS", "VALIDATED_LOCAL_NONPRODUCTION", "REJECTED"}
PLACEHOLDERS = {"tbd", "todo", "unknown", "default", "n/a", "na", "later", "pending", "none", "not defined", "not_defined"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_ref(value: Any, field: str, *, required: bool) -> str | None:
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
    absolute = ROOT / relative
    try:
        resolved = absolute.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} evidence missing or escapes repository: {value}") from exc
    require(resolved == relative and absolute.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def exact_object(value: Any, fields: set[str], field: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{field} must be object")
    require(set(value) == fields, f"{field} field drift: {sorted(set(value) ^ fields)}")
    return value


def bool_field(obj: dict[str, Any], field: str, prefix: str) -> bool:
    value = obj.get(field)
    require(isinstance(value, bool), f"{prefix}.{field} must be boolean")
    return value


def safe_text(value: Any, field: str, *, max_length: int) -> str:
    require(isinstance(value, str), f"{field} invalid")
    normalized = " ".join(value.strip().split())
    require(1 <= len(normalized) <= max_length, f"{field} invalid")
    require(normalized.casefold() not in PLACEHOLDERS, f"{field} cannot be placeholder text")
    require("://" not in normalized and "@" not in normalized, f"{field} must not contain external locator material")
    return normalized


def validate_environment_record(
    env: dict[str, Any],
    *,
    expected_environment_id: str | None = None,
    expected_generation_id: str | None = None,
) -> bool:
    require(set(env) == TOP_LEVEL_FIELDS, f"environment record field drift: {sorted(set(env) ^ TOP_LEVEL_FIELDS)}")
    require(env.get("schemaVersion") == "memory-os-production-equivalent-environment-record.v1", "environment record schema drift")
    env_id = env.get("environmentId")
    gen_id = env.get("generationId")
    require(isinstance(env_id, str) and ENV_ID.fullmatch(env_id), "environmentId invalid")
    require(isinstance(gen_id, str) and GEN_ID.fullmatch(gen_id), "generationId invalid")
    require("latest" not in gen_id.casefold() and "current" not in gen_id.casefold(), "mutable generation alias forbidden")
    if expected_environment_id is not None:
        require(env_id == expected_environment_id, "environmentId mismatch with generation record")
    if expected_generation_id is not None:
        require(gen_id == expected_generation_id, "generationId mismatch with generation record")
    status = env.get("status")
    require(status in STATUSES, "environment status invalid")

    topology = exact_object(env.get("topology"), {"regionClass", "nonLoopback", "productionTraffic", "productionCredentials"}, "topology")
    safe_text(topology.get("regionClass"), "topology.regionClass", max_length=64)
    non_loopback = bool_field(topology, "nonLoopback", "topology")
    require(topology.get("productionTraffic") is False, "topology.productionTraffic must remain false")
    require(topology.get("productionCredentials") is False, "topology.productionCredentials must remain false")

    postgres = exact_object(env.get("postgresql"), {"tlsVerified", "runtimeRoleBypassRLS", "forceRLSVerified", "connectionBudgetDeclared", "poolTelemetryVerified", "restoreEvidenceRef"}, "postgresql")
    pg_tls = bool_field(postgres, "tlsVerified", "postgresql")
    require(postgres.get("runtimeRoleBypassRLS") is False, "postgresql.runtimeRoleBypassRLS must remain false")
    pg_force_rls = bool_field(postgres, "forceRLSVerified", "postgresql")
    pg_budget = bool_field(postgres, "connectionBudgetDeclared", "postgresql")
    pg_pool = bool_field(postgres, "poolTelemetryVerified", "postgresql")

    object_storage = exact_object(env.get("objectStorage"), {"tlsVerified", "scopedCredentialsVerified", "versioningVerified", "retentionLifecycleVerified", "exactVersionDeleteVerified", "restoreEvidenceRef"}, "objectStorage")
    object_tls = bool_field(object_storage, "tlsVerified", "objectStorage")
    object_scoped = bool_field(object_storage, "scopedCredentialsVerified", "objectStorage")
    object_versioning = bool_field(object_storage, "versioningVerified", "objectStorage")
    object_retention = bool_field(object_storage, "retentionLifecycleVerified", "objectStorage")
    object_delete = bool_field(object_storage, "exactVersionDeleteVerified", "objectStorage")

    workers = exact_object(env.get("queueWorkers"), {"boundedBackpressureVerified", "queueTelemetryVerified", "deletionBacklogTelemetryVerified", "leaseRetryVerified"}, "queueWorkers")
    worker_backpressure = bool_field(workers, "boundedBackpressureVerified", "queueWorkers")
    worker_queue = bool_field(workers, "queueTelemetryVerified", "queueWorkers")
    worker_delete = bool_field(workers, "deletionBacklogTelemetryVerified", "queueWorkers")
    worker_lease = bool_field(workers, "leaseRetryVerified", "queueWorkers")

    network = exact_object(env.get("network"), {"tlsVerificationRequired", "latencyProfileRef", "failureInjectionRef"}, "network")
    require(network.get("tlsVerificationRequired") is True, "network.tlsVerificationRequired must remain true")

    identity = exact_object(env.get("identityAndSecrets"), {"dedicatedNonProductionCredentials", "credentialScopeRef", "containsSecretMaterial"}, "identityAndSecrets")
    dedicated_credentials = bool_field(identity, "dedicatedNonProductionCredentials", "identityAndSecrets")
    require(identity.get("containsSecretMaterial") is False, "identityAndSecrets.containsSecretMaterial must remain false")

    backup = exact_object(env.get("backupRestore"), {"sameGenerationLinked", "isolatedRestoreVerified", "evidenceRef"}, "backupRestore")
    same_generation = bool_field(backup, "sameGenerationLinked", "backupRestore")
    isolated_restore = bool_field(backup, "isolatedRestoreVerified", "backupRestore")

    deltas = env.get("materialDeltas")
    require(isinstance(deltas, list), "materialDeltas must be list")
    delta_ids: set[str] = set()
    material_delta_review_refs: list[str] = []
    material_deltas_accepted = True
    for index, raw_delta in enumerate(deltas):
        delta = exact_object(raw_delta, {"deltaId", "description", "classification", "accepted", "independentReviewRef"}, f"materialDeltas[{index}]")
        delta_id = delta.get("deltaId")
        require(isinstance(delta_id, str) and DELTA_ID.fullmatch(delta_id) and delta_id not in delta_ids, f"materialDeltas[{index}].deltaId invalid/duplicate")
        delta_ids.add(delta_id)
        safe_text(delta.get("description"), f"materialDeltas[{index}].description", max_length=500)
        classification = delta.get("classification")
        require(classification in {"MATERIAL", "NON_MATERIAL"}, f"materialDeltas[{index}].classification invalid")
        accepted = delta.get("accepted")
        require(isinstance(accepted, bool), f"materialDeltas[{index}].accepted must be boolean")
        review_ref = repo_ref(delta.get("independentReviewRef"), f"materialDeltas[{index}].independentReviewRef", required=False)
        if review_ref is not None:
            material_delta_review_refs.append(review_ref)
        if classification == "MATERIAL":
            if not accepted:
                material_deltas_accepted = False
            if accepted:
                require(review_ref is not None, f"materialDeltas[{index}] accepted MATERIAL delta requires independent review evidence")

    boundary = exact_object(env.get("evidenceBoundary"), {"productionEvidence", "productionEquivalentDependencies", "independentReviewCompleted", "independentReviewRef", "productionReady"}, "evidenceBoundary")
    require(boundary.get("productionEvidence") is False, "evidenceBoundary.productionEvidence must remain false")
    equivalent = bool_field(boundary, "productionEquivalentDependencies", "evidenceBoundary")
    independent_review = bool_field(boundary, "independentReviewCompleted", "evidenceBoundary")
    require(boundary.get("productionReady") is False, "evidenceBoundary.productionReady must remain false")
    independent_review_ref = repo_ref(boundary.get("independentReviewRef"), "evidenceBoundary.independentReviewRef", required=False)
    if independent_review:
        require(independent_review_ref is not None, "independentReviewCompleted requires independentReviewRef")
    else:
        require(independent_review_ref is None, "independentReviewRef requires independentReviewCompleted")

    pg_restore_ref = repo_ref(postgres.get("restoreEvidenceRef"), "postgresql.restoreEvidenceRef", required=False)
    object_restore_ref = repo_ref(object_storage.get("restoreEvidenceRef"), "objectStorage.restoreEvidenceRef", required=False)
    latency_ref = repo_ref(network.get("latencyProfileRef"), "network.latencyProfileRef", required=False)
    failure_ref = repo_ref(network.get("failureInjectionRef"), "network.failureInjectionRef", required=False)
    credential_ref = repo_ref(identity.get("credentialScopeRef"), "identityAndSecrets.credentialScopeRef", required=False)
    backup_ref = repo_ref(backup.get("evidenceRef"), "backupRestore.evidenceRef", required=False)

    if independent_review_ref is not None:
        implementation_refs = (
            pg_restore_ref,
            object_restore_ref,
            latency_ref,
            failure_ref,
            credential_ref,
            backup_ref,
        )
        require(
            independent_review_ref not in implementation_refs,
            "environment independent review evidence must not be reused as implementation/restore evidence",
        )
        require(
            independent_review_ref not in material_delta_review_refs,
            "environment independent review evidence must not be reused as material-delta review evidence",
        )

    semantic_controls = all((
        status == "VALIDATED_LOCAL_NONPRODUCTION",
        non_loopback,
        pg_tls, pg_force_rls, pg_budget, pg_pool,
        object_tls, object_scoped, object_versioning, object_retention, object_delete,
        worker_backpressure, worker_queue, worker_delete, worker_lease,
        dedicated_credentials,
        same_generation, isolated_restore,
        material_deltas_accepted,
        independent_review,
        independent_review_ref is not None,
        pg_restore_ref is not None,
        object_restore_ref is not None,
        latency_ref is not None,
        failure_ref is not None,
        credential_ref is not None,
        backup_ref is not None,
    ))
    if equivalent:
        require(semantic_controls, "productionEquivalentDependencies=true without complete validated dependency evidence")
    else:
        require(not semantic_controls, "complete equivalent controls cannot be hidden behind productionEquivalentDependencies=false")

    return equivalent and semantic_controls


def load_file(path: Path) -> dict[str, Any]:
    import json
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), "environment record root must be object")
    return value


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-memory-os-production-equivalent-environment-record.py <record.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).resolve()
    env = load_file(path)
    eligible = validate_environment_record(env)
    print("Memory OS production-equivalent environment record semantic validation PASS")
    print(f"preflight eligible generation environment: {str(eligible).lower()}")
    print("environment independent review reuse accepted: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT RECORD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
