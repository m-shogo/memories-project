# Memory OS compatibility foundations

## Purpose

This runbook explains bounded compatibility evidence that is useful before approved releases exist. It supplements—but never changes—the canonical release compatibility matrix.

## Candidate-only evidence

The pinned old backend is a historical candidate, not an approved immediately previous release. Exact-source CI currently proves:

- candidate SQL and selected Go integration surfaces run on the current expanded schema;
- sessions issued by old and current processes resolve through the other process;
- old/current persisted Apply replay is stable in both directions;
- simultaneous old/current Apply contention converges on one Apply ID with one first application and one replay;
- SIGKILL of the historical process while its PostgreSQL transaction is observably blocked leaves no Apply or Memory residue;
- the current process safely retries the same Preview and idempotency key after process death.

This evidence is `PASS_CANDIDATE_ONLY`. It does not prove an approved release pair, production traffic, rollout percentages, connection drain or rollback eligibility.

## PostgreSQL logical forward evidence

An isolated exact-source rehearsal proves a PostgreSQL 16 source can be dumped with PostgreSQL 17 client tools and restored data-only into a fresh PostgreSQL 17 target that already has the current expand-only schema.

The rehearsal verifies:

- bounded schema authority fingerprints;
- runtime roles remain `NOBYPASSRLS`;
- protected tables remain `FORCE RLS`;
- active session authority survives;
- deleted account and session authority does not resurrect;
- the complete canonical SQL integration suite passes on PostgreSQL 17.

This evidence is `PASS_LOCAL_CI_ONLY`. It is not in-place `pg_upgrade`, physical replication, production blue-green cutover, failover, downgrade or PostgreSQL 17 production support.

## Empty approval authorities

The release, rollback-admission and parser-artifact authorities are deliberately empty:

- approved releases: `0`;
- admissible rollback pairs: `0`;
- reviewed parser artifacts: `0`;
- rollback-retained parser artifacts: `0`.

Empty registries are meaningful safety evidence. Candidate commits, CI PASS, branch heads, unbound tags, copied digests and test harnesses cannot manufacture release or artifact approval.

## Canonical matrix boundary

The canonical compatibility matrix remains conservative:

- old backend against new schema is not approved-release proof;
- rolling backend mix is not production rollout proof;
- old persisted state remains only partially proven until an approved predecessor/successor pair exists;
- old parser artifact through the new supervisor remains unproven;
- PostgreSQL 17 is not a supported production baseline;
- production rollback remains forbidden without a registered rollback-eligible release pair.

Foundation evidence must not change canonical release statuses to `PROVEN_IN_CI` unless the exact release artifacts, support windows, approvals and required evidence exist.

## Remaining release blockers

The following remain required:

- approved predecessor and successor release records;
- reviewed production parser artifact bytes with replay and immutable retention evidence;
- client/server support windows and skew tests;
- PostgreSQL minor-version support policy;
- production-shaped database cutover, connection-pool drain, replication and failover evidence;
- rolling traffic and application rollback rehearsal;
- approved RPO/RTO and recovery promotion;
- independent review with no unresolved Critical or High findings.

## Decision

`OPS-P0-008` remains `PARTIAL`.

Production remains **NO_GO**.
