# Memory OS PostgreSQL Migration and Recovery Runbook

Status: **FOUNDATION — NOT PRODUCTION-PROVEN**  
Authority: `contracts/operations/migration-lifecycle-contract.v1.json`  
Production decision remains: **NO_GO**

## Purpose

This runbook controls PostgreSQL schema changes for Memory OS. It is designed to prevent a successful transaction rollback, a reversible application deployment, or a passing CI job from being misreported as complete migration-recovery proof.

The default strategy is:

```text
EXPAND
→ deploy compatible application versions
→ migrate/backfill data in bounded resumable steps
→ observe old/new mixed-version behavior
→ CONTRACT in a later deliberate change
```

The default recovery strategy after a committed additive migration is **forward-fix**, or application rollback only when the expanded schema remains compatible. A destructive down migration is never assumed safe.

## Non-negotiable invariants

- Runtime traffic uses the deployment login and fixed runtime roles; it does not switch to a superuser to make a migration pass.
- `FORCE RLS`, tenant isolation, account epoch fencing and deletion semantics may not be weakened silently.
- A migration target is identified explicitly. A command that relies on an ambiguous default database is refused.
- Exact source commit, migration sequence and recovery-point reference are recorded before mutation.
- Schema expansion and large data backfill are separate operational steps.
- Backfills are bounded, idempotent, resumable and independently accounted.
- Destructive contraction occurs only after old-version drain, compatibility observation and recovery review.
- Secrets, raw database URLs, bearer tokens and personal data are never copied into the evidence record.
- Unknown state is preserved and escalated; it is not deleted merely to clear an alert.

## Roles

| Role | Responsibility |
| --- | --- |
| Operator | Runs preflight, applies the approved step and records exact evidence. |
| Reviewer | Confirms target, source SHA, recovery point, compatibility statement and verification plan. |
| Incident commander | Owns the decision after an integrity, availability or destructive-contract failure. |
| Restore owner | Confirms the recovery point exists and can be restored in an isolated environment. |
| Application owner | Confirms which old/new application versions are compatible with the schema phase. |

One person may hold multiple roles outside production. Production requires an independently named reviewer and restore owner.

## Required inputs

Before any production-shaped rehearsal or production migration, record:

- migration run ID;
- environment and database identity digest;
- exact repository commit SHA and clean-worktree result;
- canonical migration sequence before and after;
- current deployed application versions;
- old/new compatibility statement;
- recovery-point reference and restore owner;
- lock timeout and statement timeout;
- expected lock/table footprint;
- verification queries and expected results;
- operator, reviewer and incident contact;
- recovery decision if the step fails before or after commit.

Missing input means **STOP_AND_CORRECT**.

## Phase 0 — Preflight

### 0.1 Confirm repository state

```bash
set -euo pipefail

test "$(git branch --show-current)" = "so"
test -z "$(git status --porcelain)"
git fetch origin so
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/so)"
python scripts/validate-memory-os-migration-lifecycle.py
python scripts/validate-memory-os-operability.py
```

Record the output of:

```bash
git rev-parse HEAD
sha256sum infra/postgresql/security/*.sql
```

Do not paste credentials or the full database URL into the record.

### 0.2 Confirm target identity

Use a separately supplied connection secret and record only a digest or approved environment identifier.

```sql
SELECT current_database(), current_user, inet_server_addr(), inet_server_port();
SELECT version();
```

Refuse the operation if the database, user, host class or environment differs from the approved target.

### 0.3 Confirm recovery capability

Before mutation, record:

- the backup/PITR or isolated snapshot reference;
- the latest recoverable timestamp;
- the restore owner;
- whether an isolated restore has been rehearsed for this schema generation.

A backup existing somewhere is not sufficient. If the recovery point cannot be identified and owned, do not enter `CONTRACT` and do not perform irreversible data cleanup.

### 0.4 Confirm lock and runtime budget

Set finite budgets appropriate to the reviewed migration. Example session controls:

```sql
SET lock_timeout = '5s';
SET statement_timeout = '60s';
SET idle_in_transaction_session_timeout = '60s';
```

These are examples, not universal production values. Record the approved values and abort rather than silently removing the limits.

Check for blocking activity and long transactions before applying:

```sql
SELECT pid, usename, application_name, state,
       now() - xact_start AS transaction_age,
       wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

## Phase 1 — EXPAND

Allowed examples:

- add nullable columns;
- add tables, functions and compatible policies;
- add indexes using a reviewed low-lock strategy;
- add constraints in a non-enforcing or separately validated form;
- introduce compatibility surfaces used by both old and new application versions.

Forbidden in the same release:

- dropping a column/table still read by any deployable version;
- changing meaning in place without a compatibility bridge;
- combining a large table rewrite with application deployment;
- weakening RLS, account fencing or deletion semantics;
- treating `DROP POLICY IF EXISTS`-style definition replacement as permission to remove tenant protection.

### Apply discipline

1. Acquire the repository-defined single-writer migration lock.
2. Apply only the reviewed next migration sequence.
3. Stop at the first error.
4. Record whether the failure occurred before commit, after commit, or outside the database transaction.
5. Run the post-expand verification before deploying dependent application behavior.

### Post-expand verification

At minimum verify:

- every canonical migration file is registered and applied in order;
- expected schemas, tables, functions and policies exist;
- runtime deployment role remains `NOBYPASSRLS`/`NOINHERIT` as designed;
- `FORCE ROW LEVEL SECURITY` remains active where required;
- known cross-tenant negative tests still fail closed;
- old application version can still read/write its supported surface;
- new application version can start without requiring a contract step.

## Phase 2 — MIGRATE_DATA

A backfill is not hidden inside an application startup or a long deployment transaction.

Required behavior:

- bounded batches;
- deterministic selection order;
- idempotent updates;
- resumable checkpoint;
- affected/remaining/error counts;
- explicit pause control;
- no deletion of ambiguous rows;
- verification by an independently written query.

A backfill failure normally uses:

```text
PAUSE_BACKFILL
→ preserve exact state and checkpoint
→ classify malformed/ambiguous rows
→ correct code or data rule
→ resume from the recorded boundary
```

Do not mark skipped rows complete merely to reach zero backlog.

## Phase 3 — OBSERVE_MIXED_VERSION

Operate old and new compatible application versions against the expanded schema for the approved observation window.

Capture:

- request and database error classes;
- latency and lock behavior;
- authorization/RLS negative tests;
- Preview/Apply idempotency and accounting;
- deletion fencing and session behavior;
- migration-specific alerts, queue growth or unusual retries;
- whether the old version remains a valid application rollback target.

Any unresolved integrity issue blocks `CONTRACT`.

## Phase 4 — CONTRACT

Contract is a later, independently reviewed change.

Entry conditions:

- old application version is fully drained and prevented from returning;
- compatibility observation completed;
- backfill is complete and independently verified;
- retention/deletion obligations were reviewed;
- recovery point and restore owner are current;
- contract SQL has a bounded lock/runtime plan;
- incident commander understands that an automatic destructive down migration is forbidden.

Examples include enforcing a validated constraint or removing a deprecated compatibility surface. Data deletion and column/table removal require explicit review and must not be bundled merely for cleanup convenience.

## Failure decision tree

### Failure before database mutation

Action: `STOP_AND_CORRECT`.

No rollback claim is needed because no mutation occurred. Correct target, source, configuration or review evidence and restart from preflight.

### Transaction failed before commit

Action: `VERIFY_DATABASE_ROLLBACK_THEN_CORRECT`.

Confirm the transaction ended, locks were released, migration ledger did not advance and no external side effect occurred. A PostgreSQL transaction rollback does **not** prove the migration process or application state is recovered.

### Additive migration committed, application unhealthy

Action:

```text
if old application is compatible with expanded schema:
    roll back application deployment
else:
    forward-fix application/schema under incident control
```

Do not remove additive schema merely to recreate the old shape unless a separate safety review proves that operation is non-destructive.

### Backfill incorrect or incomplete

Action: pause, preserve checkpoint and forward-fix. Do not contract. Determine whether already-written rows are valid, compensatable or require isolated restore analysis.

### Contract migration committed

Action: incident command decides between forward-fix and isolated restore. Never assume a down migration can recreate deleted data, prior constraints, object versions or external side effects.

### External side effect occurred

Database rollback cannot reverse object-store writes, notifications, credentials, or external calls. Use an explicit compensating action or forward-fix and retain the incident record.

## Verification record

The append-only record contains at least:

```json
{
  "migrationRunId": "run_...",
  "environment": "staging-or-production-identifier",
  "databaseIdentityDigest": "sha256:...",
  "sourceCommitSha": "40-character-sha",
  "migrationSequenceBefore": ["..."],
  "migrationSequenceAfter": ["..."],
  "startedAt": "RFC3339",
  "completedAt": "RFC3339-or-null",
  "operator": "named-role",
  "reviewer": "named-role",
  "recoveryPointReference": "approved-reference-no-secret",
  "preflightResult": "PASS|FAIL",
  "applyResult": "PASS|FAIL|PARTIAL",
  "verificationResult": "PASS|FAIL|NOT_RUN",
  "recoveryDecision": "NONE|STOP_AND_CORRECT|APPLICATION_ROLLBACK|FORWARD_FIX|ISOLATED_RESTORE_REVIEW",
  "openRisks": ["..."]
}
```

The record must not contain passwords, tokens, private keys, raw personal data or an unrestricted database URL.

## Completion criteria

A migration run is complete only when:

- the exact source and target are recorded;
- the approved phase completed;
- verification passed;
- migration sequence and application compatibility are known;
- locks and failed transactions are cleared;
- recovery decision is recorded;
- unresolved risks have explicit owners;
- evidence is stored append-only.

## Current limitations

This runbook and its machine-readable contract establish policy only. The repository still lacks:

- a clean-database migration dry-run job tied to the complete canonical sequence;
- mixed-version old/new application proof;
- production-shaped rehearsal;
- automatic recovery-point verification;
- an append-only migration evidence ledger;
- isolated restore linkage;
- proof that contract operations meet production lock and runtime budgets.

Therefore `OPS-P0-001` remains `PARTIAL` and production remains `NO_GO`.
