# Memory Town Hardening Tickets

最終更新: 2026-07-13

## 目的

`memory-town-architecture-hardening-contract.md` を実装・migration・testへ落とすためのP0/P1チケットを固定する。

実装はまだ開始しない。

この文書は、既存の`memory-town-spatial-foundation-tickets.md`を置き換えるものではなく、P0補正として先に適用する。

---

# P0: 実装開始前に契約固定が必要

## MT-H-001 Terminology Lock

### Scope

- `固定2.5D`を`固定視点2.5D`へ統一
- 固定視点と固定配置を区別
- glossary追加

### Acceptance

- 全正本で同じ意味
- `fixed layout`はMVPの状態だけを指す
- 将来editorと矛盾しない

---

## MT-H-002 Five-state Separation

### Scope

```txt
Memory Domain
Town Feature Progress
Town Layout
Town Environment
Town Render
```

### Acceptance

- season / time / cameraがTownFeatureProjectionへ入らない
- user decorationがMemory aggregate再計算で消えない
- render stateを永続化しない
- state ownership diagramがある

---

## MT-H-003 TownFeatureId Registry

### Scope

初期ID:

```txt
shelf.movie
shelf.story
shelf.food
box.travel
system.inbox
reflection.square
```

### Acceptance

- display nameから生成しない
- definitionId / instanceIdと別
- ID再利用禁止
- registry versionを持つ
- route mapping testがある

---

## MT-H-004 Feature Binding Contract

### Scope

- featureId
- object instance
- primary / secondary / portal role
- skin replacement

### Acceptance

- skin変更でfeature progress維持
- building移動でbinding維持
- migrationでinstance replacement時のbinding移行
- bindingなしdecor objectを許可

---

## MT-H-005 Non-shrinking Feature Progress

### Scope

- candidate stage
- max unlocked stage
- unlock event
- reset epoch

### Acceptance

- record削除でstage縮小なし
- current eligible countは正確
- ruleset変更で縮小なし
- explicit reset可能
- account deletionで全削除

---

## MT-H-006 Reset and Privacy Erasure

### Scope

- visual reset
- layout reset
- feature progress reset
- decoration reset
- full town reset
- shelf deletion option

### Acceptance

- Memory dataとの影響範囲をPreview
- reset idempotency
- rollback可否を明示
- hidden / sealed由来の推測表示を消せる
- account deletion contractと一致

---

## MT-H-007 Coordinate Convention Lock

### Scope

- origin
- +X / +Y
- orientation
- elevationLevel
- footprint pivot

### Acceptance

- 4回rotationで元へ戻る
- negative relative cell対応
- pixel elevationを保存しない
- screenToGrid round trip fixture
- depth tie-breaker固定

---

## MT-H-008 Terrain Canonical Model

### Scope

- one base terrain per cell
- water as terrain kind
- coast rule
- surface path layer

### Acceptance

- terrain重複不可
- pathとterrain共存可能
- water objectとの二重管理なし
- terrain version migration fixture

---

## MT-H-009 Derived Path Connectivity

### Scope

- persisted path type
- derived connection mask
- bridge connector
- autotile projection

### Acceptance

- maskをDB正本にしない
- add/remove後に隣接mask再計算
- physical path / semantic overlay分離
- deterministic render

---

## MT-H-010 Growth Envelope

### Scope

- envelope version
- reserved cells
- supported stages
- decoration-safe slots

### Acceptance

- stage changeでuser object削除なし
- envelope外stageを自動適用しない
- migration preview
- stored state退避
- rollback snapshot

---

## MT-H-011 Object Origin / Placement / Lock Policy

### Scope

```txt
origin: template / user / migration / system_unlock
placement: placed / stored / retired
lock: system_fixed / decor_editable / relocatable_later / user_owned
```

### Acceptance

- `source='projection'`不存在
- magic coordinate不存在
- boolean lockedだけに依存しない
- phase flagとのpermission matrix

---

## MT-H-012 Immutable Definition Versions

### Scope

- map
- template
- object definition
- catalog
- growth envelope

### Acceptance

- published version in-place変更禁止
- replacement mapping
- deprecated definition preservation
- content hash
- compatibility matrix

---

## MT-H-013 Template Three-way Merge

### Scope

```txt
old baseline
current layout
new template
```

### Acceptance

- untouched system objectのみ自動更新
- user変更を上書きしない
- new featureはreserved parcelへ
- placement失敗はstoredへ
- preview / audit / rollback

---

## MT-H-014 Atomic Editor Session

### Scope

- local draft
- command batch
- server revalidation
- compare-and-swap

### Acceptance

- dragごとのserver writeなし
- batch all-or-nothing
- batch ID idempotency
- stale revision拒否
- server authoritative validation

---

## MT-H-015 Undo / Redo / Rollback

### Scope

- local inverse commands
- saved revision snapshots
- restore as new revision

### Acceptance

- undoでevent history改変なし
- unsupported inverseを明示
- migration前snapshot
- reset前snapshot
- retention ruleへの接続

---

## MT-H-016 Multi-device Conflict

### Scope

- optimistic concurrency
- conflict response
- safe rebase policy

### Acceptance

- last-write-wins禁止
- CRDTを初期採用しない
- conflict reason code
- userへ変更消失なし
- stale client fixture

---

## MT-H-017 Persistence Source of Truth

### Scope

current state tablesとaudit eventを分離する。

### Acceptance

- event sourcingではない
- current stateから町をload可能
- eventsなしでもcurrent layout valid
- snapshot retention方針
- corruption recovery path

---

## MT-H-018 RLS and Ownership

### Scope

- user_id
- fail-closed RLS
- cross-user reference prevention
- support access boundary

### Acceptance

- another userのlayoutId拒否
- another userのinstanceId拒否
- locked object mutation拒否
- unknown catalog definition拒否
- missing current_user_id拒否

---

## MT-H-019 Structured Validation Errors

### Scope

Stable codes:

```txt
OUT_OF_MAP_BOUNDS
PARCEL_CATEGORY_DENIED
SOLID_COLLISION
GROWTH_ENVELOPE_RESERVED
ENTRANCE_BLOCKED
LOCK_POLICY_DENIED
UNKNOWN_DEFINITION
STALE_LAYOUT_REVISION
```

### Acceptance

- UI copyとcode分離
- affected cells / instances
- warning / error区別
- localization可能
- telemetryはcodeのみ

---

## MT-H-020 Export / Import / Reset Manifest

### Scope

- feature progress
- layout
- environment preference
- version set

### Acceptance

- Memory dataとsection分離
- Import Preview必須
- unsupported objectはstored
- asset本体を無条件同梱しない
- account deletionと整合

---

## MT-H-021 Responsive Camera Contract

### Scope

- world bounds
- safe area
- bottom sheet reserve
- overview / district / focus preset

### Acceptance

- viewport変更でlayout不変
- selected objectがsheetに隠れない
- pixel camera position非永続
- reduced motion対応
- map expansion対応

---

## MT-H-022 Asset Compatibility Manifest

### Scope

- texture key
- content hash
- orientation
- anchors
- render bounds
- footprint contract
- fallback
- provenance

### Acceptance

- atlas再編でstable key不変
- missing assetでinstance消失なし
- mirrored text禁止
- footprint changeを検出
- license / provenance記録

---

## MT-H-023 Recovery and Safe Storage

### Scope

- stored placement state
- last valid snapshot
- repair report

### Acceptance

- off-map magic positionなし
- invalid objectを失わない
- Memory OS本体は起動可能
- repair audit
- user-readable explanation

---

## MT-H-024 Feature Flags

### Scope

```txt
town_webgl_renderer
town_ambient_motion
town_decoration_slots
town_free_decor_editor
town_path_editor
town_structure_relocation
town_map_expansion
```

### Acceptance

- independent rollout
- independent rollback
- disabled featureのdata保持
- one giant editor flag禁止

---

## MT-H-025 Property / Fuzz / Golden Fixtures

### Scope

- property tests
- malformed command fuzz
- migration golden fixtures
- privacy snapshot tests

### Acceptance

- rotation invariant
- path derived mask invariant
- serialize round trip
- duplicate ID / stale revision fixture
- private field non-leak fixture

---

# P1: Prototypeで数値固定が必要

## MT-H-P1-001 Tile Metric Study

比較:

- tile width / height
- building footprint readability
- finger hit target
- label density

対象viewport:

```txt
360x800
375x812
390x844
393x852
412x915
430x932
```

## MT-H-P1-002 Initial Map Size

決めるもの:

- grid width / height
- initial parcels
- growth envelopes
- expansion zones
- world bounds

## MT-H-P1-003 Art Production Comparison

比較:

1. strict pixel art
2. high-resolution dot style
3. soft miniature illustration

## MT-H-P1-004 Performance Budget

実機で固定:

- texture memory
- atlas dimensions
- active sprites
- frame time
- heat / battery
- WebGL fallback rate

## MT-H-P1-005 Growth Threshold User Test

確認:

- Stage 0が寂しすぎないか
- Stage 1まで遠すぎないか
- non-shrinkingが自然か
- current countとbuilding sizeの乖離が不自然か

## MT-H-P1-006 Town Menu Comprehension

確認:

- buildingと棚の対応
- labelあり / なし
- townから棚への到達
- 通常navigationとの併存

## MT-H-P1-007 Editor Value Test

自由配置を実装する前に確認:

- decoration slotだけで十分か
- 木・花の自由配置が戻る理由になるか
- editingがMemory OS本体を邪魔しないか

---

# Implementation Order Correction

PixiJS本実装前:

```txt
MT-H-001〜013
→ MT-H-017〜023
→ spatial foundation IDs / coordinates / catalog
→ static scene composition
→ fallback
→ PixiJS adapter
```

Editor公開前:

```txt
MT-H-014〜016
→ MT-H-019
→ command API
→ editor UI
```

Map expansion前:

```txt
three-way merge
→ growth envelope migration
→ chunk / district contract
→ performance gate
```

---

# P0 Exit Gate

```txt
[ ] hardening contractと全正本が矛盾しない
[ ] feature identityとvisual identityが分離
[ ] progressとprojectionが分離
[ ] environmentがprojectionから分離
[ ] path maskが導出値
[ ] template updateがthree-way merge
[ ] editor saveがatomic batch
[ ] concurrencyがCAS
[ ] current-state tablesが正本
[ ] RLS negative tests定義済み
[ ] export / reset / deletion定義済み
[ ] recovery / stored state定義済み
[ ] property / migration fixtures定義済み
```

このGateを満たすまで、Memory Town設計を「完璧」と呼ばない。
