#!/usr/bin/env python3
"""Append one reviewed approved-release compatibility pair."""

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
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair-independent-review.py"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
LOCK = ROOT / "contracts/operations/.release-compatibility-pair.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PAIR_ID = re.compile(r"^rcp_[a-z0-9][a-z0-9_-]{7,63}$")
EVIDENCE_FIELDS = (
    "rollingDeploymentEvidenceRefs",
    "applicationRollbackEvidenceRefs",
    "persistedRouteEvidenceRefs",
    "databaseUpgradeEvidenceRefs",
    "artifactRetentionEvidenceRefs",
    "independentReviewRefs",
)
REGISTRY_FIELDS = {
    "schemaVersion",
    "appendOnly",
    "approvedPairCount",
    "rollbackEligiblePairCount",
    "latestPairId",
    "pairs",
    "productionEvidence",
    "productionReady",
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
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def validate_contract_authority() -> dict[str, Any]:
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-release-compatibility-pair.v1", "pair contract schema drift")
    require(contract.get("releaseRegistry") == str(RELEASES.relative_to(ROOT)), "pair release registry authority drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "pair registry authority drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "pair append lock authority drift")
    require(contract.get("writer") == str(Path(__file__).resolve().relative_to(ROOT)), "pair writer authority drift")
    require(contract.get("independentReviewValidator") == str(INDEPENDENT_REVIEW_VALIDATOR.relative_to(ROOT)), "pair independent review validator authority drift")
    require(contract.get("independentReviewEvidenceRoot") == "docs/evidence/release-compatibility-pairs/reviews", "pair independent review evidence root drift")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "pair contract rules must remain fail-closed")
    require(rules.get("appendLockMustRemainCanonical") is True, "pair append lock rule drift")
    require(rules.get("exactlyTwoTypedIndependentReviewsRequired") is True, "pair typed independent review rule drift")
    require(rules.get("independentReviewsCannotAuthorizeAutomaticPromotion") is True, "pair automatic promotion boundary drift")
    require(rules.get("productionEvidenceForbidden") is True and rules.get("productionReadyForbidden") is True, "pair production boundary drift")
    return contract


def repo_regular_file(ref: str, field: str) -> Path:
    require(isinstance(ref, str) and ref and not Path(ref).is_absolute() and ".." not in Path(ref).parts, f"{field} invalid reference")
    path = ROOT / ref
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise Fail(f"{field} evidence escapes repository or is unreadable: {ref}") from exc
    cursor = path
    while cursor != ROOT:
        require(not cursor.is_symlink(), f"{field} evidence path contains symlink: {ref}")
        cursor = cursor.parent
    require(path.is_file(), f"{field} evidence missing or not regular file: {ref}")
    head_blob = git("rev-parse", f"HEAD:{ref}")
    current_blob = git("hash-object", "--", ref)
    require(SHA40.fullmatch(head_blob) is not None and current_blob == head_blob, f"{field} evidence must be tracked and equal current HEAD: {ref}")
    return path


def evidence_refs(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} reference(s)")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for ref in value:
        repo_regular_file(ref, field)
    return value


def digest_file(ref: str) -> str:
    return hashlib.sha256(repo_regular_file(ref, "evidenceDigestsByField").read_bytes()).hexdigest()


def compute_evidence_digests(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for field in EVIDENCE_FIELDS:
        minimum = 2 if field == "independentReviewRefs" else 1
        refs = evidence_refs(record.get(field), field, minimum=minimum)
        result[field] = {ref: digest_file(ref) for ref in refs}
    return result


def bind_evidence_digests(record: dict[str, Any]) -> None:
    record["evidenceDigestsByField"] = compute_evidence_digests(record)


def validate_evidence_digests(record: dict[str, Any]) -> None:
    digests = record.get("evidenceDigestsByField")
    require(isinstance(digests, dict) and set(digests) == set(EVIDENCE_FIELDS), "pair evidence digest field set drift")
    expected = compute_evidence_digests(record)
    for field in EVIDENCE_FIELDS:
        field_digests = digests.get(field)
        require(isinstance(field_digests, dict), f"{field} digest authority must be object")
        require(set(field_digests) == set(expected[field]), f"{field} digest reference set drift")
        for ref, digest in field_digests.items():
            require(isinstance(digest, str) and SHA256.fullmatch(digest), f"{field} digest invalid: {ref}")
            require(digest == expected[field][ref], f"{field} evidence digest drift: {ref}")


def validated_release_registry() -> dict[str, Any]:
    release_registry = load(RELEASES)
    release_contract = load(RELEASE_CONTRACT)
    release_writer = load_module(RELEASE_WRITER, "memory_os_release_baseline_writer_for_pair")
    try:
        release_writer.validate_registry_for_append(release_registry, release_contract)
    except Exception as exc:
        raise Fail(f"approved release registry authority invalid: {exc}") from exc
    return release_registry


def validate_typed_independent_reviews(record: dict[str, Any]) -> None:
    review_validator = load_module(INDEPENDENT_REVIEW_VALIDATOR, "memory_os_release_pair_review_validator_for_writer")
    try:
        review_validator.validate_pair_reviews(record)
    except Exception as exc:
        raise Fail(f"typed independent review authority invalid: {exc}") from exc


def approved_release(releases: list[Any], release_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(release_id, str) and release_id, f"{field} required")
    matches = [row for row in releases if isinstance(row, dict) and row.get("releaseId") == release_id]
    require(len(matches) == 1, f"{field} is not uniquely approved")
    record = matches[0]
    require(record.get("approvalClass") == "PRODUCTION_RELEASE_BASELINE", f"{field} approval class drift")
    require(record.get("evidenceComplete") is True and record.get("productionReady") is True, f"{field} is not a complete approved release baseline")
    return record


def rollback_status(record: dict[str, Any]) -> str:
    rollback = record.get("rollbackEligibility")
    require(isinstance(rollback, dict), "approved release rollbackEligibility must be an object")
    status = rollback.get("status")
    require(isinstance(status, str), "approved release rollback status missing")
    return status


def validate_record(record: dict[str, Any]) -> None:
    contract = validate_contract_authority()
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"pair record field drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "pair schemaVersion drift")
    pair_id = record.get("pairId")
    require(isinstance(pair_id, str) and PAIR_ID.fullmatch(pair_id), "pairId invalid")

    release_registry = validated_release_registry()
    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry invalid")
    predecessor = approved_release(releases, record.get("predecessorReleaseId"), "predecessorReleaseId")
    successor = approved_release(releases, record.get("successorReleaseId"), "successorReleaseId")
    require(predecessor.get("releaseId") != successor.get("releaseId"), "predecessor and successor must be distinct releases")
    for field, release in (("predecessorCommitSha", predecessor), ("successorCommitSha", successor)):
        sha = record.get(field)
        require(isinstance(sha, str) and SHA40.fullmatch(sha), f"{field} invalid")
        require(sha == release.get("commitSha"), f"{field} does not match approved release registry")
        require(git("cat-file", "-e", sha + "^{commit}") == "", f"{field} commit absent from repository history")
    require(rollback_status(predecessor) == "ELIGIBLE", "predecessor must be rollback ELIGIBLE")

    evidence_refs(record.get("rollingDeploymentEvidenceRefs"), "rollingDeploymentEvidenceRefs")
    evidence_refs(record.get("applicationRollbackEvidenceRefs"), "applicationRollbackEvidenceRefs")
    evidence_refs(record.get("persistedRouteEvidenceRefs"), "persistedRouteEvidenceRefs")
    evidence_refs(record.get("databaseUpgradeEvidenceRefs"), "databaseUpgradeEvidenceRefs")
    evidence_refs(record.get("artifactRetentionEvidenceRefs"), "artifactRetentionEvidenceRefs")
    reviews = evidence_refs(record.get("independentReviewRefs"), "independentReviewRefs", minimum=2)
    require(len(set(reviews)) >= 2, "independentReviewRefs must contain at least two distinct references")
    validate_evidence_digests(record)

    approved_at = record.get("approvedAt")
    require(isinstance(approved_at, str), "approvedAt required")
    try:
        parsed = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fail("approvedAt must be ISO-8601 date-time") from exc
    require(parsed.tzinfo is not None, "approvedAt must include timezone")

    findings = record.get("openFindings")
    require(isinstance(findings, list), "openFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"openFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "CRITICAL/HIGH findings forbid pair admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"openFindings[{index}] status invalid")
    require(record.get("pairEvidenceComplete") is True, "pairEvidenceComplete must be true for admission")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, "pair admission cannot promote production")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password",
        "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@", "latest", "candidate_only_local_ci",
    ):
        require(forbidden not in serialized, f"pair record contains forbidden material: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any]) -> None:
    validate_contract_authority()
    require(set(registry) == REGISTRY_FIELDS, "pair registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-release-compatibility-pair-registry.v1", "pair registry schema drift")
    require(registry.get("appendOnly") is True, "pair registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "pair registry cannot promote production")
    pairs = registry.get("pairs")
    require(isinstance(pairs, list) and all(isinstance(row, dict) for row in pairs), "pair registry invalid")
    count = registry.get("approvedPairCount")
    rollback_count = registry.get("rollbackEligiblePairCount")
    require(isinstance(count, int) and not isinstance(count, bool), "approvedPairCount must be integer")
    require(isinstance(rollback_count, int) and not isinstance(rollback_count, bool), "rollbackEligiblePairCount must be integer")
    require(count == len(pairs), "approvedPairCount drift")
    require(rollback_count == count, "rollbackEligiblePairCount drift")
    ids: set[str] = set()
    relations: set[tuple[Any, Any]] = set()
    for row in pairs:
        validate_record(row)
        validate_typed_independent_reviews(row)
        pair_id = row.get("pairId")
        relation = (row.get("predecessorReleaseId"), row.get("successorReleaseId"))
        require(pair_id not in ids, f"duplicate pairId: {pair_id}")
        require(relation not in relations, f"duplicate predecessor/successor pair: {relation}")
        ids.add(pair_id)
        relations.add(relation)
    require(registry.get("latestPairId") == (pairs[-1].get("pairId") if pairs else None), "latestPairId drift")
    limitations = registry.get("limitations")
    require(isinstance(limitations, list) and limitations and all(isinstance(item, str) and item.strip() for item in limitations), "pair registry limitations invalid")
    release_registry = validated_release_registry()
    release_count = release_registry.get("approvedReleaseCount")
    require(isinstance(release_count, int) and not isinstance(release_count, bool), "approved release count invalid")
    if release_count < 2:
        require(count == 0, "approved pair cannot exist with fewer than two approved releases")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".release-pair.", suffix=".tmp", dir=REGISTRY.parent)
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
        raise Fail("input pair record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    bind_evidence_digests(record)
    validate_record(record)
    validate_typed_independent_reviews(record)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("release compatibility pair registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["pairId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        pairs = registry["pairs"]
        require(all(row.get("pairId") != record["pairId"] for row in pairs), "pairId already registered")
        require(all(not (row.get("predecessorReleaseId") == record["predecessorReleaseId"] and row.get("successorReleaseId") == record["successorReleaseId"]) for row in pairs), "release pair already registered")
        pairs.append(record)
        registry["approvedPairCount"] = len(pairs)
        registry["rollbackEligiblePairCount"] = len(pairs)
        registry["latestPairId"] = record["pairId"]
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        registry["limitations"] = [
            "approved release pairs are compatibility admission evidence, not application production readiness",
            "pair-specific rolling/rollback/persisted-route/database/artifact evidence must remain available and digest-bound to the admitted pair",
            "independent Security and Operability reviews must remain typed, pair-bound, role-separated, digest-bound and non-promoting",
            "candidate/local mixed-version evidence cannot substitute approved release baselines"
        ]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered approved release compatibility pair: {record['pairId']}")
    print("Production evidence: false")
    print("Production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
