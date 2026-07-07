# Long-term Database Architecture

## 目的

この文書は、Memory OS が何十年もImportを続けても破産しないためのDB/Storage設計である。

対象:

- Apple Music / Spotify / Last.fm
- X archive
- Netflix CSV
- Prime Video / Disney+ / U-NEXT paste/manual
- LINE text/copy
- 食べログ
- Filmarks
- GERA / Podcast / Radio
- 漫画 / アニメ / 映画
- Browser bookmarks
- Google Takeout / YouTube
- Books / Library / Recipes / Games

この設計の目的は、ただ保存することではない。

長期で重要なのは以下である。

- 重複しない
- 消したものが復活しない
- rawで破産しない
- embeddingで破産しない
- indexで破産しない
- backup/restoreで壊れない
- APIやLLMが変わっても移行できる
- ユーザーごとに安全に分離できる
- 何十年後もExportできる

## Research-informed Principles

### 1. Relational core first

Memory OSのsystem of recordはPostgreSQLを第一候補にする。

理由:

- 参照整合性、unique constraint、transaction、row security、partition、JSONB、full-text search、pg_trgm、拡張が使える。
- 人生文脈はグラフにも見えるが、最初からGraph DB中心にすると運用・整合性・Exportが複雑になる。
- 長期保存では「検索の速さ」より「消えない・壊れない・移せる」が重要。

### 2. Raw is not the product

raw原文、archive、画像、HTML、CSV、ZIPはDB本文に入れない。

DBにはmetadata、hash、sourceRef、正規化結果、policy、lifecycleを入れる。

raw本体はobject storageへ分離し、原則短期・暗号化・明示保存にする。

### 3. Imported source item and memory are different

外部から入った1行/1件は `source_item`。

ユーザーが後で見返す記憶単位は `memory_record`。

1つのmemory_recordは複数source_itemから作られることがある。

逆に、1つのsource_itemが複数のmemory_recordに関係することもある。

### 4. Dedup is layered, not one hash

重複排除は1つのhashでは足りない。

層を分ける。

- Import job duplicate
- Raw file duplicate
- Source-native duplicate
- Canonical activity duplicate
- Entity/work duplicate
- Semantic near-duplicate
- User-confirmed merge

自動で消すのは安全な層だけ。

曖昧なものは「同一候補」としてlinkするだけで、勝手に統合しない。

### 5. Event log for important state changes

Import、merge、delete、seal、hide、policy change、export、embedding invalidationなどはeventとして残す。

現在状態だけだと、数年後に「なぜこれが消えた/統合された/Exportされなかったか」が追えない。

### 6. Bitemporal mindset

Memory OSには複数の時間がある。

- occurred_at: その出来事が起きた日時
- captured_at: 元サービスに記録された日時
- imported_at: Memory OSに入った日時
- normalized_at: 正規化された日時
- interpreted_at: 解釈/要約された日時
- deleted_at: 削除された日時

1つのcreated_atだけで設計しない。

### 7. Derived data is disposable

Search document、embedding、recommendation cache、LLM summaryは派生データである。

原本ではない。

削除・hidden・sealed・policy changeに追従して無効化できる必要がある。

### 8. Tables should be narrow where hot, JSONB where variable

頻繁にwhere/order/joinするものは通常カラム。

サービスごとの揺れや追加情報はJSONB。

JSONBを便利なゴミ箱にしない。

### 9. Partition only where it pays

全部partitionしない。

大きくなり、append-heavyで、retention/archival/delete boundaryがあるテーブルだけpartitionする。

Partition設計はunique制約や運用に影響するため、最初に分ける。

### 10. User_id first

全ユーザーデータの主なqueryは `user_id` scopeで走る。

主要indexは `(user_id, ...)` を基本にする。

Row Level Securityやアプリケーションレベルのtenant isolationを前提にする。

## Recommended Storage Stack

### MVP / early production

```txt
PostgreSQL
Object Storage
PostgreSQL full-text / pg_trgm
Optional background worker queue
```

### Later

```txt
PostgreSQL primary relational core
Object Storage for raw/archive/media
Search index if Postgres FTS is insufficient
Vector index only for safe derived embeddings
Cold archive for old raw/exports
```

Avoid early:

- Graph DB first
- vector DB first
- one-table JSON document store first
- storing all raw chat/archive text in relational columns
- embedding every imported row

## Database Schemas

Suggested PostgreSQL schemas:

```sql
core      -- users, source refs, canonical items, activities, memories
importing -- import jobs, import files, source items, detection, preview
policy    -- policy decisions, privacy flags, lifecycle
search    -- search documents, lexical indexes, embedding metadata
security  -- credentials, oauth tokens metadata, key references
ops       -- audit, outbox, cost ledger, background jobs
```

This is not mandatory physically, but it keeps mental boundaries clear.

## Core Data Layers

### Layer 0: User / Account

- app_user
- user_profile_settings
- user_security_settings
- trusted_device
- session_metadata

### Layer 1: Import Intake

- import_job
- import_input_file
- import_detection_result
- import_preview
- import_preview_candidate

### Layer 2: Source Identity

- source_ref
- source_item
- source_item_key
- raw_object_ref

### Layer 3: Canonical Domain

- canonical_item
- canonical_item_external_id
- user_activity
- user_activity_source_link

### Layer 4: Memory

- memory_record
- memory_source_link
- evidence_record
- memory_interpretation

### Layer 5: Safety / Lifecycle

- privacy_classification
- policy_decision
- lifecycle_event
- deletion_tombstone
- merge_decision

### Layer 6: Search / Derived

- search_document
- embedding_record
- derived_summary
- search_index_task

### Layer 7: Ops / Cost

- audit_event
- cost_ledger_entry
- outbox_event
- background_job

## Table Responsibility

### import_job

One attempt to bring data into Memory OS.

Stores:

- input kind
- source candidate
- parser version
- status
- counts
- hashes
- no raw content

Partition:

- optional by created_at yearly/monthly later

### import_input_file

Metadata about uploaded files.

Stores:

- object path
- sha256
- size
- mime guess
- original filename redacted option
- retention policy

Does not store:

- file content in DB

### source_ref

Stable reference to a source or import.

Examples:

- Netflix Viewing Activity CSV uploaded on 2026-07-07
- Spotify API sync 2026-07-07
- LINE selected paste from chat with safe label
- Filmarks copied list

### source_item

One imported item/event from a source.

Examples:

- one Netflix watched row
- one Spotify recently played track
- one LINE snippet candidate
- one 食べログ restaurant URL
- one manga progress line

This is the key dedup unit.

### canonical_item

A real-world item/work/place/show/book/track/restaurant.

Examples:

- movie: Spirited Away
- restaurant: 店名
- anime: One Piece
- music track: Butter-Fly
- podcast show: 番組名

Important:

- canonical_item is not user activity.
- It does not mean the user watched/listened/read it.

### user_activity

User-specific interaction with a canonical item.

Examples:

- watched movie on date
- listened track at time
- reading manga volume 12
- visited restaurant
- saved bookmark

This is the main hobby/life activity table.

### memory_record

Human-facing memory unit.

Examples:

- 2026年7月ごろNetflixでこの作品を見ていた
- 横浜でこの店を調べていた
- 結婚式準備中にこの曲をよく聴いていた

Memory may be user-created, imported, or AI-summarized only after user request.

### search_document

Searchable projection.

Not the source of truth.

Regenerate when:

- record changes
- privacy changes
- lifecycle changes
- policy changes

### embedding_record

Vector metadata.

Not the source of truth.

Must include:

- model version
- source text hash
- policy eligibility
- invalidated_at
- lifecycle

## Dedup Strategy

### Dedupe Layer 1: ImportJob idempotency

Goal:

- same file/same selection/same parser should not create duplicate import jobs.

Key:

```txt
user_id + input_kind + input_payload_hash + parser_family + selected_scope_hash
```

Action:

- If exact same import is retried, return previous preview/result.
- Similar to idempotency key behavior.

### Dedupe Layer 2: Raw file hash

Goal:

- same uploaded ZIP/CSV/HTML should not be stored repeatedly.

Key:

```txt
sha256(file bytes)
```

Action:

- Reference existing raw object if allowed.
- Never infer that same file means same user consent/scope.

### Dedupe Layer 3: Source-native key

Goal:

- if source provides stable ID, use it.

Examples:

- Spotify track ID + played_at
- AniList media ID + user list status/progress
- YouTube video ID + watched_at
- X tweet ID
- Netflix title + watched date because no stable work ID in CSV

Key:

```txt
user_id + source_provider + source_account_hash + native_item_id + activity_time_or_state
```

### Dedupe Layer 4: Canonical activity key

Goal:

- identify same real user activity from different sources.

Examples:

- Netflix CSV and manual watched entry same title/date
- Filmarks watched entry and manual movie memory same movie/date
- Spotify and Last.fm same track/time window

Key uses normalized fields:

```txt
user_id + domain + normalized_title + normalized_creator + activity_type + occurred_date_bucket + optional_external_id
```

Action:

- high confidence: link to existing activity.
- medium confidence: create match candidate.
- low confidence: separate records.

### Dedupe Layer 5: Canonical item/entity matching

Goal:

- match same work/place/person-like reference.

Examples:

- 映画 title Japanese/English
- restaurant URL variants
- music track title variants
- manga/anime title aliases

Use:

- external IDs first
- normalized title
- creator/artist/year
- domain-specific metadata
- pg_trgm similarity as candidate generator
- user confirmation for ambiguous cases

Action:

- Do not collapse automatically unless strong external ID or exact high confidence.

### Dedupe Layer 6: Memory-level semantic near-duplicate

Goal:

- avoid duplicate human-facing memories.

Action:

- never auto-delete.
- suggest merge/link.
- keep source items intact.

## Why not simply unique(title, date)?

Because:

- same title can be watched multiple times.
- same restaurant can be visited many times.
- same song can be listened many times.
- same LINE topic may appear multiple days.
- copied lists may lack dates.
- services have different IDs and title formats.

Therefore uniqueness must be source-aware and activity-aware.

## Recommended Partitioning

### Do not partition small core tables

Do not partition:

- app_user
- source_ref
- canonical_item initially
- canonical_item_external_id initially
- policy config tables

### Partition large append-heavy tables

Consider partitioning:

- source_item
- user_activity
- audit_event
- search_document
- embedding_record
- cost_ledger_entry
- outbox_event after growth

### Partition key strategy

For user-scoped SaaS:

- Large append-only events: range partition by `created_at` or `imported_at` monthly/yearly.
- Heavy user lookup tables: hash partition by `user_id` if table becomes huge and user distribution demands it.
- Activities: begin unpartitioned, then partition by occurred_at only when table exceeds operational threshold.

Caution:

- In PostgreSQL, unique constraints on partitioned tables must include partition key columns.
- If global uniqueness across partitions is needed, use a separate key table.

## Dedupe Key Table

Because cross-partition uniqueness is hard, create a dedicated dedupe table.

```sql
create table dedupe_key (
  id uuid primary key default uuidv7(),
  user_id uuid not null,
  key_scope text not null,
  key_type text not null,
  key_hash bytea not null,
  target_table text not null,
  target_id uuid not null,
  confidence text not null,
  created_at timestamptz not null default now(),
  deleted_at timestamptz,
  unique (user_id, key_scope, key_type, key_hash)
);
```

This table stays small compared to raw/source tables because it stores hashes, not content.

## ID Strategy

Use UUID primary keys.

Preferred:

- UUIDv7 for DB-generated sortable IDs where supported.
- UUIDv4 acceptable for compatibility.

Why:

- distributed/offline/local-first possible.
- avoids leaking row counts.
- UUIDv7 improves insertion locality compared to pure random IDs.

Do not expose sequential internal IDs.

## Index Strategy

### Always index user scope

Examples:

```sql
create index idx_user_activity_user_time
  on user_activity (user_id, occurred_at desc);

create index idx_source_item_user_source
  on source_item (user_id, source_ref_id, occurred_at desc);
```

### Partial indexes for active records

Most queries should exclude deleted/hidden/sealed by default.

```sql
create index idx_memory_active_user_time
  on memory_record (user_id, occurred_at desc)
  where lifecycle_state = 'active';
```

### BRIN for very large time-ordered append tables

For audit/source events that are inserted in time order, BRIN can reduce index cost.

Candidates:

- audit_event(created_at)
- source_item(imported_at)
- cost_ledger_entry(created_at)

### GIN for JSONB only where queried

Do not add broad GIN indexes on every JSONB metadata column.

Use targeted expression indexes for fields actually queried.

### pg_trgm for title matching

Use pg_trgm similarity for candidate generation, not authoritative dedup.

Examples:

- movie title matching
- restaurant name matching
- music title matching
- manga/anime aliases

## Search Strategy

MVP:

- relational search table
- tsvector for safe text
- pg_trgm for typo/alias matching

Later:

- external search index only if Postgres becomes insufficient.
- vector search only for safe derived summaries.

Do not:

- embed raw LINE/DM.
- embed private bookmarks by default.
- embed every source_item.
- use vector similarity to merge records automatically.

## Lifecycle and Deletion

All major tables have lifecycle columns or join to lifecycle_event.

States:

- active
- hidden
- sealed
- archived
- pending_delete
- deleted

Deletion rules:

- deleted records disappear from search/tips/export immediately.
- deletion_tombstone prevents re-import resurrection.
- derived search/embedding invalidated.
- backup restore must replay tombstones.

## Re-import Resurrection Guard

When importing new data, compare against deletion tombstones.

Example:

- user deleted a LINE snippet
- later uploads same LINE export
- source_item hash matches tombstone
- Import Preview should mark it as previously deleted and exclude by default

## Cost Protection

### Storage cost

- raw off by default.
- object storage lifecycle for uncommitted import files.
- old import files expire unless user explicitly preserves.
- compress export/archive packages.

### DB cost

- no giant raw text columns in hot tables.
- no unnecessary GIN indexes.
- partition only large append tables.
- archive old audit partitions.

### Search cost

- search_document stores safe text only.
- rebuildable, not source of truth.
- lifecycle-aware.

### Embedding cost

- embed only memory_record or safe summaries.
- require `embedding_input_hash` to avoid re-embedding same content.
- store model version.
- invalidate on policy/lifecycle changes.
- lazy embed after first search/reflection request, not at import time.

## Data Retention Defaults

### Import raw files

- default: store until import completion + short grace period.
- user can opt in to retain raw.
- sensitive imports default to not retaining raw.

### Source items

- durable metadata/normalized records.
- raw off unless selected.

### Search docs

- rebuildable.
- can be deleted/recreated.

### Embeddings

- rebuildable.
- delete/disable on lifecycle change.

### Audit events

- no raw.
- long retention.

## Concrete Table Set v1

Minimum implementation tables:

```txt
app_user
source_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
source_item
source_item_key
dedupe_key
canonical_item
canonical_item_external_id
user_activity
user_activity_source_link
memory_record
memory_source_link
evidence_record
policy_decision
lifecycle_event
deletion_tombstone
search_document
embedding_record
audit_event
outbox_event
cost_ledger_entry
```

Do not start with fewer if Import is serious.

Do not combine source_item, user_activity, and memory_record into one table.

## Anti-patterns

Do not:

- one giant `memories` table with JSON blob.
- store raw imports directly in `memory_record.body`.
- dedupe only by title/date.
- delete source rows physically without tombstone.
- embed everything on import.
- make vector DB the source of truth.
- store service tokens in the same table as user profile.
- put policy flags only in app code.
- let search index decide lifecycle.
- rely on extension alone to decide parser.
- use `source_item` as user-facing memory without preview/normalization.

## Migration Strategy

### v1

- relational core
- raw object storage
- import preview
- source items
- user activity
- memory records
- dedupe_key
- search_document

### v1.5

- pg_trgm title matching
- tsvector search
- partition audit/source_item if needed
- embedding_record metadata but embeddings optional

### v2

- vector search safe summaries
- cold archive partitioning
- advanced entity resolution
- user-confirmed merge workflows

## Conclusion

Memory OS needs a relational, provenance-first, dedupe-aware database.

The correct design is not a single memories table, not a vector database, not a pure document store, and not service-specific silos.

The durable core is:

```txt
SourceRef
→ SourceItem
→ CanonicalItem
→ UserActivity
→ MemoryRecord
→ Evidence / Interpretation
→ Search / Embedding derived projections
```

This keeps imports accurate, avoids duplicates, preserves provenance, supports deletion, prevents re-import resurrection, and keeps costs under control for decades.
