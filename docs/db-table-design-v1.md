# Database Table Design v1

## 目的

この文書は、Memory OSの長期DB設計を実装前にDDLレベルへ落とすためのv1 table proposalである。

このDDLは最終migrationではなく、設計の基準である。

## 基本方針

- PostgreSQLをsystem of recordにする。
- raw本体はobject storageへ分離する。
- source_item / user_activity / memory_recordを分ける。
- dedupe_keyで重複を制御する。
- search_document / embedding_recordは派生データとして扱う。
- 全user data tableはuser_idを持つ。
- deleted/hidden/sealedは検索・Tip・Exportから即除外できる。

## Required Extensions

```sql
-- optional but recommended on supported PostgreSQL versions
-- UUIDv7 may be available in current PostgreSQL.

create extension if not exists pg_trgm;
```

Notes:

- UUID generation can be in app layer if DB UUIDv7 is unavailable.
- pg_trgm is for candidate matching, not authoritative dedupe.

## Enums

```sql
create type import_job_status as enum (
  'created',
  'security_checked',
  'detected',
  'parsed',
  'preview_ready',
  'user_confirmed',
  'policy_checked',
  'committed',
  'cancelled',
  'failed'
);

create type lifecycle_state as enum (
  'active',
  'hidden',
  'sealed',
  'archived',
  'pending_delete',
  'deleted'
);

create type privacy_level as enum (
  'owner_only',
  'owner_sensitive',
  'restricted'
);

create type ai_analysis_default as enum (
  'off',
  'allowed_after_user_request'
);

create type export_default as enum (
  'included',
  'excluded'
);

create type import_confidence as enum (
  'high',
  'medium',
  'low',
  'needs_user_selection'
);
```

## app_user

```sql
create table app_user (
  id uuid primary key,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);
```

## source_ref

A source/import/reference unit.

```sql
create table source_ref (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_provider text not null,
  source_label text,
  source_kind text not null,
  import_job_id uuid,
  external_account_hash bytea,
  external_url text,
  captured_at timestamptz,
  imported_at timestamptz not null default now(),
  raw_stored boolean not null default false,
  raw_retention_policy text not null default 'do_not_store',
  risk_flags text[] not null default '{}',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_source_ref_user_imported
  on source_ref (user_id, imported_at desc);

create index idx_source_ref_user_provider
  on source_ref (user_id, source_provider, imported_at desc);
```

## import_job

```sql
create table import_job (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  input_kind text not null,
  declared_source_id text,
  detected_source_id text,
  parser_id text,
  parser_version text,
  status import_job_status not null default 'created',
  input_payload_hash bytea,
  selected_scope_hash bytea,
  detector_confidence import_confidence,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  failed_reason_code text,
  counts jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create unique index ux_import_job_idempotency
  on import_job (user_id, input_kind, input_payload_hash, parser_id, selected_scope_hash)
  where input_payload_hash is not null and selected_scope_hash is not null;

create index idx_import_job_user_created
  on import_job (user_id, created_at desc);
```

## import_input_file

```sql
create table import_input_file (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  import_job_id uuid not null references import_job(id),
  original_filename_hash bytea,
  original_extension text,
  mime_type text,
  size_bytes bigint not null,
  sha256 bytea not null,
  object_storage_path text,
  raw_retention_policy text not null default 'store_until_import_complete',
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_import_input_file_user_sha
  on import_input_file (user_id, sha256);

create index idx_import_input_file_job
  on import_input_file (import_job_id);
```

## import_detection_result

```sql
create table import_detection_result (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  import_job_id uuid not null references import_job(id),
  detected_source_id text,
  detected_format text,
  confidence import_confidence not null,
  reasons jsonb not null default '[]'::jsonb,
  parser_candidates text[] not null default '{}',
  requires_user_selection boolean not null default false,
  created_at timestamptz not null default now()
);

create index idx_detection_job
  on import_detection_result (import_job_id);
```

## import_preview

```sql
create table import_preview (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  import_job_id uuid not null references import_job(id),
  source_summary jsonb not null default '{}'::jsonb,
  safety_summary jsonb not null default '{}'::jsonb,
  record_count int not null default 0,
  sensitive_count int not null default 0,
  duplicate_count int not null default 0,
  low_confidence_count int not null default 0,
  created_at timestamptz not null default now(),
  confirmed_at timestamptz,
  cancelled_at timestamptz
);

create unique index ux_import_preview_job
  on import_preview (import_job_id);
```

## import_preview_candidate

```sql
create table import_preview_candidate (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  import_preview_id uuid not null references import_preview(id),
  candidate_index int not null,
  source_id text not null,
  domain text not null,
  title text,
  url text,
  occurred_at timestamptz,
  status text,
  progress jsonb not null default '{}'::jsonb,
  extracted jsonb not null default '{}'::jsonb,
  confidence import_confidence not null,
  selected boolean not null default true,
  privacy_level privacy_level not null default 'owner_only',
  ai_analysis_default ai_analysis_default not null default 'off',
  export_default export_default not null default 'included',
  warnings text[] not null default '{}',
  created_at timestamptz not null default now()
);

create index idx_preview_candidate_preview
  on import_preview_candidate (import_preview_id, candidate_index);

create index idx_preview_candidate_user_sensitive
  on import_preview_candidate (user_id, privacy_level)
  where privacy_level <> 'owner_only';
```

## raw_object_ref

```sql
create table raw_object_ref (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_ref_id uuid references source_ref(id),
  import_job_id uuid references import_job(id),
  sha256 bytea not null,
  object_storage_path text not null,
  size_bytes bigint not null,
  content_type text,
  encrypted boolean not null default true,
  retention_policy text not null,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_raw_object_user_sha
  on raw_object_ref (user_id, sha256);
```

## source_item

One source-level imported record.

```sql
create table source_item (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_ref_id uuid not null references source_ref(id),
  import_job_id uuid references import_job(id),
  source_provider text not null,
  source_native_id text,
  source_native_time timestamptz,
  occurred_at timestamptz,
  captured_at timestamptz,
  imported_at timestamptz not null default now(),
  domain text not null,
  activity_type text,
  title text,
  url text,
  normalized_payload jsonb not null default '{}'::jsonb,
  payload_hash bytea,
  privacy_level privacy_level not null default 'owner_only',
  lifecycle_state lifecycle_state not null default 'active',
  raw_object_ref_id uuid references raw_object_ref(id),
  raw_stored boolean not null default false,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_source_item_user_time
  on source_item (user_id, occurred_at desc nulls last, imported_at desc);

create index idx_source_item_user_source
  on source_item (user_id, source_ref_id, imported_at desc);

create index idx_source_item_active_user_time
  on source_item (user_id, occurred_at desc nulls last)
  where lifecycle_state = 'active';

create index idx_source_item_title_trgm
  on source_item using gin (title gin_trgm_ops)
  where title is not null;
```

## source_item_key

Stores multiple dedupe keys for one source item.

```sql
create table source_item_key (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_item_id uuid not null references source_item(id),
  key_type text not null,
  key_hash bytea not null,
  confidence import_confidence not null,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_source_item_key_user_type_hash
  on source_item_key (user_id, key_type, key_hash)
  where deleted_at is null;

create index idx_source_item_key_item
  on source_item_key (source_item_id);
```

## dedupe_key

Cross-table dedupe registry.

```sql
create table dedupe_key (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  key_scope text not null,
  key_type text not null,
  key_hash bytea not null,
  target_table text not null,
  target_id uuid not null,
  confidence import_confidence not null,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_dedupe_key_active
  on dedupe_key (user_id, key_scope, key_type, key_hash)
  where deleted_at is null;

create index idx_dedupe_key_target
  on dedupe_key (target_table, target_id);
```

## canonical_item

Represents a work/place/show/book/track/restaurant, not a user activity.

```sql
create table canonical_item (
  id uuid primary key,
  item_type text not null,
  canonical_title text not null,
  original_title text,
  creator_names text[] not null default '{}',
  release_year int,
  normalized_title_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_canonical_item_type_title
  on canonical_item (item_type, normalized_title_key);

create index idx_canonical_item_title_trgm
  on canonical_item using gin (canonical_title gin_trgm_ops);
```

## canonical_item_external_id

```sql
create table canonical_item_external_id (
  id uuid primary key,
  canonical_item_id uuid not null references canonical_item(id),
  provider text not null,
  external_id text not null,
  external_url text,
  confidence import_confidence not null default 'high',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_canonical_external_id
  on canonical_item_external_id (provider, external_id)
  where deleted_at is null;

create index idx_canonical_external_item
  on canonical_item_external_id (canonical_item_id);
```

## user_activity

User's interaction with a canonical item.

```sql
create table user_activity (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  canonical_item_id uuid references canonical_item(id),
  domain text not null,
  activity_type text not null,
  status text,
  occurred_at timestamptz,
  period_start timestamptz,
  period_end timestamptz,
  progress jsonb not null default '{}'::jsonb,
  title_snapshot text,
  user_memo text,
  privacy_level privacy_level not null default 'owner_only',
  lifecycle_state lifecycle_state not null default 'active',
  ai_analysis_default ai_analysis_default not null default 'off',
  export_default export_default not null default 'included',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_user_activity_user_time
  on user_activity (user_id, occurred_at desc nulls last, created_at desc);

create index idx_user_activity_active_time
  on user_activity (user_id, occurred_at desc nulls last)
  where lifecycle_state = 'active';

create index idx_user_activity_user_domain
  on user_activity (user_id, domain, activity_type, occurred_at desc nulls last);
```

## user_activity_source_link

```sql
create table user_activity_source_link (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  user_activity_id uuid not null references user_activity(id),
  source_item_id uuid not null references source_item(id),
  link_type text not null default 'evidence',
  confidence import_confidence not null default 'high',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index ux_activity_source_link
  on user_activity_source_link (user_activity_id, source_item_id)
  where deleted_at is null;
```

## memory_record

Human-facing memory unit.

```sql
create table memory_record (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  title text,
  body text,
  summary text,
  memory_kind text not null,
  occurred_at timestamptz,
  period_start timestamptz,
  period_end timestamptz,
  privacy_level privacy_level not null default 'owner_only',
  lifecycle_state lifecycle_state not null default 'active',
  ai_analysis_default ai_analysis_default not null default 'off',
  export_default export_default not null default 'included',
  created_by text not null default 'user',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_memory_user_time
  on memory_record (user_id, occurred_at desc nulls last, created_at desc);

create index idx_memory_active_user_time
  on memory_record (user_id, occurred_at desc nulls last, created_at desc)
  where lifecycle_state = 'active';
```

## memory_source_link

```sql
create table memory_source_link (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  memory_record_id uuid not null references memory_record(id),
  source_item_id uuid references source_item(id),
  user_activity_id uuid references user_activity(id),
  evidence_record_id uuid,
  link_type text not null,
  confidence import_confidence not null default 'high',
  created_at timestamptz not null default now(),
  deleted_at timestamptz,
  check (source_item_id is not null or user_activity_id is not null or evidence_record_id is not null)
);

create index idx_memory_source_memory
  on memory_source_link (memory_record_id);
```

## evidence_record

```sql
create table evidence_record (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_ref_id uuid references source_ref(id),
  source_item_id uuid references source_item(id),
  user_activity_id uuid references user_activity(id),
  evidence_type text not null,
  quote text,
  quote_policy text not null default 'no_quote',
  occurred_at timestamptz,
  privacy_level privacy_level not null default 'owner_only',
  confidence import_confidence not null default 'medium',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_evidence_user_time
  on evidence_record (user_id, occurred_at desc nulls last);
```

## policy_decision

```sql
create table policy_decision (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  target_table text not null,
  target_id uuid not null,
  action text not null,
  decision text not null,
  reasons text[] not null default '{}',
  evaluated_at timestamptz not null default now(),
  policy_version text not null,
  expires_at timestamptz
);

create index idx_policy_target
  on policy_decision (target_table, target_id, evaluated_at desc);
```

## lifecycle_event

```sql
create table lifecycle_event (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  target_table text not null,
  target_id uuid not null,
  from_state lifecycle_state,
  to_state lifecycle_state not null,
  reason text,
  created_by text not null,
  created_at timestamptz not null default now()
);

create index idx_lifecycle_target
  on lifecycle_event (target_table, target_id, created_at desc);
```

## deletion_tombstone

Prevents deleted records from returning through re-import.

```sql
create table deletion_tombstone (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  tombstone_scope text not null,
  key_type text not null,
  key_hash bytea not null,
  target_table text,
  target_id uuid,
  deleted_at timestamptz not null default now(),
  reason text
);

create unique index ux_deletion_tombstone_key
  on deletion_tombstone (user_id, tombstone_scope, key_type, key_hash);
```

## search_document

```sql
create table search_document (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  target_table text not null,
  target_id uuid not null,
  document_type text not null,
  searchable_text text,
  title text,
  occurred_at timestamptz,
  privacy_level privacy_level not null,
  lifecycle_state lifecycle_state not null,
  source_hash bytea not null,
  tsv tsvector,
  created_at timestamptz not null default now(),
  invalidated_at timestamptz
);

create unique index ux_search_document_target
  on search_document (target_table, target_id, document_type)
  where invalidated_at is null;

create index idx_search_document_user_time
  on search_document (user_id, occurred_at desc nulls last)
  where invalidated_at is null and lifecycle_state = 'active';

create index idx_search_document_tsv
  on search_document using gin (tsv)
  where invalidated_at is null and lifecycle_state = 'active';

create index idx_search_document_title_trgm
  on search_document using gin (title gin_trgm_ops)
  where invalidated_at is null and title is not null;
```

## embedding_record

```sql
create table embedding_record (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  target_table text not null,
  target_id uuid not null,
  embedding_provider text not null,
  model_name text not null,
  model_version text,
  input_hash bytea not null,
  vector_store text,
  vector_id text,
  dimensions int,
  privacy_level privacy_level not null,
  lifecycle_state lifecycle_state not null,
  policy_decision_id uuid references policy_decision(id),
  created_at timestamptz not null default now(),
  invalidated_at timestamptz
);

create unique index ux_embedding_target_model_hash
  on embedding_record (target_table, target_id, embedding_provider, model_name, input_hash)
  where invalidated_at is null;

create index idx_embedding_user_target
  on embedding_record (user_id, target_table, target_id)
  where invalidated_at is null;
```

## audit_event

No raw content.

```sql
create table audit_event (
  id uuid primary key,
  user_id uuid references app_user(id),
  event_type text not null,
  target_table text,
  target_id uuid,
  actor_type text not null,
  actor_id_hash bytea,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index idx_audit_user_time
  on audit_event (user_id, created_at desc);

create index idx_audit_type_time
  on audit_event (event_type, created_at desc);
```

## outbox_event

```sql
create table outbox_event (
  id uuid primary key,
  event_type text not null,
  payload jsonb not null,
  status text not null default 'pending',
  attempts int not null default 0,
  next_attempt_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create index idx_outbox_pending
  on outbox_event (status, next_attempt_at)
  where status = 'pending';
```

## cost_ledger_entry

```sql
create table cost_ledger_entry (
  id uuid primary key,
  user_id uuid references app_user(id),
  cost_type text not null,
  source text not null,
  quantity numeric not null,
  unit text not null,
  estimated_cost numeric,
  currency text,
  target_table text,
  target_id uuid,
  created_at timestamptz not null default now()
);

create index idx_cost_user_time
  on cost_ledger_entry (user_id, created_at desc);
```

## Partition Plan

Do not partition immediately unless real volume requires it.

Prepare for future partitioning:

- every large table has time column.
- every user table has user_id.
- dedupe_key handles uniqueness separate from partition constraints.

Candidate partition later:

- source_item by imported_at monthly/yearly.
- audit_event by created_at monthly/yearly.
- cost_ledger_entry by created_at monthly/yearly.
- search_document by created_at or hash(user_id), only when necessary.

## Write Flow

1. create import_job
2. create import_input_file / source_ref
3. security gate
4. detection result
5. preview + candidates
6. user confirms
7. policy decisions
8. upsert source_item with dedupe_key
9. link/create canonical_item
10. create/update user_activity
11. create memory_record only if needed
12. create search_document if eligible
13. create outbox_event for optional enrichment/embedding
14. audit counts only

## Query Flow

### Timeline

- query user_activity and memory_record by user_id + occurred_at
- exclude hidden/sealed/deleted by default

### Search

- query search_document by user_id and active lifecycle
- full-text first
- trigram for typos/title matching
- vector only after enabled and policy-eligible

### Import Preview

- query import_preview_candidate by preview id

### Dedupe

- check dedupe_key before source_item insert
- check deletion_tombstone before preview selection

## Conclusion

This table design separates durable facts, imported source items, user activities, human-facing memories, and derived indexes.

It is more tables than a quick MVP, but fewer than the future system will need.

The design prevents the main long-term failures:

- duplicate imports
- raw storage explosion
- impossible deletion
- search index inconsistency
- embedding cost explosion
- source meaning confusion
- service-specific schema lock-in
