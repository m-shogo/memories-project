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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json"
POLICY = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-distributed-runtime.py"
LOCK = ROOT / "contracts/operations/.rate-limit-distributed-runtime.lock"
REVIEW_ROOT = Path("docs/evidence/rate-limit-distributed-runtime/independent-reviews")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_ID = re.compile(r"^rlrt_[a-z0-9][a-z0-9_-]{7,63}$")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION DISTRIBUTED RATE LIMIT RUNTIME EVIDENCE"
REF_FIELDS = (
    "sharedStoreEvidenceRefs", "trustedProxyEvidenceRefs", "restartContinuityEvidenceRefs",
    "failureModeEvidenceRefs", "emergencyExpiryEvidenceRefs", "deliveryAndAlertEvidenceRefs",
)
REVIEW_FIELDS = {
    "schemaVersion",
    "runtimeId",
    "environmentIdentityDigest",
    "role",
    "reviewerId",
    "decision",
    "reviewedAt",
    "productionTrafficChanged",
    "credentialsIncluded",
    "automaticProductionPromotion",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator() -> Any:
    return load_module(VALIDATOR, "memory_os_rate_limit_runtime_validator_for_writer")


def validate_registry_before_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validator = load_validator()
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "distributed runtime registry validator authority drift")
    try:
        return validator.validate_registry_for_append(registry)
    except validator.Fail as exc:
        raise Fail(f"existing distributed runtime registry rejected before append: {exc}") from exc


def validate_registry_after_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validator = load_validator()
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "distributed runtime registry validator authority drift")
    try:
        return validator.validate_registry_for_append(registry)
    except validator.Fail as exc:
        raise Fail(f"distributed runtime registry rejected after append: {exc}") from exc


def validated_generation_rows() -> list[dict[str, Any]]:
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_writer_for_rate_limit_runtime")
    require(generation_writer.REGISTRY.resolve() == GEN_REGISTRY.resolve(), "environment generation writer registry authority drift")
    try:
        return generation_writer.validate_registry_for_append(generation_writer.load(GEN_REGISTRY))
    except generation_writer.Fail as exc:
        raise Fail(f"environment generation authority rejected: {exc}") from exc


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def git_bytes(*args: str) -> bytes:
    completed = subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout


def require_source_ancestor(source: str) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    require(completed.returncode == 0, "sourceCommitSha must be an ancestor of current HEAD")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_evidence_path(item: str, field: str) -> Path:
    require(isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts, f"{field} invalid: {item!r}")
    candidate = ROOT / item
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} evidence path invalid: {item}") from exc
    require(resolved.is_file(), f"{field} evidence path missing: {item}")
    current = ROOT
    for part in Path(item).parts:
        current = current / part
        require(not current.is_symlink(), f"{field} evidence path cannot traverse symlink: {item}")
    git("ls-files", "--error-unmatch", "--", item)
    require(git_bytes("show", f"HEAD:{item}") == resolved.read_bytes(), f"{field} evidence must match committed HEAD bytes: {item}")
    return resolved


def evidence_refs(value: Any, field: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be non-empty")
    require(all(isinstance(item, str) and item for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        canonical_evidence_path(item, field)
    return value


def validate_evidence_digest_authority(paths: list[str], value: Any) -> None:
    require(len(paths) == len(set(paths)), "runtime evidence refs must be globally distinct")
    require(isinstance(value, dict), "evidenceDigests must be an object")
    require(set(value) == set(paths), "evidenceDigests path set drift")
    for item in paths:
        digest = value.get(item)
        require(isinstance(digest, str) and DIGEST.fullmatch(digest), f"evidenceDigests[{item}] must be SHA-256")
        path = canonical_evidence_path(item, "evidenceDigests")
        require(digest == sha256(path), f"evidenceDigests[{item}] does not match current committed bytes")


def canonical_reviewed_at(value: Any, field: str) -> None:
    require(isinstance(value, str) and UTC_SECOND.fullmatch(value), f"{field}.reviewedAt must be canonical UTC RFC3339 seconds")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fail(f"{field}.reviewedAt invalid") from exc
    require(parsed.tzinfo == timezone.utc, f"{field}.reviewedAt must be UTC")


def validate_review(record: dict[str, Any], ref_field: str, expected_role: str) -> str:
    ref = record.get(ref_field)
    require(
        isinstance(ref, str) and Path(ref).is_relative_to(REVIEW_ROOT),
        f"{ref_field} must use monitored rate-limit independent review namespace",
    )
    path = canonical_evidence_path(ref, ref_field)
    review = load(path)
    require(set(review) == REVIEW_FIELDS, f"{ref_field} review field drift")
    require(review.get("schemaVersion") == "memory-os-rate-limit-runtime-independent-review.v1", f"{ref_field} schemaVersion drift")
    require(review.get("runtimeId") == record.get("runtimeId"), f"{ref_field} runtimeId binding drift")
    require(review.get("environmentIdentityDigest") == record.get("environmentIdentityDigest"), f"{ref_field} environment identity binding drift")
    require(review.get("role") == expected_role, f"{ref_field} role must be {expected_role}")
    reviewer = review.get("reviewerId")
    require(isinstance(reviewer, str) and REVIEWER_ID.fullmatch(reviewer), f"{ref_field} reviewerId invalid")
    require(review.get("decision") == "APPROVED", f"{ref_field} must be APPROVED")
    canonical_reviewed_at(review.get("reviewedAt"), ref_field)
    require(review.get("productionTrafficChanged") is False, f"{ref_field} cannot change production traffic")
    require(review.get("credentialsIncluded") is False, f"{ref_field} cannot include credentials")
    require(review.get("automaticProductionPromotion") is False, f"{ref_field} cannot authorize automatic production promotion")
    return reviewer


def validate_independent_reviews(record: dict[str, Any]) -> None:
    security_reviewer = validate_review(record, "securityReviewRef", "SECURITY")
    operability_reviewer = validate_review(record, "operabilityReviewRef", "OPERABILITY")
    require(record["securityReviewRef"] != record["operabilityReviewRef"], "security and operability review records must be distinct")
    require(security_reviewer != operability_reviewer, "security and operability reviewers must be distinct")


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
    require_source_ancestor(source)
    for field in ("environmentIdentityDigest", "sharedStoreIdentityDigest", "trustedProxyConfigurationDigest"):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} must be SHA-256 digest")
    instances = record.get("runtimeInstanceIdentityDigests")
    require(isinstance(instances, list) and len(instances) >= 2, "at least two runtime instance identities are required")
    require(all(isinstance(item, str) and DIGEST.fullmatch(item) for item in instances), "runtime instance identity digest invalid")
    require(len(instances) == len(set(instances)), "runtime instance identity digests must be distinct")
    policy_digest = record.get("policyContractSha256")
    require(isinstance(policy_digest, str) and DIGEST.fullmatch(policy_digest), "policyContractSha256 invalid")
    require(policy_digest == sha256(POLICY), "policyContractSha256 does not match canonical policy bytes")
    all_evidence_refs: list[str] = []
    for field in REF_FIELDS:
        all_evidence_refs.extend(evidence_refs(record.get(field), field))
    for field in ("securityReviewRef", "operabilityReviewRef"):
        value = record.get(field)
        require(isinstance(value, str) and value, f"{field} invalid")
        canonical_evidence_path(value, field)
        all_evidence_refs.append(value)
    validate_evidence_digest_authority(all_evidence_refs, record.get("evidenceDigests"))
    validate_independent_reviews(record)
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
        generations = validated_generation_rows()
        require(any(row.get("generationId") == generation for row in generations), "environmentGenerationId is not registered in valid generation authority")
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


def atomic_restore(original: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".rate-limit-runtime-rollback.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def commit_registry_update(registry: dict[str, Any], original: bytes) -> None:
    atomic_write(registry)
    try:
        validate_registry_after_append(load(REGISTRY))
    except Exception:
        atomic_restore(original)
        raise


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
        original_registry = REGISTRY.read_bytes()
        registry = json.loads(original_registry.decode("utf-8"))
        require(isinstance(registry, dict), "distributed runtime registry root must be object")
        runtimes = validate_registry_before_append(registry)
        require(all(item.get("runtimeId") != record["runtimeId"] for item in runtimes), "runtimeId already registered")
        require(all(item.get("environmentIdentityDigest") != record["environmentIdentityDigest"] for item in runtimes), "environment identity already registered")
        runtimes.append(record)
        registry["admittedRuntimeCount"] = len(runtimes)
        registry["productionEquivalentRuntimeCount"] = sum(1 for item in runtimes if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionRuntimeCount"] = sum(1 for item in runtimes if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        commit_registry_update(registry, original_registry)
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
