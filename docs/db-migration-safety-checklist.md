# Database Migration Safety Checklist

## 目的

この文書は、Memory OS のDB migrationを安全に実施するためのchecklistである。

Memory OSのDB migrationは単なるschema変更ではない。

Import、削除、tombstone、search、embedding、raw retention、Export、policy decision、RLSに影響するため、長期運用ではmigration事故が致命傷になる。

## 基本原則

### 1. No raw in migration logs

Migration logにraw text、private title、URL token、chat snippetを出してはいけない。

### 2. Backfill must be resumable

長いbackfillは途中で止まる前提にする。

### 3. Derived data can be rebuilt

search_document / embedding_record はsource of truthではない。

Migrationで壊れたら再生成できる必要がある。

### 4. Lifecycle wins

deleted / hidden / sealed / pending_delete の状態は、migration後も維持されなければならない。

### 5. Tombstone replay is mandatory after restore

Backup restore後は、deletion_tombstoneをreplayしてsearch/embedding/export eligibilityを再計算する。

## Migration Categories

```ts
type MigrationCategory =
  | 'schema_only'
  | 'index_only'
  | 'constraint_change'
  | 'data_backfill'
  | 'dedupe_key_change'
  | 'policy_reclassification'
  | 'search_rebuild'
  | 'embedding_invalidation'
  | 'raw_storage_migration'
  | 'key_rotation'
  | 'partition_operation';
```

## Pre-migration Questions

Every migration must answer:

- Does it touch raw content?
- Does it affect deletion/hidden/sealed lifecycle?
- Does it affect dedupe keys?
- Does it affect tombstones?
- Does it affect search visibility?
- Does it affect export eligibility?
- Does it require re-embedding?
- Does it require policy re-evaluation?
- Does it require key rotation?
- Does it lock a large table?
- Can it run in chunks?
- Can it be rolled back?
- What is the validation query?

## Safe Migration Pattern

Prefer expand → backfill → switch → contract.

### Step 1: Expand

- add nullable columns
- add new tables
- add new indexes concurrently where possible
- keep old reads/writes working

### Step 2: Dual write / compatibility

- app writes old + new fields when needed
- new fields populated for new rows
- no destructive change yet

### Step 3: Backfill

- chunked by user_id, id, or time
- record progress
- no raw logs
- pause/resume safe
- skip deleted/sealed according to policy

### Step 4: Read switch

- switch reads to new schema
- monitor discrepancies
- keep rollback path

### Step 5: Contract

- remove old columns/tables only after validation window
- document irreversible changes

## Backfill Job Requirements

```ts
interface BackfillJob {
  id: string;
  migrationId: string;
  targetTable: string;
  cursor: string;
  batchSize: number;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  counts: {
    scanned: number;
    updated: number;
    skipped: number;
    failed: number;
  };
}
```

Backfill must:

- use small batches
- commit per batch
- support retry
- store cursor
- store counts only
- never log raw values

## Index Migration Rules

### Adding indexes

- create concurrently where supported.
- avoid building broad GIN indexes on huge JSONB without measured query.
- use partial indexes for active lifecycle.
- verify index size after creation.

### Removing indexes

- check query usage first.
- remove unused experimental indexes before they become permanent cost.

### Reindex

- schedule outside peak usage.
- do not block Import Preview or deletion flows.

## Constraint Migration Rules

### Adding NOT NULL

Safe sequence:

1. add nullable column.
2. backfill.
3. add check constraint NOT VALID.
4. validate constraint.
5. set NOT NULL if needed.

### Adding UNIQUE

For large tables:

- create unique index concurrently if possible.
- handle duplicates before adding constraint.
- dedupe_key should carry active uniqueness when partition limitations exist.

### Foreign keys

- add NOT VALID first for large tables.
- validate later.
- ensure error messages do not leak cross-user existence.

## Dedupe Key Migration

Changing dedupe keys is high-risk.

Rules:

- never delete old keys immediately.
- create new key type/version.
- generate new HMAC keys with key_version.
- compare old/new duplicate rate.
- keep old key read path during validation.
- only switch after false positive/false negative review.

## Tombstone Migration

Tombstones are deletion safety.

Rules:

- never drop tombstones without product/legal decision.
- use HMAC, not plain hash.
- key rotation must preserve ability to match old tombstones.
- account deletion mode may minimize tombstones differently from record deletion.

## Search Migration

Search documents are derived.

Rules:

- invalidate before rebuild when source changes.
- rebuild only policy-eligible records.
- exclude hidden/sealed/deleted.
- do not use stale search_document for Export.
- rebuild can be paused/resumed.

## Embedding Migration

Embedding is expensive and risky.

Rules:

- do not automatically re-embed all rows after schema change.
- invalidate by input_hash/model/policy/lifecycle.
- re-embed lazily or by budgeted batch.
- no private/sensitive raw embedding by default.

## Raw Storage Migration

Rules:

- raw_object_ref must map old object to new object.
- verify object checksum.
- maintain encryption metadata.
- do not expose raw in logs.
- update retention policy.
- old object deletion delayed until verification.

## Key Rotation Migration

Required for:

- raw object encryption
- OAuth token encryption
- dedupe HMAC
- tombstone HMAC
- export package encryption

Rules:

- key material outside DB.
- key_reference stores reference only.
- support old + new key during transition.
- rotate in chunks.
- verify decrypt/re-HMAC success counts.
- never log decrypted values.

## Partition Migration

Partitioning is high-risk.

Rules:

- do not partition early without measured need.
- plan unique constraints before migration.
- keep dedupe_key independent.
- detach/drop partitions only when lifecycle/retention allows.
- verify RLS policies apply to partitions.

## RLS Migration

Rules:

- app role is not table owner.
- enable RLS on user data tables.
- consider FORCE ROW LEVEL SECURITY.
- negative tests for cross-user access.
- service/admin roles documented.
- migrations run with controlled admin role.

## Rollback Strategy

Every migration must specify:

- reversible or irreversible
- rollback DDL
- data rollback approach
- search/embedding rebuild plan
- user-visible impact

Irreversible migrations require:

- explicit approval
- backup verification
- dry run
- metrics snapshot

## Validation Queries

Every migration has count checks.

Examples:

```sql
-- No active memory without user_id
select count(*) from memory_record where user_id is null;

-- No active search docs for deleted records
select count(*)
from search_document sd
join memory_record mr on mr.id = sd.target_id
where sd.target_table = 'memory_record'
  and mr.lifecycle_state = 'deleted'
  and sd.invalidated_at is null;

-- No raw object without retention policy
select count(*) from raw_object_ref where retention_policy is null;

-- No dedupe key without key version
select count(*) from dedupe_key where key_version is null;
```

## Production Deployment Checklist

Before deploy:

- [ ] migration categorized
- [ ] backup verified
- [ ] dry run completed
- [ ] estimated row counts known
- [ ] lock risk reviewed
- [ ] rollback plan written
- [ ] validation queries written
- [ ] raw/log safety reviewed
- [ ] RLS impact reviewed
- [ ] search/embedding impact reviewed
- [ ] cost impact estimated

After deploy:

- [ ] validation queries pass
- [ ] error rate normal
- [ ] import preview still works
- [ ] deletion still removes from search
- [ ] export eligibility still correct
- [ ] raw expiration job still works
- [ ] no raw/private titles in logs

## 結論

DB migrationは、Memory OSの長期信頼を壊しやすい作業である。

安全なmigrationは、expand/backfill/switch/contract、chunked jobs、no raw logs、lifecycle-aware rebuild、dedupe/tombstone preservationを前提にする。

実装時は、migrationそのものもテスト対象にする。
