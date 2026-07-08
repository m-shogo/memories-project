# Migration 001 Foundation Contract

## 目的

この文書は、Memory OSの最初のDB migrationが**何を作ってよく、何を作ってはならないか**を固定する実装契約である。

実装エージェントは、この契約と `docs/db-table-design-v1.md` に反しないmigrationのみを書くことができる。

この文書自体はmigrationではない。SQL/ORMファイルの生成はこの契約の承認後に行う。

## Contract Precedence

```txt
1. this doc
2. docs/db-table-design-v1.md
3. docs/fable-review-and-db-hardening-addendum.md
4. docs/first-migration-slice-plan.md
```

矛盾があればこの文書が勝つ。矛盾を見つけたら実装を止め、docsを直す。

## Allowed Tables (exactly these 17)

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

DDLは `docs/db-table-design-v1.md` の各テーブル定義(v1.1修正済み)に従う。

## Forbidden Tables in Migration 001

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
cost_ledger_entry
entity_match_candidate
merge_decision
persona_agent          (permanently forbidden)
relationship_state     (permanently forbidden)
```

- `persona_agent` / `relationship_state` はslice判断ではなく、プロダクト境界として永久に禁止。
- `cost_ledger_entry` はmigration 001に含めない。ただし、embedding / LLM / media / API sync等のimport-heavy pathを実装するsliceでは、その同じsliceで先に作る(cost ledgerなしでimport-heavy pathを出荷することは禁止)。
- テスト用のローカルfixtureテーブルが必要な場合は、production domain stateにしないこと。

## Required Column Contracts

実装エージェントが省略しやすい箇所。省略はP0違反。

### import_job

- `import_idempotency_key_hash bytea` + `unique(user_id, import_idempotency_key_hash) where not null`。
- nullable複合unique(`input_payload_hash` 等の組)をidempotencyの唯一の根拠にしない。
- detector/parser確定後にhashを書き込むまでSafe Commit不可。

### import_preview_candidate

- `occurred_at_precision`(default `'unknown'`)、`timezone`、`timezone_source`。
- `title` / `url` / `extracted` はSafeMetadataGuard対象。log/audit/outboxへ出さない。
- cancelled/failed job候補のTTL削除方針をコメントで明記。

### dedupe_key / deletion_tombstone

- `key_algorithm text not null default 'hmac_sha256'`
- `key_version text not null`
- tombstoneの理由は `reason_code`(管理語彙)。自由記述禁止。

### source_account_ref

- `shared_or_unknown boolean not null default false`
- account/profile識別子はHMAC hashカラムのみ(`account_label_hash` / `external_account_hash` / `profile_label_hash`)。平文カラム禁止。

### source_ref

- `source_account_ref_id uuid references source_account_ref(id)`。
- 平文の外部アカウント識別子カラムを持たない。

### raw_object_ref

- `key_reference_id uuid references key_reference(id)`
- `retention_policy not null` + `expires_at`。TTLなしのraw参照を作らない。
- DB内にraw本文カラム(text/bytea本文)を作らない。object storage pathとhashのみ。

### key_reference

- KMS参照のみ。key material・秘密値のカラムを作らない。
- `unique(purpose, key_version)`。

### oauth_connection

- `token_ciphertext` / `token_nonce` / `token_encryption_key_ref not null`。
- 平文token・平文refresh tokenのカラムを作らない。
- `revoked_at` / `deleted_at` 必須。

### audit_event / outbox_event

- raw本文カラムなし。`metadata` / `payload` jsonbはSafeMetadataGuard前提。
- outboxの処理済み行に保持期限を設ける前提の`processed_at`。

## RLS / Role Matrix for Migration 001

migration 001は、テーブル作成と同時にRLSを有効化しなければならない。「後でRLSを足す」は禁止。

| table | RLS | policy | notes |
|---|---|---|---|
| app_user | enable + force | `id = app_current_user_id()` | |
| source_account_ref | enable + force | user_id isolation | |
| source_ref | enable + force | user_id isolation | |
| import_job | enable + force | user_id isolation | |
| import_input_file | enable + force | user_id isolation | |
| import_detection_result | enable + force | user_id isolation | |
| import_preview | enable + force | user_id isolation | |
| import_preview_candidate | enable + force | user_id isolation | |
| raw_object_ref | enable + force | user_id isolation | |
| dedupe_key | enable + force | user_id isolation | |
| deletion_tombstone | enable + force | user_id isolation | |
| policy_decision | enable + force | user_id isolation | |
| lifecycle_event | enable + force | user_id isolation | |
| audit_event | enable + force | user_id isolation (insert: app/worker) | user_id nullable行はsystem eventのみ、管理role限定 |
| outbox_event | enable + force | worker roleのみ read/update | user非公開。payloadはSafeMetadataGuard済み前提 |
| key_reference | enable + force | 管理role限定。app roleはselect(id, purpose, key_version, status)相当の最小権限 | user_idなしglobal表 |
| oauth_connection | enable + force | user_id isolation。ciphertext列はapp roleに直接返さない設計を推奨 | |

Role rules:

- `memory_migration_role` がowner。`memory_app_role` / `memory_worker_role` はownerではない。
- `app_current_user_id()` helper(`docs/rls-policy-and-negative-tests.md`)を使う。NULL時はfail closed。
- RLS negative tests RLS-001〜RLS-010がmigration 001と同じPRで存在しなければならない。

## Validation After Migration 001

```sql
-- forbidden tables must not exist
select count(*) = 0 from information_schema.tables
 where table_name in ('source_item','memory_record','search_document',
                      'embedding_record','persona_agent','relationship_state');

-- RLS enabled on all 17 tables
select relname from pg_class
 where relname in ('app_user','source_account_ref','source_ref','import_job',
   'import_input_file','import_detection_result','import_preview',
   'import_preview_candidate','raw_object_ref','dedupe_key','deletion_tombstone',
   'policy_decision','lifecycle_event','audit_event','outbox_event',
   'key_reference','oauth_connection')
   and (relrowsecurity = false or relforcerowsecurity = false);
-- expected: zero rows

-- key/version contracts
select count(*) from dedupe_key where key_version is null;
select count(*) from deletion_tombstone where key_version is null;
select count(*) from oauth_connection where token_encryption_key_ref is null;
```

## Explicit "Do Not Implement Yet" Guardrails

migration 001の時点で、以下は実装禁止(docs onlyの状態を維持):

- parser / adapter本体
- OAuth connector本体(テーブルは作るがconnectorコードは別ゲート)
- embedding / vector store
- export package生成
- search projection
- Tip / notification生成

## Go Criteria

migration 001実装を開始してよい条件:

- この契約が承認されている。
- `docs/db-migration-safety-checklist.md` を満たす計画がある。
- RLS negative testsが同時に書かれる。
- SafeMetadataGuard spec(`docs/safe-metadata-guard-spec.md`)が存在する。
- account deletion mode決定(`docs/account-deletion-and-tombstone-decision.md`)が存在する。

## 結論

migration 001は「記憶を保存する」migrationではない。「安全に保存できる状態を作る」migrationである。

この契約から外れたmigrationはrevert対象。
