#!/usr/bin/env python3
"""Validate append-only non-production migration rehearsal evidence authority."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_migration_recovery_point import RecoveryPointFailure, validate_recovery_point

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
RECOVERY_VALIDATOR = ROOT / "scripts/memory_os_migration_recovery_point.py"
ARTIFACT_VALIDATOR = ROOT / "scripts/validate-memory-os-local-migration-recovery-artifact.py"
WORKFLOW = ROOT / ".github/workflows/migration-evidence-registry.yml"
LOCAL_RESTORE = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
LOCAL_ARTIFACT_ROOT = ROOT / "docs/evidence/migrations/recovery"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^mig_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")


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


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commit_exists(sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", sha + "^{commit}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def is_passing(record: dict[str, Any]) -> bool:
    return all(record.get(field) == "PASS" for field in ("preflightResult", "applyResult", "verificationResult"))


def validate_record(
    record: dict[str, Any],
    required: set[str],
    canonical: list[str],
    generations: list[Any],
    contract: dict[str, Any],
    index: int,
) -> None:
    prefix = f"records[{index}]"
    require(set(record) >= required, f"{prefix} missing fields")
    require(record.get("schemaVersion") == "memory-os-migration-rehearsal-evidence.v1", f"{prefix} schema drift")
    run_id = record.get("migrationRunId")
    require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id) is not None, f"{prefix}.migrationRunId invalid")
    env = record.get("environmentClass")
    require(env in {"LOCAL_POSTGRES_REHEARSAL", "PRODUCTION_EQUIVALENT_REHEARSAL"}, f"{prefix}.environmentClass invalid")
    require(isinstance(record.get("databaseIdentityDigest"), str) and SHA256.fullmatch(record["databaseIdentityDigest"]) is not None, f"{prefix}.databaseIdentityDigest invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None and commit_exists(source), f"{prefix}.sourceCommitSha invalid")
    before = record.get("migrationSequenceBefore")
    after = record.get("migrationSequenceAfter")
    require(isinstance(before, list) and before == canonical[:len(before)], f"{prefix}.migrationSequenceBefore not canonical prefix")
    require(after == canonical, f"{prefix}.migrationSequenceAfter must equal canonical sequence")
    require(isinstance(record.get("operatorRef"), str) and record["operatorRef"].startswith("opr_"), f"{prefix}.operatorRef invalid")
    require(isinstance(record.get("reviewerRef"), str) and record["reviewerRef"].startswith("rev_") and record["reviewerRef"] != record["operatorRef"], f"{prefix}.reviewerRef invalid")
    try:
        validate_recovery_point(record, env, canonical, contract)
    except RecoveryPointFailure as exc:
        raise Fail(f"{prefix} recovery evidence invalid: {exc}") from exc
    for field in ("lockBudgetMs", "statementBudgetMs", "observedLockWaitMs", "observedRuntimeMs"):
        require(isinstance(record.get(field), int) and record[field] >= 0, f"{prefix}.{field} invalid")
    require(record["lockBudgetMs"] > 0 and record["statementBudgetMs"] > 0, f"{prefix} budgets must be positive")
    for field in ("preflightResult", "applyResult", "verificationResult"):
        require(record.get(field) in {"PASS", "FAIL", "NOT_RUN"}, f"{prefix}.{field} invalid")
    require(record.get("containsSecrets") is False and record.get("productionTraffic") is False and record.get("productionCredentials") is False and record.get("productionEvidence") is False, f"{prefix} evidence boundary drift")
    if is_passing(record):
        require(record["observedLockWaitMs"] <= record["lockBudgetMs"], f"{prefix} passing lock wait exceeded budget")
        require(record["observedRuntimeMs"] <= record["statementBudgetMs"], f"{prefix} passing runtime exceeded budget")
        require(record.get("recoveryDecision") == "NO_RECOVERY_REQUIRED", f"{prefix} passing rehearsal recovery decision drift")
    if env == "LOCAL_POSTGRES_REHEARSAL":
        require(record.get("environmentGenerationId") is None, f"{prefix} local rehearsal cannot claim generation")
    else:
        gen_id = record.get("environmentGenerationId")
        require(isinstance(gen_id, str) and any(isinstance(row, dict) and row.get("generationId") == gen_id for row in generations), f"{prefix} unknown production-equivalent generation")
    risks = record.get("openRisks")
    require(isinstance(risks, list), f"{prefix}.openRisks invalid")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    lifecycle = load(LIFECYCLE)
    gen_registry = load(GEN_REGISTRY)

    require(contract.get("schemaVersion") == "memory-os-migration-evidence-registry-contract.v1", "contract schema drift")
    require(contract.get("migrationLifecycleContract") == str(LIFECYCLE.relative_to(ROOT)), "lifecycle reference drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry reference drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer reference drift")
    require(contract.get("validator") == str(Path(__file__).resolve().relative_to(ROOT)), "validator reference drift")
    require(contract.get("recoveryPointValidator") == str(RECOVERY_VALIDATOR.relative_to(ROOT)), "recovery-point validator reference drift")
    require(contract.get("recoveryArtifactResultValidator") == str(ARTIFACT_VALIDATOR.relative_to(ROOT)), "recovery-artifact result validator reference drift")
    require(contract.get("appendOnly") is True and contract.get("productionEnvironmentRegistrationImplemented") is False, "contract production boundary drift")
    require(set(contract.get("allowedEnvironmentClasses", [])) == {"LOCAL_POSTGRES_REHEARSAL", "PRODUCTION_EQUIVALENT_REHEARSAL"}, "environment classes drift")
    require(WRITER.is_file() and RECOVERY_VALIDATOR.is_file() and ARTIFACT_VALIDATOR.is_file(), "migration rehearsal writer/recovery validators missing")

    writer = load_module(WRITER, "memory_os_migration_rehearsal_writer_for_registry_validation")
    require(writer.CONTRACT.resolve() == CONTRACT.resolve(), "writer contract authority drift")
    require(writer.REGISTRY.resolve() == REGISTRY.resolve(), "writer registry authority drift")
    require(writer.LIFECYCLE.resolve() == LIFECYCLE.resolve(), "writer lifecycle authority drift")
    try:
        writer.validate_registry_for_append(registry, contract)
    except writer.Failure as exc:
        raise Fail(f"writer append-only authority rejected registry: {exc}") from exc

    canonical = lifecycle.get("migrationSequence")
    require(isinstance(canonical, list) and canonical, "canonical migration sequence missing")
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list) and len(required) == len(set(required)), "requiredRecordFields invalid")
    for field in lifecycle.get("evidenceRecord", {}).get("requiredFields", []):
        aliases = {"environment": "environmentClass", "operator": "operatorRef", "reviewer": "reviewerRef"}
        require(aliases.get(field, field) in required, f"registry record omits lifecycle evidence field: {field}")
    for field in (
        "recoveryPointArtifactDigest",
        "restoreCapabilityEvidenceRef",
        "restoreCapabilityVerified",
        "recoveryPointRestoreEvidenceRef",
    ):
        require(field in required, f"typed recovery field missing: {field}")

    rules = contract.get("registrationRules")
    require(isinstance(rules, dict), "registrationRules missing")
    for flag in (
        "recoveryPointReferenceMustBeSha256Digest",
        "recoveryPointArtifactDigestMustMatchReference",
        "recoveryPointVerifiedRequired",
        "restoreCapabilityEvidenceMustExistAndPass",
        "restoreCapabilityVerifiedRequired",
        "actualRecoveryArtifactRestoreEvidenceRequired",
        "actualRecoveryArtifactDigestMustMatchRecord",
        "actualRecoveryArtifactRestoreResultMustPass",
        "productionEquivalentRehearsalRequiresConfiguredRestoreCapability",
    ):
        require(rules.get(flag) is True, f"registrationRules.{flag} must be true")

    authorities = contract.get("restoreCapabilityAuthorities")
    require(isinstance(authorities, dict), "restoreCapabilityAuthorities missing")
    local = authorities.get("LOCAL_POSTGRES_REHEARSAL")
    pe = authorities.get("PRODUCTION_EQUIVALENT_REHEARSAL")
    require(isinstance(local, dict) and local.get("configured") is True,
            "local restore capability authority must be configured")
    require(local.get("evidenceRef") == str(LOCAL_RESTORE.relative_to(ROOT)),
            "local restore capability evidence path drift")
    require(local.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "local restore capability schema drift")
    require(isinstance(pe, dict) and pe.get("configured") is False and pe.get("evidenceRef") is None,
            "production-equivalent restore capability must remain unconfigured")
    local_restore = load(LOCAL_RESTORE)
    require(local_restore.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "local logical restore result schema drift")
    local_scenario = local_restore.get("scenario")
    local_env = local_restore.get("environment")
    require(isinstance(local_scenario, dict) and local_scenario.get("result") == "PASS" and
            local_scenario.get("integrityResult") == "PASS",
            "local logical restore capability is not PASS")
    require(local_scenario.get("migrationFilesApplied") == len(canonical),
            "local logical restore capability is stale for canonical migration count")
    require(isinstance(local_env, dict) and local_env.get("productionEvidence") is False,
            "local logical restore capability cannot be production evidence")

    artifact_authorities = contract.get("actualRecoveryArtifactAuthorities")
    require(isinstance(artifact_authorities, dict), "actualRecoveryArtifactAuthorities missing")
    local_artifact = artifact_authorities.get("LOCAL_POSTGRES_REHEARSAL")
    pe_artifact = artifact_authorities.get("PRODUCTION_EQUIVALENT_REHEARSAL")
    require(isinstance(local_artifact, dict), "local actual recovery artifact authority missing")
    require(local_artifact.get("evidenceRoot") == str(LOCAL_ARTIFACT_ROOT.relative_to(ROOT)),
            "local actual recovery artifact evidence root drift")
    require(local_artifact.get("schemaVersion") == "memory-os-local-migration-recovery-artifact.v1",
            "local actual recovery artifact schema drift")
    require(local_artifact.get("validator") == str(ARTIFACT_VALIDATOR.relative_to(ROOT)),
            "local actual recovery artifact validator drift")
    for flag in ("requireMigrationRunIdMatch", "requireArtifactDigestMatch", "requireActualRecoveryArtifactRestored"):
        require(local_artifact.get(flag) is True, f"local actual recovery authority missing {flag}")
    require(local_artifact.get("productionEvidenceRequired") is False,
            "local actual recovery authority cannot require production evidence")
    require(isinstance(pe_artifact, dict) and pe_artifact.get("evidenceRoot") is None and
            pe_artifact.get("schemaVersion") is None and pe_artifact.get("validator") is None,
            "production-equivalent actual recovery authority must remain unconfigured")

    require(registry.get("schemaVersion") == "memory-os-migration-evidence-registry.v1", "registry schema drift")
    require(registry.get("registryClass") == "NON_PRODUCTION_MIGRATION_REHEARSAL_EVIDENCE", "registry class drift")
    require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False, "registry authority boundary drift")
    records = registry.get("records")
    count = registry.get("rehearsalEvidenceCount")
    require(isinstance(records, list) and isinstance(count, int) and count == len(records), "registry count mismatch")
    generations = gen_registry.get("generations")
    require(isinstance(generations, list), "generation registry invalid")

    ids: set[str] = set()
    passing = 0
    local_passing = 0
    pe_count = 0
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"records[{index}] invalid")
        validate_record(record, set(required), canonical, generations, contract, index)
        run_id = record["migrationRunId"]
        require(run_id not in ids, f"duplicate migrationRunId: {run_id}")
        ids.add(run_id)
        if is_passing(record):
            passing += 1
            if record.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL":
                local_passing += 1
        if record.get("environmentClass") == "PRODUCTION_EQUIVALENT_REHEARSAL":
            pe_count += 1
    require(registry.get("passingRehearsalCount") == passing, "passing rehearsal count drift")
    require(registry.get("productionEquivalentRehearsalCount") == pe_count, "production-equivalent rehearsal count drift")
    expected_latest = records[-1]["migrationRunId"] if records else None
    require(registry.get("latestRehearsalRunId") == expected_latest, "latest rehearsal run drift")

    authority = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(authority, dict) and isinstance(readiness, dict), "contract authority/readiness missing")
    require(authority.get("rehearsalEvidenceCount") == count, "contract rehearsal count drift")
    require(authority.get("passingRehearsalCount") == passing, "contract passing count drift")
    require(authority.get("productionEquivalentRehearsalCount") == pe_count, "contract PE count drift")
    require(authority.get("productionMigrationEvidenceCount") == 0 and authority.get("productionEvidence") is False and authority.get("productionReady") is False and authority.get("productionDecision") == "NO_GO", "contract production authority drift")
    for flag in (
        "contractDefined",
        "registryImplemented",
        "writerImplemented",
        "validatorImplemented",
        "operatorEvidenceRecordImplemented",
        "typedRecoveryArtifactReferenceImplemented",
        "localRestoreCapabilityBound",
        "perRunRecoveryArtifactEvidenceRequired",
    ):
        require(readiness.get(flag) is True, f"foundation readiness incomplete: {flag}")
    require(readiness.get("automaticWorkflowImplemented") is WORKFLOW.is_file(), "workflow readiness drift")
    require(readiness.get("localActualRecoveryArtifactRestoreLinked") is (local_passing > 0),
            "local actual recovery artifact readiness/count drift")
    for flag in (
        "productionEquivalentRestoreCapabilityConfigured",
        "productionEquivalentActualRecoveryArtifactRestoreLinked",
        "productionShapedRehearsalCompleted",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(flag) is False, f"unsafe migration readiness promotion: {flag}")

    print("Memory OS migration rehearsal evidence registry validation PASS")
    print(f"registered rehearsals: {count}")
    print(f"passing rehearsals: {passing}")
    print(f"local passing actual-artifact rehearsals: {local_passing}")
    print(f"production-equivalent rehearsals: {pe_count}")
    print("local restore capability: BOUND_TO_VALIDATED_LOGICAL_RESTORE")
    print(f"local actual recovery artifact restore linkage: {'PROVEN_LOCAL_ONLY' if local_passing else 'NOT_YET_REGISTERED'}")
    print("production migration evidence: 0")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION EVIDENCE REGISTRY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
