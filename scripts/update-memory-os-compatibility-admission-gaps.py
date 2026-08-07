#!/usr/bin/env python3
"""Generate a machine-readable next-admission report from canonical compatibility registries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CLIENTS = ROOT / "contracts/operations/client-baseline-registry.v1.json"
PARSERS = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
FOUNDATIONS = ROOT / "contracts/operations/version-compatibility-foundations.v1.json"
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
OUTPUT = ROOT / "contracts/operations/compatibility-admission-gaps.v1.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    releases = load(RELEASES)
    clients = load(CLIENTS)
    parsers = load(PARSERS)
    foundations = load(FOUNDATIONS)
    execution = load(EXECUTION)

    release_count = releases.get("approvedReleaseCount")
    client_count = clients.get("approvedClientBaselineCount")
    parser_count = parsers.get("reviewedArtifactCount")
    rollback_count = foundations.get("aggregateBoundaries", {}).get("approvedRollbackPairCount")
    if not all(isinstance(value, int) and value >= 0 for value in (release_count, client_count, parser_count, rollback_count)):
        raise SystemExit("compatibility registry counts must be non-negative integers")

    execution_readiness = execution.get("readiness", {})
    proven_candidate = {
        "candidateOnlyMixedVersionExecution": execution_readiness.get("candidateOnlyMixedVersionExecutionProven") is True,
        "candidateApplyConcurrencyAndSIGKILLRecovery": execution_readiness.get("candidateApplyConcurrencyAndSIGKILLRecoveryProven") is True,
        "postgresql17LogicalForwardExecution": execution_readiness.get("postgresql17LogicalForwardExecutionProven") is True,
    }
    if not all(proven_candidate.values()):
        raise SystemExit("candidate/local execution evidence regressed")

    blockers: list[dict[str, Any]] = []
    if release_count < 2:
        blockers.append({
            "id": "COMPAT-GAP-APPROVED-RELEASE-PAIR",
            "blocking": True,
            "current": release_count,
            "requiredMinimum": 2,
            "reason": "an approved predecessor and approved successor are required before release compatibility can be executed",
        })
    if rollback_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-ROLLBACK-PAIR",
            "blocking": True,
            "current": rollback_count,
            "requiredMinimum": 1,
            "reason": "at least one rollback-eligible approved release pair with retained exact artifacts and admitted rehearsal is required",
        })
    if client_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-APPROVED-CLIENT-BASELINE",
            "blocking": True,
            "current": client_count,
            "requiredMinimum": 1,
            "reason": "client/server support windows cannot exist without an immutable approved client artifact baseline",
        })
    if parser_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-REVIEWED-PARSER-ARTIFACT",
            "blocking": True,
            "current": parser_count,
            "requiredMinimum": 1,
            "reason": "production parser compatibility requires a reviewed immutable parser artifact and replay evidence",
        })

    blockers.extend([
        {
            "id": "COMPAT-GAP-ROLLING-DEPLOYMENT",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "approved old/current simultaneous traffic, connection drain, rollout ordering, stop conditions and application rollback are not proven",
        },
        {
            "id": "COMPAT-GAP-REMAINING-ROUTES",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "candidate/local execution covers session and Apply but not all import, Preview, parser and other persisted-state routes against an approved pair",
        },
        {
            "id": "COMPAT-GAP-DB-PRODUCTION-UPGRADE",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "local PostgreSQL 16-to-17 logical forward restore passes, but production-shaped pool drain, replication, WAL, failover and rollback decision evidence is absent",
        },
        {
            "id": "COMPAT-GAP-INDEPENDENT-REVIEW",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "integrated compatibility review with zero unresolved Critical or High findings is absent",
        },
    ])

    document = {
        "schemaVersion": "memory-os-compatibility-admission-gaps.v1",
        "sourceAuthorities": [
            str(RELEASES.relative_to(ROOT)),
            str(CLIENTS.relative_to(ROOT)),
            str(PARSERS.relative_to(ROOT)),
            str(FOUNDATIONS.relative_to(ROOT)),
            str(EXECUTION.relative_to(ROOT)),
        ],
        "currentCounts": {
            "approvedBackendReleases": release_count,
            "approvedClientBaselines": client_count,
            "reviewedProductionParserArtifacts": parser_count,
            "approvedRollbackPairs": rollback_count,
        },
        "alreadyProvenCandidateLocalOnly": proven_candidate,
        "blockingGaps": blockers,
        "blockingGapCount": len(blockers),
        "releaseCompatibilityEvidence": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "nextAdmissionOrder": [
            "approve an immutable backend release baseline only after its existing release-evidence gate passes",
            "obtain a second approved release and form an approved predecessor/successor pair",
            "approve at least one immutable client baseline and reviewed parser artifact",
            "execute approved-pair mixed-version routes and rolling rollback rehearsal",
            "execute production-shaped PostgreSQL upgrade/failover evidence",
            "complete independent integrated compatibility review"
        ]
    }
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print("Memory OS compatibility admission gaps updated")
    print(f"blocking gaps: {len(blockers)}")
    print(f"approved backend releases: {release_count}")
    print(f"approved client baselines: {client_count}")
    print(f"reviewed parser artifacts: {parser_count}")
    print(f"approved rollback pairs: {rollback_count}")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
