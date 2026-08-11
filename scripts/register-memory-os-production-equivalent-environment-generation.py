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
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
ENV_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
GEN_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"
ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
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
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to its canonical repository file")
    return path


def load_environment_validator():
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
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository: {value}") from exc
    require(resolved == relative and absolute.is_file(), f"{field} must resolve to the canonical repository file")
    return absolute


def validate_record(record: dict[str, Any]) -> bool:
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
        require(registry.get("appendOnly") is True, "registry must remain append-only")
        rows = registry.get("generations")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry generations invalid")
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
        atomic_write(registry)
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
