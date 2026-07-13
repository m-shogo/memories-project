# Memory Town Persistence, RLS and Recovery Contract

最終更新: 2026-07-13

## 目的

Memory Town のdata modelを、将来の配置編集、複数端末、migration、Export、Resetへ拡張しても、cross-user leakage、silent overwrite、壊れたlayoutによる全体障害を起こさない形で固定する。

実装はまだ開始しない。

本書はDB実装時のP0契約である。

参照:

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-concrete-data-contract.md`
- `docs/rls-policy-and-negative-tests.md`
- `docs/account-deletion-and-tombstone-decision.md`

---

# 1. Global definitionsとuser stateを分ける

## Global read-only definitions

```txt
town_feature_registry
town_map_definition
town_object_catalog
town_object_definition
town_layout_template
town_asset_manifest
town_environment_theme_catalog
```

特徴:

- user_idを持たない
- versioned immutable
- application roleはread-only
- production更新はmigration / controlled publishのみ
- user入力を直接保存しない

## User-owned state

```txt
town_layout
town_layout_object
town_path_cell
town_feature_binding
town_feature_progress
town_environment_preference
town_layout_revision
town_layout_snapshot
town_layout_event
town_command_dedupe
town_reset_event
```

全tableに`user_id`を持たせる。

---

# 2. Table responsibility

## 2.1 town_layout

現在layoutのheader。

```txt
layout_id
user_id
map_definition_id
map_definition_version
baseline_template_id
baseline_template_version
layout_revision
status
created_at
updated_at
```

Rules:

- userあたりactive layoutは初期1件
- layout_revisionは単調増加
- renderer session stateを保存しない
- map pixel座標を保存しない

## 2.2 town_layout_object

配置object instance。

```txt
instance_id
user_id
layout_id
definition_id
definition_version
parcel_id nullable
cell_x nullable
cell_y nullable
elevation_level nullable
orientation nullable
origin
placement_state
lock_policy
variant_key nullable
created_at
updated_at
```

Placement invariant:

```txt
placement_state = placed
→ cell_x / cell_y / elevation_level / orientation required

placement_state in (stored, retired)
→ cell_x / cell_y / elevation_level / orientation must be NULL
```

DB NULLは、JSONの無意味なnullとは別である。

DBでは未配置を表すためnullable columnを使用し、API JSONではfieldを省略する。

## 2.3 town_path_cell

```txt
user_id
layout_id
cell_x
cell_y
elevation_level
path_type
created_at
updated_at
```

Primary candidate:

```txt
(user_id, layout_id, cell_x, cell_y, elevation_level)
```

`connection_mask`を保存しない。

## 2.4 town_feature_binding

```txt
binding_id
user_id
layout_id
feature_id
object_instance_id
binding_role
created_at
updated_at
```

Constraints:

- primary bindingは`(user_id, layout_id, feature_id)`につき最大1
- object_instance_idは同じuser / layoutに属する
- feature_idはregistryに存在
- stored / retired objectをprimary portalとして使用しない

## 2.5 town_feature_progress

```txt
user_id
feature_id
max_unlocked_stage
unlocked_at_by_stage
 growth_ruleset_version
reset_epoch
created_at
updated_at
```

`unlocked_at_by_stage`は小さなversioned JSONでもよいが、無制限任意JSONにしない。

Rules:

-通常更新でstageを下げない
- stageを下げるのは明示的reset commandだけ
- candidate countやprivate titleを保存しない
- reset_epochは単調増加

## 2.6 town_environment_preference

```txt
user_id
theme_id
season_mode
manual_season nullable
time_mode
weather_visual
motion_level
sound_enabled
created_at
updated_at
```

Rules:

- GPS必須にしない
- precise locationを保存しない
- weather_visualは実天候の事実を意味しない

## 2.7 town_layout_revision

保存成功ごとのrevision metadata。

```txt
user_id
layout_id
revision
source
batch_id nullable
snapshot_id nullable
created_at
```

現在状態の正本ではない。

## 2.8 town_layout_snapshot

復旧用snapshot。

```txt
snapshot_id
user_id
layout_id
revision
reason
schema_version
compressed_payload_ref
safe_metadata
expires_at nullable
created_at
```

raw memory title / bodyを含めない。

snapshot retentionは無制限にしない。

## 2.9 town_layout_event

監査・復旧補助。

```txt
event_id
user_id
layout_id
revision
batch_id nullable
event_type
safe_summary
created_at
```

Event sourcingの唯一正本にしない。

## 2.10 town_command_dedupe

```txt
user_id
batch_id
layout_id
expected_revision
result_revision
result_status
request_hash
created_at
expires_at
```

Unique:

```txt
(user_id, batch_id)
```

同じbatch IDで異なるrequest hashが来た場合は拒否する。

---

# 3. Foreign key and ownership rules

必須:

```txt
town_layout_object.layout_id
→ town_layout.layout_id

layout object user_id
= parent layout user_id

feature binding object_instance_id
→ same user / same layout object

path cell layout_id
→ same user layout

revision / snapshot / event
→ same user layout
```

単独IDだけで他user rowを参照できるschemaにしない。

推奨:

- composite FK `(user_id, layout_id)`
- composite FK `(user_id, layout_id, instance_id)`
- application layerでもownershipを再確認

---

# 4. Role model

既存role modelを継続する。

```txt
memory_migration_role
memory_app_role
memory_worker_role
memory_support_role
memory_analytics_role
memory_readonly_debug_role
```

## memory_migration_role

- schema / policy作成
- global catalog publish
- table owner

## memory_app_role

- current userのtown stateだけread / write
- global catalog read-only
- table ownerにしない

## memory_worker_role

- user contextを明示したprojection / migration / snapshot処理
- unrestricted global readを持たない
- raw memoryとtown auditを不要に結合しない

## memory_support_role

-通常はtown layout内容を閲覧不可
- support ceremonyが承認された場合のみ限定access
- access audit必須

## memory_analytics_role

- aggregateのみ
- instance coordinateやfeature progressの個別user追跡を原則不要にする
- private titleやnoteは当然不可

---

# 5. RLS fail-closed contract

全user-owned town tableでRLSを有効にする。

概念policy:

```sql
USING (
  user_id = app_current_user_id_required()
)
WITH CHECK (
  user_id = app_current_user_id_required()
)
```

`app_current_user_id_required()`は、context未設定時にNULL許容で空結果にするのではなく、明示的にfail closedする。

禁止:

- table ownerでapplication runtime
- `user_id = current_setting(..., true)::uuid`を無検証利用
- support roleへの常時bypassrls
- service role共通接続でuser filterをapplication queryだけに依存

---

# 6. Server authoritative command apply

Command Batch apply:

```txt
1. authenticated user resolve
2. batch dedupe check
3. layout row SELECT FOR UPDATE
4. expected revision compare
5. command schema validation
6. ownership / lock policy
7. object catalog / map version resolution
8. spatial validation
9. whole batch dry-run
10. pre-save snapshot
11. transaction apply
12. revision increment
13. revision / event / dedupe row write
14. commit
```

一件ずつcommitしない。

一件でもinvalidなら全体rollback。

## Revision CAS

```txt
expected_revision != current_revision
→ STALE_LAYOUT_REVISION
```

silent last-write-wins禁止。

---

# 7. Reset transaction

Resetもcommand batchと同等に扱う。

必須:

- explicit scope
- preview
- expected revision / reset epoch
- snapshot
- atomic apply
- audit event
- memory domain不変assertion

User object disposition:

```txt
stored
explicit_delete
```

Defaultは`stored`。

`explicit_delete`は確認copyを分ける。

---

# 8. Corruption recovery

Townの破損でMemory OS全体を起動不能にしない。

Recovery order:

```txt
1. current layout structural validation
2. referential validation
3. spatial validation
4. repairable derived data再構築
5. invalid objectをstoredへ退避
6. last valid snapshot候補
7. fallback town表示
8. userへsafe summary
```

自動修復してよいもの:

- path derived mask cache
- scene snapshot cache
- missing optional overlay
- stale render asset mapping

自動修復で消してはいけないもの:

- user object
- user path
- feature progress
- feature binding

修復不能なuser objectはstoredへ移す。

---

# 9. Account deletion

Account deletion時は以下を削除対象に含める。

```txt
town_layout
town_layout_object
town_path_cell
town_feature_binding
town_feature_progress
town_environment_preference
town_layout_revision
town_layout_snapshot
town_layout_event
town_command_dedupe
town_reset_event
```

Global catalogは削除しない。

Account deletion完了後にTownだけ復旧できる状態を残さない。

Backup / delayed deletionは既存account deletion契約へ従う。

---

# 10. Audit safe metadata

許可候補:

```txt
layout_id opaque ID
revision
command type
object category
issue code
count
schema version
catalog version
success / failure
```

禁止:

```txt
memory title
user note
person name
private URL
precise location
raw screenshot
object custom label containing private text
```

---

# 11. RLS negative tests

最低限:

```txt
MT-RLS-001 user A cannot read user B layout
MT-RLS-002 user A cannot update user B object by instance ID
MT-RLS-003 user A cannot bind own feature to user B object
MT-RLS-004 user A cannot insert path into user B layout
MT-RLS-005 user A cannot read user B snapshots
MT-RLS-006 missing user context fails closed
MT-RLS-007 app role cannot update global catalog
MT-RLS-008 support role cannot normally read layout
MT-RLS-009 worker without user context cannot rebuild projection
MT-RLS-010 cross-user batch ID replay does not reveal existence
MT-RLS-011 invalid parent user_id composite FK fails
MT-RLS-012 account deletion removes all town user state
```

## Response leakage

他user IDを指定した時も、存在有無を推測しにくい統一errorへする。

```txt
NOT_FOUND_OR_NOT_OWNED
```

---

# 12. DB constraints and application validators

DB constraintで守るもの:

- revision non-negative
- stage non-negative
- reset epoch non-negative
- orientation enum
- placement state / nullable position整合
- unique IDs
- duplicate path cell禁止
- primary binding unique
- composite ownership FK

Application domain validatorで守るもの:

- footprint collision
- parcel category
- terrain compatibility
- growth envelope
- entrance clearance
- orientation asset support
- command permission phase

DB triggerへ複雑なspatial business ruleを集中させない。

---

# 13. Persistence design gate

実装開始前:

```txt
[ ] table責務が確定
[ ] global definition / user state分離
[ ] 全user tableにuser_id
[ ] composite ownership FK方針
[ ] RLS fail closed
[ ] app role非owner
[ ] batch idempotency unique
[ ] revision CAS
[ ] stored object nullable position constraint
[ ] reset transaction
[ ] snapshot retention方針
[ ] corruption fallback
[ ] account deletion inclusion
[ ] 12以上のRLS negative test
```

---

# 結論

```txt
町は感情的なUIでも、保存層は厳密なuser data systemである。

layoutを壊さない。
他人の町を見せない。
再送で増殖させない。
古い端末で上書きさせない。
町の破損でMemory OS本体を落とさない。
```
