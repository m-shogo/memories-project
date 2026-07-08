# Fable Review and DB Hardening Addendum

## 目的

この文書は、Fable / Codex / Claude Code などの実装エージェントに渡す前の最終レビュー用addendumである。

今回の目的は **実装ではない**。

目的は、Memory OS の設計をいきなりコード化した時に破綻しやすい場所を先に固定し、特にDB周りを実装可能な契約へ近づけること。

## Review Verdict

```txt
ready_for_fable_review_with_db_contract_corrections
```

`ready` ではない。

理由:

- Product philosophy / privacy / import safety / healthy attachment boundary はかなり強い。
- DB long-term architecture も方向性は強い。
- ただし、古い概念モデルと新しいDB設計の間に名前・責務・DDL detailのズレが残っている。
- このズレをそのまま実装すると、migration・RLS・delete・dedupe・exportで事故る。

## Reviewed Docs

主に以下を前提としてレビューする。

```txt
README.md
docs/memory-data-model.md
docs/import-export-strategy.md
docs/import-security-checklist.md
docs/privacy-and-ethics.md
docs/product-boundaries.md
docs/mvp-roadmap.md
docs/next-chat-handoff.md
docs/db-long-term-architecture.md
docs/db-table-design-v1.md
docs/db-edge-cases-and-hardening.md
docs/db-implementation-preflight-checklist.md
docs/first-migration-slice-plan.md
docs/rls-policy-and-negative-tests.md
docs/token-encryption-and-oauth-security.md
docs/policy-test-cases.md
docs/policy-test-cases-media-persona.md
docs/schema-api-and-export-version-governance.md
```

## Good Parts Already Strong

### Product / Philosophy

- ChatGPT代替ではない。
- Character.AI化しない。
- 故人・親・妻・恋人・AIキャラ本人として話さない。
- AIは人生を評価しない。
- 保存時に分析しすぎない。
- 小さな記録を捨てない。
- 大きなイベントを押し付けない。
- 記憶は本人を固定するものではなく、時期ごとの文脈として扱う。

### Import / Safety

- Import Preview mandatory は正しい。
- Rawをすぐ全文解析しない方針は正しい。
- ZIP / HTML / CSV / Image / PDF の安全方針はよい。
- Prompt injectionを外部データとして扱う方針はよい。
- LINE / DM / Gmail / 画像 / persona-like data を後回しまたは制限対象にしているのは正しい。

### DB Architecture

- PostgreSQLをsystem of recordにする方針は正しい。
- raw本体をDB本文に入れずobject storageへ逃がす方針は正しい。
- `source_item` / `user_activity` / `memory_record` を分ける方針は正しい。
- `search_document` / `embedding_record` を派生データ扱いにする方針は正しい。
- `dedupe_key` / `deletion_tombstone` を初期から設計しているのは非常に重要。
- First migrationをPreview-firstに切る判断は正しい。

## Main Risk: Concept Model and Physical DB Drift

`docs/memory-data-model.md` は初期概念モデルとして有用だが、今後の実装時は `docs/db-table-design-v1.md` とこのaddendumを優先する。

理由:

- `MemoryCandidate.importance` は「AIが重要度を決めない」という思想と衝突しやすい。
- `privacyLevel: normal/sensitive/very_sensitive` と `privacy_level: owner_only/owner_sensitive/restricted` が混在している。
- `SourceRef` / `RawRecord` / `MemoryCandidate` / `Memory` だけで実装すると、dedupe・tombstone・policy・RLS・export eligibility が不足する。

### Correction Rule

```txt
Concept docs are explanatory.
DB docs are implementation contracts.
If there is a conflict, use db-table-design-v1 + this addendum + first-migration-slice-plan.
```

## P0 Corrections Before DB Implementation

### P0-DB-001: Unify privacy terminology

Do not implement two privacy systems.

Canonical physical enum:

```txt
privacy_level:
- owner_only
- owner_sensitive
- restricted
```

Conceptual mapping:

```txt
normal          -> owner_only
sensitive       -> owner_sensitive
very_sensitive  -> restricted
```

Rules:

- UI may use Japanese labels.
- DB must use one enum vocabulary.
- Export / Search / Tip / AI eligibility must read from the same physical privacy field.

### P0-DB-002: MemoryCandidate importance must not become AI life score

Do not implement user-visible `importance` as AI judgment.

Replace or interpret it as:

```txt
candidate_review_priority
```

Allowed use:

- sorting review queue
- flagging risky/high-impact candidate for explicit confirmation
- estimating future reference usefulness

Forbidden use:

- life score
- person score
- relationship score
- AI deciding what matters in user's life
- hiding low-score memories by default

### P0-DB-003: `source_account_ref` must be first-class in DDL

The first migration slice already references `source_account_ref`, but `db-table-design-v1` must treat it as mandatory foundation.

Required table:

```sql
create table source_account_ref (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  provider text not null,
  account_label_hash bytea,
  external_account_hash bytea,
  profile_label_hash bytea,
  shared_or_unknown boolean not null default false,
  key_algorithm text not null default 'hmac_sha256',
  key_version text,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_source_account_ref_user_provider
  on source_account_ref (user_id, provider);
```

Required FK additions:

```sql
alter table source_ref
  add column source_account_ref_id uuid references source_account_ref(id);

alter table source_item
  add column source_account_ref_id uuid references source_account_ref(id);
```

Rules:

- Netflix profile, Spotify account, X sub account, LINE migrated account, YouTube brand account must not collapse into one user identity.
- Shared/family profile imports default to `owner_sensitive`.
- Shared/family profile imports must not drive personality/taste inference without explicit user confirmation.

### P0-DB-004: Dedupe and tombstone keys need algorithm + key version

`dedupe_key` and `deletion_tombstone` must never rely on plain SHA for sensitive title/url/snippet keys.

Required columns:

```sql
alter table dedupe_key
  add column key_algorithm text not null default 'hmac_sha256',
  add column key_version text;

alter table deletion_tombstone
  add column key_algorithm text not null default 'hmac_sha256',
  add column key_version text;
```

Rules:

- Sensitive keys use HMAC.
- Key material is never stored in DB.
- key rotation can check old keys and issue new keys.
- Low confidence keys cannot auto-merge.
- Tombstones must not expose deleted content by error message, admin UI, or audit metadata.

### P0-DB-005: `key_reference` must exist before token/raw/export encryption shortcuts

Required table:

```sql
create table key_reference (
  id uuid primary key,
  purpose text not null,
  key_version text not null,
  kms_key_id text not null,
  status text not null,
  created_at timestamptz not null default now(),
  retired_at timestamptz
);
```

Minimum purposes:

```txt
raw_object_encryption
dedupe_hmac
tombstone_hmac
oauth_token_encryption
export_package_encryption
```

Required additions:

```sql
alter table raw_object_ref
  add column key_reference_id uuid references key_reference(id);
```

Rules:

- `key_reference` stores references only, not key material.
- raw object encryption, OAuth token encryption, HMAC, and export encryption must not reuse one generic key.
- crypto-erasure is a high-risk ceremony, not a normal delete path.

### P0-DB-006: OAuth connection table must be defined before API connector work

No API connector work until token storage is designed.

Required table:

```sql
create table oauth_connection (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_account_ref_id uuid references source_account_ref(id),
  provider text not null,
  scope_set text[] not null default '{}',
  token_ciphertext bytea not null,
  token_nonce bytea not null,
  token_tag bytea not null,
  token_encryption_key_ref uuid not null references key_reference(id),
  status text not null default 'active',
  granted_at timestamptz,
  refreshed_at timestamptz,
  revoked_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now()
);

create index idx_oauth_connection_user_provider
  on oauth_connection (user_id, provider, status);
```

Rules:

- Plain token storage is a hard blocker.
- Revoked connections cannot sync.
- Scope changes require new provider review.
- Audit must record provider/scope/counts, not token or private payload.

### P0-DB-007: Time precision is a first-class field

Required additions:

```sql
alter table import_preview_candidate
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;

alter table source_item
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;

alter table user_activity
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;

alter table memory_record
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;
```

Allowed precision:

```txt
exact_timestamp
date
month
year
period
unknown
```

Rules:

- Netflix date-only and Spotify exact timestamp are not equal by default.
- Manual memories can be year/month/period only.
- Dedupe buckets must use precision-aware matching.
- UI should show uncertainty instead of pretending exactness.

### P0-DB-008: Parser / adapter / source schema version must be stored on committed source items

Required additions:

```sql
alter table source_item
  add column adapter_id text,
  add column adapter_version text,
  add column parser_id text,
  add column parser_version text,
  add column source_schema_version text,
  add column detection_signature text;
```

Rules:

- Parser bug fixes must be traceable.
- Backfill must know which rows were parsed by old logic.
- Schema drift must downgrade confidence and require preview warning.
- Do not silently parse changed CSV/JSON/ZIP formats.

### P0-DB-009: Import idempotency cannot depend on nullable parser fields

Current idempotency shape is good, but implementation must avoid nullable uniqueness holes.

Risk:

```sql
unique (user_id, input_kind, input_payload_hash, parser_id, selected_scope_hash)
```

If `parser_id` is null, PostgreSQL unique constraints allow multiple nulls.

Fix options:

```txt
Option A: parser_id is required before idempotency key is written.
Option B: use generated/coalesced idempotency_key_hash.
Option C: partial unique indexes per import stage.
```

Recommended:

```txt
Create a deterministic import_idempotency_key_hash after detector/parser selection.
Use unique(user_id, import_idempotency_key_hash).
```

### P0-DB-010: `canonical_item` must not leak private user-specific items

`canonical_item` can be global only for public works/places/providers.

Risk:

- private manual title becomes global canonical item
- private restaurant/home/work/place becomes globally matchable
- cross-user existence leak via unique constraints or admin UI

Correction options:

```txt
Option A: canonical_item has visibility_scope = public | user_private
          and owner_user_id nullable.

Option B: split public_canonical_item and user_private_item.
```

Minimum rule:

```sql
alter table canonical_item
  add column visibility_scope text not null default 'public',
  add column owner_user_id uuid references app_user(id);
```

Rules:

- `visibility_scope='public'` rows must never include private imported titles/snippets.
- `visibility_scope='user_private'` rows must include owner_user_id.
- Cross-user unique constraints only apply to public safe external IDs.

### P0-DB-011: Lifecycle must be enforced consistently across derived data

For every target table with lifecycle:

```txt
active -> searchable/exportable/tippable if policy allows
hidden -> not shown in normal UI / no Tip / no proactive surfacing
sealed -> no search/Tip/export by default / explicit user action only
deleted -> excluded everywhere / tombstone blocks resurrection
pending_delete -> hidden immediately; async delete finalizes
```

Required derived invalidation triggers/jobs:

```txt
privacy_level changed
lifecycle_state changed
policy_decision changed
deleted_at set
source account revoked
raw object expired
memory body/summary changed
```

Invalidate:

```txt
search_document
embedding_record
derived_summary
Tip cache
export staging
recommendation cache
```

### P0-DB-012: Audit and outbox payloads need raw-content guardrails

`audit_event.metadata` and `outbox_event.payload` are JSONB risk zones.

Rules:

- no raw title for private/restricted imports
- no snippets
- no URL with tokens
- no OAuth token fragments
- no exact private filename
- no full user text
- no EXIF/GPS raw
- use counts, ids, reason codes, policy versions

Recommended review invariant:

```txt
Any JSONB field that can reach logs/queue/admin UI must pass SafeMetadataGuard.
```

### P0-DB-013: Account deletion mode must be a product/legal decision before production

Do not hide this under normal delete.

Required decision:

```txt
delete_records_keep_nonreversible_tombstones
full_erasure_with_no_reimport_guard
legal_hold_restricted
```

Rules:

- Record deletion can keep privacy-preserving tombstones.
- Full account deletion may require tombstone minimization or crypto-erasure.
- Backup restore must not resurrect deleted records.
- Export packages must be revoked/expired on account deletion.

### P0-DB-014: Safe Commit contract must be explicit

A row may move from preview to committed domain only if all are true:

```txt
Import Preview exists
User confirmed selected scope
Policy decision exists and allows commit
Dedupe checked
Tombstone checked
Raw retention decided
Privacy level assigned
AI analysis default assigned
Export default assigned
Lifecycle state assigned
Audit count written
No hard-block warning remains
```

Hard block examples:

```txt
secret/API key/private key detected
path traversal/archive bomb risk
unsafe active content
persona activation request
relationship state creation request
plain OAuth token storage
unknown high-risk parser schema drift
missing current_user_id
```

## First Migration Contract After This Review

First DB migration may create only foundation tables.

Create:

```txt
app_user
source_account_ref
source_ref
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
export_package
persona_agent
relationship_state
```

Exception:

- If implementation needs a tiny local fixture table for testing, it must not be production domain state.

## Fable Review Output Format

Fable should not simply say "looks good".

Ask Fable to output:

```txt
1. Verdict: ready / ready_with_known_risks / blocked
2. P0 blockers before implementation
3. P1 fixes before production
4. P2 future improvements
5. DB schema contradictions
6. RLS bypass possibilities
7. Deletion/re-import resurrection paths
8. Dedupe false positive / false negative risks
9. Raw data / JSONB / queue / audit leakage risks
10. Export/re-import safety risks
11. Concrete doc changes or migration contract changes
```

## Fable Red Team Questions

Use these as mandatory review questions.

### DB / RLS

1. Can user B read any row that belongs to user A?
2. Can missing `app.current_user_id` accidentally read rows?
3. Can app runtime role bypass RLS by being table owner?
4. Can support/admin read private raw/title/snippet by default?
5. Can a foreign key or unique constraint leak another user's private item existence?

### Dedupe / Tombstone

6. Can deleting an item and re-importing the same archive resurrect it?
7. Can tombstone hashes be dictionary-attacked?
8. Can sensitive dedupe keys be generated with plain SHA?
9. Can low-confidence dedupe silently merge two different works/restaurants/people?
10. Can key rotation make old dedupe/tombstone keys unusable?

### Import

11. Can import skip preview and commit directly?
12. Can parser schema drift silently produce wrong rows?
13. Can huge imports create millions of candidates/search docs/embeddings?
14. Can private bookmark/LINE/Gmail titles leak into logs?
15. Can a shared Netflix/Spotify profile become a personality inference about the user?

### Search / Embedding / Tip

16. Can hidden/sealed/deleted data appear in search?
17. Can sealed data appear in Tip/notification?
18. Can embedding remain after deletion or privacy change?
19. Can vector DB become source of truth?
20. Can AI summary be treated as fact rather than interpretation?

### Export / Re-import

21. Can export include raw/media/persona-like data by default?
22. Can export package live forever?
23. Can re-import bypass tombstone/policy?
24. Can old export schema be imported without version migration?
25. Can deleted data return after backup restore?

### Product Safety

26. Can a persona/relationship table be introduced accidentally?
27. Can AI generate "wife/father/deceased would say" as direct speech?
28. Can memory importance become a life/personality score?
29. Can streak/guilt/loneliness copy appear in notifications?
30. Can sensitive surprise reveal happen in weekly/monthly rituals?

## Additional Review: Visible Motivation vs Safety

Recent docs correctly move toward visible reward loops: shelf, map, box, timeline, weekly ritual.

But safety rule:

```txt
Visible reward must show structure and progress, not private interpretation surprise.
```

Allowed:

- shelf created
- count increased
- timeline slot filled
- source link connected
- export readiness improved
- duplicate cleaned
- empty slot suggestion

Forbidden:

- "Your marriage pattern changed"
- "You seem depressed again"
- "Your wife is probably..."
- "You abandoned this dream"
- guilt/streak/loneliness pressure
- private relationship analysis as surprise Tip

## Implementation Priority After Fable Review

If still not implementing:

```txt
1. Update db-table-design-v1 with P0 corrections from this addendum.
2. Produce migration-001-foundation-contract.md.
3. Produce RLS policy matrix for first-slice tables.
4. Produce SafeMetadataGuard spec for audit/outbox/log JSONB.
5. Produce account deletion mode decision memo.
```

If implementing after review:

```txt
1. Synthetic fixtures.
2. Migration 001 foundation only.
3. RLS policies + negative tests.
4. SafeMetadataGuard.
5. SecurityGate v0.
6. ParserRegistry v0.
7. Import Preview DTO + UI fixture.
8. Dedupe/Tombstone check in preview.
9. No Safe Commit until policy and preview are proven.
```

## Final Decision Locks

These are locked unless explicitly revised by a later architecture decision record.

```txt
PostgreSQL is system of record.
Object storage holds raw/archive/media.
Raw is not product.
Import Preview is mandatory.
Policy runs before commit.
Dedupe and Tombstone exist before real save.
Search and Embedding are derived.
Embedding is lazy/budgeted.
Vector DB is not source of truth.
RLS negative tests are P0.
Admin/support raw access is denied by default.
No persona_agent table.
No relationship_state table.
No direct import-to-memory save.
No one-table JSON memories design.
No unversioned export.
No full raw/media export by default.
```

## Conclusion

設計思想はかなり強い。

破綻しそうな場所は、思想ではなく **実装境界** にある。

特に危険なのは以下。

```txt
概念モデルとDDLのズレ
privacy enum混在
source account/profile混同
HMACなしdedupe/tombstone
key_referenceなし暗号化
nullable idempotency
private canonical itemのglobal化
時刻精度なしdedupe
JSONB audit/outbox raw leakage
削除後re-import復活
hidden/sealed/deletedの派生index残留
```

このaddendumをFableに読ませて、P0指摘が潰れるまで実装に入らない。
