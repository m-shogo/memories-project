#!/usr/bin/env python3
"""Fail-closed validation for bounded compatibility foundations.

This authority is supplemental. It may record candidate-only and local-CI-only
proof, but it cannot promote the canonical approved-release matrix or production
readiness.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_PATH = ROOT / "contracts/operations/version-compatibility-foundations.v1.json"
CANONICAL_PATH = ROOT / "contracts/operations/version-compatibility-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RELEASE_CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
ROLLBACK_CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
ROLLBACK_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
ROLLBACK_WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
PARSER_REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
PARSER_WRITER_PATH = ROOT / "scripts/register-memory-os-parser-artifact.py"
PAIR_REGISTRY_PATH = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
PAIR_WRITER_PATH = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
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

REQUIRED_STATUS_REFS = {
    "contracts/operations/version-compatibility-foundations.v1.json",
    "docs/runbooks/memory-os-version-compatibility-foundations.md",
    "scripts/validate-memory-os-version-compatibility-foundations.py",
    "scripts/reconcile-memory-os-version-compatibility-foundation-status.py",
    ".github/workflows/version-compatibility-foundations.yml",
}
PAIR_MISSING = "approved predecessor and successor release pair despite candidate-only mixed-version evidence"
PARSER_MISSING = "reviewed production parser artifact with exact-byte replay and immutable rollback retention evidence"


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


def load_module(path: Path, name: str) -> Any:
    require(path.is_file(), f"missing authority module: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique_strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", value, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def validate_foundation_contract() -> dict[str, Any]:
    contract = load(FOUNDATION_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-version-compatibility-foundations.v1",
            "foundation schema drift")
    require(contract.get("canonicalCompatibilityContract") ==
            "contracts/operations/version-compatibility-contract.v1.json",
            "canonical compatibility reference drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-version-compatibility-foundations.py",
            "foundation validator path drift")
    require(contract.get("reconcile") ==
            "scripts/reconcile-memory-os-version-compatibility-foundation-status.py",
            "foundation reconcile path drift")
    require(contract.get("runbook") ==
            "docs/runbooks/memory-os-version-compatibility-foundations.md",
            "foundation runbook path drift")
    require(contract.get("workflow") ==
            ".github/workflows/version-compatibility-foundations.yml",
            "foundation workflow path drift")

    canonical = load(CANONICAL_PATH)
    require(canonical.get("schemaVersion") == "memory-os-version-compatibility.v1",
            "canonical compatibility schema drift")
    require(canonical.get("productionDecision") == "NO_GO",
            "canonical compatibility decision changed")
    require("supplementalCompatibilityEvidence" not in canonical,
            "bounded foundations must not be embedded into the canonical matrix")
    require("foundationEvidenceRefs" not in canonical,
            "bounded foundation refs must remain outside the canonical matrix")

    foundations = contract.get("foundations")
    require(isinstance(foundations, list) and len(foundations) == 5,
            "foundation count drift")
    by_id: dict[str, dict[str, Any]] = {}
    for item in foundations:
        require(isinstance(item, dict), "foundation entry must be an object")
        identifier = item.get("id")
        require(isinstance(identifier, str) and identifier not in by_id,
                "foundation ID invalid or duplicated")
        by_id[identifier] = item
    require(set(by_id) == set(EXPECTED_FOUNDATIONS),
            "foundation ID set drift")

    for identifier, (direction, status) in EXPECTED_FOUNDATIONS.items():
        item = by_id[identifier]
        require(item.get("direction") == direction,
                f"{identifier}: direction drift")
        require(item.get("status") == status,
                f"{identifier}: status drift")
        unique_strings(item.get("proven"), f"{identifier}.proven")
        unique_strings(item.get("notProven"), f"{identifier}.notProven")
        refs = unique_strings(item.get("evidenceRefs"), f"{identifier}.evidenceRefs")
        for ref in refs:
            require(not ref.startswith("/") and ".." not in Path(ref).parts,
                    f"{identifier}: unsafe evidence path: {ref}")
            require((ROOT / ref).exists(), f"{identifier}: missing evidence: {ref}")

    boundary = contract.get("aggregateBoundaries")
    require(isinstance(boundary, dict), "aggregateBoundaries missing")
    expected_boundary = {
        "canonicalReleaseMatrixChanged": False,
        "approvedReleaseCount": 0,
        "approvedRollbackPairCount": 0,
        "reviewedParserArtifactCount": 0,
        "productionEvidence": False,
        "releaseCompatibilityEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    }
    count_fields = {
        "approvedReleaseCount",
        "approvedRollbackPairCount",
        "reviewedParserArtifactCount",
    }
    for field, expected in expected_boundary.items():
        value = boundary.get(field)
        if field in count_fields:
            require(isinstance(value, int) and not isinstance(value, bool) and value == 0,
                    f"aggregate boundary {field} must be integer zero")
        else:
            require(value == expected, f"aggregate boundary drift: {field}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "foundation readiness missing")
    for field in (
        "contractDefined", "validatorImplemented", "statusReconcileImplemented",
        "automaticWorkflowImplemented", "candidateOnlyMixedVersionEvidenceAvailable",
        "postgresql17LogicalForwardEvidenceAvailable",
        "parserArtifactAuthorityDefined",
        "releaseAndRollbackAdmissionAuthoritiesDefined",
    ):
        require(readiness.get(field) is True, f"foundation readiness missing: {field}")
    for field in (
        "approvedReleasePairAvailable", "reviewedParserArtifactAvailable",
        "productionRolloutRehearsed", "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"foundation authority overclaims readiness: {field}")

    refs = unique_strings(contract.get("evidenceRefs"), "evidenceRefs")
    for ref in refs:
        require((ROOT / ref).is_file(), f"foundation authority evidence missing: {ref}")
    return contract


def validate_candidate_result() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-candidate-results.v1",
            "candidate result schema drift")
    require(is_ancestor(result.get("currentCommitSha")),
            "candidate source is not an ancestor of HEAD")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("candidateBaselineOnly") is True and
            environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("containsSecrets") is False,
            "candidate evidence boundary drift")
    require(isinstance(scenario, dict) and
            scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "candidate result is not PASS")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions and all(assertions.values()),
            "candidate assertions are incomplete")


def validate_session_result() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-session-results.v1",
            "session result schema drift")
    require(is_ancestor(result.get("commitSha")),
            "mixed-version session source is not an ancestor of HEAD")
    environment = result.get("environment")
    assertions = result.get("assertions")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "session evidence boundary drift")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "session result is not PASS")
    require(isinstance(assertions, dict) and
            assertions.get("oldHealthStatus") == 200 and
            assertions.get("currentHealthStatus") == 200 and
            assertions.get("activeSessionRows") == 2 and
            assertions.get("sharedCurrentSchema") is True and
            assertions.get("oldAndCurrentProcessesConcurrent") is True and
            assertions.get("rawTokensPersisted") is False,
            "session assertions are incomplete")


def validate_apply_result() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json")
    require(result.get("schemaVersion") == "memory-os-mixed-version-apply-results.v1",
            "Apply result schema drift")
    require(is_ancestor(result.get("currentCommitSha")),
            "Apply result source is not an ancestor of HEAD")
    environment = result.get("environment")
    assertions = result.get("assertions")
    require(isinstance(environment, dict) and
            environment.get("historicalCandidateOnly") is True and
            environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("containsSecrets") is False,
            "Apply evidence boundary drift")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "Apply result is not PASS")
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
        "noDuplicateMaterialization": True,
    }
    require(isinstance(assertions, dict), "Apply assertions missing")
    for field, expected_value in expected.items():
        require(assertions.get(field) == expected_value,
                f"Apply assertion drift: {field}")


def validate_postgresql_result() -> None:
    result = load(ROOT / "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json")
    require(result.get("schemaVersion") ==
            "memory-os-postgresql-major-upgrade-results.v1",
            "PostgreSQL result schema drift")
    require(is_ancestor(result.get("commitSha")),
            "PostgreSQL result source is not an ancestor of HEAD")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("containsSecrets") is False,
            "PostgreSQL evidence boundary drift")
    require(isinstance(scenario, dict) and
            scenario.get("sourceMajor") == 16 and
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
            "PostgreSQL logical upgrade assertions are incomplete")


def validate_source_authorities() -> dict[str, int]:
    releases = load(RELEASE_REGISTRY_PATH)
    rollback = load(ROLLBACK_REGISTRY_PATH)
    parsers = load(PARSER_REGISTRY_PATH)
    pairs = load(PAIR_REGISTRY_PATH)
    release_contract = load(RELEASE_CONTRACT_PATH)
    rollback_contract = load(ROLLBACK_CONTRACT_PATH)
    release_writer = load_module(RELEASE_WRITER_PATH, "memory_os_release_baseline_writer_for_foundation_validator")
    rollback_writer = load_module(ROLLBACK_WRITER_PATH, "memory_os_rollback_rehearsal_writer_for_foundation_validator")
    parser_writer = load_module(PARSER_WRITER_PATH, "memory_os_parser_artifact_writer_for_foundation_validator")
    pair_writer = load_module(PAIR_WRITER_PATH, "memory_os_release_pair_writer_for_foundation_validator")
    try:
        release_writer.validate_registry_for_append(releases, release_contract)
        rollback_writer.validate_registry_for_append(rollback, rollback_contract, releases)
        parser_writer.validate_registry_for_append(parsers)
        pair_writer.validate_registry_for_append(pairs)
    except Exception as exc:
        raise ValidationFailure(f"compatibility source authority invalid: {exc}") from exc
    counts = {
        "approvedReleases": releases.get("approvedReleaseCount"),
        "rollbackRequests": rollback.get("rehearsalRequestCount"),
        "reviewedParserArtifacts": parsers.get("reviewedArtifactCount"),
        "approvedReleasePairs": pairs.get("approvedPairCount"),
    }
    for field, value in counts.items():
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"compatibility source {field} must be a non-negative integer")
    return counts


def validate_status(source_counts: dict[str, int]) -> None:
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "foundation authority changed production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    matches = [item for item in areas
               if isinstance(item, dict) and item.get("id") == "OPS-P0-008"]
    require(len(matches) == 1, "OPS-P0-008 must exist exactly once")
    area = matches[0]
    require(area.get("status") == "PARTIAL",
            "bounded foundations cannot make OPS-P0-008 READY")
    refs = area.get("evidenceRefs")
    require(isinstance(refs, list), "OPS-P0-008 evidenceRefs missing")
    require(REQUIRED_STATUS_REFS.issubset(set(refs)),
            "OPS-P0-008 omits bounded foundation authority refs")
    existing = [str(item).lower() for item in area.get("existingEvidence", [])]
    missing_raw = area.get("missingEvidence")
    require(isinstance(missing_raw, list), "OPS-P0-008 missingEvidence must be a list")
    missing = [str(item).lower() for item in missing_raw]
    require(any("supplemental compatibility foundation authority" in item
                for item in existing),
            "OPS-P0-008 omits bounded foundation evidence")
    required_terms = [
        ("rolling", "rollback", "rollback-eligible"),
        ("client/server", "skew"),
        ("blue-green", "connection-pool", "failover"),
        ("independent review", "critical", "high"),
    ]
    if source_counts["approvedReleasePairs"] == 0:
        required_terms.append(("approved", "predecessor", "successor"))
        require(PAIR_MISSING in missing_raw, "approved release pair gap missing while pair authority is empty")
    else:
        require(PAIR_MISSING not in missing_raw, "satisfied approved release pair gap was reintroduced")
    if source_counts["reviewedParserArtifacts"] == 0:
        required_terms.append(("reviewed", "parser artifact", "retention"))
        require(PARSER_MISSING in missing_raw, "parser artifact gap missing while parser authority is empty")
    else:
        require(PARSER_MISSING not in missing_raw, "satisfied parser artifact gap was reintroduced")
    for terms in required_terms:
        require(any(all(term in item for term in terms) for item in missing),
                f"required compatibility gap disappeared: {terms}")


def main() -> int:
    validate_foundation_contract()
    validate_candidate_result()
    validate_session_result()
    validate_apply_result()
    validate_postgresql_result()
    source_counts = validate_source_authorities()
    validate_status(source_counts)
    print("Memory OS bounded compatibility foundation validation PASS")
    print("foundations: 5")
    print(f"approved source release pairs: {source_counts['approvedReleasePairs']}")
    print(f"reviewed source parser artifacts: {source_counts['reviewedParserArtifacts']}")
    print("foundation production authority: unchanged")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"COMPATIBILITY FOUNDATION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
