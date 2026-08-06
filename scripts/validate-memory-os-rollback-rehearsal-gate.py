#!/usr/bin/env python3
"""Fail-closed validation for rollback rehearsal admission authority."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REHEARSAL_ID_RE = re.compile(r"^rrh_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
REQUIRED_ROLES = {"RELEASE_OWNER", "DATABASE_RECOVERY_OWNER"}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    require((ROOT / path).is_file(), f"{field} path missing: {value}")
    return value


def validate_request(record: dict[str, Any], releases_by_id: dict[str, dict[str, Any]],
                     required_fields: set[str]) -> None:
    require(set(record) >= required_fields,
            f"rehearsal record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-rollback-rehearsal-request.v1",
            "rehearsal record schema drift")
    require(isinstance(record.get("rehearsalId"), str) and
            REHEARSAL_ID_RE.fullmatch(record["rehearsalId"]) is not None,
            "rehearsalId format invalid")
    source_id = record.get("sourceReleaseId")
    target_id = record.get("rollbackTargetReleaseId")
    require(source_id in releases_by_id and target_id in releases_by_id and
            source_id != target_id,
            "rehearsal release pair is not approved and distinct")
    source = releases_by_id[source_id]
    target = releases_by_id[target_id]
    for request_field, release_field, release in (
        ("sourceCommitSha", "commitSha", source),
        ("sourceReleaseTag", "releaseTag", source),
        ("rollbackTargetCommitSha", "commitSha", target),
        ("rollbackTargetReleaseTag", "releaseTag", target),
    ):
        require(record.get(request_field) == release.get(release_field),
                f"rehearsal {request_field} binding drift")
    require(SHA_RE.fullmatch(record["sourceCommitSha"]) is not None and
            SHA_RE.fullmatch(record["rollbackTargetCommitSha"]) is not None,
            "rehearsal commit SHA invalid")
    rollback = target.get("rollbackEligibility")
    require(isinstance(rollback, dict) and
            rollback.get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
            rollback.get("verified") is True,
            "rollback target is not verified eligible")
    conditions = rollback.get("conditions")
    require(isinstance(conditions, list), "rollback target conditions invalid")

    require(record.get("environmentClass") == "ISOLATED_NON_PRODUCTION_REHEARSAL",
            "rehearsal environment class drift")
    traffic = record.get("trafficPolicy")
    require(isinstance(traffic, dict) and
            traffic.get("productionTrafficAllowed") is False and
            traffic.get("productionCredentialsAllowed") is False and
            traffic.get("automaticPromotionAllowed") is False and
            traffic.get("syntheticOrApprovedSanitizedDataOnly") is True,
            "rehearsal traffic boundary drift")
    database = record.get("databasePolicy")
    require(isinstance(database, dict) and
            database.get("destructiveDownMigrationAllowed") is False and
            database.get("automaticRecoveryDecisionAllowed") is False,
            "rehearsal database boundary drift")
    safe_ref(database.get("recoveryPointEvidenceRef"),
             "databasePolicy.recoveryPointEvidenceRef")
    safe_ref(database.get("forwardFixDecisionRef"),
             "databasePolicy.forwardFixDecisionRef")
    artifacts = record.get("artifactPolicy")
    require(isinstance(artifacts, dict) and
            artifacts.get("exactRetainedArtifactsRequired") is True,
            "rehearsal artifact boundary drift")
    safe_ref(artifacts.get("parserArtifactEvidenceRef"),
             "artifactPolicy.parserArtifactEvidenceRef")
    safe_ref(artifacts.get("objectVersionEvidenceRef"),
             "artifactPolicy.objectVersionEvidenceRef")
    for ref in strings(record.get("entryCriteriaRefs"), "entryCriteriaRefs", 5):
        safe_ref(ref, "entryCriteriaRefs")
    stops = strings(record.get("stopConditions"), "stopConditions", 6)
    require(all(condition in stops for condition in conditions),
            "rollback eligibility condition missing from stopConditions")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 2,
            "rehearsal requires exactly two approvers")
    roles = {item.get("role") for item in approvers if isinstance(item, dict)}
    identities = {item.get("approverRef") for item in approvers if isinstance(item, dict)}
    require(roles == REQUIRED_ROLES and len(identities) == 2 and None not in identities,
            "rehearsal approvers are incomplete or duplicated")
    require(isinstance(record.get("openRisks"), list), "openRisks must be a list")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "session_id", "job_id",
        "preview_id", "object_key", "apple_subject", "@",
    ):
        require(forbidden not in serialized,
                f"rehearsal record contains forbidden content: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-rollback-rehearsal-gate-contract.v1",
            "rollback rehearsal gate contract schema drift")
    require(contract.get("appendOnly") is True,
            "rollback rehearsal authority must be append-only")
    for field, expected in {
        "approvedReleaseRegistry": str(RELEASE_REGISTRY_PATH.relative_to(ROOT)),
        "rehearsalRegistry": str(REHEARSAL_REGISTRY_PATH.relative_to(ROOT)),
        "writer": "scripts/request-memory-os-rollback-rehearsal.py",
        "validator": "scripts/validate-memory-os-rollback-rehearsal-gate.py",
        "reconcile": "scripts/reconcile-memory-os-rollback-rehearsal-gate.py",
        "runbook": "docs/runbooks/memory-os-rollback-rehearsal.md",
        "workflow": ".github/workflows/rollback-rehearsal-gate.yml",
    }.items():
        require(contract.get(field) == expected, f"contract path drift: {field}")
        safe_ref(expected, field)
    required_fields = set(strings(contract.get("requiredRequestFields"),
                                  "requiredRequestFields", 17))
    strings(contract.get("admissionGuards"), "admissionGuards", 12)
    strings(contract.get("forbiddenAdmissionSources"), "forbiddenAdmissionSources", 8)

    environment = contract.get("environmentPolicy")
    require(isinstance(environment, dict) and
            environment.get("allowedEnvironmentClass") ==
            "ISOLATED_NON_PRODUCTION_REHEARSAL" and
            environment.get("productionTrafficAllowed") is False and
            environment.get("productionCredentialsAllowed") is False and
            environment.get("automaticTrafficPromotionAllowed") is False and
            environment.get("destructiveDownMigrationAllowed") is False and
            environment.get("syntheticOrApprovedSanitizedDataOnly") is True,
            "contract environment policy drift")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict) and
            boundary.get("planningAuthorityOnly") is True and
            all(boundary.get(field) is False for field in (
                "rehearsalExecuted", "rollbackExecuted", "productionEvidence",
                "releaseCompatibilityEvidence", "productionReady",
            )), "rollback rehearsal evidence boundary drift")

    release_registry = load(RELEASE_REGISTRY_PATH)
    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry releases invalid")
    require(release_registry.get("approvedReleaseCount") == len(releases),
            "approved release count drift")
    releases_by_id = {
        item.get("releaseId"): item
        for item in releases
        if isinstance(item, dict) and isinstance(item.get("releaseId"), str)
    }
    eligible = [
        item for item in releases
        if isinstance(item, dict) and
        isinstance(item.get("rollbackEligibility"), dict) and
        item["rollbackEligibility"].get("status") in
        {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
        item["rollbackEligibility"].get("verified") is True
    ]
    admissible_pairs = max(0, len(releases) - 1) * len(eligible)

    rehearsal_registry = load(REHEARSAL_REGISTRY_PATH)
    require(rehearsal_registry.get("schemaVersion") ==
            "memory-os-rollback-rehearsal-registry.v1",
            "rollback rehearsal registry schema drift")
    require(rehearsal_registry.get("appendOnly") is True and
            rehearsal_registry.get("planningAuthorityOnly") is True and
            rehearsal_registry.get("productionEvidence") is False,
            "rollback rehearsal registry boundary drift")
    requests = rehearsal_registry.get("requests")
    require(isinstance(requests, list), "rehearsal registry requests invalid")
    require(rehearsal_registry.get("rehearsalRequestCount") == len(requests),
            "rehearsal request count drift")
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for record in requests:
        require(isinstance(record, dict), "rehearsal request must be an object")
        validate_request(record, releases_by_id, required_fields)
        require(record["rehearsalId"] not in ids, "duplicate rehearsalId")
        pair = (record["sourceReleaseId"], record["rollbackTargetReleaseId"])
        require(pair not in pairs, "duplicate admitted release pair")
        ids.add(record["rehearsalId"])
        pairs.add(pair)
    require(rehearsal_registry.get("latestRehearsalId") ==
            (requests[-1]["rehearsalId"] if requests else None),
            "latestRehearsalId drift")

    state = contract.get("currentAdmissionState")
    require(isinstance(state, dict), "currentAdmissionState missing")
    require(state.get("approvedReleaseCount") == len(releases) and
            state.get("rollbackEligibleReleaseCount") == len(eligible) and
            state.get("admissibleReleasePairCount") == admissible_pairs and
            state.get("rehearsalRequestCount") == len(requests),
            "current admission state count drift")
    expected_decision = (
        "ADMISSION_AVAILABLE" if admissible_pairs > 0
        else "BLOCKED_NO_APPROVED_ROLLBACK_PAIR"
    )
    require(state.get("admissionDecision") == expected_decision,
            "rollback rehearsal admission decision drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "rollback rehearsal readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"gate implementation missing: {field}")
    require(readiness.get("approvedReleasePairAvailable") is (admissible_pairs > 0) and
            readiness.get("rollbackTargetAvailable") is (len(eligible) > 0) and
            readiness.get("rehearsalRequested") is (len(requests) > 0),
            "rollback rehearsal readiness count drift")
    require(readiness.get("rehearsalExecuted") is False and
            readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "admission gate cannot claim execution or production readiness")

    if not releases:
        require(not requests and admissible_pairs == 0 and
                expected_decision == "BLOCKED_NO_APPROVED_ROLLBACK_PAIR",
                "empty approved release registry must block all rehearsal admission")

    runbook = (ROOT / contract["runbook"]).read_text(encoding="utf-8")
    for phrase in (
        "Candidate is not a release", "Required release pair",
        "Required environment boundary", "Stop conditions",
        "Production remains **NO_GO**",
    ):
        require(phrase in runbook, f"rollback runbook missing phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "rollback rehearsal gate cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "rollback admission authority cannot make OPS-P0-008 ready")

    print("Memory OS rollback rehearsal admission validation PASS")
    print(f"approved releases: {len(releases)}")
    print(f"rollback eligible releases: {len(eligible)}")
    print(f"admissible pairs: {admissible_pairs}")
    print(f"rehearsal requests: {len(requests)}")
    print(f"admission decision: {expected_decision}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"ROLLBACK REHEARSAL GATE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
