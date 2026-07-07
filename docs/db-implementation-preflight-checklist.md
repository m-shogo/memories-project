# Database Implementation Preflight Checklist

## 目的

この文書は、Memory OS のDB/Import実装に入る前の最終preflight checklistである。

このchecklistを満たさない限り、DB migration実装に入らない。

## Verdict Scale

```ts
type PreflightVerdict =
  | 'ready'
  | 'ready_with_known_risks'
  | 'blocked';
```

## Current Verdict

現時点の設計は:

```txt
ready_with_known_risks
```

理由:

- 大枠のDB architectureは十分強い。
- Import Core / Adapter / Parser / Preview / Policy / Dedupe / Lifecycle は設計済み。
- ただし、実装前にfixture、migration safety、RLS tests、key management detailsを固める必要がある。

## P0: Must be true before DB implementation

### Architecture

- [ ] PostgreSQL is selected as system of record.
- [ ] Object storage is selected for raw/archive/media.
- [ ] Vector DB is not source of truth.
- [ ] Raw is not stored in memory_record body.
- [ ] source_item / user_activity / memory_record are separate.
- [ ] canonical_item is separate from user_activity.
- [ ] search_document is derived.
- [ ] embedding_record is derived.

### Import Pipeline

- [ ] Import Core exists as a single pipeline.
- [ ] Source Adapter interface exists.
- [ ] Parser Registry exists.
- [ ] Detector does not rely on extension only.
- [ ] Import Preview is mandatory.
- [ ] Policy Evaluation runs before Safe Commit.
- [ ] Audit stores no raw.

### Security

- [ ] File upload allowlist exists.
- [ ] MIME/content type is not trusted alone.
- [ ] raw filenames are replaced or hashed.
- [ ] active content is never rendered.
- [ ] archive traversal is blocked.
- [ ] zip bomb / XML bomb limits exist.
- [ ] raw object storage is outside webroot/public access.
- [ ] token/encryption key material is not stored in DB.
- [ ] RLS policy approach is defined.
- [ ] app runtime DB role is not table owner.

### Dedup / Tombstone

- [ ] dedupe_key table exists.
- [ ] deletion_tombstone table exists.
- [ ] sensitive dedupe keys use HMAC.
- [ ] key_version is stored.
- [ ] source_account_ref exists.
- [ ] time precision is modeled.
- [ ] low confidence match does not auto-merge.
- [ ] deleted records are excluded on re-import by default.

### Privacy

- [ ] LINE/DM raw default off.
- [ ] X likes/bookmarks owner_sensitive.
- [ ] streaming watch history owner_sensitive.
- [ ] shared profile warning exists.
- [ ] private bookmark titles are not logged.
- [ ] private/sealed/deleted records excluded from search/tips/export.

### Cost

- [ ] raw expiration job is planned.
- [ ] Export staging TTL is planned.
- [ ] search_document invalidation is planned.
- [ ] embedding is lazy/budgeted.
- [ ] no Import-time embedding of all source_items.
- [ ] index budget review exists.
- [ ] partitioning is delayed until needed.

### Backup / Restore

- [ ] backup restore drill includes deletion tombstone replay.
- [ ] search documents can be rebuilt.
- [ ] embeddings can be invalidated/rebuilt.
- [ ] raw objects can be expired/deleted.
- [ ] export packages expire.

## P1: Should be true before production

- [ ] source_account_ref implemented for all API connectors.
- [ ] parser_version and adapter_version stored on source_item.
- [ ] source_schema_version stored when known.
- [ ] entity_match_candidate table exists.
- [ ] merge_decision table exists.
- [ ] canonical_item_alias table exists.
- [ ] RLS negative tests exist.
- [ ] account deletion mode is product/legal reviewed.
- [ ] token rotation and revocation jobs exist.
- [ ] large import cancellation tested.
- [ ] restore test is automated.

## P2: Nice but later

- [ ] advanced partitioning.
- [ ] external search index.
- [ ] vector search.
- [ ] cross-device local-first conflict resolution.
- [ ] advanced entity resolution UI.
- [ ] user-visible merge/unmerge interface.

## Implementation Blockers

DB implementation is blocked if any are true:

- memory_record is planned as the only core table.
- raw imports are planned to be stored in relational text columns by default.
- Import Preview is skipped.
- dedupe_key is missing.
- deletion_tombstone is missing.
- raw expiration is not planned.
- API tokens are stored without encryption plan.
- private/sealed/deleted lifecycle does not affect search/export.
- embedding all import rows is planned.
- RLS/admin role plan is absent.

## First Migration Slice Recommendation

Create only foundational tables first:

```txt
app_user
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
dedupe_key
deletion_tombstone
policy_decision
lifecycle_event
audit_event
outbox_event
key_reference
```

Do not create all domain tables before the first preview prototype unless necessary.

Second slice:

```txt
source_item
source_item_key
canonical_item
canonical_item_external_id
canonical_item_alias
user_activity
user_activity_source_link
```

Third slice:

```txt
memory_record
memory_source_link
evidence_record
search_document
embedding_record
cost_ledger_entry
entity_match_candidate
merge_decision
```

## Why staged migration

Staging reduces risk:

- Preview-only can be tested without committing memory records.
- Security gate can be tested early.
- Dedupe/tombstone can be tested before domain complexity.
- Search/embedding can be added after lifecycle is correct.

## Final Go/No-Go Before Coding

Go only if:

```txt
Import Preview exists first.
Dedupe and Tombstone exist before first real save.
Raw object storage has TTL.
Policy runs before commit.
Search/Embedding are derived and lifecycle-aware.
```

Otherwise, do not start DB implementation.

## 結論

今の設計は、実装に近い。

しかし、いきなり全テーブルを作るのではなく、Preview-first / Dedupe-first / Tombstone-first / Raw-TTL-first で切る。

これが、Memory OSを何十年運用しても破産しにくくする最初の実装順である。
