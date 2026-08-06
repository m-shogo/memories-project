#!/usr/bin/env python3
"""Fail-closed validator for Memory OS version compatibility policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/version-compatibility-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_DIMENSIONS = {
    "HTTP_CLIENT_SERVER": "SAME_VERSION_SERVER_TESTS_ONLY",
    "BACKEND_DATABASE": "CLEAN_DATABASE_CURRENT_VERSION_ONLY",
    "ROLLING_BACKEND": "NOT_PROVEN",
    "PERSISTED_JOB_PREVIEW": "PARTIAL_VERSION_AND_HASH_BINDINGS",
    "PARSER_ARTIFACT": "DIGEST_PINNING_AND_CURRENT_ARTIFACT_TESTS",
    "OBJECT_VERSION": "LOCAL_MINIO_VERSION_BINDING_ONLY",
}
EXPECTED_MATRIX = {
    "COMPAT-001": ("CURRENT_BACKEND_CURRENT_SCHEMA", "PROVEN_IN_CI"),
    "COMPAT-002": ("OLD_BACKEND_NEW_SCHEMA", "NOT_PROVEN"),
    "COMPAT-003": ("NEW_BACKEND_OLD_SCHEMA", "FORBIDDEN_RELEASE_ORDER"),
    "COMPAT-004": ("ROLLING_BACKEND_MIX", "NOT_PROVEN"),
    "COMPAT-005": ("OLD_PERSISTED_STATE_NEW_CONSUMER", "PARTIAL"),
    "COMPAT-006": ("OLD_ARTIFACT_NEW_SUPERVISOR", "NOT_PROVEN"),
    "COMPAT-007": ("OLD_CLIENT_NEW_SERVER", "NOT_IMPLEMENTED_OR_PROVEN"),
    "COMPAT-008": ("NEW_CLIENT_OLD_SERVER", "NOT_IMPLEMENTED_OR_PROVEN"),
    "COMPAT-009": ("OLD_OBJECT_VERSION_NEW_CONSUMER", "LOCAL_PROOF_ONLY"),
}
REQUIRED_STATUS_REFS = {
    ".github/workflows/security-contracts.yml",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/version-compatibility-contract.v1.json",
    "docs/runbooks/memory-os-version-compatibility.md",
    "scripts/validate-memory-os-version-compatibility.py",
}
REQUIRED_RUNBOOK_HEADINGS = [
    "## Compatibility directions are not interchangeable",
    "## Current proven baseline",
    "## Required release record",
    "## Step 1 — Classify every change",
    "## Step 2 — Build the matrix",
    "## Step 3 — Verify rollback target",
    "## Step 4 — Rollout order",
    "## Step 5 — Client compatibility",
    "## Step 6 — PostgreSQL upgrades",
    "## Step 7 — Observe mixed versions",
    "## Step 8 — Contract and retire versions",
    "## Failure decisions",
    "## Evidence and status rules",
    "## Current limitations",
]
REQUIRED_RUNBOOK_PHRASES = [
    "Production decision remains: **NO_GO**",
    "A PASS in one direction does not imply the reverse direction",
    "Do not begin a rolling production rollout while `ROLLING_BACKEND_MIX` is `NOT_PROVEN`",
    "The canonical iOS client is not implemented",
    "A mobile client cannot be rolled back instantly",
    "A successful schema migration on PostgreSQL 16 does not prove PostgreSQL 17 compatibility",
    "No matrix entry becomes proven from dependency pinning alone",
]


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
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def unique_strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    if not allow_empty:
        require(value, f"{field} must not be empty")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def object_map(value: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{field} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        require(isinstance(item, dict), f"{field} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier, f"{field}.{key} is required")
        require(identifier not in result, f"duplicate {field} identifier: {identifier}")
        result[identifier] = item
    return result


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-version-compatibility.v1",
            "unsupported compatibility schemaVersion")
    require(contract.get("canonicalRunbook") == "docs/runbooks/memory-os-version-compatibility.md",
            "canonicalRunbook drift")
    require(contract.get("validator") == "scripts/validate-memory-os-version-compatibility.py",
            "validator path drift")
    require(contract.get("productionDecision") == "NO_GO",
            "compatibility policy cannot change productionDecision")

    baselines = contract.get("currentBaselines")
    require(isinstance(baselines, dict), "currentBaselines must be an object")
    expected_baselines = {
        "go": "1.23.x",
        "postgresql": "16",
        "httpApiMajor": "v1",
        "signedUploadOpenAPI": "memory-os-signed-upload.v1",
        "genericCsvAdapter": "1.0.0",
        "parserArtifactPolicy": "DIGEST_PINNED",
        "databaseMigrationPolicy": "EXPAND_MIGRATE_CONTRACT",
        "canonicalClient": "IOS_NOT_IMPLEMENTED",
        "desktopPortal": "LIMITED_NOT_IMPLEMENTED",
    }
    require(baselines == expected_baselines,
            f"current compatibility baselines drift: {baselines}")

    dimensions = object_map(contract.get("compatibilityDimensions"), "id", "compatibilityDimensions")
    require(set(dimensions) == set(EXPECTED_DIMENSIONS),
            f"compatibility dimension set drift: {sorted(dimensions)}")
    for dimension_id, expected_evidence in EXPECTED_DIMENSIONS.items():
        item = dimensions[dimension_id]
        require(item.get("currentEvidence") == expected_evidence,
                f"{dimension_id}: currentEvidence drift")
        require(item.get("ready") is False,
                f"{dimension_id}: dimension cannot be READY before mixed-version proof")
        unique_strings(item.get("compatibleChanges"), f"{dimension_id}.compatibleChanges", allow_empty=False)
        unique_strings(item.get("breakingChanges"), f"{dimension_id}.breakingChanges", allow_empty=False)
        require(isinstance(item.get("breakingChangeAction"), str)
                and item["breakingChangeAction"],
                f"{dimension_id}: breakingChangeAction is required")
        require(isinstance(item.get("versionSignal"), str) and item["versionSignal"],
                f"{dimension_id}: versionSignal is required")

    require(dimensions["HTTP_CLIENT_SERVER"].get("breakingChangeAction")
            == "NEW_API_MAJOR_OR_EXPLICIT_COMPATIBILITY_BRIDGE",
            "HTTP breaking changes require a new API major or bridge")
    require(dimensions["BACKEND_DATABASE"].get("breakingChangeAction")
            == "STOP_RELEASE_AND_FOLLOW_MIGRATION_RECOVERY_RUNBOOK",
            "backend/database breaking changes must stop release")
    require(dimensions["OBJECT_VERSION"].get("breakingChangeAction")
            == "FAIL_CLOSED_AND_PRESERVE_AMBIGUOUS_STATE",
            "object version mismatch must fail closed")

    support = contract.get("supportPolicy")
    require(isinstance(support, dict), "supportPolicy must be an object")
    api_major = support.get("apiMajor")
    require(isinstance(api_major, dict), "supportPolicy.apiMajor must be an object")
    require(api_major.get("supportedMajors") == ["v1"], "supported API major drift")
    require(api_major.get("breakingChangeRequiresNewMajor") is True,
            "breaking HTTP change must require a new major")
    for unimplemented in (
        "parallelMajorSupportPolicyDefined",
        "deprecationNoticeWindowDefined",
        "clientMinimumVersionEnforcementImplemented",
    ):
        require(api_major.get(unimplemented) is False,
                f"unimplemented API support claim cannot be true: {unimplemented}")

    rolling = support.get("backendRollingWindow")
    require(isinstance(rolling, dict), "backendRollingWindow must be an object")
    require(rolling.get("target") == "CURRENT_AND_IMMEDIATELY_PREVIOUS_RELEASE",
            "rolling compatibility target drift")
    require(rolling.get("mixedVersionObservationRequired") is True,
            "mixed-version observation must be required")
    require(rolling.get("currentAndPreviousTested") is False,
            "current+previous backend mix is not proven")
    require(rolling.get("rollbackTargetValidatedBeforeRollout") is False,
            "rollback target validation is not implemented")

    database = support.get("database")
    require(isinstance(database, dict), "database support policy must be an object")
    require(database.get("supportedMajor") == "16", "PostgreSQL supported major drift")
    require(database.get("migrationLifecycleRef")
            == "contracts/operations/migration-lifecycle-contract.v1.json",
            "migration lifecycle reference drift")
    require(database.get("minorUpgradePolicyDefined") is False,
            "PostgreSQL minor upgrade policy is not defined")
    require(database.get("majorUpgradeRehearsalCompleted") is False,
            "PostgreSQL major upgrade rehearsal is not complete")

    clients = support.get("clients")
    require(isinstance(clients, dict), "client support policy must be an object")
    for claim in (
        "iOSSupportWindowDefined",
        "limitedPortalSupportWindowDefined",
        "offlineQueueSkewPolicyDefined",
        "forcedUpgradePolicyDefined",
    ):
        require(clients.get(claim) is False,
                f"client policy is not implemented: {claim}")

    parser = support.get("parserArtifacts")
    require(isinstance(parser, dict), "parserArtifacts support policy must be an object")
    for claim in (
        "reviewedRegistryImplemented",
        "retentionWindowDefined",
        "oldArtifactReplayTested",
    ):
        require(parser.get(claim) is False,
                f"parser artifact policy is not proven: {claim}")

    matrix = object_map(contract.get("compatibilityMatrix"), "id", "compatibilityMatrix")
    require(set(matrix) == set(EXPECTED_MATRIX),
            f"compatibility matrix set drift: {sorted(matrix)}")
    for matrix_id, (expected_direction, expected_status) in EXPECTED_MATRIX.items():
        item = matrix[matrix_id]
        require(item.get("direction") == expected_direction,
                f"{matrix_id}: direction drift")
        require(item.get("status") == expected_status,
                f"{matrix_id}: unsupported status promotion from {expected_status}")
        refs = unique_strings(item.get("evidenceRefs"), f"{matrix_id}.evidenceRefs",
                              allow_empty=True)
        for ref in refs:
            require((ROOT / ref).exists(), f"{matrix_id}: evidence path missing: {ref}")
        if expected_status in {"PROVEN_IN_CI", "PARTIAL", "LOCAL_PROOF_ONLY", "FORBIDDEN_RELEASE_ORDER"}:
            require(refs, f"{matrix_id}: status {expected_status} requires evidenceRefs")
        if expected_status in {"NOT_PROVEN", "NOT_IMPLEMENTED_OR_PROVEN"}:
            require(not refs, f"{matrix_id}: unproven status must not carry proof refs")

    release_gates = unique_strings(contract.get("releaseGates"), "releaseGates")
    for required_gate in (
        "record exact old and new",
        "classify every changed",
        "run old/new mixed-version tests",
        "prove rollback target",
        "unknown version",
        "schema contraction",
        "retain required parser artifacts",
        "update the compatibility matrix",
        "block release",
    ):
        require(any(required_gate in gate for gate in release_gates),
                f"releaseGates omit: {required_gate}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "policyDefined",
        "dimensionsDefined",
        "matrixDefined",
        "releaseGatesDefined",
        "sameVersionCurrentStackProven",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "oldBackendNewSchemaProven",
        "rollingBackendMixProven",
        "oldPersistedStateNewConsumerProven",
        "oldArtifactNewSupervisorProven",
        "clientServerSkewPolicyImplemented",
        "clientServerSkewProven",
        "databaseUpgradePolicyDefined",
        "productionRolloutRehearsalCompleted",
        "independentReviewCompleted",
        "ready",
    ):
        require(readiness.get(unproven) is False,
                f"unproven compatibility readiness cannot be true: {unproven}")

    evidence_refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs")
    require(set(evidence_refs) == REQUIRED_STATUS_REFS,
            f"compatibility evidenceRefs drift: {evidence_refs}")
    for ref in evidence_refs:
        require((ROOT / ref).exists(), f"compatibility evidence path missing: {ref}")

    runbook_path = ROOT / contract["canonicalRunbook"]
    try:
        runbook = runbook_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("canonical compatibility runbook is missing") from exc
    for heading in REQUIRED_RUNBOOK_HEADINGS:
        require(heading in runbook, f"compatibility runbook missing heading: {heading}")
    for phrase in REQUIRED_RUNBOOK_PHRASES:
        require(phrase in runbook, f"compatibility runbook missing binding phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "compatibility foundations cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-008"]
    require(len(matches) == 1, "OPS-P0-008 must exist exactly once")
    area = matches[0]
    require(area.get("status") in {"PARTIAL", "READY"},
            "OPS-P0-008 must be PARTIAL or READY after compatibility policy")
    status_refs = area.get("evidenceRefs")
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs must be a list")
    missing_refs = REQUIRED_STATUS_REFS - set(status_refs)
    require(not missing_refs,
            f"OPS-P0-008 omits compatibility evidence: {sorted(missing_refs)}")

    if area.get("status") == "READY":
        for requirement in (
            "oldBackendNewSchemaProven",
            "rollingBackendMixProven",
            "oldPersistedStateNewConsumerProven",
            "oldArtifactNewSupervisorProven",
            "clientServerSkewPolicyImplemented",
            "clientServerSkewProven",
            "databaseUpgradePolicyDefined",
            "productionRolloutRehearsalCompleted",
            "independentReviewCompleted",
            "ready",
        ):
            require(readiness.get(requirement) is True,
                    f"OPS-P0-008 READY without readiness.{requirement}")
    else:
        missing = area.get("missingEvidence")
        require(isinstance(missing, list) and missing,
                "PARTIAL OPS-P0-008 requires missingEvidence")
        for required_gap in (
            "mixed-version",
            "persisted-state",
            "parser artifact",
            "client/server",
            "PostgreSQL",
            "production rolling",
            "independent review",
        ):
            require(any(required_gap in item for item in missing),
                    f"OPS-P0-008 missingEvidence must retain: {required_gap}")

    print("Memory OS version compatibility validation PASS")
    print(f"compatibility dimensions: {len(dimensions)}")
    print(f"matrix entries: {len(matrix)}")
    print(f"OPS-P0-008 status: {area.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"VERSION COMPATIBILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
