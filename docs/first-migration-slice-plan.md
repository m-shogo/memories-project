# First Migration Slice Plan

## 目的

この文書は、Memory OS のDB実装を始める場合に、最初のmigration sliceで何を作り、何をまだ作らないかを固定する。

最初のmigrationで全部のtableを作らない。

最初は、Import Preview / Dedupe / Tombstone / Raw TTL / Policy / Audit / Key Reference の土台だけを作る。

## Why First Slice Is Small

Memory OSでは、保存そのものよりも保存前の安全確認が重要。

したがって、最初に作るべきは `memory_record` ではなく、以下である。

- import_job
- import_preview
- dedupe_key
- deletion_tombstone
- raw_object_ref
- policy_decision
- key_reference
- audit_event

これにより、Preview-only prototypeを安全に実装できる。

## First Migration Scope

Create:

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
oauth_connection
```

Do not create yet:

```txt
source_item
source_item_key
canonical_item
canonical_item_external_id
canonical_item_alias
user_activity
user_activity_source_link
memory_record
memory_source_link
evidence_record
search_document
embedding_record
cost_ledger_entry
entity_match_candidate
merge_decision
```

Reason:

- first slice proves intake/preview/security/policy foundations.
- domain commit can wait until preview and policy are correct.

## First Slice Capabilities

After first migration, the system should support:

- creating an ImportJob.
- attaching uploaded file metadata.
- storing detection results.
- creating ImportPreview.
- creating ImportPreviewCandidate rows.
- storing dedupe_key candidates.
- checking deletion_tombstone.
- writing policy_decision.
- writing lifecycle_event for import job/candidate state.
- writing audit_event counts only.
- referencing key_reference for future encrypted data.
- storing OAuth connection ciphertext only, if API work begins later.

It should not yet:

- create final user_activity.
- create final memory_record.
- create search_document.
- create embeddings.
- create Export packages.

## Migration 001: Foundation Types

Create enums:

```txt
import_job_status
lifecycle_state
privacy_level
ai_analysis_default
export_default
import_confidence
```

Potential extra enums:

```txt
key_status
connection_status
```

Decision:

- PostgreSQL enums are stable but harder to change.
- If rapid iteration expected, text + check constraints may be easier.
- For design clarity, enum names are defined, but implementation can choose check constraints.

## Migration 002: User and Source Foundation

Create:

- app_user
- source_account_ref
- source_ref

Important columns:

- source_account_ref.provider
- source_account_ref.external_account_hash
- source_account_ref.profile_label_hash
- source_account_ref.key_version
- source_account_ref.shared_or_unknown flag
- source_ref.source_provider
- source_ref.source_kind
- source_ref.source_account_ref_id
- source_ref.raw_stored

## Migration 003: Import Job and File Intake

Create:

- import_job
- import_input_file
- import_detection_result

Must include:

- input_payload_hash
- selected_scope_hash
- parser_id
- parser_version
- detected_source_id
- detector_confidence
- counts jsonb
- sha256 for files
- object_storage_path metadata only
- expires_at for temp raw

Important:

- no raw content in DB.
- original filename should be hashed or redacted.

## Migration 004: Preview

Create:

- import_preview
- import_preview_candidate

Candidate columns:

- source_id
- domain
- title
- url
- occurred_at
- occurred_at_precision
- timezone
- status
- progress
- confidence
- selected
- privacy_level
- ai_analysis_default
- export_default
- warnings

Security:

- title may exist for preview, but private titles must not be logged.
- raw text not stored.

## Migration 005: Dedupe and Tombstone

Create:

- dedupe_key
- deletion_tombstone

Must include:

- key_algorithm
- key_version
- key_scope
- key_type
- key_hash
- target table/id where applicable
- confidence

Rules:

- HMAC for sensitive keys.
- no cleartext key material.
- no raw title/URL.

## Migration 006: Policy / Lifecycle / Audit / Outbox

Create:

- policy_decision
- lifecycle_event
- audit_event
- outbox_event

Rules:

- audit_event metadata cannot contain raw.
- policy_decision carries policy_version.
- outbox_event payload must not contain raw private content.

## Migration 007: Key / OAuth Foundation

Create:

- key_reference
- oauth_connection

Rules:

- key_reference stores KMS reference only.
- oauth_connection stores ciphertext/nonce/tag, never plaintext.
- source_account_ref linkage is supported.
- revoked_at/deleted_at present.

This migration can be included in first slice or delayed until first API connector.

Because S Rank includes Spotify/Apple Music/AniList later, include it in first slice to avoid unsafe later shortcut.

## RLS in First Slice

Enable RLS on:

```txt
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
oauth_connection
```

Use app_current_user_id helper.

Do not rely on RLS alone.

## Indexes in First Slice

Required:

```txt
import_job(user_id, created_at desc)
import_preview(import_job_id) unique
import_preview_candidate(import_preview_id, candidate_index)
source_ref(user_id, imported_at desc)
source_account_ref(user_id, provider)
dedupe_key(user_id, key_scope, key_type, key_hash) unique active
deletion_tombstone(user_id, tombstone_scope, key_type, key_hash) unique
audit_event(user_id, created_at desc)
oauth_connection(user_id, provider, status)
```

Avoid:

- broad GIN indexes
- partitioning
- vector indexes
- full text indexes

## Validation Queries

After migration:

```sql
select count(*) from information_schema.tables where table_name = 'import_job';
select count(*) from information_schema.tables where table_name = 'dedupe_key';
select count(*) from information_schema.tables where table_name = 'deletion_tombstone';
```

P0 validation:

```sql
-- no dedupe_key without key version
select count(*) from dedupe_key where key_version is null;

-- no tombstone without key version
select count(*) from deletion_tombstone where key_version is null;

-- no oauth token without key ref
select count(*) from oauth_connection where token_encryption_key_ref is null;
```

## First Slice Test Scenarios

1. create import_job for user A.
2. create preview candidates.
3. user B cannot see user A preview.
4. candidate matches tombstone and selected=false.
5. raw file expires_at exists.
6. private candidate has AI off and export excluded.
7. audit contains counts only.
8. OAuth connection cannot store plaintext token.
9. revoked OAuth connection cannot be synced.
10. missing current_user_id returns no rows.

## Not Yet Tested in First Slice

- final memory timeline.
- canonical entity matching.
- full search.
- embeddings.
- export package generation.

These wait until later slices.

## Rollback Plan

Because first slice creates foundational tables only:

- rollback can drop tables if no production data.
- after production data, rollback must be logical and preserve import/audit/tombstone.

Do not drop tombstone in production rollback without explicit product/legal approval.

## Go Criteria

First migration can begin only if:

- parser fixture spec exists.
- migration safety checklist exists.
- RLS negative test spec exists.
- token encryption spec exists.
- policy tests P0-001〜P0-040 exist.

## 結論

最初のmigrationは、Memoryを保存するためではなく、Memoryを安全に保存する準備を作るためのmigrationである。

最初に作るべきは、Preview、Dedupe、Tombstone、Raw TTL、Policy、Audit、Key Referenceである。

これを先に作ることで、後からdomain tablesを追加しても破産しにくい。
