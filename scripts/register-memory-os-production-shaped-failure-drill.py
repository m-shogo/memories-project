#!/usr/bin/env python3
"""Register one production-shaped failure-drill evidence record."""

from __future__ import annotations

import argparse
import datetime as dt
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
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-shaped-failure-drills.py"
LOCK = ROOT / "contracts/operations/.production-shaped-failure-drill.lock"
REVIEW_ROOT = Path("docs/evidence/production-shaped-failure-drills/independent-reviews")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
DRILL_ID = re.compile(r"^fdr_[a-z0-9][a-z0-9_-]{7,63}$")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION FAILURE DRILL EVIDENCE"
REVIEW_FIELDS = {
    "schemaVersion",
    "drillId",
    "scenarioId",
    "environmentClass",
    "environmentIdentityDigest",
    "environmentGenerationId",
    "sourceCommitSha",
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


def validate_registry_before_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validator = load_module(VALIDATOR, "memory_os_production_failure_validator_for_writer")
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "failure-drill registry validator authority drift")
    require(validator.WRITER.resolve() == Path(__file__).resolve(), "failure-drill writer validator authority drift")
    try:
        return validator.validate_registry_for_append(registry)
    except validator.Fail as exc:
        raise Fail(f"existing failure-drill registry rejected before append: {exc}") from exc


def validated_generation_rows() -> list[dict[str, Any]]:
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_writer_for_failure_drill")
    require(generation_writer.REGISTRY.resolve() == GEN_REGISTRY.resolve(), "environment generation writer registry authority drift")
    try:
        return generation_writer.validate_registry_for_append(generation_writer.load(GEN_REGISTRY))
    except generation_writer.Fail as exc:
        raise Fail(f"environment generation authority rejected: {exc}") from exc


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def require_source_commit_ancestor(source_commit: str) -> None:
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


def head_blob(relative: str, field: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"{field} must be tracked at current HEAD")
    return completed.stdout


def canonical_evidence_path(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be a canonical repository-relative path")
    absolute = ROOT / relative
    try:
        resolved = absolute.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository: {value}") from exc
    require(resolved == relative and absolute.is_file(), f"{field} must resolve to the canonical repository file")
    require(absolute.read_bytes() == head_blob(value, field), f"{field} working bytes differ from current HEAD")
    return absolute


def timestamp(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")
    return parsed


def canonical_reviewed_at(value: Any, field: str) -> None:
    require(isinstance(value, str) and UTC_SECOND.fullmatch(value), f"{field}.reviewedAt must be canonical UTC RFC3339 seconds")
    parsed = timestamp(value, f"{field}.reviewedAt")
    require(parsed.microsecond == 0, f"{field}.reviewedAt must not include fractional seconds")


def refs(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} ref(s)")
    require(all(isinstance(item, str) and item for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        canonical_evidence_path(item, field)
    return value


def scenario_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = contract.get("scenarioClasses")
    require(isinstance(rows, list) and rows, "scenarioClasses missing")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("id"), str), "scenario class invalid")
        require(row["id"] not in result, "duplicate scenario class")
        result[row["id"]] = row
    return result


def evidence_refs_for_record(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    assertions = record.get("assertions")
    if isinstance(assertions, list):
        for row in assertions:
            if isinstance(row, dict) and isinstance(row.get("evidenceRefs"), list):
                values.extend(item for item in row["evidenceRefs"] if isinstance(item, str))
    for field in ("operabilityReviewRef", "securityReviewRef"):
        value = record.get(field)
        if isinstance(value, str):
            values.append(value)
    return sorted(set(values))


def evidence_digests_for_record(record: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in evidence_refs_for_record(record):
        path = canonical_evidence_path(relative, "failure-drill evidence ref")
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_review_payload(review: dict[str, Any], record: dict[str, Any], field: str, expected_role: str) -> str:
    require(set(review) == REVIEW_FIELDS, f"{field} review field drift")
    require(review.get("schemaVersion") == "memory-os-production-shaped-failure-drill-independent-review.v1", f"{field} schemaVersion drift")
    for key in (
        "drillId",
        "scenarioId",
        "environmentClass",
        "environmentIdentityDigest",
        "environmentGenerationId",
        "sourceCommitSha",
    ):
        require(review.get(key) == record.get(key), f"{field} {key} binding drift")
    require(review.get("role") == expected_role, f"{field} role must be {expected_role}")
    reviewer = review.get("reviewerId")
    require(isinstance(reviewer, str) and REVIEWER_ID.fullmatch(reviewer), f"{field} reviewerId invalid")
    require(review.get("decision") == "APPROVED", f"{field} must be APPROVED")
    canonical_reviewed_at(review.get("reviewedAt"), field)
    require(review.get("productionTrafficChanged") is False, f"{field} cannot change production traffic")
    require(review.get("credentialsIncluded") is False, f"{field} cannot include credentials")
    require(review.get("automaticProductionPromotion") is False, f"{field} cannot authorize automatic production promotion")
    return reviewer


def validate_review(record: dict[str, Any], ref_field: str, expected_role: str) -> str:
    review_ref = record.get(ref_field)
    require(
        isinstance(review_ref, str) and Path(review_ref).is_relative_to(REVIEW_ROOT),
        f"{ref_field} must use monitored failure-drill independent review namespace",
    )
    path = canonical_evidence_path(review_ref, ref_field)
    try:
        review = load(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{ref_field} must be typed JSON review evidence") from exc
    return validate_review_payload(review, record, ref_field, expected_role)


def validate_independent_reviews(record: dict[str, Any]) -> None:
    security_reviewer = validate_review(record, "securityReviewRef", "SECURITY")
    operability_reviewer = validate_review(record, "operabilityReviewRef", "OPERABILITY")
    require(record["securityReviewRef"] != record["operabilityReviewRef"], "security and operability review records must be distinct")
    require(security_reviewer != operability_reviewer, "security and operability reviewers must be distinct")


def validate_record(record: dict[str, Any], confirmation: str) -> None:
    contract = load(CONTRACT)
    scenarios = scenario_map(contract)
    required_fields = {
        "schemaVersion", "drillId", "scenarioId", "environmentClass",
        "sourceCommitSha", "environmentIdentityDigest", "environmentGenerationId",
        "failureControllerIdentityDigest", "dependencyIdentityDigests",
        "startedAt", "failedAt", "recoveredAt", "syntheticAccountsOnly",
        "productionTraffic", "assertions", "operabilityReviewRef", "securityReviewRef",
        "unresolvedFindings", "productionEvidence", "productionReady"
    }
    require(set(record) == required_fields, f"record field set drift: {sorted(set(record) ^ required_fields)}")
    require(record.get("schemaVersion") == "memory-os-production-shaped-failure-drill-record.v1", "record schema drift")
    require(isinstance(record.get("drillId"), str) and DRILL_ID.fullmatch(record["drillId"]), "drillId invalid")
    scenario_id = record.get("scenarioId")
    require(isinstance(scenario_id, str) and scenario_id in scenarios, "scenarioId invalid")
    environment = record.get("environmentClass")
    require(environment in contract.get("allowedEnvironmentClasses", []), "environmentClass invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "source commit does not exist")
    require_source_commit_ancestor(source)
    for field in ("environmentIdentityDigest", "failureControllerIdentityDigest"):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} invalid")
    dependency_digests = record.get("dependencyIdentityDigests")
    require(isinstance(dependency_digests, list) and dependency_digests, "dependencyIdentityDigests must be non-empty")
    require(all(isinstance(item, str) and DIGEST.fullmatch(item) for item in dependency_digests), "dependencyIdentityDigests invalid")
    require(len(dependency_digests) == len(set(dependency_digests)), "dependencyIdentityDigests duplicated")
    started = timestamp(record.get("startedAt"), "startedAt")
    failed = timestamp(record.get("failedAt"), "failedAt")
    recovered = timestamp(record.get("recoveredAt"), "recoveredAt")
    require(started <= failed <= recovered, "drill timestamps out of order")

    generation = record.get("environmentGenerationId")
    if environment == "PRODUCTION_EQUIVALENT":
        require(record.get("syntheticAccountsOnly") is True, "production-equivalent drill requires synthetic accounts only")
        require(record.get("productionTraffic") is False, "production-equivalent drill cannot use production traffic")
        require(record.get("productionEvidence") is False, "production-equivalent drill cannot be production evidence")
        require(isinstance(generation, str) and generation, "production-equivalent drill requires generation id")
        generations = validated_generation_rows()
        require(any(row.get("generationId") == generation for row in generations), "environment generation not registered in valid generation authority")
    else:
        require(generation is None, "production drill must not borrow production-equivalent generation id")
        require(confirmation == PRODUCTION_CONFIRMATION, f"production drill requires confirmation: {PRODUCTION_CONFIRMATION}")
        require(record.get("productionEvidence") is True, "production drill must classify itself as production evidence")
    require(record.get("productionReady") is False, "failure drill cannot make application productionReady")

    assertions = record.get("assertions")
    require(isinstance(assertions, list), "assertions must be a list")
    expected = scenarios[scenario_id].get("requiredAssertions")
    require(isinstance(expected, list) and expected, "scenario requiredAssertions missing")
    actual_requirements: set[str] = set()
    for index, row in enumerate(assertions):
        require(isinstance(row, dict) and set(row) == {"requirement", "result", "evidenceRefs"}, f"assertions[{index}] field drift")
        requirement = row.get("requirement")
        require(isinstance(requirement, str) and requirement in expected and requirement not in actual_requirements, f"assertions[{index}].requirement invalid")
        require(row.get("result") == "PASS", f"assertions[{index}] must be PASS")
        refs(row.get("evidenceRefs"), f"assertions[{index}].evidenceRefs")
        actual_requirements.add(requirement)
    require(actual_requirements == set(expected), "all required scenario assertions need PASS evidence")

    validate_independent_reviews(record)
    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be a list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(isinstance(finding.get("findingId"), str) and finding["findingId"], f"unresolvedFindings[{index}].findingId invalid")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "Critical/High findings block drill admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "minioadmin", "authorization: bearer", "password", "private_key", "access_key", "account_id", "session_id", "@"):
        require(forbidden not in serialized, f"record contains forbidden runtime material: {forbidden}")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".failure-drill-registry.", suffix=".tmp", dir=REGISTRY.parent)
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


def atomic_write_bytes(value: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".failure-drill-registry.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def append_registry_transactionally(registry: dict[str, Any], original_bytes: bytes) -> None:
    atomic_write(registry)
    try:
        validate_registry_before_append(load(REGISTRY))
    except Exception:
        atomic_write_bytes(original_bytes)
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
        raise Fail("production-shaped failure drill registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["drillId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        original_registry_bytes = REGISTRY.read_bytes()
        registry = load(REGISTRY)
        drills = validate_registry_before_append(registry)
        require(all(item.get("drillId") != record["drillId"] for item in drills), "drillId already registered")
        require(all(not (item.get("scenarioId") == record["scenarioId"] and item.get("environmentClass") == record["environmentClass"] and item.get("environmentIdentityDigest") == record["environmentIdentityDigest"]) for item in drills), "same scenario/environment already registered")
        digest_authority = registry.get("evidenceDigestsByDrillId")
        require(isinstance(digest_authority, dict), "evidence digest authority missing")
        require(record["drillId"] not in digest_authority, "evidence digest authority already exists for drillId")
        digest_authority[record["drillId"]] = evidence_digests_for_record(record)
        drills.append(record)
        registry["registeredDrillCount"] = len(drills)
        registry["productionEquivalentDrillCount"] = sum(1 for item in drills if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionDrillCount"] = sum(1 for item in drills if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        append_registry_transactionally(registry, original_registry_bytes)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered production-shaped failure drill: {record['drillId']}")
    print("Application production readiness remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-SHAPED FAILURE DRILL REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
