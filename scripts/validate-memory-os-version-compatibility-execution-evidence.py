#!/usr/bin/env python3
"""Validate supplemental compatibility execution evidence without manufacturing release authority."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
FOUNDATION = ROOT / "contracts/operations/version-compatibility-foundations.v1.json"
RESULTS = {
    "historicalCandidateCurrentExpandedSchema": ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json",
    "crossVersionSessionAuthority": ROOT / "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
    "crossVersionPersistedApplyReplay": ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "simultaneousOldCurrentApplyClaimRace": ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "historicalProcessSIGKILLApplyRollbackRecovery": ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "postgresql16To17LogicalForwardRestore": ROOT / "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
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
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-version-compatibility-execution-evidence.v1", "contract schema drift")
    evidence = contract.get("evidence")
    require(isinstance(evidence, dict), "evidence must be object")
    for key, path in RESULTS.items():
        item = evidence.get(key)
        require(isinstance(item, dict), f"evidence entry missing: {key}")
        require(item.get("proven") is True, f"execution evidence must remain true: {key}")
        require(item.get("scope") in {"CANDIDATE_ONLY_LOCAL_CI", "LOCAL_CI_ONLY"}, f"unsafe scope: {key}")
        require(item.get("resultRef") == str(path.relative_to(ROOT)), f"result ref drift: {key}")

    candidate = load(RESULTS["historicalCandidateCurrentExpandedSchema"])
    require(candidate.get("environment", {}).get("candidateBaselineOnly") is True, "candidate result must remain candidate-only")
    require(candidate.get("environment", {}).get("releaseCompatibilityEvidence") is False, "candidate result cannot become release evidence")
    require(candidate.get("environment", {}).get("productionEvidence") is False, "candidate result cannot be production evidence")
    scenario = candidate.get("scenario", {})
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "candidate result must PASS")
    assertions = scenario.get("assertions", {})
    for key in (
        "baselineIsAncestorOfCurrent",
        "currentExpandedSchemaAppliedToBothDatabases",
        "candidateBaselineSqlTestsPassed",
        "candidateBaselineGoTestsPassed",
        "candidateExecutionPreservedSchemaFingerprint",
        "currentSqlTestsPassed",
        "currentGoTestsPassed",
    ):
        require(assertions.get(key) is True, f"candidate assertion missing: {key}")

    session = load(RESULTS["crossVersionSessionAuthority"])
    require(session.get("result") == "PASS" and session.get("integrityResult") == "PASS", "session result must PASS")
    require(session.get("environment", {}).get("productionEvidence") is False, "session result cannot be production evidence")
    session_assertions = session.get("assertions", {})
    require(session_assertions.get("sharedCurrentSchema") is True, "shared session schema proof missing")
    require(session_assertions.get("oldAndCurrentProcessesConcurrent") is True, "old/current session processes must be concurrent")
    require(session_assertions.get("activeSessionRows") == 2, "session row proof drift")

    apply = load(RESULTS["crossVersionPersistedApplyReplay"])
    require(apply.get("result") == "PASS" and apply.get("integrityResult") == "PASS", "mixed-version Apply result must PASS")
    environment = apply.get("environment", {})
    require(environment.get("historicalCandidateOnly") is True, "Apply evidence must remain candidate-only")
    require(environment.get("releaseCompatibilityEvidence") is False, "Apply evidence cannot become release evidence")
    require(environment.get("productionEvidence") is False, "Apply evidence cannot become production evidence")
    apply_assertions = apply.get("assertions", {})
    for key in (
        "oldToCurrentApplyIdStable",
        "currentToOldApplyIdStable",
        "concurrentOldCurrentClaimRacePassed",
        "oldProcessKilledDuringInProgressApply",
        "oldProcessTerminationRecoveryPassed",
        "noDuplicateMaterialization",
        "sharedCurrentSchema",
        "oldAndCurrentProcessesConcurrent",
    ):
        require(apply_assertions.get(key) is True, f"mixed-version Apply assertion missing: {key}")
    for key in ("terminatedAttemptApplyRows", "terminatedAttemptMemoryRows", "terminatedAttemptInProgressRows", "finalInProgressApplyRows"):
        require(apply_assertions.get(key) == 0, f"mixed-version Apply durable residue drift: {key}")

    pg = load(RESULTS["postgresql16To17LogicalForwardRestore"])
    require(pg.get("environment", {}).get("productionEvidence") is False, "PG upgrade result cannot be production evidence")
    pg_scenario = pg.get("scenario", {})
    require(pg_scenario.get("result") == "PASS" and pg_scenario.get("integrityResult") == "PASS", "PG16->17 result must PASS")
    pg_assertions = pg_scenario.get("assertions", {})
    for key in (
        "allCurrentMigrationsAppliedToSource",
        "allCurrentMigrationsAppliedToTarget",
        "dataOnlyDumpCreated",
        "dataOnlyRestoreCompleted",
        "schemaAuthorityFingerprintEqual",
        "allCanonicalSqlTestsPassedOnTarget",
    ):
        require(pg_assertions.get(key) is True, f"PG16->17 assertion missing: {key}")
    require(pg_assertions.get("deletedSyntheticAccountsAfterUpgrade") == 0, "deleted account resurrection detected")
    require(pg_assertions.get("deletedSyntheticSessionsResolvedAfterUpgrade") == 0, "deleted session resurrection detected")

    foundation = load(FOUNDATION)
    boundaries = foundation.get("aggregateBoundaries", {})
    release = contract.get("releaseAuthorityBoundary", {})
    for key in ("approvedReleaseCount", "approvedRollbackPairCount", "reviewedParserArtifactCount"):
        require(release.get(key) == boundaries.get(key) == 0, f"release boundary drift: {key}")
    for key in ("canonicalReleaseMatrixChanged", "releaseCompatibilityEvidence", "productionEvidence", "productionReady"):
        require(release.get(key) is False, f"execution evidence cannot enable {key}")
    require(release.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    not_proven = contract.get("notProven")
    require(isinstance(not_proven, dict) and not_proven, "notProven boundary required")
    for key, value in not_proven.items():
        require(value is True, f"unproven boundary disappeared: {key}")

    readiness = contract.get("readiness", {})
    for key in (
        "executionEvidenceClassified",
        "candidateOnlyMixedVersionExecutionProven",
        "candidateApplyConcurrencyAndSIGKILLRecoveryProven",
        "postgresql17LogicalForwardExecutionProven",
    ):
        require(readiness.get(key) is True, f"readiness proof missing: {key}")
    for key in (
        "approvedReleasePairAvailable",
        "productionRollingDeploymentProven",
        "clientServerSkewProven",
        "reviewedParserArtifactAvailable",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"execution evidence cannot enable readiness.{key}")

    print("Memory OS version compatibility execution evidence PASS")
    print("candidate/current sessions + Apply concurrency/SIGKILL: proven locally")
    print("PostgreSQL 16->17 logical forward restore: proven locally")
    print("approved release pair: false")
    print("release compatibility evidence: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"VERSION COMPATIBILITY EXECUTION EVIDENCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
