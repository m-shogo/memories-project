#!/usr/bin/env python3
"""Append one approved rollback rehearsal request under an exclusive lock.

This tool records admission to an isolated rehearsal only. It never executes a
rollback, changes traffic, edits a release record or creates production proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
LOCK_PATH = ROOT / "contracts/operations/.rollback-rehearsal-registry.lock"
APPROVAL_EVIDENCE_DIR = Path("docs/evidence/rollback-rehearsal/approvals")
CONFIRMATION = "REQUEST ISOLATED ROLLBACK REHEARSAL"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REHEARSAL_ID_RE = re.compile(r"^rrh_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
APPROVER_RE = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
APPROVER_FIELDS = {"role", "approverRef", "approvalEvidenceRef"}
APPROVAL_SCHEMA = "memory-os-rollback-rehearsal-approval.v1"
APPROVAL_FIELDS = {
    "schemaVersion",
    "rehearsalId",
    "sourceReleaseId",
    "rollbackTargetReleaseId",
    "reviewRole",
    "decision",
    "approvedAt",
    "reviewerPseudonym",
    "productionTraffic",
    "productionCredentials",
    "automaticPromotion",
}
TRAFFIC_POLICY_FIELDS = {
    "productionTrafficAllowed",
    "productionCredentialsAllowed",
    "automaticPromotionAllowed",
    "syntheticOrApprovedSanitizedDataOnly",
}
DATABASE_POLICY_FIELDS = {
    "destructiveDownMigrationAllowed",
    "automaticRecoveryDecisionAllowed",
    "recoveryPointEvidenceRef",
    "forwardFixDecisionRef",
}
ARTIFACT_POLICY_FIELDS = {
    "exactRetainedArtifactsRequired",
    "parserArtifactEvidenceRef",
    "objectVersionEvidenceRef",
}
RISK_FIELDS = {"riskId", "ownerRef", "deadline", "status"}
REQUIRED_ROLES = {"RELEASE_OWNER", "DATABASE_RECOVERY_OWNER"}
EVIDENCE_DIGEST_FIELD = "evidenceDigests"
REQUIRED_REQUEST_FIELDS = {
    "schemaVersion",
    "rehearsalId",
    "requestedAt",
    "sourceReleaseId",
    "rollbackTargetReleaseId",
    "sourceCommitSha",
    "rollbackTargetCommitSha",
    "sourceReleaseTag",
    "rollbackTargetReleaseTag",
    "environmentClass",
    "trafficPolicy",
    "databasePolicy",
    "artifactPolicy",
    "entryCriteriaRefs",
    "stopConditions",
    "approvers",
    "openRisks",
}
EVIDENCE_DIGEST_GUARD = (
    "every admitted request stores append-time SHA-256 digests for all entry-criteria, "
    "recovery-point, forward-fix, artifact and human approval evidence references and historical validation "
    "rejects later byte drift"
)
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "planningAuthorityOnly",
    "productionEvidence",
    "rehearsalRequestCount",
    "latestRehearsalId",
    "requests",
    "limitations",
}
EXPECTED_LIMITATIONS = (
    "only distinct approved release-baseline records may be referenced as source and rollback target",
    "the rollback target must already be verified ELIGIBLE or CONDITIONALLY_ELIGIBLE and all eligibility conditions remain binding stop conditions",
    "reviewed rehearsal requests are planning authority only and never prove rehearsal execution, rollback execution or production readiness",
    "production traffic, production credentials, destructive down migration and automatic promotion remain forbidden",
    "historical candidate, branch, tag and CI evidence cannot substitute for approved release or reviewed rehearsal authority",
)
CURRENT_ADMISSION_STATE_FIELDS = {
    "approvedReleaseCount",
    "rollbackEligibleReleaseCount",
    "admissibleReleasePairCount",
    "rehearsalRequestCount",
    "admissionDecision",
}
READINESS_FIELDS = {
    "contractDefined",
    "registryImplemented",
    "writerImplemented",
    "validatorImplemented",
    "automaticWorkflowImplemented",
    "approvedReleasePairAvailable",
    "rollbackTargetAvailable",
    "rehearsalRequested",
    "rehearsalExecuted",
    "independentReviewCompleted",
    "productionReady",
}


class RequestFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RequestFailure(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RequestFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RequestFailure(f"invalid JSON: {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(arguments)} failed without admission")
    return completed.stdout.strip()


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def exact_object(value: Any, fields: set[str], field: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{field} must be an object")
    require(set(value) == fields, f"{field} field set drift")
    return value


def validate_derived_contract_state(contract: dict[str, Any]) -> None:
    state = exact_object(
        contract.get("currentAdmissionState"),
        CURRENT_ADMISSION_STATE_FIELDS,
        "currentAdmissionState",
    )
    for field in (
        "approvedReleaseCount",
        "rollbackEligibleReleaseCount",
        "admissibleReleasePairCount",
        "rehearsalRequestCount",
    ):
        require(valid_count(state.get(field)),
                f"current admission state count invalid: {field}")
    expected_decision = (
        "ADMISSION_AVAILABLE"
        if state["admissibleReleasePairCount"] > 0
        else "BLOCKED_NO_APPROVED_ROLLBACK_PAIR"
    )
    require(state.get("admissionDecision") == expected_decision,
            "rollback rehearsal admission decision drift")

    readiness = exact_object(contract.get("readiness"), READINESS_FIELDS, "readiness")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True,
                f"rollback rehearsal implementation readiness drift: {field}")
    require(
        readiness.get("approvedReleasePairAvailable") is
        (state["admissibleReleasePairCount"] > 0) and
        readiness.get("rollbackTargetAvailable") is
        (state["rollbackEligibleReleaseCount"] > 0) and
        readiness.get("rehearsalRequested") is
        (state["rehearsalRequestCount"] > 0),
        "rollback rehearsal readiness count drift",
    )
    require(readiness.get("rehearsalExecuted") is False and
            readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "rollback rehearsal readiness cannot claim execution or production readiness")


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be RFC3339 UTC ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RequestFailure(f"{field} must be valid RFC3339 UTC") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")
    return parsed


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    candidate = ROOT / path
    current = ROOT
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), f"{field} contains a symlink path")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise RequestFailure(f"{field} escapes or is missing from the repository: {value}") from exc
    require(resolved.is_file(), f"{field} does not reference a regular file: {value}")
    require(bool(git("ls-files", "--error-unmatch", "--", value)),
            f"{field} is not tracked by the repository: {value}")
    return value


def validate_contract_for_append(contract: dict[str, Any]) -> set[str]:
    require(contract.get("schemaVersion") == "memory-os-rollback-rehearsal-gate-contract.v1",
            "rollback rehearsal contract schemaVersion drift")
    require(contract.get("appendOnly") is True,
            "rollback rehearsal contract must remain append-only")
    expected_paths = {
        "approvedReleaseRegistry": str(RELEASE_REGISTRY_PATH.relative_to(ROOT)),
        "rehearsalRegistry": str(REHEARSAL_REGISTRY_PATH.relative_to(ROOT)),
        "appendLockPath": str(LOCK_PATH.relative_to(ROOT)),
        "writer": str(Path(__file__).resolve().relative_to(ROOT)),
        "validator": "scripts/validate-memory-os-rollback-rehearsal-gate.py",
        "reconcile": "scripts/reconcile-memory-os-rollback-rehearsal-gate.py",
        "workflow": ".github/workflows/rollback-rehearsal-gate.yml",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"rollback rehearsal contract path drift: {field}")
    require(contract.get("approvalSchemaVersion") == APPROVAL_SCHEMA,
            "rollback rehearsal approval schema drift")
    require(contract.get("approvalEvidenceDirectory") == APPROVAL_EVIDENCE_DIR.as_posix(),
            "rollback rehearsal approval evidence directory drift")
    required_approval_fields = set(strings(
        contract.get("requiredApprovalFields"), "requiredApprovalFields", len(APPROVAL_FIELDS)
    ))
    require(required_approval_fields == APPROVAL_FIELDS,
            "rollback rehearsal approval fields drift")
    required_fields = set(strings(contract.get("requiredRequestFields"),
                                  "requiredRequestFields", len(REQUIRED_REQUEST_FIELDS)))
    require(required_fields == REQUIRED_REQUEST_FIELDS,
            "rollback rehearsal required request fields drift")
    guards = strings(contract.get("admissionGuards"), "admissionGuards", 14)
    require(EVIDENCE_DIGEST_GUARD in guards,
            "rollback rehearsal immutable evidence digest guard missing")
    environment = contract.get("environmentPolicy")
    require(isinstance(environment, dict) and
            environment.get("allowedEnvironmentClass") == "ISOLATED_NON_PRODUCTION_REHEARSAL" and
            environment.get("productionTrafficAllowed") is False and
            environment.get("productionCredentialsAllowed") is False and
            environment.get("syntheticOrApprovedSanitizedDataOnly") is True and
            environment.get("automaticTrafficPromotionAllowed") is False and
            environment.get("destructiveDownMigrationAllowed") is False,
            "rollback rehearsal environment policy drift")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict) and boundary.get("planningAuthorityOnly") is True and
            boundary.get("rehearsalExecuted") is False and
            boundary.get("rollbackExecuted") is False and
            boundary.get("productionEvidence") is False and
            boundary.get("releaseCompatibilityEvidence") is False and
            boundary.get("productionReady") is False,
            "rollback rehearsal evidence boundary drift")
    validate_derived_contract_state(contract)
    return required_fields


def approval_evidence_ref(value: Any, field: str) -> str:
    ref = safe_ref(value, field)
    parts = Path(ref).parts
    prefix = APPROVAL_EVIDENCE_DIR.parts
    require(parts[:len(prefix)] == prefix,
            f"{field} must be under {APPROVAL_EVIDENCE_DIR.as_posix()}")
    return ref


def approval_document(approver: dict[str, Any], request: dict[str, Any]) -> None:
    ref = approval_evidence_ref(
        approver.get("approvalEvidenceRef"), "approvers.approvalEvidenceRef"
    )
    document = load(ROOT / ref)
    require(set(document) == APPROVAL_FIELDS,
            "rollback rehearsal approval evidence field set drift")
    require(document.get("schemaVersion") == APPROVAL_SCHEMA,
            "rollback rehearsal approval schemaVersion drift")
    require(document.get("rehearsalId") == request.get("rehearsalId"),
            "rollback rehearsal approval rehearsalId binding mismatch")
    require(document.get("sourceReleaseId") == request.get("sourceReleaseId"),
            "rollback rehearsal approval sourceReleaseId binding mismatch")
    require(document.get("rollbackTargetReleaseId") == request.get("rollbackTargetReleaseId"),
            "rollback rehearsal approval rollbackTargetReleaseId binding mismatch")
    require(document.get("reviewRole") == approver.get("role"),
            "rollback rehearsal approval reviewRole binding mismatch")
    require(document.get("reviewerPseudonym") == approver.get("approverRef"),
            "rollback rehearsal approval reviewer binding mismatch")
    require(document.get("decision") == "APPROVED",
            "rollback rehearsal approval decision must be APPROVED")
    approved_at = parse_utc(document.get("approvedAt"), "approvalEvidence.approvedAt")
    requested_at = parse_utc(request.get("requestedAt"), "requestedAt")
    require(approved_at >= requested_at,
            "rollback rehearsal approval predates request")
    for field in ("productionTraffic", "productionCredentials", "automaticPromotion"):
        require(document.get(field) is False,
                f"rollback rehearsal approval {field} must remain false")


def evidence_refs(request: dict[str, Any]) -> list[str]:
    database = request.get("databasePolicy")
    artifacts = request.get("artifactPolicy")
    require(isinstance(database, dict), "databasePolicy missing for evidence binding")
    require(isinstance(artifacts, dict), "artifactPolicy missing for evidence binding")
    refs = [
        safe_ref(database.get("recoveryPointEvidenceRef"),
                 "databasePolicy.recoveryPointEvidenceRef"),
        safe_ref(database.get("forwardFixDecisionRef"),
                 "databasePolicy.forwardFixDecisionRef"),
        safe_ref(artifacts.get("parserArtifactEvidenceRef"),
                 "artifactPolicy.parserArtifactEvidenceRef"),
        safe_ref(artifacts.get("objectVersionEvidenceRef"),
                 "artifactPolicy.objectVersionEvidenceRef"),
    ]
    refs.extend(
        safe_ref(ref, "entryCriteriaRefs")
        for ref in strings(request.get("entryCriteriaRefs"), "entryCriteriaRefs", 5)
    )
    approvers = request.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 2,
            "exactly two rehearsal approvers are required for evidence binding")
    refs.extend(
        approval_evidence_ref(approver.get("approvalEvidenceRef"), "approvers.approvalEvidenceRef")
        for approver in approvers
        if isinstance(approver, dict)
    )
    return list(dict.fromkeys(refs))


def committed_evidence_bytes(ref: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{ref}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"rollback rehearsal evidence is not present in exact HEAD: {ref}")
    current = (ROOT / ref).read_bytes()
    require(current == completed.stdout,
            f"rollback rehearsal evidence differs from exact HEAD bytes: {ref}")
    return completed.stdout


def evidence_digest_map(request: dict[str, Any]) -> dict[str, str]:
    return {
        ref: hashlib.sha256(committed_evidence_bytes(ref)).hexdigest()
        for ref in evidence_refs(request)
    }


def validate_evidence_digest_binding(
    request: dict[str, Any], *, required: bool
) -> None:
    digests = request.get(EVIDENCE_DIGEST_FIELD)
    if digests is None and not required:
        return
    require(isinstance(digests, dict),
            "rollback rehearsal evidence digest authority missing")
    refs = evidence_refs(request)
    require(set(digests) == set(refs),
            "rollback rehearsal evidence digest ref set drift")
    for ref in refs:
        digest = digests.get(ref)
        require(isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None,
                f"rollback rehearsal evidence digest invalid: {ref}")
        current = hashlib.sha256(committed_evidence_bytes(ref)).hexdigest()
        require(digest == current,
                f"rollback rehearsal evidence bytes changed after admission: {ref}")


def validate_release_registry_for_append(release_registry: dict[str, Any]) -> None:
    release_contract = load(RELEASE_CONTRACT_PATH)
    try:
        release_writer = load_module(RELEASE_WRITER_PATH, "memory_os_release_baseline_writer")
        release_writer.validate_registry_for_append(release_registry, release_contract)
    except Exception as exc:
        raise RequestFailure(f"approved release registry authority invalid: {exc}") from exc


def validate_approvers(value: Any, request: dict[str, Any] | None = None) -> None:
    require(isinstance(value, list) and len(value) == 2,
            "exactly two rehearsal approvers are required")
    roles: set[str] = set()
    identities: set[str] = set()
    refs: set[str] = set()
    for approver in value:
        require(isinstance(approver, dict), "approver entry must be an object")
        require(set(approver) == APPROVER_FIELDS,
                "approver entry field set drift")
        role = approver.get("role")
        identity = approver.get("approverRef")
        ref = approver.get("approvalEvidenceRef")
        require(role in REQUIRED_ROLES and role not in roles,
                f"approval role invalid or duplicated: {role}")
        require(isinstance(identity, str) and APPROVER_RE.fullmatch(identity) is not None,
                "approverRef must be an operational pseudonym")
        require(identity not in identities, "duplicate rehearsal approver detected")
        require(isinstance(ref, str) and ref and ref not in refs,
                "approvalEvidenceRef must be distinct")
        if request is not None:
            approval_document(approver, request)
        roles.add(role)
        identities.add(identity)
        refs.add(ref)
    require(roles == REQUIRED_ROLES, "required rehearsal approval roles incomplete")


def validate_request(
    request: dict[str, Any], required_fields: set[str], release_registry: dict[str, Any],
    *, require_evidence_digests: bool = False,
) -> None:
    expected_fields = set(required_fields)
    if require_evidence_digests:
        expected_fields.add(EVIDENCE_DIGEST_FIELD)
    require(set(request) == expected_fields,
            f"request field set drift: {sorted(set(request) ^ expected_fields)}")
    require(request.get("schemaVersion") == "memory-os-rollback-rehearsal-request.v1",
            "request schemaVersion drift")
    rehearsal_id = request.get("rehearsalId")
    require(isinstance(rehearsal_id, str) and
            REHEARSAL_ID_RE.fullmatch(rehearsal_id) is not None,
            "rehearsalId format invalid")
    parse_utc(request.get("requestedAt"), "requestedAt")

    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry is invalid")
    by_id = {
        item.get("releaseId"): item
        for item in releases
        if isinstance(item, dict) and isinstance(item.get("releaseId"), str)
    }
    source_id = request.get("sourceReleaseId")
    target_id = request.get("rollbackTargetReleaseId")
    require(isinstance(source_id, str) and isinstance(target_id, str) and
            source_id != target_id,
            "source and rollback target release IDs must be distinct")
    require(source_id in by_id, "source release is not approved")
    require(target_id in by_id, "rollback target release is not approved")
    source = by_id[source_id]
    target = by_id[target_id]

    for request_field, release_field, release in (
        ("sourceCommitSha", "commitSha", source),
        ("sourceReleaseTag", "releaseTag", source),
        ("rollbackTargetCommitSha", "commitSha", target),
        ("rollbackTargetReleaseTag", "releaseTag", target),
    ):
        require(request.get(request_field) == release.get(release_field),
                f"{request_field} differs from approved release authority")
    require(SHA_RE.fullmatch(str(request.get("sourceCommitSha", ""))) is not None and
            SHA_RE.fullmatch(str(request.get("rollbackTargetCommitSha", ""))) is not None,
            "release SHA binding invalid")

    rollback = target.get("rollbackEligibility")
    require(isinstance(rollback, dict), "rollback target eligibility missing")
    require(rollback.get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
            rollback.get("verified") is True,
            "rollback target is not verified rollback eligible")
    target_conditions = rollback.get("conditions")
    require(isinstance(target_conditions, list) and
            all(isinstance(item, str) and item for item in target_conditions),
            "rollback target conditions are invalid")

    require(request.get("environmentClass") == "ISOLATED_NON_PRODUCTION_REHEARSAL",
            "environmentClass must be isolated non-production rehearsal")
    traffic = exact_object(request.get("trafficPolicy"), TRAFFIC_POLICY_FIELDS, "trafficPolicy")
    require(traffic.get("productionTrafficAllowed") is False and
            traffic.get("productionCredentialsAllowed") is False and
            traffic.get("automaticPromotionAllowed") is False and
            traffic.get("syntheticOrApprovedSanitizedDataOnly") is True,
            "traffic policy violates rehearsal boundary")
    database = exact_object(request.get("databasePolicy"), DATABASE_POLICY_FIELDS, "databasePolicy")
    require(database.get("destructiveDownMigrationAllowed") is False and
            database.get("automaticRecoveryDecisionAllowed") is False,
            "database policy violates rehearsal boundary")
    safe_ref(database.get("recoveryPointEvidenceRef"),
             "databasePolicy.recoveryPointEvidenceRef")
    safe_ref(database.get("forwardFixDecisionRef"),
             "databasePolicy.forwardFixDecisionRef")

    artifacts = exact_object(request.get("artifactPolicy"), ARTIFACT_POLICY_FIELDS, "artifactPolicy")
    for field in ("parserArtifactEvidenceRef", "objectVersionEvidenceRef"):
        safe_ref(artifacts.get(field), f"artifactPolicy.{field}")
    require(artifacts.get("exactRetainedArtifactsRequired") is True,
            "exact retained artifacts must be required")

    for ref in strings(request.get("entryCriteriaRefs"), "entryCriteriaRefs", 5):
        safe_ref(ref, "entryCriteriaRefs")

    stop_conditions = strings(request.get("stopConditions"), "stopConditions", 6)
    for condition in target_conditions:
        require(condition in stop_conditions,
                "rollback target condition is missing from stopConditions")

    validate_approvers(request.get("approvers"), request)
    validate_evidence_digest_binding(request, required=require_evidence_digests)

    risks = request.get("openRisks")
    require(isinstance(risks, list), "openRisks must be a list")
    for risk in risks:
        risk = exact_object(risk, RISK_FIELDS, "openRisks entry")
        require(risk.get("riskId") and risk.get("ownerRef") and
                risk.get("deadline") and risk.get("status"),
                "open risk entry is incomplete")

    serialized = json.dumps(request, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "session_id", "job_id",
        "preview_id", "object_key", "apple_subject", "@",
    ):
        require(forbidden not in serialized,
                f"request contains forbidden content: {forbidden}")


def validate_registry_for_append(
    registry: dict[str, Any], contract: dict[str, Any], release_registry: dict[str, Any]
) -> None:
    required_fields = validate_contract_for_append(contract)
    validate_release_registry_for_append(release_registry)
    require(set(registry) == REGISTRY_FIELDS,
            "rollback rehearsal registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-rollback-rehearsal-registry.v1",
            "rollback rehearsal registry schemaVersion drift")
    require(registry.get("registryClass") == "APPROVED_ROLLBACK_REHEARSAL_REQUESTS",
            "rollback rehearsal registry class drift")
    require(registry.get("appendOnly") is True,
            "rollback rehearsal registry must remain append-only")
    require(registry.get("planningAuthorityOnly") is True,
            "rollback rehearsal registry must remain planning authority only")
    require(registry.get("productionEvidence") is False,
            "rollback rehearsal registry cannot claim production evidence")
    limitations = registry.get("limitations")
    require(limitations == list(EXPECTED_LIMITATIONS),
            "rollback rehearsal registry limitations drift")
    requests = registry.get("requests")
    require(isinstance(requests, list) and all(isinstance(item, dict) for item in requests),
            "rollback rehearsal registry contains invalid requests")
    count = registry.get("rehearsalRequestCount")
    require(isinstance(count, int) and not isinstance(count, bool),
            "rehearsalRequestCount must be an integer")
    require(count == len(requests), "rehearsalRequestCount drift")
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for record in requests:
        validate_request(
            record, required_fields, release_registry, require_evidence_digests=True
        )
        rehearsal_id = record["rehearsalId"]
        pair = (record["sourceReleaseId"], record["rollbackTargetReleaseId"])
        require(rehearsal_id not in ids, "duplicate rehearsalId")
        require(pair not in pairs, "duplicate admitted release pair")
        ids.add(rehearsal_id)
        pairs.add(pair)
    expected_latest = requests[-1]["rehearsalId"] if requests else None
    require(registry.get("latestRehearsalId") == expected_latest,
            "latestRehearsalId drift")

    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry releases must be a list")
    eligible = [
        item for item in releases
        if isinstance(item, dict) and
        isinstance(item.get("rollbackEligibility"), dict) and
        item["rollbackEligibility"].get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
        item["rollbackEligibility"].get("verified") is True
    ]
    admissible_pairs = max(0, len(releases) - 1) * len(eligible)
    state = contract["currentAdmissionState"]
    require(state.get("approvedReleaseCount") == len(releases) and
            state.get("rollbackEligibleReleaseCount") == len(eligible) and
            state.get("admissibleReleasePairCount") == admissible_pairs and
            state.get("rehearsalRequestCount") == len(requests),
            "rollback rehearsal derived source-count drift")
    readiness = contract["readiness"]
    require(readiness.get("approvedReleasePairAvailable") is (admissible_pairs > 0) and
            readiness.get("rollbackTargetAvailable") is (len(eligible) > 0) and
            readiness.get("rehearsalRequested") is (len(requests) > 0),
            "rollback rehearsal derived readiness source-count drift")


def acquire_lock() -> int:
    try:
        return os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RequestFailure("rollback rehearsal registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".rollback-rehearsal-registry.", suffix=".tmp",
        dir=REHEARSAL_REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REHEARSAL_REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True,
                        help="JSON request outside the repository working tree")
    parser.add_argument("--confirm", required=True)
    arguments = parser.parse_args()

    require(arguments.confirm == CONFIRMATION,
            f"confirmation must equal: {CONFIRMATION}")
    request_path = Path(arguments.request).resolve()
    try:
        request_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise RequestFailure("input request must be outside the repository")
    require(git("status", "--porcelain") == "",
            "working tree must be clean before rehearsal admission")

    contract = load(CONTRACT_PATH)
    required_fields = validate_contract_for_append(contract)
    release_registry = load(RELEASE_REGISTRY_PATH)
    validate_release_registry_for_append(release_registry)
    request = load(request_path)
    validate_request(request, required_fields, release_registry)
    request[EVIDENCE_DIGEST_FIELD] = evidence_digest_map(request)
    validate_evidence_digest_binding(request, required=True)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, f"{request['rehearsalId']}\n".encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REHEARSAL_REGISTRY_PATH)
        validate_registry_for_append(registry, contract, release_registry)
        validate_request(
            request, required_fields, release_registry, require_evidence_digests=True
        )
        requests = registry["requests"]
        require(all(item.get("rehearsalId") != request["rehearsalId"]
                    for item in requests),
                "rehearsalId is already registered")
        require(all(not (
            item.get("sourceReleaseId") == request["sourceReleaseId"] and
            item.get("rollbackTargetReleaseId") == request["rollbackTargetReleaseId"]
        ) for item in requests),
                "release pair already has an admitted rehearsal request")

        requests.append(request)
        registry["rehearsalRequestCount"] = len(requests)
        registry["latestRehearsalId"] = request["rehearsalId"]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    print(f"Admitted isolated rollback rehearsal request: {request['rehearsalId']}")
    print("No rollback or traffic action was executed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RequestFailure as exc:
        print(f"ROLLBACK REHEARSAL REQUEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
