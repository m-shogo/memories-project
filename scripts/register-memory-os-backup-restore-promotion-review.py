#!/usr/bin/env python3
"""Append one human-reviewed backup/restore promotion recommendation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-promotion-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
EVIDENCE_ROOT = ROOT / "docs/evidence/backup-restore"
LOCK = ROOT / "contracts/operations/.backup-restore-promotion-review.lock"
DECISION_ID = re.compile(r"^brpr_[a-z0-9][a-z0-9_-]{7,63}$")
EVIDENCE_ID = re.compile(r"^brge_[a-z0-9][a-z0-9_-]{7,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVIEW_EVIDENCE_SCHEMA = "memory-os-backup-restore-promotion-review-evidence.v1"
REVIEW_RESULT = "APPROVED"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def domain_validation_failure(exc: BaseException) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, RuntimeError) and current.__class__.__name__ == "Fail":
            return True
        current = current.__cause__ or current.__context__
    return False


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


def load_generation_writer():
    writer = canonical_repo_file(GEN_WRITER, "generation recovery writer")
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_for_promotion_review", writer)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be a canonical repository-relative path")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} evidence missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def promotion_evidence_ref(value: Any, field: str) -> str:
    ref = repo_ref(value, field)
    evidence_root = EVIDENCE_ROOT.relative_to(ROOT)
    try:
        Path(ref).relative_to(evidence_root)
    except ValueError as exc:
        raise Fail(f"{field} must remain inside monitored backup/restore evidence namespace") from exc
    return ref


def payload_sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def require_payload_digest(record: dict[str, Any], ref_field: str, digest_field: str) -> str:
    ref = promotion_evidence_ref(record.get(ref_field), ref_field)
    digest = record.get(digest_field)
    require(isinstance(digest, str) and SHA256.fullmatch(digest), f"{digest_field} invalid")
    require(digest == payload_sha256(ref), f"{digest_field} binding mismatch")
    return ref


def parse_timestamp(value: Any, field: str = "decidedAt") -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field} must be UTC")
    return parsed


def registered_recovery_evidence(evidence_id: Any) -> dict[str, Any]:
    """Resolve immutable registered recovery evidence without requiring it to remain current."""
    require(isinstance(evidence_id, str) and EVIDENCE_ID.fullmatch(evidence_id), "recoveryEvidenceId invalid")
    registry = load(GEN_REGISTRY)
    generation_writer = load_generation_writer()
    try:
        rows = generation_writer.validate_registry_for_append(registry)
    except Exception as exc:
        if domain_validation_failure(exc):
            raise Fail(f"generation recovery evidence registry authority invalid: {exc}") from exc
        raise
    matches = [row for row in rows if row.get("evidenceId") == evidence_id]
    require(len(matches) == 1, "recoveryEvidenceId is not uniquely registered")
    return matches[0]


def recovery_candidate(evidence_id: Any) -> dict[str, Any]:
    """Resolve evidence only when it is a current final production-equivalent recovery candidate."""
    row = registered_recovery_evidence(evidence_id)
    generation_writer = load_generation_writer()
    require(generation_writer.candidate(row) is True, "recoveryEvidenceId is not a current final production-equivalent recovery candidate")
    return row


def review_current(record: dict[str, Any]) -> bool:
    try:
        recovery_candidate(record.get("recoveryEvidenceId"))
    except Exception as exc:
        if domain_validation_failure(exc):
            return False
        raise
    return True


def validate_review_evidence(
    record: dict[str, Any],
    *,
    ref_field: str,
    digest_field: str,
    expected_role: str,
    required_fields: set[str],
    decided_at: datetime,
) -> str:
    ref = require_payload_digest(record, ref_field, digest_field)
    document = load(ROOT / ref)
    require(set(document) == required_fields, f"{ref_field} review evidence field drift")
    require(document.get("schemaVersion") == REVIEW_EVIDENCE_SCHEMA, f"{ref_field} review evidence schema drift")
    require(document.get("decisionId") == record.get("decisionId"), f"{ref_field} decisionId binding mismatch")
    require(document.get("recoveryEvidenceId") == record.get("recoveryEvidenceId"), f"{ref_field} recoveryEvidenceId binding mismatch")
    require(document.get("reviewRole") == expected_role, f"{ref_field} reviewRole mismatch")
    require(document.get("reviewResult") == REVIEW_RESULT, f"{ref_field} reviewResult must be APPROVED")
    reviewed_at = parse_timestamp(document.get("reviewedAt"), f"{ref_field}.reviewedAt")
    require(reviewed_at <= decided_at, f"{ref_field} review cannot post-date decision")
    reviewer = document.get("reviewerPseudonym")
    require(isinstance(reviewer, str), f"{ref_field} reviewerPseudonym required")
    canonical_reviewer = reviewer.strip()
    require(1 <= len(canonical_reviewer) <= 128 and reviewer == canonical_reviewer, f"{ref_field} reviewerPseudonym must be canonical non-empty text")
    for field in ("productionTrafficChanged", "productionCredentialsUsed", "automaticPromotion"):
        require(document.get(field) is False, f"{ref_field} {field} must remain false")
    return reviewer


def validate_record(record: dict[str, Any], *, require_current_candidate: bool = True) -> None:
    """Validate immutable review data; history does not regain current authority automatically."""
    contract = load(CONTRACT)
    require(contract.get("reviewEvidenceRoot") == str(EVIDENCE_ROOT.relative_to(ROOT)), "promotion review evidence root authority drift")
    require(
        contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "promotion review transactional append authority drift",
    )
    required = set(contract.get("requiredRecordFields", []))
    require(required and set(record) == required, f"promotion review field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "promotion review schemaVersion drift")
    require(contract.get("reviewEvidenceSchemaVersion") == REVIEW_EVIDENCE_SCHEMA, "promotion review evidence schema contract/writer drift")
    review_fields = set(contract.get("requiredReviewEvidenceFields", []))
    require(review_fields, "promotion review requiredReviewEvidenceFields missing")
    roles = contract.get("reviewRoles")
    require(
        isinstance(roles, dict)
        and roles == {
            "recoveryOwnerReviewRef": "RECOVERY_OWNER",
            "securityReviewRef": "SECURITY",
            "operabilityReviewRef": "OPERABILITY",
        },
        "promotion review role authority drift",
    )
    decision_id = record.get("decisionId")
    require(isinstance(decision_id, str) and DECISION_ID.fullmatch(decision_id), "decisionId invalid")
    if require_current_candidate:
        recovery_candidate(record.get("recoveryEvidenceId"))
    else:
        registered_recovery_evidence(record.get("recoveryEvidenceId"))
    decided_at = parse_timestamp(record.get("decidedAt"))
    decisions = contract.get("decisionValues")
    require(isinstance(decisions, list) and record.get("decision") in decisions, "decision invalid")

    rationale = require_payload_digest(record, "rationaleRef", "rationaleSha256")
    review_specs = (
        ("recoveryOwnerReviewRef", "recoveryOwnerReviewSha256"),
        ("securityReviewRef", "securityReviewSha256"),
        ("operabilityReviewRef", "operabilityReviewSha256"),
    )
    review_refs = [promotion_evidence_ref(record.get(ref_field), ref_field) for ref_field, _ in review_specs]
    require(len(set(review_refs)) == 3, "Recovery Owner, Security and Operability review refs must be distinct")
    require(rationale not in set(review_refs), "rationaleRef must be distinct from reviewer evidence")
    reviewers = [
        validate_review_evidence(
            record,
            ref_field=ref_field,
            digest_field=digest_field,
            expected_role=roles[ref_field],
            required_fields=review_fields,
            decided_at=decided_at,
        )
        for ref_field, digest_field in review_specs
    ]
    require(len(set(reviewers)) == 3, "Recovery Owner, Security and Operability reviewers must be distinct")

    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be list")
    finding_ids: set[str] = set()
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status", "ownerRef"}, f"unresolvedFindings[{index}] field drift")
        finding_id = finding.get("findingId")
        require(isinstance(finding_id, str) and finding_id and finding_id not in finding_ids, f"unresolvedFindings[{index}].findingId invalid/duplicate")
        finding_ids.add(finding_id)
        require(finding.get("severity") in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}, f"unresolvedFindings[{index}].severity invalid")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")
        repo_ref(finding.get("ownerRef"), f"unresolvedFindings[{index}].ownerRef")
    if record.get("decision") == "GO_RECOMMENDATION":
        require(findings == [], "GO_RECOMMENDATION requires zero unresolved findings")
    for field in ("productionTrafficChanged", "productionCredentialsUsed", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@", "latest"):
        require(forbidden not in serialized, f"promotion review contains forbidden material: {forbidden}")


def validate_registry_history(registry: dict[str, Any]) -> list[dict[str, Any]]:
    require(registry.get("schemaVersion") == "memory-os-backup-restore-promotion-review-registry.v1", "promotion review registry schema drift")
    require(registry.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(registry.get("productionTrafficChanged") is False and registry.get("productionEvidence") is False and registry.get("productionReady") is False, "promotion review registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "promotion review registry rows invalid")
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    require(valid_count(count) and count == len(rows), "promotion review registeredReviewCount drift")
    require(all(valid_count(value) for value in (go_count, no_go_count, defer_count)), "promotion review derived counts invalid")
    ids: set[str] = set()
    decisions = load(CONTRACT).get("decisionValues")
    require(isinstance(decisions, list), "promotion review decision authority invalid")
    for index, row in enumerate(rows):
        decision_id = row.get("decisionId")
        require(isinstance(decision_id, str) and DECISION_ID.fullmatch(decision_id) is not None and decision_id not in ids, f"promotion review records[{index}] decisionId authority invalid")
        ids.add(decision_id)
        require(row.get("decision") in decisions, f"promotion review records[{index}] decision invalid")
        validate_record(row, require_current_candidate=False)
    derived_go = sum(1 for row in rows if row.get("decision") == "GO_RECOMMENDATION")
    derived_no_go = sum(1 for row in rows if row.get("decision") == "NO_GO")
    derived_defer = sum(1 for row in rows if row.get("decision") == "DEFER")
    require((go_count, no_go_count, defer_count) == (derived_go, derived_no_go, derived_defer), "promotion review derived count authority drift")
    require(go_count + no_go_count + defer_count == count, "promotion review decision counts do not partition registry")
    expected_latest = rows[-1].get("decisionId") if rows else None
    require(registry.get("latestDecisionId") == expected_latest, "promotion review latestDecisionId authority drift")
    return rows


def expected_current_decision_id(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    latest = rows[-1]
    return latest.get("decisionId") if review_current(latest) else None


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = validate_registry_history(registry)
    expected_current = expected_current_decision_id(rows)
    require(registry.get("currentDecisionId") == expected_current, "promotion review currentDecisionId authority drift")
    return rows


def reconcile_current_decision(registry: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """Permit only monotonic current-authority revocation after upstream supersession."""
    rows = validate_registry_history(registry)
    latest_id = registry.get("latestDecisionId")
    stored_current = registry.get("currentDecisionId")
    expected_current = expected_current_decision_id(rows)
    if expected_current is not None:
        require(stored_current == expected_current, "promotion review current authority cannot be auto-created or repaired")
    else:
        require(stored_current in {None, latest_id}, "promotion review currentDecisionId corruption cannot be auto-healed")
        registry["currentDecisionId"] = None
    return rows, expected_current


def atomic_write(value: dict[str, Any]) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-promotion-review.", suffix=".tmp", dir=REGISTRY.parent)
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


def atomic_restore(payload: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-promotion-review-rollback.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
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
        raise Fail("cannot snapshot promotion review registry before append") from exc
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
        raise Fail("promotion review input must be external to repository")
    record = load(input_path)
    validate_record(record, require_current_candidate=True)
    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("promotion review registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["decisionId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        rows = validate_registry_for_append(registry)
        require(all(row.get("decisionId") != record["decisionId"] for row in rows), "decisionId already registered")
        rows.append(record)
        registry["registeredReviewCount"] = len(rows)
        registry["goRecommendationCount"] = sum(1 for row in rows if row.get("decision") == "GO_RECOMMENDATION")
        registry["noGoCount"] = sum(1 for row in rows if row.get("decision") == "NO_GO")
        registry["deferCount"] = sum(1 for row in rows if row.get("decision") == "DEFER")
        registry["latestDecisionId"] = record["decisionId"]
        registry["currentDecisionId"] = record["decisionId"]
        registry["productionTrafficChanged"] = False
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        write_registry_transactionally(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered backup/restore promotion review: {record['decisionId']}")
    print(f"review decision: {record['decision']}")
    print("typed human review evidence: true")
    print("human review evidence namespace monitored: true")
    print("human review payload digests bound: true")
    print("historical review retained on later supersession: true")
    print("traffic changed: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW REGISTRATION FAILED: {exc}")
        raise SystemExit(1)