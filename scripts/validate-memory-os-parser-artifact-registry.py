#!/usr/bin/env python3
"""Fail-closed validation for the reviewed parser artifact registry."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_ID_RE = re.compile(r"^par_[a-z0-9][a-z0-9._-]{7,95}$")
REQUIRED_ROLES = {"SECURITY_REVIEWER", "RUNTIME_REVIEWER", "RELEASE_OWNER"}
RETENTION_STATES = {"RETAINED", "RETENTION_PENDING", "RETIRED_BLOCKED_FROM_ROLLBACK"}


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


def load_release_writer() -> Any:
    require(RELEASE_WRITER_PATH.is_file(), "canonical release writer missing")
    spec = importlib.util.spec_from_file_location(
        "memory_os_release_baseline_writer_for_parser_validator", RELEASE_WRITER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "cannot load canonical release writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.REGISTRY_PATH).resolve() == RELEASE_REGISTRY_PATH.resolve(),
            "canonical release registry authority drift")
    return module


def approved_release_ids() -> set[str]:
    release_writer = load_release_writer()
    release_registry = load(RELEASE_REGISTRY_PATH)
    release_contract = load(Path(release_writer.CONTRACT_PATH))
    try:
        release_writer.validate_registry_for_append(release_registry, release_contract)
    except Exception as exc:
        raise ValidationFailure(f"approved release authority invalid: {exc}") from exc
    return {item["releaseId"] for item in release_registry["releases"]}


def validate_record(record: dict[str, Any], required_fields: set[str],
                    approved_release_ids: set[str]) -> None:
    require(set(record) >= required_fields,
            f"artifact record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-parser-artifact-record.v1",
            "artifact record schema drift")
    require(isinstance(record.get("artifactId"), str) and
            ARTIFACT_ID_RE.fullmatch(record["artifactId"]) is not None,
            "artifactId format invalid")
    require(isinstance(record.get("artifactSha256"), str) and
            DIGEST_RE.fullmatch(record["artifactSha256"]) is not None,
            "artifact digest invalid")
    require(isinstance(record.get("artifactSizeBytes"), int) and
            record["artifactSizeBytes"] > 0,
            "artifact size invalid")
    for field in (
        "adapterId", "adapterVersion", "artifactFormat", "targetOs", "targetArch",
        "protocolVersion", "registeredAt",
    ):
        require(isinstance(record.get(field), str) and record[field].strip(),
                f"{field} is required")
    require(record.get("reviewClass") == "REVIEWED_PARSER_ARTIFACT",
            "artifact reviewClass drift")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3,
            "artifact requires exactly three approvers")
    roles = {item.get("role") for item in approvers if isinstance(item, dict)}
    identities = {item.get("approverRef") for item in approvers if isinstance(item, dict)}
    require(roles == REQUIRED_ROLES and len(identities) == 3 and None not in identities,
            "artifact approvers are incomplete or duplicated")

    for field in ("buildProvenanceRef", "securityReviewRef", "retentionEvidenceRef"):
        safe_ref(record.get(field), field)
    for ref in strings(record.get("replayEvidenceRefs"), "replayEvidenceRefs", 1):
        safe_ref(ref, "replayEvidenceRefs")
    compatible = strings(record.get("compatibleReleaseIds"), "compatibleReleaseIds", 1)
    require(set(compatible) <= approved_release_ids,
            "artifact references an unapproved release")

    retention = record.get("rollbackRetentionState")
    require(isinstance(retention, dict) and retention.get("state") in RETENTION_STATES,
            "artifact retention state invalid")
    if retention.get("state") == "RETAINED":
        require(retention.get("immutableLocationVerified") is True,
                "RETAINED artifact requires verified immutable location")
        safe_ref(retention.get("verificationEvidenceRef"),
                 "rollbackRetentionState.verificationEvidenceRef")
    else:
        require(retention.get("immutableLocationVerified") is False,
                "non-retained artifact cannot claim immutable retention")
    require(isinstance(record.get("openRisks"), list), "openRisks must be a list")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "services/import-api/internal/parsersup/worker.go",
        "memory_os_parser_worker_mode", "go test", "postgres://", "postgresql://",
        "password=", "authorization: bearer", "minioadmin", "secretaccesskey",
        "account_id", "session_id", "job_id", "preview_id", "object_key", "@",
    ):
        require(forbidden not in serialized,
                f"artifact record contains forbidden content: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-parser-artifact-registry-contract.v1",
            "parser artifact contract schema drift")
    require(contract.get("appendOnly") is True,
            "parser artifact registry must be append-only")
    for field, expected in {
        "registryPath": str(REGISTRY_PATH.relative_to(ROOT)),
        "runbook": "docs/runbooks/memory-os-parser-artifact-registry.md",
        "writer": "scripts/register-memory-os-parser-artifact.py",
        "validator": "scripts/validate-memory-os-parser-artifact-registry.py",
        "reconcile": "scripts/reconcile-memory-os-parser-artifact-registry.py",
        "workflow": ".github/workflows/parser-artifact-registry.yml",
    }.items():
        require(contract.get(field) == expected, f"contract path drift: {field}")
        safe_ref(expected, field)
    required_fields = set(strings(contract.get("requiredRecordFields"),
                                  "requiredRecordFields", 20))
    strings(contract.get("registrationGuards"), "registrationGuards", 12)
    forbidden_sources = strings(contract.get("forbiddenArtifactSources"),
                                "forbiddenArtifactSources", 7)
    require(any("worker.go" in item for item in forbidden_sources),
            "test harness is not explicitly forbidden")

    review = contract.get("reviewPolicy")
    require(isinstance(review, dict) and
            review.get("reviewClass") == "REVIEWED_PARSER_ARTIFACT" and
            review.get("minimumDistinctApprovers") == 3 and
            set(review.get("requiredRoles", [])) == REQUIRED_ROLES,
            "parser artifact review policy drift")
    for field in (
        "selfApprovalForbidden", "sourceCodeIsInsufficient",
        "testHarnessIsInsufficient", "successfulBuildIsInsufficient",
        "digestStringAloneIsInsufficient", "releaseTagAloneIsInsufficient",
    ):
        require(review.get(field) is True, f"review guard missing: {field}")

    retention_policy = contract.get("retentionPolicy")
    require(isinstance(retention_policy, dict) and
            set(retention_policy.get("allowedStates", [])) == RETENTION_STATES and
            retention_policy.get("retainedRequiresImmutableLocationEvidence") is True and
            retention_policy.get("retiredArtifactCannotSupportRollback") is True and
            retention_policy.get("automaticDeletionForbidden") is True,
            "parser artifact retention policy drift")

    release_ids = approved_release_ids()

    registry = load(REGISTRY_PATH)
    require(registry.get("schemaVersion") == "memory-os-parser-artifact-registry.v1",
            "parser artifact registry schema drift")
    require(registry.get("registryClass") == "REVIEWED_RETAINED_PARSER_ARTIFACTS" and
            registry.get("appendOnly") is True and
            registry.get("productionEvidence") is False,
            "parser artifact registry authority drift")
    artifacts = registry.get("artifacts")
    require(isinstance(artifacts, list), "parser artifact registry artifacts invalid")
    ids: set[str] = set()
    digests: set[str] = set()
    adapter_versions: set[tuple[str, str]] = set()
    for record in artifacts:
        require(isinstance(record, dict), "artifact record must be an object")
        validate_record(record, required_fields, release_ids)
        artifact_id = record["artifactId"]
        digest = record["artifactSha256"]
        adapter_version = (record["adapterId"], record["adapterVersion"])
        require(artifact_id not in ids, "duplicate artifactId")
        require(digest not in digests, "duplicate artifact digest")
        require(adapter_version not in adapter_versions, "duplicate adapter version")
        ids.add(artifact_id)
        digests.add(digest)
        adapter_versions.add(adapter_version)

    retained = sum(
        1 for item in artifacts
        if item.get("rollbackRetentionState", {}).get("state") == "RETAINED"
    )
    replayed = sum(1 for item in artifacts if item.get("replayEvidenceRefs"))
    require(registry.get("reviewedArtifactCount") == len(artifacts) and
            registry.get("retainedRollbackArtifactCount") == retained and
            registry.get("replayProvenArtifactCount") == replayed,
            "parser artifact registry counts drift")
    require(registry.get("latestReviewedArtifactId") ==
            (artifacts[-1]["artifactId"] if artifacts else None),
            "latestReviewedArtifactId drift")

    state = contract.get("currentAuthorityState")
    require(isinstance(state, dict), "currentAuthorityState missing")
    compatible_release_count = len({
        release_id for item in artifacts for release_id in item.get("compatibleReleaseIds", [])
    })
    expected_decision = (
        "ARTIFACT_AUTHORITY_AVAILABLE" if artifacts
        else "BLOCKED_NO_REVIEWED_PARSER_ARTIFACT"
    )
    require(state.get("reviewedArtifactCount") == len(artifacts) and
            state.get("retainedRollbackArtifactCount") == retained and
            state.get("replayProvenArtifactCount") == replayed and
            state.get("compatibleApprovedReleaseCount") == compatible_release_count and
            state.get("decision") == expected_decision,
            "parser artifact authority state drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict) and
            boundary.get("testHarnessApproved") is False and
            boundary.get("productionEvidence") is False and
            boundary.get("productionReady") is False,
            "parser artifact evidence boundary drift")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "parser artifact readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"parser registry foundation missing: {field}")
    require(readiness.get("reviewedArtifactAvailable") is (len(artifacts) > 0) and
            readiness.get("oldArtifactReplayExecuted") is (replayed > 0) and
            readiness.get("rollbackArtifactAvailable") is (retained > 0),
            "parser artifact readiness count drift")
    require(readiness.get("independentRetentionVerified") is (retained > 0) and
            readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "parser artifact registry overclaims readiness")

    if not artifacts:
        require(not release_ids and retained == 0 and replayed == 0 and
                expected_decision == "BLOCKED_NO_REVIEWED_PARSER_ARTIFACT",
                "empty parser registry boundary drift")

    runbook = (ROOT / contract["runbook"]).read_text(encoding="utf-8")
    for phrase in (
        "Test harness is not an artifact", "Required artifact identity",
        "Required review", "Retention states", "Replay evidence",
        "Production remains **NO_GO**",
    ):
        require(phrase in runbook, f"parser artifact runbook missing phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "parser artifact registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "empty parser registry cannot make OPS-P0-008 ready")

    print("Memory OS parser artifact registry validation PASS")
    print(f"reviewed artifacts: {len(artifacts)}")
    print(f"retained rollback artifacts: {retained}")
    print(f"replay-proven artifacts: {replayed}")
    print(f"decision: {expected_decision}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"PARSER ARTIFACT REGISTRY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
