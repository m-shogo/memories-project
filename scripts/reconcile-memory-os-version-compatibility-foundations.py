#!/usr/bin/env python3
"""Integrate candidate-only compatibility foundations without promoting release support."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/version-compatibility-contract.v1.json"
RUNBOOK_PATH = ROOT / "docs/runbooks/memory-os-version-compatibility.md"

FOUNDATION_REFS = [
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
]

SUPPLEMENTAL = [
    {
        "id": "FOUNDATION-001",
        "direction": "HISTORICAL_CANDIDATE_BACKEND_CURRENT_EXPANDED_SCHEMA",
        "status": "PASS_CANDIDATE_ONLY",
        "proven": [
            "pinned historical candidate remains an ancestor of current source",
            "candidate SQL and reviewed common Go integration surfaces pass on the current expanded PostgreSQL schema",
            "candidate execution preserves the normalized memory_os schema fingerprint",
        ],
        "notProven": [
            "approved immediately previous release",
            "production traffic or production dependencies",
            "rolling deployment or rollback eligibility",
        ],
        "evidenceRefs": [
            "contracts/operations/mixed-version-candidate-contract.v1.json",
            "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json",
        ],
    },
    {
        "id": "FOUNDATION-002",
        "direction": "HISTORICAL_CANDIDATE_CURRENT_SHARED_SCHEMA_SESSIONS_AND_APPLY",
        "status": "PASS_CANDIDATE_ONLY",
        "proven": [
            "sessions issued by either process resolve through the other process",
            "old and current processes replay each other's persisted Apply idempotency claims",
            "simultaneous old/current Apply contention converges on one Apply ID with no duplicate materialization",
            "SIGKILL of the historical process inside an uncommitted Apply transaction leaves no durable residue and current safely retries the exact request",
        ],
        "notProven": [
            "approved current and previous release pair",
            "production-shaped connection pools, host loss or network partition",
            "traffic drain, rollout percentages or application rollback",
        ],
        "evidenceRefs": [
            "contracts/operations/mixed-version-session-contract.v1.json",
            "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
            "contracts/operations/mixed-version-apply-contract.v1.json",
            "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
        ],
    },
    {
        "id": "FOUNDATION-003",
        "direction": "POSTGRESQL_16_TO_17_LOGICAL_FORWARD_RESTORE",
        "status": "PASS_LOCAL_CI_ONLY",
        "proven": [
            "fresh PostgreSQL 17 target receives the exact current expand-only migration sequence",
            "PostgreSQL 17 client creates a data-only dump from PostgreSQL 16 and restores it into the fresh target",
            "schema authority, NOBYPASSRLS roles, FORCE RLS, active session authority and deletion non-resurrection checks pass",
            "the complete canonical SQL integration suite passes on PostgreSQL 17",
        ],
        "notProven": [
            "in-place pg_upgrade or production blue-green cutover",
            "physical replication, WAL continuity, replication slots or failover",
            "PostgreSQL 17 production support or target-to-source downgrade",
        ],
        "evidenceRefs": [
            "contracts/operations/postgresql-major-upgrade-contract.v1.json",
            "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
        ],
    },
    {
        "id": "FOUNDATION-004",
        "direction": "REVIEWED_PARSER_ARTIFACT_AUTHORITY",
        "status": "FOUNDATION_ONLY_EMPTY",
        "proven": [
            "append-only parser artifact registration authority exists",
            "test harness, source, build success, digest strings and unapproved releases cannot imply reviewed artifact authority",
            "writer verifies exact external artifact bytes, digest, size, approvals, retention and replay evidence before atomic registration",
        ],
        "notProven": [
            "any reviewed production parser artifact",
            "old registered artifact replay through the current supervisor",
            "immutable rollback retention for an approved release",
        ],
        "evidenceRefs": [
            "contracts/operations/parser-artifact-registry-contract.v1.json",
            "contracts/operations/parser-artifact-registry.v1.json",
        ],
    },
    {
        "id": "FOUNDATION-005",
        "direction": "APPROVED_RELEASE_AND_ROLLBACK_ADMISSION",
        "status": "BLOCKED_NO_APPROVED_PAIR",
        "proven": [
            "append-only release and rollback-rehearsal admission authorities exist",
            "candidate, CI PASS, branch head, unbound tag and unapproved release IDs cannot manufacture approval",
            "zero approved releases yields zero admissible rollback pairs",
        ],
        "notProven": [
            "approved predecessor and successor releases",
            "rollback-eligible retained binaries and parser artifacts",
            "executed isolated rollback rehearsal or production rollout",
        ],
        "evidenceRefs": [
            "contracts/operations/release-baseline-registry-contract.v1.json",
            "contracts/operations/release-baseline-registry.v1.json",
            "contracts/operations/rollback-rehearsal-gate-contract.v1.json",
            "contracts/operations/rollback-rehearsal-registry.v1.json",
        ],
    },
]

CURRENT_SECTION = """## Current proven baseline

The repository now proves several **bounded, directional foundations**. They are not interchangeable and none is an approved production release pair.

### Same-version current stack

```text
current Go 1.23.x backend
→ clean current PostgreSQL 16 schema
→ complete canonical migration sequence
→ current SQL and Go integration suites
```

### Historical-candidate compatibility foundation

A pinned historical candidate—not an approved immediately previous release—has passed exact-source CI against the current expanded schema. Old/current processes also share session authority and persisted Apply idempotency correctly, including:

- bidirectional session resolution;
- old Apply → current replay and current Apply → old replay;
- simultaneous old/current contention on one Preview and idempotency key;
- one first application plus one replay with one Apply ID;
- SIGKILL of the historical process while its PostgreSQL Apply transaction is observably blocked before materialization;
- complete rollback of the killed transaction and safe current-process retry of the exact request.

This remains `PASS_CANDIDATE_ONLY`. It does not prove an approved release pair, production rolling traffic, traffic drain or rollback eligibility.

### PostgreSQL 16 → 17 logical forward foundation

An isolated exact-source rehearsal applies the current expand-only schema independently to PostgreSQL 16 and 17, dumps PostgreSQL 16 with PostgreSQL 17 client tools, restores data-only into the fresh PostgreSQL 17 target, and verifies schema authority, RLS, session authority, deletion non-resurrection and all canonical SQL integration tests.

This is `PASS_LOCAL_CI_ONLY`. It is not in-place `pg_upgrade`, physical replication, production blue-green cutover, failover, downgrade or PostgreSQL 17 production support.

### Approval and artifact foundations

The repository has append-only authorities for approved releases, rollback-rehearsal admission and reviewed parser artifacts. All are deliberately empty:

- approved releases: `0`;
- admissible rollback pairs: `0`;
- reviewed parser artifacts: `0`;
- retained rollback parser artifacts: `0`.

Therefore the following remain unproven:

- an approved immediately previous/current release pair;
- production rolling deployment and rollback rehearsal;
- reviewed old parser artifact replay and immutable retention;
- old/new iOS client and server skew;
- PostgreSQL minor-version policy, production cutover, replication and failover;
- independent review.

"""

PG_SECTION = """## Step 6 — PostgreSQL upgrades

Current production baseline remains PostgreSQL 16. The repository has an isolated PostgreSQL 16 → 17 **logical forward restore** foundation, but this does not automatically support PostgreSQL 17 in production.

The bounded rehearsal proves:

- the exact current expand-only migration sequence applies independently to PostgreSQL 16 and 17;
- PostgreSQL 17 client tools can create a data-only dump from PostgreSQL 16;
- data restores into a fresh migrated PostgreSQL 17 target;
- bounded schema authority fingerprints match;
- runtime roles remain `NOBYPASSRLS` and protected tables remain `FORCE RLS`;
- active session authority survives and deleted authority does not resurrect;
- all canonical SQL integration tests pass on PostgreSQL 17.

It does **not** prove:

- supported PostgreSQL 16 or 17 minor-version windows;
- in-place `pg_upgrade`;
- production blue-green cutover or connection-pool drain;
- physical replication, WAL continuity, replication slots or failover;
- target-to-source downgrade;
- approved RPO/RTO or operator promotion.

Before a production upgrade:

- define supported minor versions;
- test approved current/previous releases against source and target database versions;
- verify extensions, roles, functions, RLS policies and SQL behavior;
- rehearse backup/restore/PITR with the target version;
- verify migration lock/runtime behavior and connection-pool drain;
- verify forward-fix and irreversible rollback boundaries;
- obtain database recovery and independent review approval;
- update the matrix and release evidence.

A successful schema migration on PostgreSQL 16 does not prove PostgreSQL 17 compatibility. The isolated logical rehearsal is useful evidence, but it does not prove every production upgrade mode.

"""

LIMITATIONS_SECTION = """## Current limitations

The repository still lacks:

- an approved immediately previous/current release pair despite strong historical-candidate compatibility evidence;
- production rolling traffic, connection drain and application rollback rehearsal;
- a reviewed production parser artifact, old-artifact replay and immutable rollback retention;
- iOS/portal implementation and client support windows;
- client/server skew tests;
- PostgreSQL minor-version policy, in-place or production blue-green cutover, replication and failover evidence;
- approved RPO/RTO and production recovery promotion;
- independent review.

The existing candidate-only, empty-registry and logical-upgrade foundations must not be relabeled as production or release compatibility evidence.

Therefore `OPS-P0-008` remains `PARTIAL` and production remains `NO_GO`.
"""


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def replace_section(text: str, heading: str, next_heading: str | None,
                    replacement: str) -> str:
    start = text.find(heading)
    require(start >= 0, f"runbook heading missing: {heading}")
    if next_heading is None:
        end = len(text)
    else:
        end = text.find(next_heading, start + len(heading))
        require(end >= 0, f"runbook next heading missing: {next_heading}")
    return text[:start] + replacement + (text[end:] if next_heading else "")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-version-compatibility.v1",
            "version compatibility schema drift")
    support = contract.get("supportPolicy")
    readiness = contract.get("readiness")
    require(isinstance(support, dict) and isinstance(readiness, dict),
            "version compatibility support/readiness missing")

    rolling = support.get("backendRollingWindow")
    database = support.get("database")
    parser = support.get("parserArtifacts")
    require(isinstance(rolling, dict) and isinstance(database, dict) and
            isinstance(parser, dict), "compatibility support sub-policy missing")
    rolling.update({
        "historicalCandidateAndCurrentTested": True,
        "approvedCurrentAndPreviousReleaseTested": False,
        "candidateOnlyEvidenceRef":
            "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    })
    database.update({
        "postgresql17LogicalForwardUpgradeRehearsed": True,
        "postgresql17InPlaceOrBlueGreenCutoverRehearsed": False,
        "postgresql17PhysicalReplicationOrFailoverRehearsed": False,
        "postgresql17ProductionSupported": False,
        "logicalUpgradeEvidenceRef":
            "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
    })
    parser.update({
        "reviewedRegistryAuthorityImplemented": True,
        "reviewedArtifactCount": 0,
        "rollbackRetainedArtifactCount": 0,
        "testHarnessApproved": False,
        "registryRef": "contracts/operations/parser-artifact-registry.v1.json",
    })
    readiness.update({
        "historicalCandidateNewSchemaProven": True,
        "historicalCandidateMixedProcessProven": True,
        "historicalCandidatePersistedApplyProven": True,
        "historicalCandidateConcurrentApplyRaceProven": True,
        "historicalCandidateInFlightTerminationRecoveryProven": True,
        "postgresql17LogicalForwardUpgradeProven": True,
        "parserArtifactRegistryAuthorityDefined": True,
        "reviewedParserArtifactAvailable": False,
        "rollbackRehearsalAdmissionGateDefined": True,
        "approvedRollbackPairAvailable": False,
    })
    readiness["note"] = (
        "Current same-version evidence is supplemented by historical-candidate mixed-process, "
        "persisted Apply race and in-flight termination recovery, an isolated PostgreSQL 16 to 17 "
        "logical forward rehearsal, and empty fail-closed release/rollback/parser authorities. "
        "No approved release pair, reviewed parser artifact, production rollout, client skew or "
        "production database cutover is proven; OPS-P0-008 remains PARTIAL."
    )
    contract["supplementalCompatibilityEvidence"] = SUPPLEMENTAL
    contract["foundationEvidenceRefs"] = FOUNDATION_REFS
    for ref in FOUNDATION_REFS:
        require((ROOT / ref).is_file(), f"foundation evidence missing: {ref}")

    CONTRACT_PATH.write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    try:
        runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReconcileFailure("version compatibility runbook missing") from exc
    runbook = replace_section(runbook, "## Current proven baseline\n",
                              "## Required release record\n", CURRENT_SECTION)
    runbook = replace_section(runbook, "## Step 6 — PostgreSQL upgrades\n",
                              "## Step 7 — Observe mixed versions\n", PG_SECTION)
    runbook = replace_section(runbook, "## Current limitations\n", None,
                              LIMITATIONS_SECTION)
    RUNBOOK_PATH.write_text(runbook, encoding="utf-8")

    print("Reconciled candidate-only compatibility foundations; production remains NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"VERSION COMPATIBILITY FOUNDATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
