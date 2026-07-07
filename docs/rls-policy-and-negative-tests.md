# RLS Policy and Negative Tests

## 目的

この文書は、Memory OS のDB実装前に、PostgreSQL Row Level Security / application role / admin role / negative tests の設計を固定する。

Memory OSのDBは、人生文脈・LINE・視聴履歴・趣味・場所・家族・private bookmark・Export staging・OAuth token metadataを扱う。

そのため、アプリケーションコードだけで user_id filter を守る設計では足りない。

ただし、RLSだけを唯一の壁にもしない。

## 最上位原則

### 1. RLS is defense in depth

RLSは重要だが、唯一の防御ではない。

必須の防御層:

- application-level user authorization
- database RLS
- service role separation
- policy engine
- audit without raw
- export/re-auth gates
- encryption/key management

### 2. App runtime role must not be table owner

app runtime DB role が table owner だと、RLSの期待が崩れる。

方針:

- migration role: DDL専用
- app role: runtime query専用
- worker role: background job専用。必要最小権限
- support/admin role: raw不可・restricted access
- read-only analytics role: aggregate only, no raw/private title

### 3. All user data tables carry user_id

RLS policyの基本は `user_id = current_setting('app.current_user_id')::uuid`。

user_idがないcross-user tableは原則作らない。

例外:

- public catalog tables: canonical_item, canonical_item_external_id
- key_reference: key materialなし、管理role限定
- system config tables

### 4. No raw through support/admin

support/adminは、ユーザー本人ではない。

管理者がrawを見る運用は作らない。

必要なreviewは counts / ids / risk reasons / policy ids で行う。

## Session Context

App must set user context per transaction/request.

Example:

```sql
select set_config('app.current_user_id', '<uuid>', true);
select set_config('app.current_actor_type', 'user', true);
select set_config('app.current_request_id', '<request-id>', true);
```

Rules:

- use local transaction setting where possible.
- clear context after request.
- connection pool must not leak previous user context.
- tests must simulate context leakage.

## Role Model

```txt
memory_migration_role
memory_app_role
memory_worker_role
memory_support_role
memory_analytics_role
memory_readonly_debug_role
```

### memory_migration_role

Allowed:

- DDL
- migrations
- constraints/indexes

Not used by runtime.

### memory_app_role

Allowed:

- user-scoped CRUD through RLS
- no raw object direct access
- no key material
- no table ownership

### memory_worker_role

Allowed:

- background jobs scoped by job user_id
- import parser writes
- search projection writes
- raw expiration by object refs

Must respect lifecycle/policy.

### memory_support_role

Allowed:

- no raw
- no private titles
- support diagnostics
- policy reason codes
- import job counts

Denied:

- raw LINE/DM
- raw bookmarks
- tokens
- private URLs
- sealed content

### memory_analytics_role

Allowed:

- aggregate counts only
- no user-level content
- no raw
- no private title

## RLS Policy Template

For user-owned tables:

```sql
alter table source_item enable row level security;

create policy source_item_user_isolation
  on source_item
  for all
  using (user_id = current_setting('app.current_user_id', true)::uuid)
  with check (user_id = current_setting('app.current_user_id', true)::uuid);
```

Caution:

- `current_setting(..., true)` may return null. Queries must fail closed.
- policy helper function can make behavior explicit.

Example helper:

```sql
create function app_current_user_id() returns uuid
language sql stable as $$
  select nullif(current_setting('app.current_user_id', true), '')::uuid;
$$;
```

Policy:

```sql
using (user_id = app_current_user_id())
with check (user_id = app_current_user_id())
```

## Tables Requiring RLS

P0:

```txt
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
source_item
source_item_key
dedupe_key
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
outbox_event if user scoped
cost_ledger_entry
entity_match_candidate
merge_decision
oauth_connection
```

Usually not RLS user-owned:

```txt
canonical_item
canonical_item_external_id
canonical_item_alias if global
key_reference
api_credential_reference
```

Global catalog tables must not contain private user facts.

## Lifecycle-aware Policies

RLS alone does not hide deleted/sealed from normal queries.

Application queries and search projections must additionally filter lifecycle.

Default query scope:

```txt
lifecycle_state = active
```

Special unlock flows:

- sealed unlock requires re-auth and policy decision.
- deleted records are not returned.
- pending_delete excluded from search/tips/export immediately.

## RLS and Search

Search must query `search_document`, not raw tables.

Rules:

- search_document has user_id.
- search_document excludes hidden/sealed/deleted by default.
- sealed/private scopes require explicit user action.
- search index rebuild must respect policy.

## RLS and Export

Export must not rely only on RLS.

Export filter order:

1. user authentication / re-auth
2. export safety ceremony
3. RLS user isolation
4. policy evaluation
5. lifecycle filtering
6. sensitivity filtering
7. raw/sealed/third-party restrictions

## RLS Negative Tests

### RLS-001 Cross-user source_item read denied

- user A creates source_item.
- request context set to user B.
- query source_item by ID.
- expected: zero rows.

### RLS-002 Cross-user memory_record update denied

- user B tries update user A memory_record.
- expected: update count zero or DB error.

### RLS-003 Cross-user import_preview_candidate denied

- user B cannot see user A import preview candidates.

### RLS-004 Missing app.current_user_id fails closed

- no current_user_id set.
- query user table.
- expected: zero rows or error, never all rows.

### RLS-005 Connection pool context does not leak

- request A sets user A.
- request B on reused connection must set user B or clear.
- expected: B cannot see A.

### RLS-006 App role is not table owner

- assert current app role does not own user data tables.

### RLS-007 Support role cannot read raw/private title

- support role can see counts/risk codes but not title/body/raw fields.

### RLS-008 Worker role cannot process revoked/deleted user job

- background job for deleted user or revoked connector should fail closed.

### RLS-009 Search document respects lifecycle

- sealed/deleted memory has no active search_document.

### RLS-010 Export query cannot bypass policy with direct SQL path

- direct export query path still checks policy/lifecycle, not just user_id.

## Test Fixture Requirements

Use synthetic user IDs:

```txt
user_a = 00000000-0000-7000-8000-0000000000aa
user_b = 00000000-0000-7000-8000-0000000000bb
```

Synthetic content only.

No real personal data.

## Failure Modes

RLS test failure is P0 blocker if:

- cross-user read succeeds.
- missing user context returns rows.
- support role sees raw/private title.
- search returns sealed/deleted.
- export bypasses policy.

## Implementation Gate

DB implementation may start only after:

- app roles are defined.
- RLS policies have negative tests.
- app runtime role is not owner.
- missing context fails closed.
- support/admin raw access is denied by design.

## 結論

Memory OSのDBは、アプリ側のwhere user_idだけに頼らない。

RLSを入れる。

ただし、RLSだけに頼らず、policy engine、lifecycle、Export ceremony、audit、key managementと組み合わせる。

RLSの価値は、設計ではなくnegative testで証明する。
