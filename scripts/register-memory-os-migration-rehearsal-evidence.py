#!/usr/bin/env python3
"""Append one reviewed non-production migration rehearsal evidence record.

The input JSON must live outside the repository. This writer verifies the
canonical migration sequence, privacy boundary, budgets, typed recovery artifact
reference, separately validated restore capability, and operator/reviewer
separation, then performs one atomic append-only update. It cannot write
production migration evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_migration_recovery_point import RecoveryPointFailure, validate_recovery_point

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
LOCK = ROOT / "contracts/operations/.migration-evidence-registry.lock"
CONFIRMATION = "REGISTER NON-PRODUCTION MIGRATION REHEARSAL"
RUN_ID = re.compile(r"^mig_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACTOR = re.compile(r"^(?:opr|rev)_[a-z0-9][a-z0-9_-]{7,63}$")
ENV_CLASSES = {"LOCAL_POSTGRES_REHEARSAL", "PRODUCTION_EQUIVALENT_REHEARSAL"}
RESULTS = {"PASS", "FAIL", "NOT_RUN"}
RECOVERY = {
    "NO_RECOVERY_REQUIRED",
    "STOP_AND_CORRECT",
    "VERIFY_DATABASE_ROLLBACK_THEN_CORRECT",
    "ROLL_BACK_APPLICATION_IF_SCHEMA_COMPATIBLE_OR_FORWARD_FIX",
    "PAUSE_BACKFILL_PRESERVE_STATE_AND_FORWARD_FIX",
    "INCIDENT_COMMAND_DECIDES_FORWARD_FIX_OR_ISOLATED_RESTORE",
}
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "rehearsalEvidenceCount",
    "passingRehearsalCount",
    "productionEquivalentRehearsalCount",
    "latestRehearsalRunId",
    "records",
    "limitations",
}


class Failure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Failure(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_contract_authority(registry_contract: dict[str, Any]) -> None:
    require(registry_contract.get("schemaVersion") == "memory-os-migration-evidence-registry-contract.v1", "migration evidence contract schema drift")
    require(registry_contract.get("migrationLifecycleContract") == str(LIFECYCLE.relative_to(ROOT)), "migration evidence lifecycle authority drift")
    require(registry_contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "migration evidence registry authority drift")
    require(registry_contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "migration evidence append lock authority drift")
    require(registry_contract.get("writer") == str(Path(__file__).resolve().relative_to(ROOT)), "migration evidence writer authority drift")
    require(registry_contract.get("appendOnly") is True, "migration evidence contract must remain append-only")
    require(registry_contract.get("productionEnvironmentRegistrationImplemented") is False, "migration evidence contract production boundary drift")
    require(set(registry_contract.get("allowedEnvironmentClasses", [])) == ENV_CLASSES, "migration evidence environment class authority drift")


def validated_generation_rows() -> list[dict[str, Any]]:
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_writer_for_migration_rehearsal")
    require(generation_writer.REGISTRY.resolve() == GEN_REGISTRY.resolve(), "environment generation writer registry authority drift")
    try:
        return generation_writer.validate_registry_for_append(generation_writer.load(GEN_REGISTRY))
    except generation_writer.Fail as exc:
        raise Failure(f"environment generation authority rejected: {exc}") from exc


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def require_source_ancestor(source: str) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, "sourceCommitSha must be an ancestor of current HEAD")


def timestamp(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be RFC3339 UTC")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise Failure(f"{field} invalid timestamp") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")
    return parsed


def validate_risks(value: Any) -> None:
    require(isinstance(value, list), "openRisks must be a list")
    seen: set[str] = set()
    for item in value:
        require(isinstance(item, dict), "open risk must be object")
        risk_id = item.get("riskId")
        owner = item.get("ownerRef")
        deadline = item.get("deadline")
        status = item.get("status")
        require(isinstance(risk_id, str) and risk_id.startswith("risk_"), "open risk riskId invalid")
        require(risk_id not in seen, "duplicate open risk")
        require(isinstance(owner, str) and owner.startswith("opr_"), "open risk ownerRef invalid")
        require(isinstance(deadline, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", deadline) is not None, "open risk deadline invalid")
        require(status in {"OPEN", "MITIGATED_PENDING_REVIEW"}, "open risk status invalid")
        seen.add(risk_id)


def validate_record(record: dict[str, Any], required_fields: set[str], registry_contract: dict[str, Any]) -> None:
    require(set(record) >= required_fields, f"record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-migration-rehearsal-evidence.v1", "record schema drift")
    run_id = record.get("migrationRunId")
    require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id) is not None, "migrationRunId invalid")
    env_class = record.get("environmentClass")
    require(env_class in ENV_CLASSES, "environmentClass invalid")
    digest = record.get("databaseIdentityDigest")
    require(isinstance(digest, str) and SHA256.fullmatch(digest) is not None, "databaseIdentityDigest invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None, "sourceCommitSha invalid")
    git("cat-file", "-e", source + "^{commit}")
    require_source_ancestor(source)

    lifecycle = load(LIFECYCLE)
    canonical = lifecycle.get("migrationSequence")
    require(isinstance(canonical, list) and canonical, "canonical migration sequence missing")
    before = record.get("migrationSequenceBefore")
    after = record.get("migrationSequenceAfter")
    require(isinstance(before, list) and all(isinstance(item, str) for item in before), "migrationSequenceBefore invalid")
    require(isinstance(after, list) and all(isinstance(item, str) for item in after), "migrationSequenceAfter invalid")
    require(before == canonical[:len(before)], "migrationSequenceBefore must be canonical prefix")
    require(after == canonical, "migrationSequenceAfter must equal canonical sequence")

    started = timestamp(record.get("startedAt"), "startedAt")
    completed = timestamp(record.get("completedAt"), "completedAt")
    require(completed >= started, "completedAt precedes startedAt")
    operator = record.get("operatorRef")
    reviewer = record.get("reviewerRef")
    require(isinstance(operator, str) and ACTOR.fullmatch(operator) is not None and operator.startswith("opr_"), "operatorRef invalid")
    require(isinstance(reviewer, str) and ACTOR.fullmatch(reviewer) is not None and reviewer.startswith("rev_"), "reviewerRef invalid")
    require(operator != reviewer, "operator and reviewer must be distinct")
    try:
        validate_recovery_point(record, env_class, canonical, registry_contract)
    except RecoveryPointFailure as exc:
        raise Failure(f"recovery evidence invalid: {exc}") from exc

    for field in ("lockBudgetMs", "statementBudgetMs", "observedLockWaitMs", "observedRuntimeMs"):
        require(isinstance(record.get(field), int) and not isinstance(record.get(field), bool) and record[field] >= 0, f"{field} invalid")
    require(record["lockBudgetMs"] > 0 and record["statementBudgetMs"] > 0, "budgets must be positive")
    for field in ("preflightResult", "applyResult", "verificationResult"):
        require(record.get(field) in RESULTS, f"{field} invalid")
    require(record.get("recoveryDecision") in RECOVERY, "recoveryDecision invalid")
    validate_risks(record.get("openRisks"))
    require(record.get("containsSecrets") is False, "record cannot contain secrets")
    require(record.get("productionTraffic") is False, "production traffic is forbidden")
    require(record.get("productionCredentials") is False, "production credentials are forbidden")
    require(record.get("productionEvidence") is False, "non-production registry cannot contain production evidence")

    passing = record.get("preflightResult") == "PASS" and record.get("applyResult") == "PASS" and record.get("verificationResult") == "PASS"
    if passing:
        require(record["observedLockWaitMs"] <= record["lockBudgetMs"], "passing rehearsal exceeded lock budget")
        require(record["observedRuntimeMs"] <= record["statementBudgetMs"], "passing rehearsal exceeded runtime budget")
        require(record.get("recoveryDecision") == "NO_RECOVERY_REQUIRED", "passing rehearsal must require no recovery")

    gen_id = record.get("environmentGenerationId")
    rows = validated_generation_rows()
    if env_class == "LOCAL_POSTGRES_REHEARSAL":
        require(gen_id is None, "local rehearsal must not claim environment generation")
    else:
        require(isinstance(gen_id, str) and gen_id, "production-equivalent rehearsal requires environmentGenerationId")
        require(any(isinstance(row, dict) and row.get("generationId") == gen_id for row in rows), "unknown production-equivalent environment generation")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer", "minioadmin",
        "secretaccesskey", "account_id", "session_id", "job_id", "preview_id", "object_key", "@",
    ):
        require(forbidden not in serialized, f"record contains forbidden content: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any], registry_contract: dict[str, Any]) -> None:
    validate_contract_authority(registry_contract)
    require(set(registry) == REGISTRY_FIELDS, "migration evidence registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-migration-evidence-registry.v1", "registry schema drift")
    require(registry.get("registryClass") == "NON_PRODUCTION_MIGRATION_REHEARSAL_EVIDENCE", "registry class drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False, "registry cannot claim production evidence")
    records = registry.get("records")
    require(isinstance(records, list) and all(isinstance(item, dict) for item in records), "registry records invalid")
    count = registry.get("rehearsalEvidenceCount")
    passing_count = registry.get("passingRehearsalCount")
    pe_count = registry.get("productionEquivalentRehearsalCount")
    for value, field in ((count, "rehearsalEvidenceCount"), (passing_count, "passingRehearsalCount"), (pe_count, "productionEquivalentRehearsalCount")):
        require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer")
    require(count == len(records), "rehearsalEvidenceCount drift")
    required = registry_contract.get("requiredRecordFields")
    require(isinstance(required, list) and all(isinstance(item, str) for item in required), "requiredRecordFields invalid")
    ids: set[str] = set()
    derived_passing = 0
    derived_pe = 0
    for index, record in enumerate(records):
        validate_record(record, set(required), registry_contract)
        run_id = record.get("migrationRunId")
        require(run_id not in ids, f"duplicate migrationRunId at records[{index}]: {run_id}")
        ids.add(run_id)
        if all(record.get(field) == "PASS" for field in ("preflightResult", "applyResult", "verificationResult")):
            derived_passing += 1
        if record.get("environmentClass") == "PRODUCTION_EQUIVALENT_REHEARSAL":
            derived_pe += 1
    require(passing_count == derived_passing, "passingRehearsalCount drift")
    require(pe_count == derived_pe, "productionEquivalentRehearsalCount drift")
    expected_latest = records[-1].get("migrationRunId") if records else None
    require(registry.get("latestRehearsalRunId") == expected_latest, "latestRehearsalRunId drift")
    limitations = registry.get("limitations")
    require(isinstance(limitations, list) and all(isinstance(item, str) and item for item in limitations), "registry limitations invalid")


def acquire_lock() -> int:
    try:
        return os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Failure("migration evidence registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    fd, name = tempfile.mkstemp(prefix=".migration-evidence-registry.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, REGISTRY)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def write_registry_transactionally(updated: dict[str, Any], previous: dict[str, Any], registry_contract: dict[str, Any]) -> None:
    atomic_write(updated)
    try:
        validate_registry_for_append(load(REGISTRY), registry_contract)
    except Exception:
        atomic_write(previous)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    require(args.confirm == CONFIRMATION, f"confirmation must equal: {CONFIRMATION}")
    record_path = Path(args.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Failure("input record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean before migration evidence registration")

    contract = load(CONTRACT)
    validate_contract_authority(contract)
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list) and all(isinstance(item, str) for item in required), "requiredRecordFields invalid")
    record = load(record_path)
    validate_record(record, set(required), contract)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, (record["migrationRunId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        validate_registry_for_append(registry, contract)
        previous = json.loads(json.dumps(registry))
        records = registry["records"]
        require(all(item.get("migrationRunId") != record["migrationRunId"] for item in records), "migrationRunId already registered")
        records.append(record)
        registry["rehearsalEvidenceCount"] = len(records)
        registry["passingRehearsalCount"] = sum(
            1 for item in records
            if item.get("preflightResult") == "PASS" and item.get("applyResult") == "PASS" and item.get("verificationResult") == "PASS"
        )
        registry["productionEquivalentRehearsalCount"] = sum(1 for item in records if item.get("environmentClass") == "PRODUCTION_EQUIVALENT_REHEARSAL")
        registry["latestRehearsalRunId"] = record["migrationRunId"]
        write_registry_transactionally(registry, previous, contract)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered non-production migration rehearsal: {record['migrationRunId']}")
    print("This registry never creates production migration evidence or Production readiness.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Failure as exc:
        print(f"MIGRATION REHEARSAL REGISTRATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
