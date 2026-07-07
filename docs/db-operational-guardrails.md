# Database Operational Guardrails

## 目的

この文書は、Memory OS が長期運用でDB・検索・Embedding・Backup・Exportコストに潰されないための運用ガードレールである。

設計が正しくても、運用ルールがないと破産する。

## 破産ポイント

Memory OSの主な破産ポイント:

1. raw archiveを保存しすぎる
2. source_itemが重複で増える
3. search_documentを増やしすぎる
4. embeddingをImport時に乱発する
5. GIN indexを貼りすぎる
6. partitionを早すぎ/細かすぎに作る
7. auditにrawを入れて削除不能になる
8. backupから削除済みデータが復活する
9. Export stagingが残り続ける
10. API syncが差分でなく全量再Importになる

## Guardrail 1: Raw Retention Budget

Default:

- raw file: store until import complete + short grace period
- LINE/DM raw: do not store by default
- private bookmarks raw: do not store by default
- streaming history raw file: short-lived unless user preserves

Required fields:

- raw_stored
- raw_retention_policy
- expires_at
- deleted_at
- object_storage_path

Scheduled job:

- delete expired raw objects
- verify object deleted
- mark raw_stored=false if no raw remains
- audit count only

Never:

- keep raw forever by accident
- store raw in logs
- store raw in audit metadata

## Guardrail 2: Import Idempotency

Every import route must provide or derive an idempotency key.

Examples:

- file upload: sha256 + parser + selected scope
- paste import: text hash + source + selected scope
- API sync: source account + cursor/window + native item IDs
- email import: message-id hash + source + payload hash

If idempotency key matches, do not create duplicate records.

## Guardrail 3: Incremental Sync First

API connectors should be incremental.

Do:

- store sync cursor if service provides it.
- store last successful sync window.
- use source-native IDs.
- dedupe every item anyway.

Do not:

- re-import entire history on every sync.
- embed every synced item.
- delete missing items unless source explicitly supports deletion semantics.

## Guardrail 4: Search Projection Budget

Search documents are derived.

Rules:

- create search_document only for policy-eligible records.
- no raw LINE/DM search docs by default.
- private/sealed records excluded unless user explicitly searches inside private scope.
- invalidate search docs on lifecycle/policy change.
- rebuild search docs from source_item/user_activity/memory_record.

Metric:

```txt
search_document_count / active_user_activity_count
```

This ratio should not grow without reason.

## Guardrail 5: Embedding Budget

Embedding is optional and derived.

Rules:

- never embed raw imports by default.
- never embed private/sensitive records by default.
- never embed all source_items at import time.
- embed memory_record or safe summary only.
- use input_hash to avoid re-embedding same content.
- model version must be stored.
- invalidated_at must be supported.

Cost controls:

- monthly embedding budget per user/plan.
- lazy embedding on first semantic search/reflection.
- batch embedding only after policy approval.
- no embedding for deleted/hidden/sealed unless explicitly allowed.

## Guardrail 6: Index Budget

Indexes are not free.

Rules:

- every index must have a query owner.
- remove unused experimental indexes before production.
- avoid broad GIN on generic JSONB.
- use partial indexes for active records.
- use BRIN for huge append-only time-ordered tables when appropriate.
- use pg_trgm for candidate generation only.

Index review questions:

- Which query uses this index?
- Is this query on a hot path?
- Can a composite index replace two indexes?
- Is this index huge compared to table size?
- Does this index include deleted/hidden/sealed records unnecessarily?

## Guardrail 7: Partition Budget

Partitioning helps large tables but adds operational complexity.

Do not partition early just because it feels scalable.

Partition when:

- table size exceeds comfortable maintenance threshold.
- queries naturally filter by time/user.
- retention/archive/drop by time is needed.
- indexes no longer fit operationally.

Avoid:

- daily partitions early.
- partitioning every table.
- relying on unique constraints that cannot work across partitions.

Recommended first partitions later:

- audit_event by created_at month/year
- cost_ledger_entry by created_at month/year
- source_item by imported_at month/year if huge

Keep dedupe_key separate to enforce active uniqueness.

## Guardrail 8: Deletion and Backup

Deletion is not just DB row update.

Must handle:

- source_item lifecycle
- user_activity lifecycle
- memory_record lifecycle
- search_document invalidation
- embedding invalidation/deletion
- raw_object_ref deletion
- export_staging deletion
- deletion_tombstone creation
- backup restore replay

Backup restore rule:

```txt
restore data
→ replay deletion_tombstones
→ invalidate derived indexes
→ rebuild search/embedding eligibility
```

Do not restore deleted data into active search.

## Guardrail 9: Export Staging TTL

Export packages are temporary.

Rules:

- encrypted
- expires_at required
- no permanent signed URL
- delete after expiry or download window
- export manifest stored without raw if possible
- raw export requires Export Safety ceremony

## Guardrail 10: Observability Without Content

Metrics allowed:

- counts
- sizes
- source IDs
- parser IDs
- policy reason codes
- timings
- cost estimates

Forbidden:

- raw text
- private titles
- chat snippets
- URLs with private tokens
- full search queries if sensitive

## Core Metrics

Track:

```txt
import_jobs_created
import_candidates_parsed
import_candidates_saved
import_duplicates_skipped
source_items_created
user_activities_created
memory_records_created
search_documents_created
embeddings_created
raw_bytes_stored
raw_bytes_expired
export_packages_active
search_documents_invalidated
embeddings_invalidated
policy_denies
storage_cost_estimate
embedding_cost_estimate
```

## SLO-ish Operational Targets

Early targets:

- Import Preview generation should work before any commit.
- Pasted list import should not require LLM.
- Search should work without embeddings.
- Deletion should remove from search immediately.
- Raw expiration job should run daily.
- Export staging cleanup should run daily.

## Plan/Payment Guardrails

Paid plan can increase:

- storage retention
- number of sources
- import frequency
- export size
- semantic search budget

Paid plan cannot override:

- policy deny
- third-party raw restrictions
- crisis safety
- impersonation safety
- deleted tombstones
- export re-auth requirements

## Migration Guardrails

Every migration must answer:

- Does it touch raw?
- Does it affect lifecycle/deletion?
- Does it require backfilling search docs?
- Does it require re-embedding?
- Does it change dedupe keys?
- Can it run incrementally?
- Can it be rolled back?
- Does it lock large tables?

Large migrations:

- backfill in chunks.
- use background jobs.
- avoid long exclusive locks.
- verify counts before/after.

## Minimal Production Readiness

Before production Import:

- raw expiration job exists.
- deletion tombstone check exists.
- dedupe_key exists.
- Import Preview exists.
- search_document invalidation exists.
- no raw in logs.
- basic DB backup and restore test exists.
- Export staging TTL exists.
- cost ledger records raw bytes and embedding count.

## 結論

Memory OSが長期で破産しない条件は、DB設計だけではない。

運用で守るべきなのは、raw、dedupe、search、embedding、index、partition、backup、export stagingである。

特に重要なのは:

```txt
rawは短期/明示保存
Importはidempotent
search/embeddingは派生
dedupe_keyで重複を止める
deletion_tombstoneで復活を止める
index/partition/embeddingを増やしすぎない
```

この運用ルールがあって初めて、何十年分の人生文脈を保存できる。
