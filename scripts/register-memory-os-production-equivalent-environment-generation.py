#!/usr/bin/env python3
"""Append one reviewed production-equivalent environment generation record."""

from __future__ import annotations

import argparse
import hashlib
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
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_ref(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value and not Path(value).is_absolute(), f"{field} invalid")
    path = Path(value)
    require(".." not in path.parts, f"{field} traversal forbidden")
    absolute = ROOT / path
    require(absolute.is_file(), f"{field} missing: {value}")
    return absolute


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    require(set(record) == REQUIRED, f"record field set drift: {sorted(set(record) ^ REQUIRED)}")
    require(record.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-record.v1", "schemaVersion drift")
    require(isinstance(record.get("environmentId"), str) and ENV_ID.fullmatch(record["environmentId"]), "environmentId invalid")
    require(isinstance(record.get("generationId"), str) and GEN_ID.fullmatch(record["generationId"]), "generationId invalid")
    require("latest" not in record["generationId"].lower() and "current" not in record["generationId"].lower(), "mutable generation aliases are forbidden")
    registered_at = record.get("registeredAt")
    require(isinstance(registered_at, str), "registeredAt required")
    try:
        datetime.fromisoformat(registered_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fail("registeredAt must be ISO-8601 date-time") from exc
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
    require(env.get("schemaVersion") == "memory-os-production-equivalent-environment-record.v1", "environment record schema drift")
    require(env.get("environmentId") == record["environmentId"], "environmentId mismatch with environment record")
    require(env.get("generationId") == record["generationId"], "generationId mismatch with environment record")
    boundary = env.get("evidenceBoundary")
    topology = env.get("topology")
    identity = env.get("identityAndSecrets")
    require(isinstance(boundary, dict) and boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "environment record production boundary invalid")
    require(isinstance(topology, dict) and topology.get("productionTraffic") is False and topology.get("productionCredentials") is False, "environment record must remain non-production")
    require(isinstance(identity, dict) and identity.get("containsSecretMaterial") is False, "environment record contains secret material")

    require(contract.get("environmentRecordSchema") == str(ENV_SCHEMA.relative_to(ROOT)), "environment record schema ref drift")
    require(contract.get("generationRegistryRecordSchema") == str(GEN_SCHEMA.relative_to(ROOT)), "generation registry record schema ref drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "registry ref drift")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer",
        "password", "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@",
    ):
        require(forbidden not in serialized, f"generation record contains forbidden material: {forbidden}")


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
    validate_record(record)

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
    print("Production evidence: false")
    print("Application production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
