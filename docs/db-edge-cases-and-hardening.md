# Database Edge Cases and Hardening

## 目的

この文書は、DB長期設計に残りうる抜け漏れ・イレギュラーを洗い出し、実装前に追加で潰すためのhardening checklistである。

結論:

現時点のDB設計は強いが、完璧とは言わない。

長期運用で怖いのは、通常ケースではなく以下のようなイレギュラーである。

- 同じサービスを複数アカウントで使う
- 家族/共有プロフィールの履歴が混ざる
- 時刻・タイムゾーン・日付精度が曖昧
- source schemaが変わる
- 削除tombstone自体が個人情報になる
- dedupe keyから元データを推測される
- RLSやservice roleの抜け道
- key rotation / crypto erasure
- raw temporary storageが残る
- API syncが全量再Importになる
- user merge / account delete / backup restoreで整合性が崩れる

## 追加で固定する原則

### 1. Dedupe keys must be privacy-preserving

`dedupe_key.key_hash` や `deletion_tombstone.key_hash` は、単純なSHA-256では不十分な場合がある。

理由:

- title/date/URLの組み合わせは辞書攻撃で推測できる。
- private bookmarkやLINE snippetのhashは、それ自体がsensitiveな存在証明になりうる。

方針:

- sensitive dedupe keyはHMAC-SHA-256を使う。
- key materialはDBに置かない。
- key_versionを持つ。
- rotation時に旧keyで照合し、新keyへ再発行できる設計にする。

```sql
alter table dedupe_key
  add column key_version text,
  add column key_algorithm text not null default 'hmac_sha256';

alter table deletion_tombstone
  add column key_version text,
  add column key_algorithm text not null default 'hmac_sha256';
```

### 2. Tombstones must not become a privacy leak

削除済みを復活させないためのtombstoneは必要。

ただし、tombstoneが「このユーザーはこのprivate URL/作品/会話を持っていた」という漏えいになってはいけない。

Rules:

- tombstone stores HMAC key only, not clear text.
- tombstone scope is coarse enough to avoid revealing content.
- tombstone reason uses controlled enum, not free raw text.
- audit logs reference tombstone id only.
- account deletion may require tombstone minimization or crypto-erasure strategy.

### 3. Time uncertainty is first-class

Import sourceの時刻はよく曖昧である。

Examples:

- Netflix CSV has date but not precise time.
- Letterboxd may have watched date but no time.
- Manual entry may have only month/year.
- Spotify has precise played_at.
- LINE has timestamp but timezone/export format may vary.
- 食べログ visit date may be user memory, not source fact.

Add fields:

```sql
alter table source_item
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;

alter table user_activity
  add column occurred_at_precision text not null default 'unknown',
  add column timezone text,
  add column timezone_source text;
```

Allowed precision:

```ts
type TimePrecision =
  | 'exact_timestamp'
  | 'date'
  | 'month'
  | 'year'
  | 'period'
  | 'unknown';
```

Dedupe must use precision-aware buckets.

Do not treat `2026-07-07 date` and `2026-07-07T23:51:00+09:00` as equal without confidence rules.

### 4. Source account identity must be explicit

Same provider may have multiple accounts/profiles.

Examples:

- Netflix profile A/B
- Spotify personal/work/family
- Apple Music family account
- X main/sub account
- LINE account migration
- YouTube brand account

Add:

```sql
create table source_account_ref (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  provider text not null,
  account_label text,
  external_account_hash bytea,
  profile_label_hash bytea,
  key_version text,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_source_account_user_provider
  on source_account_ref (user_id, provider);
```

Then `source_ref` should reference `source_account_ref_id` where available.

### 5. Shared profile contamination must be visible

Shared/family profiles are common.

Rules:

- import preview shows `shared profile可能性` warning.
- source_account_ref can be marked `shared_or_unknown`.
- shared_or_unknown imports default to owner_sensitive.
- dedupe confidence is lowered for shared profiles.
- AI should not infer user's taste/personality from shared profile imports.

### 6. Parser/schema versioning is mandatory

External services change formats.

Every parsed record must know:

- adapter_id
- adapter_version
- parser_id
- parser_version
- source_schema_version if known
- detection_signature

Add to source_item:

```sql
alter table source_item
  add column adapter_id text,
  add column adapter_version text,
  add column parser_id text,
  add column parser_version text,
  add column source_schema_version text;
```

Why:

- old parse bugs can be reprocessed.
- service export format changes can be detected.
- migrations can know which rows are affected.

### 7. Schema drift must stop automatic import

If a CSV/JSON/ZIP manifest suddenly changes:

- do not silently parse incorrectly.
- downgrade confidence.
- show preview warning.
- require user confirmation or parser update.

Examples:

- Netflix changes column names.
- X archive changes folder structure.
- LINE export timestamp format changes.
- Browser bookmark export contains extra active content.

### 8. RLS is defense in depth, not the only wall

PostgreSQL Row Level Security can restrict which rows are visible/modifiable per user, but by default tables have no policies, and table owners/superusers can bypass unless designed carefully. Therefore RLS is useful but not sufficient alone.

Rules:

- enable RLS on user data tables.
- use FORCE ROW LEVEL SECURITY where appropriate.
- avoid app runtime connecting as table owner.
- separate migration/admin roles from app roles.
- test RLS with negative tests.
- do not rely on RLS for backup/export filtering alone.

### 9. Referential integrity can leak existence

Foreign keys and unique constraints can leak existence by error behavior.

Rules:

- public-facing errors must be generic.
- dedupe conflict errors should not expose target title/source.
- user-scoped keys must always include user_id.
- avoid cross-user unique constraints on sensitive external IDs unless provider data is public and safe.

### 10. Key management needs its own model

Encryption keys and HMAC keys must not be normal DB config.

Minimum key classes:

```ts
type KeyPurpose =
  | 'raw_object_encryption'
  | 'dedupe_hmac'
  | 'tombstone_hmac'
  | 'oauth_token_encryption'
  | 'export_package_encryption';
```

Required metadata:

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

This table stores references only, not key material.

### 11. Crypto-erasure must be planned

For highly sensitive raw/object data, deleting the encryption key can be part of deletion.

But crypto-erasure is dangerous if used accidentally.

Rules:

- key deletion is separate high-risk ceremony.
- raw_object_ref must know key_reference_id.
- backup must not retain unwrapped keys.
- export packages have separate short-lived keys.

### 12. Account deletion differs from record deletion

Record deletion:

- may keep privacy-preserving tombstone to prevent resurrection.

Account deletion:

- user may expect no recoverable personal data.
- tombstones must be minimized, anonymized, or crypto-erased depending policy/legal requirements.

Need separate states:

```ts
type AccountDeletionMode =
  | 'delete_records_keep_nonreversible_tombstones'
  | 'full_erasure_with_no_reimport_guard'
  | 'legal_hold_restricted';
```

This needs legal/product decision before production.

### 13. Multi-device/offline conflict is future risk

If local-first is added:

- two devices can import overlapping data offline.
- same manual memory can be edited on two devices.
- one device can delete while another imports.

Rules:

- use UUID IDs.
- use event/lifecycle model.
- deletion wins over re-import by default.
- merge conflicts go to user-visible conflict state.

### 14. Backfills must be reversible

Schema changes will happen.

Rules:

- never backfill by overwriting original source_item fields without preserving previous value.
- large backfills chunked.
- backfill version recorded.
- search/embedding rebuilt after backfill only if policy eligible.

### 15. Low-confidence matches must not silently affect search

If dedupe/entity resolution is medium/low confidence:

- do not merge.
- do not show as same item in primary timeline without marking.
- do not use it to remove records.
- use candidate UI.

### 16. Internationalization and aliases are first-class

Japanese/English titles, half-width/full-width, punctuation, emojis, sequels, seasons, translations all cause false matches.

Rules:

- store original title.
- store normalized title key.
- store aliases separately.
- domain-specific matching required.
- canonical item merge must be undoable.

### 17. Location precision must be controlled

Food/place imports can expose life patterns.

Rules:

- restaurant URL is less sensitive than visit timestamp + companion.
- precise location/time combinations default owner_sensitive.
- location timeline is not generated by default.
- no relationship/location pattern inference.

### 18. Large import blast radius is limited

If user uploads huge Takeout/archive:

- create preview only.
- paginate candidates.
- do not create search docs until confirmed.
- do not embed.
- apply per-import max candidate count.
- allow cancel/delete import job and temp raw.

### 19. AI extraction is optional, not required for DB correctness

The database must work without LLM.

LLM can help classify/summarize later, but:

- deterministic parser first.
- sourceRef first.
- user correction before save.
- LLM output stored as interpretation/derived summary, not fact.

### 20. Production-readiness test must include restore

DB design is incomplete without restore tests.

Minimum restore drill:

1. create records.
2. delete some records.
3. create tombstones.
4. create search docs/embeddings.
5. backup.
6. restore to staging.
7. replay tombstones.
8. verify deleted records not searchable/exportable.

## Additional Tables / Columns Summary

Add before production:

```txt
source_account_ref
key_reference
entity_match_candidate
merge_decision
canonical_item_alias
```

Add to existing tables:

```txt
key_algorithm
key_version
occurred_at_precision
timezone
timezone_source
adapter_id
adapter_version
parser_id
parser_version
source_schema_version
source_account_ref_id
```

## Red Team Edge Cases

1. Same Netflix CSV imported 10 times.
2. Same Netflix CSV imported with different selected scope.
3. X archive imported, then account deleted, then old archive imported again.
4. LINE snippet deleted, then same chat export imported again.
5. Spotify and Last.fm disagree by 20 seconds.
6. Same movie title exists in two years.
7. Same restaurant chain different branch.
8. Family Netflix profile includes spouse/child viewing.
9. User imports private bookmarks with explicit titles.
10. User changes timezone after import.
11. Parser bug misreads dates, later fixed.
12. HMAC key rotation occurs after millions of dedupe keys.
13. Backup restore brings back old search_document rows.
14. API token compromised; source revoked.
15. External service changes export schema.
16. User wants full account deletion, but tombstones remain.
17. Multi-device offline import overlaps with deletion.
18. Large Takeout contains millions of items.
19. Import Preview is cancelled; temp raw must expire.
20. Search index exists for a sealed item.

## Conclusion

The current DB architecture is strong, but production-grade hardening requires these additional constraints.

The most important missing hardening items are:

```txt
HMAC dedupe/tombstone keys
source_account_ref
key_reference
parser/schema versioning
occurred_at_precision and timezone_source
RLS policy tests
shared profile contamination handling
restore drill with tombstone replay
large import blast-radius limits
```

With these, the design becomes much closer to production-ready for decades-long Memory OS operation.
