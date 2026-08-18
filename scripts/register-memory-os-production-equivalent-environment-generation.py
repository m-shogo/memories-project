#!/usr/bin/env python3
"""Append one reviewed production-equivalent environment generation record."""

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
CANONICAL_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
CANONICAL_ENV_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
CANONICAL_GEN_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"
CANONICAL_ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
CONTRACT = CANONICAL_CONTRACT
REGISTRY = CANONICAL_REGISTRY
ENV_SCHEMA = CANONICAL_ENV_SCHEMA
GEN_SCHEMA = CANONICAL_GEN_SCHEMA
ENV_VALIDATOR = CANONICAL_ENV_VALIDATOR
LOCK = ROOT / "contracts/operations/.production-equivalent-environment-generation.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ENV_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
GEN_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,95}$")
REQUIRED = {
    "schemaVersion", "environmentId", "generationId", "registeredAt",
    "sourceCommitSha", "environmentManifestSha256", "dependencyInventorySha256",
    "evidenceBundleManifestSha256", "materialDeltaLedgerSha256", "environmentRecordRef",
    "environmentRecordSha256", "supersedesGenerationId", "productionTraffic",
    "productionCredentials", "productionEvidence", "productionReady",
}
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "registeredGenerationCount",
    "currentGenerationId",
    "generations",
    "limitations",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


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
    """Contain canonical runtime authority while permitting isolated test substitutions."""
    if ROOT == CANONICAL_ROOT and path == canonical:
        canonical_repo_file(path, field)


def require_canonical_runtime_authorities() -> None:
    require_canonical_runtime_authority(CONTRACT, CANONICAL_CONTRACT, "environment generation contract")
    require_canonical_runtime_authority(REGISTRY, CANONICAL_REGISTRY, "environment generation registry")
    require_canonical_runtime_authority(ENV_SCHEMA, CANONICAL_ENV_SCHEMA, "environment record schema")
    require_canonical_runtime_authority(GEN_SCHEMA, CANONICAL_GEN_SCHEMA, "generation record schema")
    require_canonical_runtime_authority(ENV_VALIDATOR, CANONICAL_ENV_VALIDATOR, "environment record semantic validator")
    if ROOT == CANONICAL_ROOT and CONTRACT == CANONICAL_CONTRACT:
        contract = load(CONTRACT)
        require(
            contract.get("bindingRules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "environment generation transactional append authority drift",
        )


def load_environment_validator():
    require_canonical_runtime_authority(ENV_VALIDATOR, CANONICAL_ENV_VALIDATOR, "environment record semantic validator")
    validator = canonical_repo_file(ENV_VALIDATOR, "environment record semantic validator")
    spec = importlib.util.spec_from_file_location("memory_os_environment_record_validator_for_generation_writer", validator)
    require(spec is not None and spec.loader is not None, "cannot load environment record semantic validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def require_source_commit_ancestor(source_commit: str) -> None:
    """Require source authority to belong to the current checked-out history."""
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode == 0:
        return
    require(completed.returncode == 1, "cannot verify sourceCommitSha ancestry")
    raise Fail("sourceCommitSha must be an ancestor of current HEAD")


def git_blob(source_commit: str, relative: str, field: str) -> bytes:
    require(isinstance(relative, str) and relative and ":" not in relative, f"{field} invalid for immutable source binding")
    completed = subprocess.run(
        ["git", "show", f"{source_commit}:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"{field} evidence missing from sourceCommitSha")
    return completed.stdout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_ref(value: Any, field: str) -> Path:
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
        raise Fail(f"{field} missing or escapes repository: {value}") from exc
    require(resolved == relative and absolute.is_file(), f"{field} must resolve to the canonical repository file")
    return absolute


def require_repo_file_bound_to_source(source_commit: str, path: Path, field: str) -> None:
    """Require one canonical repository file to match its bytes at sourceCommitSha."""
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise Fail(f"{field} escapes repository") from exc
    current = path.read_bytes()
    historical = git_blob(source_commit, relative, field)
    require(current == historical, f"{field} changed since sourceCommitSha")


def require_environment_evidence_bound_to_source(source_commit: str, env: dict[str, Any]) -> None:
    """Keep semantic generation evidence immutable against the registered source commit."""
    refs: list[tuple[Any, str]] = [
        (env.get("postgresql", {}).get("restoreEvidenceRef"), "postgresql.restoreEvidenceRef"),
        (env.get("objectStorage", {}).get("restoreEvidenceRef"), "objectStorage.restoreEvidenceRef"),
        (env.get("network", {}).get("latencyProfileRef"), "network.latencyProfileRef"),
        (env.get("network", {}).get("failureInjectionRef"), "network.failureInjectionRef"),
        (env.get("identityAndSecrets", {}).get("credentialScopeRef"), "identityAndSecrets.credentialScopeRef"),
        (env.get("backupRestore", {}).get("evidenceRef"), "backupRestore.evidenceRef"),
        (env.get("evidenceBoundary", {}).get("independentReviewRef"), "evidenceBoundary.independentReviewRef"),
    ]
    deltas = env.get("materialDeltas")
    if isinstance(deltas, list):
        for index, delta in enumerate(deltas):
            if isinstance(delta, dict):
                refs.append((delta.get("independentReviewRef"), f"materialDeltas[{index}].independentReviewRef"))

    checked: set[str] = set()
    for value, field in refs:
        if value is None:
            continue
        require(isinstance(value, str) and value, f"{field} invalid")
        if value in checked:
            continue
        require_repo_file_bound_to_source(source_commit, repo_ref(value, field), field)
        checked.add(value)


def validate_record(record: dict[str, Any]) -> bool:
    require_canonical_runtime_authorities()
    contract = load(CONTRACT)
    require(set(record) == REQUIRED, f"record field set drift: {sorted(set(record) ^ REQUIRED)}")
    require(record.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-record.v1", "schemaVersion drift")
    require(isinstance(record.get("environmentId"), str) and ENV_ID.fullmatch(record["environmentId"]), "environmentId invalid")
    require(isinstance(record.get("generationId"), str) and GEN_ID.fullmatch(record["generationId"]), "generationId invalid")
    require("latest" not in record["generationId"].casefold() and "current" not in record["generationId"].casefold(), "mutable generation aliases are forbidden")
    registered_at = record.get("registeredAt")
    require(isinstance(registered_at, str) and registered_at.endswith("Z"), "registeredAt must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(registered_at[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail("registeredAt must be UTC RFC3339 date-time") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "registeredAt must be UTC")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "sourceCommitSha does not exist")
    require_source_commit_ancestor(source)
    for field in (
        "environmentManifestSha256", "dependencyInventorySha256", "evidenceBundleManifestSha256",
        "materialDeltaLedgerSha256", "environmentRecordSha256",
    ):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} invalid")
    supersedes = record.get("supersedesGenerationId")
    require(supersedes is None or (isinstance(supersedes, str) and GEN_ID.fullmatch(supersedes)), "supersedesGenerationId invalid")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")

    env_path = repo_ref(record.get("environmentRecordRef"), "environmentRecordRef")
    require(record["environmentRecordSha256"] == sha256(env_path), "environmentRecordSha256 mismatch")
    require_repo_file_bound_to_source(source, env_path, "environmentRecordRef")
    env = load(env_path)
    env_validator = load_environment_validator()
    try:
        preflight_eligible = env_validator.validate_environment_record(
            env,
            expected_environment_id=record["environmentId"],
            expected_generation_id=record["generationId"],
        )
    except env_validator.Fail as exc:
        raise Fail(f"environment record semantic validation failed: {exc}") from exc
    require_environment_evidence_bound_to_source(source, env)

    require(contract.get("environmentRecordSchema") == str(ENV_SCHEMA.relative_to(ROOT)), "environment record schema ref drift")
    require(contract.get("environmentRecordSemanticValidator") == str(ENV_VALIDATOR.relative_to(ROOT)), "environment semantic validator ref drift")
    require(contract.get("generationRegistryRecordSchema") == str(GEN_SCHEMA.relative_to(ROOT)), "generation registry record schema ref drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "registry ref drift")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer",
        "password", "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@", "latest",
    ):
        require(forbidden not in serialized, f"generation record contains forbidden material: {forbidden}")
    return preflight_eligible


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject corrupted append-only generation authority instead of healing it on the next write."""
    require(set(registry) == REGISTRY_FIELDS, f"registry field set drift: {sorted(set(registry) ^ REGISTRY_FIELDS)}")
    require(
        registry.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-registry.v1",
        "registry schema drift",
    )
    require(registry.get("registryClass") == "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS", "registry class drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False, "registry production evidence boundary drift")
    rows = registry.get("generations")
    count = registry.get("registeredGenerationCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry generations invalid")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(rows), "registeredGenerationCount drift")

    ids: set[str] = set()
    prior_by_environment: dict[str, str] = {}
    for index, row in enumerate(rows):
        generation_id = row.get("generationId")
        environment_id = row.get("environmentId")
        require(isinstance(generation_id, str) and generation_id and generation_id not in ids, f"registry generations[{index}] generationId authority invalid")
        require(isinstance(environment_id, str) and environment_id, f"registry generations[{index}] environmentId invalid")
        ids.add(generation_id)
        expected_supersedes = prior_by_environment.get(environment_id)
        require(row.get("supersedesGenerationId") == expected_supersedes, f"supersedes chain drift for environment {environment_id}")
        prior_by_environment[environment_id] = generation_id
        validate_record(row)

    current_id = registry.get("currentGenerationId")
    if count == 0:
        require(current_id is None, "empty generation registry must have null currentGenerationId")
    else:
        require(current_id == rows[-1].get("generationId"), "currentGenerationId must equal latest append-only registry record")
    return rows


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".environment-generation.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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


def atomic_restore(payload: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".environment-generation-rollback.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
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
    except OSError as exc:
        raise Fail("cannot snapshot environment generation registry before append") from exc
    atomic_write(value)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        atomic_restore(original)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    input_path = Path(args.record).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input generation record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    require_canonical_runtime_authorities()
    record = load(input_path)
    preflight_eligible = validate_record(record)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("environment generation registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["generationId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        rows = validate_registry_for_append(registry)
        require(all(row.get("generationId") != record["generationId"] for row in rows), "generationId already registered")
        same_environment = [row for row in rows if row.get("environmentId") == record["environmentId"]]
        expected_supersedes = same_environment[-1].get("generationId") if same_environment else None
        require(record.get("supersedesGenerationId") == expected_supersedes, "supersedesGenerationId must reference the latest registered generation for this environment")
        rows.append(record)
        registry["registeredGenerationCount"] = len(rows)
        registry["currentGenerationId"] = record["generationId"]
        registry["productionEvidence"] = False
        registry["limitations"] = [
            "registered generations are non-production evidence until independent admission requirements are satisfied",
            "registration preserves planned/provisioned/rejected environment history and never implies restore-drill preflight eligibility",
            "preflight eligibility is independently re-derived from the full environment record and repository-resolvable evidence",
            "environmentId alone is never an evidence key",
            "generation registration does not by itself prove production-equivalent dependencies or application readiness"
        ]
        write_registry_transactionally(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered production-equivalent environment generation candidate: {record['generationId']}")
    print(f"Restore-drill preflight eligible now: {str(preflight_eligible).lower()}")
    print("Registration implies equivalence: false")
    print("Production evidence: false")
    print("Application production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
