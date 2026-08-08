#!/usr/bin/env python3
"""Append one typed non-resurrection evidence record for backup/restore admission."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_EVIDENCE_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
LOCK = ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RECORD_ID = re.compile(r"^brnr_[a-z0-9][a-z0-9_-]{7,63}$")

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

def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value and not Path(value).is_absolute(), f"{field} invalid")
    path = Path(value)
    require(".." not in path.parts and (ROOT / path).is_file(), f"{field} evidence path missing")
    return value

def generation_record(evidence_id: Any) -> dict[str, Any]:
    require(isinstance(evidence_id, str) and evidence_id, "generationEvidenceId required")
    registry = load(GEN_EVIDENCE_REGISTRY)
    rows = registry.get("records")
    require(isinstance(rows, list), "generation evidence registry records invalid")
    matches = [row for row in rows if isinstance(row, dict) and row.get("evidenceId") == evidence_id]
    require(len(matches) == 1, "generationEvidenceId is not uniquely registered")
    return matches[0]

def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required_fields = set(contract.get("requiredRecordFields", []))
    required_domains = tuple(contract.get("requiredDomains", []))
    require(required_fields and required_domains, "non-resurrection contract incomplete")
    require(set(record) == required_fields, f"record field set drift: {sorted(set(record) ^ required_fields)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("recordId"), str) and RECORD_ID.fullmatch(record["recordId"]), "recordId invalid")
    generation = generation_record(record.get("generationEvidenceId"))
    source_sha = record.get("sourceCommitSha")
    require(isinstance(source_sha, str) and SHA40.fullmatch(source_sha), "sourceCommitSha invalid")
    require(source_sha == generation.get("sourceCommitSha"), "sourceCommitSha must match generation recovery evidence")

    prefixes = contract.get("domainEvidencePathPrefixes")
    require(isinstance(prefixes, dict) and set(prefixes) == set(required_domains), "domainEvidencePathPrefixes drift")
    domains = record.get("domains")
    require(isinstance(domains, dict) and set(domains) == set(required_domains), "domain coverage drift")
    refs_seen: set[str] = set()
    for name in required_domains:
        entry = domains.get(name)
        require(isinstance(entry, dict) and set(entry) == {"result", "evidenceRef"}, f"domain {name} field drift")
        require(entry.get("result") in {"PASS", "FAIL", "NOT_RUN"}, f"domain {name} result invalid")
        evidence_ref = repo_ref(entry.get("evidenceRef"), f"domains.{name}.evidenceRef")
        prefix = prefixes.get(name)
        require(isinstance(prefix, str) and evidence_ref.startswith(prefix) and evidence_ref.endswith(".json"), f"domain {name} evidence path is not typed")
        require(evidence_ref not in refs_seen, f"domain {name} evidenceRef must be distinct")
        refs_seen.add(evidence_ref)

    security = repo_ref(record.get("securityReviewRef"), "securityReviewRef")
    operability = repo_ref(record.get("operabilityReviewRef"), "operabilityReviewRef")
    require(security != operability, "security and operability reviews must be distinct")
    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL findings block admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}] status invalid")
    require(isinstance(record.get("evidenceComplete"), bool), "evidenceComplete must be boolean")
    complete = all(domains[name]["result"] == "PASS" for name in required_domains) and not findings
    require(record.get("evidenceComplete") is complete, "evidenceComplete derivation drift")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@", "latest"):
        require(forbidden not in serialized, f"record contains forbidden recovery material: {forbidden}")

def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_recovery_writer", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def candidate_complete(record: dict[str, Any]) -> bool:
    """Return whether this typed record covers a generation record that passed all pre-overlay gates."""
    generation = generation_record(record.get("generationEvidenceId"))
    generation_writer = load_generation_writer()
    return record.get("evidenceComplete") is True and generation_writer.base_candidate(generation)

def atomic_write(value: dict[str, Any]) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-non-resurrection.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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
        raise Fail("input non-resurrection evidence must be outside repository")
    record = load(input_path)
    validate_record(record)
    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("non-resurrection admission registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["recordId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        require(registry.get("appendOnly") is True, "registry must remain append-only")
        rows = registry.get("records")
        require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "registry records invalid")
        require(all(row.get("recordId") != record["recordId"] for row in rows), "recordId already registered")
        require(all(row.get("generationEvidenceId") != record["generationEvidenceId"] for row in rows), "generationEvidenceId already has non-resurrection evidence")
        rows.append(record)
        registry["registeredRecordCount"] = len(rows)
        registry["completeRecordCount"] = sum(1 for row in rows if row.get("evidenceComplete") is True)
        registry["candidateCoveredCount"] = sum(1 for row in rows if candidate_complete(row))
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered backup/restore non-resurrection evidence: {record['recordId']}")
    print(f"pre-overlay candidate covered: {str(candidate_complete(record)).lower()}")
    print("production evidence: false")
    print("production ready: false")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
