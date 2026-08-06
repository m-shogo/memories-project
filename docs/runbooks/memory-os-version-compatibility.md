# Memory OS Version Compatibility and Rollout Runbook

Status: **FOUNDATION — NOT PRODUCTION-PROVEN**  
Authority: `contracts/operations/version-compatibility-contract.v1.json`  
Migration authority: `contracts/operations/migration-lifecycle-contract.v1.json`  
Production decision remains: **NO_GO**

## Purpose

This runbook controls compatibility decisions across:

- iOS/limited-portal clients and the v1 HTTP API;
- old/new Go backend instances during rolling deployment;
- backend releases and PostgreSQL schema phases;
- persisted jobs, Preview bindings and canonical records;
- digest-pinned parser artifacts and supervisor versions;
- exact object versions and later consumers.

A dependency pin, same-version unit test or clean current-stack CI run does **not** prove mixed-version compatibility. Each direction must be classified and tested independently.

## Compatibility directions are not interchangeable

These are separate questions:

```text
old client → new server
new client → old server
old backend → expanded/new schema
new backend → old schema
old backend ↔ new backend on shared dependencies
old persisted state → new consumer
new persisted state → old consumer
old parser artifact → new supervisor
old object version → new completion/parser path
```

A PASS in one direction does not imply the reverse direction.

## Current proven baseline

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

## Required release record

Before a rollout that changes a public or persisted contract, record:

- release ID;
- old and new source commit SHA;
- old and new deployment generation;
- PostgreSQL migration sequence before/after;
- affected compatibility dimensions;
- changed contracts and whether each change is compatible or breaking;
- old/new test matrix and results;
- rollback target and startup verification;
- parser artifact/version retention impact;
- object-version retention impact;
- client minimum/support window impact;
- observation window and abort conditions;
- reviewer and open risks.

No secrets or raw user data belong in the record.

## Step 1 — Classify every change

### HTTP client/server

Compatible candidates:

- add an optional response field that older clients ignore;
- add a new endpoint without changing existing route semantics;
- add an optional capability with an explicit fallback;
- internal implementation change preserving public status/error meaning.

Breaking changes:

- remove/rename a field;
- change meaning, unit, authority, nullability or requiredness;
- change an existing success/error condition incompatibly;
- reuse an enum token with new meaning;
- move an existing v1 route without a compatibility bridge.

Breaking v1 changes require a new API major or a deliberate compatibility bridge. Do not silently reinterpret v1.

Unknown request fields follow each endpoint’s binding contract and fail closed where strict decoding is required. Unknown response fields must be safely ignored by clients before the server begins adding them.

### Backend/database

Use:

```text
EXPAND
→ deploy old/new-compatible code
→ bounded data migration
→ observe mixed versions
→ CONTRACT later
```

Forbidden release order:

```text
new backend requiring expansion
→ old schema without expansion
```

Also forbidden:

- contract/remove a surface while an old version can return;
- weaken RLS, account fencing or deletion semantics without old/new proof;
- combine large backfill and application deployment;
- assume transaction rollback proves application recovery.

### Rolling backend

Both old and new instances must:

- operate against the expanded schema;
- preserve tenant isolation, authority, deletion and idempotency invariants;
- agree on persisted job/Preview/object semantics;
- tolerate state written by the other version or reject it explicitly;
- leave the old version deployable as the rollback target.

Do not begin a rolling production rollout while `ROLLING_BACKEND_MIX` is `NOT_PROVEN`.

### Persisted jobs and Previews

Every persisted boundary must have explicit version/hash identity. Unknown or conflicting versions fail closed.

Never:

- reinterpret old bytes under a new implicit schema;
- treat unknown as latest;
- change canonical-record meaning in place;
- remove a reader/artifact while in-flight or retryable work references it.

When compatibility is impossible, quarantine or run an explicit migration with accounting. Do not silently discard records.

### Parser artifacts

The binding is:

```text
adapter ID
+ adapter version
+ artifact SHA-256
+ options SHA-256
+ source object version/checksum
```

A new artifact requires a reviewed digest and fixture/canonical-output verification. Bytes cannot change behind an existing digest/version claim.

Retain an older artifact while persisted work can reference it. Operator-supplied arbitrary production pins are not a reviewed registry.

### Object versions

Consumers read the exact bound object version. They do not substitute latest.

Lifecycle changes must not expire a version still needed by:

- an active job;
- Preview/Apply retry;
- deletion investigation;
- incident evidence;
- restore verification.

## Step 2 — Build the matrix

At minimum test changed directions:

| Direction | Required before rollout |
| --- | --- |
| Current backend → current clean schema | Always |
| Previous backend → expanded new schema | Schema/API changes |
| New backend → old schema | Must remain forbidden unless explicitly designed |
| Previous + new backend concurrently | Rolling deployment |
| Old persisted state → new consumer | Persisted contract change |
| New persisted state → old consumer | Rolling mixed-version writes |
| Old parser artifact → new supervisor | Parser/supervisor change |
| Old client → new server | Client/server release |
| New client → old server | Staged client rollout/fallback |
| Bound older object version → new consumer | Object/completion/parser change |

Use synthetic privacy-safe fixtures. Each matrix result records exact source/schema/artifact versions.

`NOT_PROVEN` blocks a release that needs that direction. `FORBIDDEN_RELEASE_ORDER` is not converted into PASS by skipping the test.

## Step 3 — Verify rollback target

Before deployment:

1. identify the exact prior application commit/image;
2. verify it starts against the expanded schema;
3. verify old-version tenant/RLS negative tests;
4. verify old-version authentication/session behavior;
5. verify old-version Preview/Apply accounting;
6. verify old-version handling of new/unknown persisted versions;
7. verify it does not resurrect deleted state or accept expired sessions;
8. record which forward-only state it cannot safely consume.

If the rollback target cannot start or preserve invariants, do not call it a rollback target. Choose a forward-fix plan before rollout.

## Step 4 — Rollout order

Recommended order:

```text
1. Validate contracts and exact repository state.
2. Apply reviewed additive schema expansion.
3. Run current + previous backend compatibility tests.
4. Deploy a bounded new-version slice while old remains active.
5. Observe errors, latency, database locks, job/backlog and integrity checks.
6. Increase new-version share only while matrix assumptions remain true.
7. Drain old version.
8. Complete bounded backfill and observation.
9. Contract in a later independently reviewed release.
```

Abort rollout when:

- cross-tenant, authority, deletion or integrity behavior differs;
- unknown persisted version is accepted or misinterpreted;
- old/new instances produce incompatible state;
- rollback target fails startup or negative tests;
- error/latency/backlog exceeds reviewed thresholds;
- required object/parser version becomes unavailable;
- target source/schema identity is ambiguous.

## Step 5 — Client compatibility

The canonical iOS client is not implemented, so no client skew is currently proven.

Before client release policy can be READY, define:

- supported client versions/window;
- minimum-version enforcement behavior;
- staged rollout and rollback/fallback;
- offline queued request compatibility;
- unknown response field/enum handling;
- forced-upgrade policy and user experience;
- API-major deprecation window;
- server support duration for an older client.

A mobile client cannot be rolled back instantly after broad distribution. Server compatibility must account for that asymmetry.

## Step 6 — PostgreSQL upgrades

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

## Step 7 — Observe mixed versions

Observe:

- public status/error classes;
- p50/p95/p99 latency where measured;
- database errors, locks and transaction retry;
- Preview/Apply counts and idempotency replay;
- account/session/deletion behavior;
- object exact-version completion;
- parser artifact/version selection;
- queue/lease/backlog growth;
- unknown-version rejections;
- old-version rollback viability.

The observation window must be defined before rollout. “No immediate error” is not mixed-version proof.

## Step 8 — Contract and retire versions

Contract only when:

- old application version is drained and prevented from returning;
- in-flight/retryable old persisted work is exhausted or explicitly migrated;
- old parser/object versions meet retention and incident requirements;
- client support/deprecation window has elapsed;
- independent verification passes;
- a recovery point exists;
- the contract step is separately reviewed.

Do not remove old readers, artifacts, fields or object versions simply because current tests are green.

## Failure decisions

### New backend fails against expanded schema

If the prior backend is verified compatible, roll back the application. Otherwise forward-fix under incident command. Do not destructively remove additive schema merely to recreate the old shape.

### Old backend fails on new persisted state

Stop mixed writes, preserve examples and determine whether new state can be gated, migrated or requires forward-fix. Do not relabel unknown state as old-compatible.

### Client/server skew found after release

Preserve the existing v1 behavior where safe, add a compatibility bridge or capability gate, and assess staged client remediation. Do not silently break older distributed clients.

### Required parser artifact/object version is missing

Fail closed and hold bound work. Restore the exact reviewed artifact/version when possible. Never substitute “closest” or latest.

### Contract already removed required compatibility

Treat as an incident. Decide forward-fix or isolated restore using the migration and incident runbooks. A down migration is not assumed safe.

## Evidence and status rules

- `PROVEN_IN_CI` requires named repository evidence for the exact direction.
- `LOCAL_PROOF_ONLY` is not production-equivalent.
- `PARTIAL` must state what portion is proven.
- `NOT_PROVEN` blocks a rollout that depends on it.
- `NOT_IMPLEMENTED_OR_PROVEN` cannot become SUPPORTED through documentation alone.
- `FORBIDDEN_RELEASE_ORDER` is a policy guard, not a failed test.
- No matrix entry becomes proven from dependency pinning alone.

## Current limitations

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
