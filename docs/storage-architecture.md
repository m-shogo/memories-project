# Storage Architecture

## 目的

Storage Architecture は、Memory OS のデータをどこに、どの粒度で、どの保持方針で保存するかを定義する。

このサービスは、ただのファイル置き場ではない。

人生文脈、原文、出典、要約、解釈、第三者情報、削除状態、Export、Backup、Embedding を分けて扱う必要がある。

## 最上位原則

### 1. Raw is dangerous

Raw原文・添付・画像本体は最も危険である。

DB本文と同じ扱いにしない。raw保存は明示的・暗号化・短期/限定・削除可能にする。

### 2. Metadata is durable

SourceRef / occurredAt / importedAt / risk / lifecycle / evidence は長期の索引として重要。

rawがなくても文脈を保てるようにする。

### 3. Vector is derived

Embeddingは原本ではない。検索補助の派生データであり、hidden/sealed/deletedに追従して無効化できる必要がある。

### 4. Audit without content

監査ログ・コストログ・セキュリティログは raw text を持たない。

### 5. Delete across stores

削除はDBだけでは不十分。

Object storage、vector index、export package、backup restore marker まで一貫して扱う。

## Storage Classes

```ts
type StorageClass =
  | 'relational_core'
  | 'raw_object_storage'
  | 'search_index'
  | 'vector_index'
  | 'audit_log'
  | 'export_staging'
  | 'backup_snapshot'
  | 'local_archive';
```

## Recommended MVP Storage Split

### Relational Core

Use for:

- User
- SourceRef
- ImportJob
- RawRecord metadata
- NormalizedRecord
- Memory
- Evidence
- MemoryInterpretation
- PolicyDecisionRecord
- DeletionTombstone
- CostEstimateRecord
- CostLedgerEntry
- ExportJob
- EmbeddingRecord metadata

MVP options:

- SQLite for local/dev/single-user prototype
- PostgreSQL for service deployment

Rule:

- relational DB may hold safe text / summaries.
- high-risk raw should not be casually stored as normal columns.

### Raw Object Storage

Use for:

- uploaded files
- raw archives
- raw text blobs if allowed
- media files if ever supported

Controls:

- encrypted at rest
- path by userId/importJobId/sourceRefId
- signed access only
- rawRetentionPolicy required
- rawStored flag mirrors reality

### Search Index

MVP can start inside relational DB.

Use for:

- searchableText
- topicHints
- placeHints
- timeHints
- tags

Rule:

- only safe normalized text.
- no secrets.
- no third-party raw.
- lifecycle filter mandatory.

### Vector Index

Post-MVP or optional.

Use for:

- safe normalized text embeddings
- safe memory summaries

Controls:

- userId partition/filter
- target lifecycle
- policy eligibility
- EmbeddingRecord lifecycle
- delete/disable hook

### Audit Log

Use for:

- policy decisions
- export events
- deletion events
- admin access
- break-glass
- cost ledger

Rule:

- no raw text
- no secret values
- no third-party raw

### Export Staging

Use for:

- temporary export packages
- manifest
- redaction reports

Controls:

- encrypted
- short-lived
- signed URL
- expiresAt
- delete after download/expiry

### Backup Snapshot

Use for:

- operational recovery
- encrypted snapshots

Controls:

- deletion markers replayed on restore
- no hidden retention loophole
- restore audit

## Entity Storage Table

| Entity | Storage | Raw allowed? | Notes |
|---|---|---|---|
| SourceRef | relational | no | source metadata only |
| ImportJob | relational | no | inspection summary safe only |
| RawRecord | relational + object optional | risky | text optional, object preferred for raw |
| NormalizedRecord | relational | safe text only | searchableText sanitized |
| Memory | relational | no raw default | summary/body safe |
| Evidence | relational | quote limited | quotePolicy required |
| Interpretation | relational | safe/inference | never fact without evidence |
| Embedding vector | vector index | derived | lifecycle enforced |
| Export package | export staging | policy only | temporary |
| Backup snapshot | backup | encrypted | deletion replay |

## Raw Storage Policy

```ts
type RawStoragePolicy =
  | 'do_not_store'
  | 'metadata_only'
  | 'store_until_import_complete'
  | 'store_until_user_deletes'
  | 'store_with_retention_period'
  | 'store_if_low_risk';
```

Defaults:

| Source | Raw default |
|---|---|
| manual low-risk | optional |
| share text | optional |
| ChatGPT subset | metadata/safe text |
| LINE/DM | no/default |
| Gmail | no/default |
| Slack/work | no/default |
| Photos | metadata only |
| GitHub | metadata only |

## Indexing Rules

### SearchableText

Allowed:

- user-authored low-risk text
- safe summary
- metadata titles
- dates
- tags

Denied:

- secrets
- third-party raw
- corporate raw
- minor sensitive raw
- self-harm/crisis raw
- sealed content

### Embeddings

Allowed only when:

- policy allows create_embedding
- embeddingEligibility is true
- lifecycle active
- visibility searchable
- no secret/corporate/third-party raw

## Deletion Propagation

```txt
user delete
-> relational lifecycle pending_deletion
-> search index remove/disable
-> vector index remove/disable
-> object storage delete or mark purge
-> export staging revoke if needed
-> backup deletion marker
-> tombstone create
-> audit no raw
```

## Backup Restore Rule

Restore order:

```txt
restore snapshot
-> load deletion tombstones and markers
-> replay deletions
-> rebuild search index from allowed active records
-> rebuild vector index only for eligible records
-> audit restore
```

Never restore raw first into visible state before deletion replay.

## Multi-store Consistency

MVP can use eventual consistency for heavy deletes, but user-facing access must stop immediately.

Therefore:

- relational lifecycle is source of truth.
- search/vector must check lifecycle at query time.
- object deletion can be async.
- pending_delete blocks access immediately.

## Local Development Recommendation

For MVP local/dev:

```txt
SQLite: relational core
local encrypted folder: raw/export staging
in-memory or SQLite FTS: search
no vector initially
JSON fixture logs: audit dev only, no raw
```

For hosted MVP:

```txt
PostgreSQL: relational core + FTS
S3-compatible object storage: raw/export/backup
managed or self-hosted vector index: later
append-only audit table: no raw
```

## Security Controls

- encryption at rest for object storage
- no raw in application logs
- per-user path isolation
- short-lived signed URLs
- object access through policy gate
- rawStoragePath never exposed directly to user

## Cost Controls

- raw object storage retention
- no default full archive raw storage
- vector index optional/post-MVP
- export staging expiry
- backup retention windows

## Failure Modes

- DB delete but vector row remains.
- object storage raw remains after raw delete.
- export package not expired.
- backup restore resurrects tombstoned data.
- search index includes secret.
- audit log stores raw.
- SourceRef deleted before Memory loses provenance.

## Acceptance Criteria

- SourceRef persists even if raw is deleted.
- rawStored reflects actual storage.
- lifecycle source of truth blocks all surfaces.
- vector index is disabled/deleted on lifecycle changes.
- export packages expire.
- backup restore replays tombstones.
- audit/cost logs contain no raw.
- search index excludes forbidden data.

## Non-goals

- Choosing one permanent vendor.
- Building vector search in MVP before safe keyword search.
- Keeping all raw forever.
- Hiding storage behavior from user.

## 結論

Storage Architecture は、Memory OS の思想を物理的に守る層である。

raw、metadata、summary、embedding、export、backup、auditを分けることで、削除・安全・出典・持ち出し可能性を同時に守る。
