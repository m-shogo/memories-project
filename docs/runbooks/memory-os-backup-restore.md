# Memory OS Backup, PITR and Isolated Restore Runbook

Status: **FOUNDATION — NOT PRODUCTION-PROVEN**  
Authority: `contracts/operations/backup-restore-contract.v1.json`  
Incident authority: `contracts/operations/incident-response-contract.v1.json`  
Production decision remains: **NO_GO**

## Purpose

This runbook governs PostgreSQL backup/PITR, object-version retention and isolated restore verification for Memory OS.

It enforces three distinctions:

```text
object versioning ≠ independent backup
backup creation ≠ restore proof
healthy restored service ≠ safe promotion
```

A restore is not safe until tenant isolation, authority, Preview/Apply accounting, exact object bindings, deleted-data non-resurrection and expired/revoked-session rejection all pass independently.

## Current state

Defined:

- protected data domains;
- backup and restore control requirements;
- isolated restore lifecycle;
- mandatory integrity and non-resurrection checks;
- promotion guards;
- append-only restore evidence record;
- required drill scenarios.

Not configured or proven:

- production PostgreSQL backup;
- WAL/PITR;
- independent object retention/copy;
- approved RPO and RTO;
- backup freshness alerts;
- isolated restore environment;
- automated deletion/session non-resurrection verification;
- completed restore drill;
- production promotion rehearsal.

Therefore this runbook is policy, not recovery evidence.

## Non-negotiable rules

- Restore into an isolated environment. Normal user traffic and outbound side effects remain disabled.
- Use separate least-privilege backup/restore authority, not runtime application credentials.
- Record recovery points and identities without copying passwords, keys, tokens or unrestricted database URLs.
- Preserve restored evidence before cleanup or repair.
- Correlate PostgreSQL and object recovery points. Unknown skew fails closed.
- Never substitute the latest object version for a bound version.
- Never promote based only on health checks or row counts.
- Deleted data and expired/revoked sessions must not silently reappear.
- A database rollback cannot reverse object-store, notification, credential or other external side effects.
- Promotion is an incident-command decision with system-owner and security/privacy approval.

## Roles

| Role | Responsibility |
| --- | --- |
| Restore operator | Executes approved backup/restore steps and records exact results. |
| Restore reviewer | Independently checks target, recovery point, commands and verification. |
| System owner | Defines expected data, schema, object and idempotency invariants. |
| Security/privacy lead | Owns deletion/session non-resurrection and access review. |
| Incident commander | Approves recovery strategy and promotion/refusal decision. |
| Backup owner | Owns backup freshness, retention and restore availability. |

Production cannot assign all roles to an unnamed automation.

## Required inputs

Before a production-shaped restore:

- restore run/incident ID;
- reason and target recovery time;
- exact source commit/deployment generation;
- database identity digest;
- PostgreSQL base backup and WAL/PITR reference;
- object recovery point and version-retention reference;
- migration sequence and parser-artifact generation;
- expected data-loss window;
- approved RPO/RTO and owners;
- isolation controls;
- operator, reviewers and incident commander;
- verification plan;
- promotion and abort conditions.

Missing or ambiguous input means **STOP_AND_CORRECT**.

## Phase 1 — Declare and plan

Create the append-only restore record before mutation.

```json
{
  "restoreRunId": "restore_...",
  "reason": "approved reason",
  "environment": "isolated-restore-identifier",
  "sourceCommitSha": "40-character-sha",
  "databaseIdentityDigest": "sha256:...",
  "databaseRecoveryPoint": "approved reference",
  "objectRecoveryPoint": "approved reference",
  "migrationSequence": ["..."],
  "startedAt": "RFC3339",
  "operator": "named role",
  "reviewers": ["named role"],
  "measuredRpo": null,
  "measuredRto": null,
  "verificationResults": [],
  "nonResurrectionResults": [],
  "promotionDecision": "NOT_EVALUATED",
  "openRisks": [],
  "evidenceRefs": []
}
```

Record only references/digests for sensitive systems.

## Phase 2 — Select a coherent recovery point

### PostgreSQL

Identify:

- base backup generation;
- WAL/PITR availability;
- exact target timestamp or transaction boundary;
- database major/minor version;
- migration sequence expected at that point;
- application versions compatible with that schema.

### Objects

Identify:

- bucket/repository generation;
- object-version retention boundary;
- exact version IDs referenced by active jobs/Previews;
- lifecycle/deletion events around the database target;
- backup/copy independence from the primary object store.

### Correlation

State the allowed database/object skew. It is currently `NOT_DEFINED`, so no production promotion is allowed until an owner approves it.

If a database row references an object version unavailable at the selected object recovery point, classify it before restore:

- safely absent and fail-closed;
- retrievable from an independent copy;
- intentionally deleted with retained evidence;
- inconsistent and promotion-blocking.

Do not substitute latest.

## Phase 3 — Restore in isolation

The restored environment must:

- use a separate network boundary;
- have no public/user ingress;
- have outbound notifications and external writes disabled;
- use restore-only credentials;
- avoid production signing/auth keys where unnecessary;
- clearly identify itself as restore/testing;
- preserve all initial restored state before repair;
- prevent automatic migration, cleanup, deletion sweep or queue processing until reviewed.

Record exact commands and outcomes, but redact credentials.

If the restore unexpectedly contacts production services or emits an external side effect, stop and treat it as an incident.

## Phase 4 — Verify structure and authority

### Schema and migration

Verify:

- canonical migration sequence;
- expected schemas, tables, functions and policies;
- reviewed schema/policy fingerprints;
- application release compatibility;
- no unapproved migration auto-applied during restore.

### Runtime roles

Verify the deployment runtime role remains:

- `NOBYPASSRLS`;
- `NOINHERIT` where designed;
- limited to fixed runtime roles;
- unable to bypass tenant context.

### Tenant isolation

Run synthetic cross-tenant negative tests through the deployment principal:

- Preview read;
- Apply;
- upload completion;
- session/account control;
- deletion visibility.

A privileged administrative query is not an RLS test.

Failure blocks promotion.

## Phase 5 — Verify data and idempotency

### Preview

Verify:

- one ready Preview per expected binding;
- candidate/rejection counts;
- source row accounting;
- exact Preview hash;
- object/adapter/options/spool bindings;
- no orphan candidate or rejection rows.

### Apply

Verify:

- confirmation row and memory-item accounting;
- exact Preview hash binding;
- created/updated/skipped totals;
- no partial materialization;
- exact idempotent replay returns the original result;
- unsupported destructive update policy remains closed.

### Database/object coherence

Verify each sampled/required reference:

- object key;
- exact version ID;
- content length;
- checksum;
- metadata;
- quarantine/scan state;
- parser artifact and adapter version.

Unknown or missing bindings remain blocked/quarantined.

## Phase 6 — Verify deletion and session non-resurrection

This is mandatory before any promotion.

### Deleted account fixtures

For accounts deleted before the target recovery point, verify:

- account remains fenced/deleted;
- epoch state is correct;
- sessions are absent or unusable;
- memory and Preview rows are not user-visible;
- deletion work does not repeat unsafe external actions;
- retained backup-only data cannot be served by normal APIs.

### Deleted content/object fixtures

Verify:

- deleted memory/Preview content does not reappear through user APIs;
- object versions follow approved retention and erasure semantics;
- any legally/operationally retained backup version remains access-restricted;
- restore does not recreate a completion/scan job for intentionally deleted state.

### Sessions and replay

Verify:

- expired session rejected;
- revoked session rejected;
- session digest and authority rules preserved;
- authorization-code/nonce replay still rejected;
- account epoch fencing invalidates stale authority;
- raw bearer tokens are absent from evidence.

Any resurrection is SEV0 and keeps the restore isolated.

## Phase 7 — Measure RPO and RTO

Do not invent targets after observing the result.

Measure:

```text
measured RPO = incident/target point − latest safely recoverable coherent point
measured RTO = restore declaration − verified promotion-ready or verified-refused decision
```

Also record:

- database/object skew;
- time to base restore;
- time to WAL/PITR replay;
- time to object recovery;
- time to integrity verification;
- time to non-resurrection verification;
- backlog/catch-up time;
- manual intervention.

Current RPO and RTO are `NOT_DEFINED`; this alone blocks production promotion readiness.

## Phase 8 — Promotion decision

Promotion requires all of:

- cross-tenant negative tests PASS;
- schema/migration/release compatibility PASS;
- Preview/Apply accounting PASS;
- exact object binding PASS;
- deletion non-resurrection PASS;
- expired/revoked session rejection PASS;
- replay/account epoch checks PASS;
- database/object skew within approved bound;
- measured RPO/RTO within approved targets;
- no external side effect from the restore environment;
- incident commander approval;
- system-owner approval;
- security/privacy approval;
- explicit cutover and rollback/forward-fix plan.

Promotion is refused when any critical check is `FAIL`, `PARTIAL` or `NOT_RUN`.

A green `/healthz` is not promotion evidence.

## Phase 9 — Cutover safeguards

When a future production promotion is approved:

- freeze conflicting writes or define reconciliation boundary;
- record final source/target identities;
- revoke restore-only credentials after use;
- ensure notifications/jobs do not duplicate external side effects;
- preserve the pre-cutover environment/recovery point;
- monitor errors, latency, queues, deletion/session behavior and object mismatches;
- retain a bounded fallback/forward-fix decision window;
- communicate fact-only impact and residual risk.

This repository does not currently implement or authorize production cutover.

## Phase 10 — Close and remediate

Record:

- actual recovered point;
- measured RPO/RTO;
- verification results;
- non-resurrection results;
- promotion/refusal decision;
- failed/partial checks;
- manual steps;
- evidence references;
- remediation owners and target dates;
- next restore rehearsal.

The evidence record is append-only. Corrections are appended, not rewritten.

## Required drill matrix

### RESTORE-DRILL-001 — Clean isolated restore

Restore current PostgreSQL plus correlated object state. Verify full schema/authority/data matrix.

### RESTORE-DRILL-002 — In-flight Preview/Apply PITR

Choose a point across Preview/Apply activity and prove no partial accounting or dishonest replay.

### RESTORE-DRILL-003 — Deletion/session non-resurrection

Restore around account deletion, session expiry and revocation. Prove none becomes usable/visible.

### RESTORE-DRILL-004 — Intentional database/object skew

Restore mismatched recovery points and prove the system detects and fails closed rather than using latest.

### RESTORE-DRILL-005 — Missing artifact/version

Remove access to a required old parser artifact or object version and prove bound work is held/quarantined.

None of these drills is currently completed.

## Backup operation requirements

A future production backup system must provide:

- encrypted PostgreSQL backups and WAL/PITR;
- encrypted transport;
- separate least-privilege backup credentials;
- retention and expiry policy;
- immutability/deletion protection;
- backup-job success/failure monitoring;
- backup freshness alerts;
- independent object retention/copy;
- release/migration/parser metadata retention;
- periodic isolated restore;
- append-only evidence;
- access review and credential rotation.

A primary versioned bucket alone does not satisfy these requirements.

## Current limitations

The repository has only local MinIO versioning behavior and component integration tests. It does not have:

- production backup/PITR configuration;
- independent object backup/retention;
- approved RPO/RTO;
- restore-only identity/environment;
- automated restore verification;
- deletion/session non-resurrection automation;
- completed restore drill;
- promotion rehearsal;
- independent review.

Therefore `OPS-P0-007` remains `PARTIAL_FOUNDATIONS_ONLY` and production remains `NO_GO`.
