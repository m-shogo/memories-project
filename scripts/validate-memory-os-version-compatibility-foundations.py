#!/usr/bin/env python3
"""Validate candidate-only and foundation-only compatibility overlays.

This validator never promotes the canonical release matrix. It verifies that
bounded evidence is represented accurately alongside explicit non-production
and non-release limitations.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/version-compatibility-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RUNBOOK_PATH = ROOT / "docs/runbooks/memory-os-version-compatibility.md"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_FOUNDATIONS = {
    "FOUNDATION-001": (
        "HISTORICAL_CANDIDATE_BACKEND_CURRENT_EXPANDED_SCHEMA",
        "PASS_CANDIDATE_ONLY",
    ),
    "FOUNDATION-002": (
        "HISTORICAL_CANDIDATE_CURRENT_SHARED_SCHEMA_SESSIONS_AND_APPLY",
        "PASS_CANDIDATE_ONLY",
    ),
    "FOUNDATION-003": (
        "POSTGRESQL_16_TO_17_LOGICAL_FORWARD_RESTORE",
        "PASS_LOCAL_CI_ONLY",
    ),
    "FOUNDATION-004": (
        "REVIEWED_PARSER_ARTIFACT_AUTHORITY",
        "FOUNDATION_ONLY_EMPTY",
    ),
    "FOUNDATION-005": (
        "APPROVED_RELEASE_AND_ROLLBACK_ADMISSION",
        "BLOCKED_NO_APPROVED_PAIR",
    ),
}
REQUIRED_FOUNDATION_REFS = {
    "contracts/operations/mixed-version-session-contract.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
    "contracts/operations/mixed-version-candidate-contract.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json",
    "contracts/operations/mixed-version-apply-contract.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "contracts/operations/rollback-rehearsal-gate-contract.v1.json",
    "contracts/operations/rollback-rehearsal-registry.v1.json",
    "contracts/operations/parser-artifact-registry-contract.v1.json",
    "contracts/operations/parser-artifact-registry.v1.json",
    "contracts/operations/postgresql-major-upgrade-contract.v1.json",
    "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
    "scripts/validate-memory-os-version-compatibility-foundations.py",
}


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


def is_ancestor(base: Any, head: str = "HEAD") -> bool:
    if not isinstance(base, str) or SHA_RE.fullmatch(base) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, head],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def unique_strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_foundation_entry(item: dict[str, Any], expected_direction: str,
                              expected_status: str) -> None:
    require(item.get("direction") == expected_direction,
            f"{item.get('id')}: direction drift")
    require(item.get("status") == expected_status,
            f"{item.get('id')}: status drift")
    proven = unique_strings(item.get("proven"), f"{item.get('id')}.proven")
    not_proven = unique_strings(item.get("notProven"), f"{item.get('id')}.notProven")
    refs = unique_strings(item.get("evidenceRefs"), f"{item.get('id')}.evidenceRefs")
    require(proven and not_proven, f"{item.get('id')}: boundaries must be explicit")
    for ref in refs:
        path = ROOT / ref
        require(path.exists(), f"{item.get('id')}: evidence missing: {ref}")


def validate_mixed_version_candidate() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-candidate-results.v1",
            "candidate result schema drift")
    require(is_ancestor(result.get("currentCommitSha")),
            "candidate current source is not an ancestor")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("candidateBaselineOnly") is True and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "candidate evidence boundary drift")
    require(isinstance(scenario, dict) and scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS" and
            all(scenario.get("assertions", {}).values()),
            "candidate compatibility result is not complete PASS")


def validate_mixed_version_session() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-session-results.v1",
            "mixed-version session result schema drift")
    current_sha = result.get("currentCommitSha")
    require(is_ancestor(current_sha), "mixed-version session source is not an ancestor")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    require("pass" in serialized, "mixed-version session evidence does not contain PASS")
    for forbidden in ("postgres://", "postgresql://", "bearer ", "password="):
        require(forbidden not in serialized,
                f"mixed-version session evidence contains forbidden content: {forbidden}")


def validate_mixed_version_apply() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-apply-results.v1",
            "mixed-version Apply result schema drift")
    require(is_ancestor(result.get("currentCommitSha")),
            "mixed-version Apply source is not an ancestor")
    environment = result.get("environment")
    assertions = result.get("assertions")
    require(isinstance(environment, dict) and
            environment.get("historicalCandidateOnly") is True and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "mixed-version Apply evidence boundary drift")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "mixed-version Apply result is not PASS")
    require(isinstance(assertions, dict), "mixed-version Apply assertions missing")
    expected = {
        "concurrentOldCurrentClaimRacePassed": True,
        "concurrentOldCurrentClaimRaceReplaySplit": True,
        "concurrentOldCurrentClaimRaceApplyIdStable": True,
        "oldProcessTerminationWaitObserved": True,
        "oldProcessKilledDuringInProgressApply": True,
        "terminatedAttemptApplyRows": 0,
        "terminatedAttemptMemoryRows": 0,
        "terminatedAttemptInProgressRows": 0,
        "currentRecoveryStatus": 200,
        "currentRecoveryReplayed": False,
        "currentRecoveryCreatedCount": 1,
        "oldProcessTerminationRecoveryPassed": True,
        "postTerminationRecoveryApplyConfirmationRows": 4,
        "postTerminationRecoveryMemoryItemRows": 4,
        "postTerminationRecoveryDistinctSourcePreviews": 4,
        "postTerminationRecoveryInProgressRows": 0,
        "recoveredPreviewApplyConfirmationRows": 1,
        "recoveredPreviewMemoryItemRows": 1,
        "noDuplicateMaterialization": True,
    }
    for field, value in expected.items():
        require(assertions.get(field) == value,
                f"mixed-version Apply assertion drift: {field}")


def validate_postgresql_upgrade() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json")
    require(result.get("schemaVersion") ==
            "memory-os-postgresql-major-upgrade-results.v1",
            "PostgreSQL upgrade result schema drift")
    require(is_ancestor(result.get("commitSha")),
            "PostgreSQL upgrade source is not an ancestor")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("containsSecrets") is False,
            "PostgreSQL upgrade evidence boundary drift")
    require(isinstance(scenario, dict) and scenario.get("sourceMajor") == 16 and
            scenario.get("targetMajor") == 17 and
            scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "PostgreSQL logical upgrade result is not PASS")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and
            assertions.get("schemaAuthorityFingerprintEqual") is True and
            assertions.get("runtimeRolesWithoutBypassRls") == 4 and
            assertions.get("activeSyntheticSessionsResolvedAfterUpgrade") == 1 and
            assertions.get("deletedSyntheticSessionsResolvedAfterUpgrade") == 0 and
            assertions.get("allCanonicalSqlTestsPassedOnTarget") is True,
            "PostgreSQL logical upgrade assertions incomplete")


def validate_empty_authorities() -> None:
    releases = load(ROOT / "contracts/operations/release-baseline-registry.v1.json")
    rollback = load(ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json")
    rollback_gate = load(ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json")
    parsers = load(ROOT / "contracts/operations/parser-artifact-registry.v1.json")
    parser_contract = load(ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json")
    require(releases.get("approvedReleaseCount") == 0 and releases.get("releases") == [],
            "approved release registry is no longer empty")
    require(rollback.get("rehearsalRequestCount") == 0 and rollback.get("requests") == [],
            "rollback rehearsal registry is no longer empty")
    state = rollback_gate.get("currentAdmissionState")
    require(isinstance(state, dict) and state.get("approvedReleaseCount") == 0 and
            state.get("admissibleReleasePairCount") == 0 and
            state.get("admissionDecision") == "BLOCKED_NO_APPROVED_ROLLBACK_PAIR",
            "rollback admission is not blocked by empty approved release authority")
    require(parsers.get("reviewedArtifactCount") == 0 and
            parsers.get("retainedRollbackArtifactCount") == 0 and
            parsers.get("replayProvenArtifactCount") == 0 and
            parsers.get("artifacts") == [],
            "parser artifact registry is no longer empty")
    parser_state = parser_contract.get("currentAuthorityState")
    require(isinstance(parser_state, dict) and
            parser_state.get("decision") == "BLOCKED_NO_REVIEWED_PARSER_ARTIFACT",
            "empty parser authority decision drift")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-version-compatibility.v1",
            "version compatibility schema drift")
    foundations = contract.get("supplementalCompatibilityEvidence")
    require(isinstance(foundations, list) and len(foundations) == len(EXPECTED_FOUNDATIONS),
            "supplemental compatibility foundation count drift")
    by_id: dict[str, dict[str, Any]] = {}
    for item in foundations:
        require(isinstance(item, dict), "supplemental foundation must be an object")
        identifier = item.get("id")
        require(isinstance(identifier, str) and identifier not in by_id,
                "supplemental foundation ID invalid or duplicated")
        by_id[identifier] = item
    require(set(by_id) == set(EXPECTED_FOUNDATIONS),
            "supplemental foundation ID set drift")
    for identifier, (direction, status) in EXPECTED_FOUNDATIONS.items():
        validate_foundation_entry(by_id[identifier], direction, status)

    refs = unique_strings(contract.get("foundationEvidenceRefs"),
                          "foundationEvidenceRefs", len(REQUIRED_FOUNDATION_REFS))
    require(set(refs) == REQUIRED_FOUNDATION_REFS,
            "foundationEvidenceRefs drift")
    for ref in refs:
        require((ROOT / ref).is_file(), f"foundation evidence missing: {ref}")

    support = contract.get("supportPolicy")
    readiness = contract.get("readiness")
    require(isinstance(support, dict) and isinstance(readiness, dict),
            "supportPolicy or readiness missing")
    rolling = support.get("backendRollingWindow")
    database = support.get("database")
    parser = support.get("parserArtifacts")
    require(isinstance(rolling, dict) and
            rolling.get("historicalCandidateAndCurrentTested") is True and
            rolling.get("approvedCurrentAndPreviousReleaseTested") is False and
            rolling.get("currentAndPreviousTested") is False,
            "rolling foundation boundary drift")
    require(isinstance(database, dict) and
            database.get("postgresql17LogicalForwardUpgradeRehearsed") is True and
            database.get("postgresql17InPlaceOrBlueGreenCutoverRehearsed") is False and
            database.get("postgresql17PhysicalReplicationOrFailoverRehearsed") is False and
            database.get("postgresql17ProductionSupported") is False and
            database.get("majorUpgradeRehearsalCompleted") is False,
            "PostgreSQL support boundary drift")
    require(isinstance(parser, dict) and
            parser.get("reviewedRegistryAuthorityImplemented") is True and
            parser.get("reviewedArtifactCount") == 0 and
            parser.get("rollbackRetainedArtifactCount") == 0 and
            parser.get("testHarnessApproved") is False and
            parser.get("reviewedRegistryImplemented") is False and
            parser.get("oldArtifactReplayTested") is False,
            "parser artifact foundation boundary drift")

    for field in (
        "historicalCandidateNewSchemaProven",
        "historicalCandidateMixedProcessProven",
        "historicalCandidatePersistedApplyProven",
        "historicalCandidateConcurrentApplyRaceProven",
        "historicalCandidateInFlightTerminationRecoveryProven",
        "postgresql17LogicalForwardUpgradeProven",
        "parserArtifactRegistryAuthorityDefined",
        "rollbackRehearsalAdmissionGateDefined",
    ):
        require(readiness.get(field) is True, f"readiness foundation missing: {field}")
    for field in (
        "reviewedParserArtifactAvailable", "approvedRollbackPairAvailable",
        "oldBackendNewSchemaProven", "rollingBackendMixProven",
        "oldPersistedStateNewConsumerProven", "oldArtifactNewSupervisorProven",
        "productionRolloutRehearsalCompleted", "independentReviewCompleted", "ready",
    ):
        require(readiness.get(field) is False,
                f"foundation evidence overpromotes readiness: {field}")

    validate_mixed_version_candidate()
    validate_mixed_version_session()
    validate_mixed_version_apply()
    validate_postgresql_upgrade()
    validate_empty_authorities()

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "compatibility foundations cannot change production decision")
    area = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(area, dict) and area.get("status") == "PARTIAL",
            "OPS-P0-008 must remain PARTIAL")
    status_refs = area.get("evidenceRefs")
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs missing")
    status_required = REQUIRED_FOUNDATION_REFS - {
        "scripts/validate-memory-os-version-compatibility-foundations.py"
    }
    require(status_required <= set(status_refs),
            f"OPS-P0-008 omits foundation refs: {sorted(status_required - set(status_refs))}")
    missing = [str(item).lower() for item in area.get("missingEvidence", [])]
    for label, terms in {
        "approved release pair": ("approved", "predecessor", "successor"),
        "production rolling rollback": ("rolling", "rollback"),
        "reviewed parser artifact": ("reviewed", "parser artifact"),
        "client skew": ("client/server",),
        "database cutover": ("blue-green", "connection-pool"),
        "independent review": ("independent review",),
    }.items():
        require(any(all(term in item for term in terms) for item in missing),
                f"OPS-P0-008 required gap disappeared: {label}")

    try:
        runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure("version compatibility runbook missing") from exc
    for phrase in (
        "PASS_CANDIDATE_ONLY", "PASS_LOCAL_CI_ONLY",
        "approved releases: `0`", "reviewed parser artifacts: `0`",
        "SIGKILL of the historical process",
        "This is `PASS_LOCAL_CI_ONLY`",
        "The existing candidate-only, empty-registry and logical-upgrade foundations",
        "production remains `NO_GO`",
    ):
        require(phrase in runbook, f"runbook foundation phrase missing: {phrase}")

    print("Memory OS version compatibility foundation validation PASS")
    print(f"supplemental foundations: {len(foundations)}")
    print("approved releases: 0")
    print("reviewed parser artifacts: 0")
    print("OPS-P0-008 status: PARTIAL")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"VERSION COMPATIBILITY FOUNDATION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
