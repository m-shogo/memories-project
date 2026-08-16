#!/usr/bin/env python3
"""Register one reviewed distributed rate-limit runtime evidence record."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json"
POLICY = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-distributed-runtime.py"
LOCK = ROOT / "contracts/operations/.rate-limit-distributed-runtime.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_ID = re.compile(r"^rlrt_[a-z0-9][a-z0-9_-]{7,63}$")
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION DISTRIBUTED RATE LIMIT RUNTIME EVIDENCE"
REF_FIELDS = (
    "sharedStoreEvidenceRefs", "trustedProxyEvidenceRefs", "restartContinuityEvidenceRefs",
    "failureModeEvidenceRefs", "emergencyExpiryEvidenceRefs", "deliveryAndAlertEvidenceRefs",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_runtime_validator_for_writer", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load distributed runtime validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_registry_before_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validator = load_validator()
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "distributed runtime registry validator authority drift")
    try:
        return validator.validate_registry_for_append(registry)
    except validator.Fail as exc:
        raise Fail(f"existing distributed runtime registry rejected before append: {exc}") from exc


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_refs(value: Any, field: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be non-empty")
    require(all(isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        require((ROOT / item).is_file(), f"{field} evidence path missing: {item}")
    return value


def validate_record(record: dict[str, Any], confirmation: str) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("runtimeId"), str) and RUNTIME_ID.fullmatch(record["runtimeId"]), "runtimeId invalid")
    environment = record.get("environmentClass")
    require(environment in contract.get("allowedEnvironmentClasses", []), "environmentClass invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "source commit does not exist")
    for field in ("environmentIdentityDigest", "sharedStoreIdentityDigest", "trustedProxyConfigurationDigest"):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} must be SHA-256 digest")
    instances = record.get("runtimeInstanceIdentityDigests")
    require(isinstance(instances, list) and len(instances) >= 2, "at least two runtime instance identities are required")
    require(all(isinstance(item, str) and DIGEST.fullmatch(item) for item in instances), "runtime instance identity digest invalid")
    require(len(instances) == len(set(instances)), "runtime instance identity digests must be distinct")
    policy_digest = record.get("policyContractSha256")
    require(isinstance(policy_digest, str) and DIGEST.fullmatch(policy_digest), "policyContractSha256 invalid")
    require(policy_digest == sha256(POLICY), "policyContractSha256 does not match canonical policy bytes")
    for field in REF_FIELDS:
        evidence_refs(record.get(field), field)
    for field in ("securityReviewRef", "operabilityReviewRef"):
        value = record.get(field)
        require(isinstance(value, str) and value and not Path(value).is_absolute() and ".." not in Path(value).parts and (ROOT / value).is_file(), f"{field} invalid")
    require(record["securityReviewRef"] != record["operabilityReviewRef"], "security and operability review records must be distinct")
    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be a list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(isinstance(finding.get("findingId"), str) and finding["findingId"], f"unresolvedFindings[{index}].findingId invalid")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "Critical/High findings block runtime admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")
    require(record.get("evidenceComplete") is True, "evidenceComplete must be true")
    require(record.get("productionReady") is False, "runtime evidence cannot make application productionReady")

    generation = record.get("environmentGenerationId")
    if environment == "PRODUCTION_EQUIVALENT":
        require(isinstance(generation, str) and generation, "production-equivalent runtime requires environmentGenerationId")
        generations = load(GEN_REGISTRY).get("generations")
        require(isinstance(generations, list) and any(isinstance(row, dict) and row.get("generationId") == generation for row in generations), "environmentGenerationId is not registered")
        require(record.get("productionEvidence") is False, "production-equivalent runtime cannot be production evidence")
    else:
        require(generation is None, "production runtime must not borrow production-equivalent generation id")
        require(confirmation == PRODUCTION_CONFIRMATION, f"production runtime requires confirmation: {PRODUCTION_CONFIRMATION}")
        require(record.get("productionEvidence") is True, "production runtime record must explicitly classify production evidence")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer",
        "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@",
    ):
        require(forbidden not in serialized, f"record contains forbidden runtime material: {forbidden}")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".rate-limit-runtime.", suffix=".tmp", dir=REGISTRY.parent)
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
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    record_path = Path(args.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(record_path)
    validate_record(record, args.confirm)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("distributed runtime registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["runtimeId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        runtimes = validate_registry_before_append(registry)
        require(all(item.get("runtimeId") != record["runtimeId"] for item in runtimes), "runtimeId already registered")
        require(all(item.get("environmentIdentityDigest") != record["environmentIdentityDigest"] for item in runtimes), "environment identity already registered")
        runtimes.append(record)
        registry["admittedRuntimeCount"] = len(runtimes)
        registry["productionEquivalentRuntimeCount"] = sum(1 for item in runtimes if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionRuntimeCount"] = sum(1 for item in runtimes if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered distributed rate-limit runtime evidence: {record['runtimeId']}")
    print("Application production readiness remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
