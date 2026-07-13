# Memory Town Spatial Foundation Tickets

最終更新: 2026-07-13

## 目的

Memory TownのMVP固定layoutだけに最適化したpixel座標実装を作り、将来の道路、木、花、家具、建物移動で全面作り直しになることを防ぐ。

優先参照:

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-hardening-tickets.md`
- `docs/memory-town-long-term-spatial-model.md`
- `docs/memory-town-webgl-architecture.md`
- `docs/current-product-direction.md`

本書は空間基盤の実装順を固定する。

実装はまだ開始しない。

---

## Non-negotiable Rules

```txt
1. screen x/yを永続化しない
2. PixiJS spriteをdomain stateにしない
3. Memory / Feature Progress / Layout / Environment / Renderを混ぜない
4. Feature IDをvisual definition IDへ直結しない
5. 建物を1block単位へ分解しない
6. 固定mapをcomponent内へ直書きしない
7. stable IDを表示名から生成しない
8. user配置をmemory aggregateから再生成しない
9. renderer内でcollisionやgrowth ruleを決めない
10. physical pathとsemantic connectionを同じmodelにしない
11. path connection maskをDB正本にしない
12. source='projection'のobject instanceを作らない
13. holding areaをmagic coordinateで表現しない
14. boolean lockedだけでpermissionを表現しない
15. MVPでeditorを作らなくてもvalidatorを省略しない
16. client validationだけで保存しない
17. new templateでuser layoutを丸ごと上書きしない
18. record削除で建物を罰のように縮ませない
```

---

## Recommended Module Boundary

```txt
src/town/
├─ domain/
│  ├─ featureId.ts
│  ├─ featureProgress.ts
│  ├─ coordinates.ts
│  ├─ footprint.ts
│  ├─ placement.ts
│  ├─ layout.ts
│  ├─ objectDefinition.ts
│  ├─ parcel.ts
│  ├─ growthEnvelope.ts
│  ├─ path.ts
│  ├─ environment.ts
│  ├─ commands.ts
│  └─ versions.ts
├─ application/
│  ├─ createLayoutFromTemplate.ts
│  ├─ validatePlacement.ts
│  ├─ applyLayoutCommandBatch.ts
│  ├─ unlockFeatureStage.ts
│  ├─ buildTownSceneSnapshot.ts
│  ├─ mergeLayoutTemplate.ts
│  ├─ resetTownState.ts
│  └─ migrateTownLayout.ts
├─ projection/
│  ├─ buildTownFeatureProjection.ts
│  └─ growthRules.ts
├─ infrastructure/
│  ├─ layoutRepository.ts
│  ├─ featureProgressRepository.ts
│  ├─ objectCatalogRepository.ts
│  ├─ assetManifestRepository.ts
│  └─ environmentPreferenceRepository.ts
├─ renderer/
│  ├─ PixiTownRenderer.ts
│  ├─ layers/
│  ├─ sprites/
│  └─ fallback/
└─ ui/
   ├─ TownScreen.tsx
   ├─ TownSummarySheet.tsx
   ├─ TownAccessibilityList.tsx
   └─ future-editor/
```

Frameworkに合わせて変更可能だが、責務分離を維持する。

---

# Foundation Tickets

## MT-SP-001 Stable IDs and Version Set

### Scope

IDs:

```txt
featureId
featureBindingId
mapDefinitionId
layoutTemplateId
parcelId
definitionId
instanceId
layoutId
batchId
commandId
```

Versions:

```txt
spatialSchemaVersion
featureRegistryVersion
mapDefinitionVersion
layoutTemplateVersion
objectCatalogVersion
growthEnvelopeVersion
featureProjectionSchemaVersion
growthRulesetVersion
assetManifestVersion
sceneSchemaVersion
```

### Acceptance

- 表示名変更でID不変
- ID再利用禁止
- deprecated definition保持
- versionを一つへまとめない
- deterministic fixture

---

## MT-SP-002 Five-state Domain Contract

### Scope

```txt
Memory Domain
Town Feature Progress
Town Layout
Town Environment
Town Render
```

### Acceptance

- ownership diagram
- forbidden dependencies test
- season / camera非流入
- user decoration非再生成
- Render State非永続

---

## MT-SP-003 TownFeature Registry and Binding

### Scope

初期Feature:

```txt
shelf.movie
shelf.story
shelf.food
box.travel
system.inbox
reflection.square
```

### Acceptance

- visual definitionと分離
- route mapping
- skin変更でbinding維持
- building移動でbinding維持
- replacement migration fixture

---

## MT-SP-004 Feature Progress Contract

### Scope

- candidate stage
- max unlocked stage
- unlock event
- reset epoch

### Acceptance

- record削除で縮小なし
- current count正確
- explicit reset
- shelf deletion option
- account deletion全削除

---

## MT-SP-005 Logical Coordinate System

### Scope

- origin / axes
- orientation
- elevationLevel
- gridToScreen
- screenToGrid

### Acceptance

- viewport非依存
- pixel elevation非永続
- round trip fixture
- deterministic projection
- camera zoomで保存値不変

---

## MT-SP-006 Footprint Pivot and Rotation

### Scope

- pivot cell
- occupied / walkable / entrance / clearance
- reserved growth cells
- negative relative cells

### Acceptance

- 4 rotationで元へ戻る
- rotationでposition不意移動なし
- transparent bounds非依存
- multi-cell structure対応

---

## MT-SP-007 Map / Terrain / Parcel

### Scope

- immutable map definition
- one base terrain per cell
- water as terrain kind
- parcels
- expansion zones

### Acceptance

- terrain重複拒否
- parcel bounds
- old coordinates不変のmap expansion
- system reserved / editable later区別

---

## MT-SP-008 Growth Envelope

### Scope

- envelope version
- reserved cells
- supported stages
- decoration-safe slots

### Acceptance

- stage changeでuser object削除なし
- envelope外stageを自動適用しない
- migration preview / rollback
- stored state退避

---

## MT-SP-009 Object Catalog

### Scope

- definition / instance分離
- origin
- placement state
- lock policy
- replacement mapping

### Acceptance

- source='projection'不存在
- magic coordinate不存在
- deprecated instance保持
- lock policy permission matrix
- missing asset fallback

---

## MT-SP-010 Versioned Layout Template

### Scope

- template placements
- path cells
- feature bindings
- deterministic instance IDs
- baseline version

### Acceptance

- code内pixel配置なし
- same template → same layout
- system placement policy
- published template immutable

---

## MT-SP-011 Three-way Template Merge

### Scope

```txt
old baseline
current user layout
new template
```

### Acceptance

- user変更を上書きしない
- untouched template objectのみ自動更新
- new featureをreserved parcelへ
- placement失敗はstored
- preview / audit / rollback

---

## MT-SP-012 Placement Validator

### Scope

```txt
schema
ownership
permission
definition availability
map bounds
parcel
a footprint collision
layer
growth envelope
entrance clearance
category limit
```

### Acceptance

- structured error codes
- rendererなしでunit test
- invalid template拒否
- cross-user reference拒否
- valid overlay許可

---

## MT-SP-013 Physical Path Foundation

### Scope

- path type persistence
- derived connection mask
- autotile projection
- bridge connector

### Acceptance

- mask非永続
- add / removeで隣接再計算
- physical / semantic分離
- deterministic snapshot

---

## MT-SP-014 Layout Current State and Revision

### Scope

- current-state source of truth
- layout revision
- baseline
- snapshots
- audit events

### Acceptance

- event sourcingではない
- eventsなしでcurrent layout load可能
- migration前snapshot
- corruption recovery
- user_id / RLS

---

## MT-SP-015 Atomic Command Batch

### Scope

- local draft
- batch ID
- expected revision
- server revalidation
- CAS

### Acceptance

- all-or-nothing
- idempotency
- stale revision拒否
- last-write-wins禁止
- command replay test

Editor UIは後続でもcontractは固定する。

---

## MT-SP-016 Scene Composition

### Scope

```txt
Feature Projection
+ Feature Progress
+ Feature Binding
+ Layout
+ Environment
→ TownSceneSnapshot
```

### Acceptance

- display stage解決
- path mask導出
- missing asset placeholder
- deterministic sort
- private data非流入

---

## MT-SP-017 Static Fallback

### Scope

- static town representation
- DOM feature buttons
- object list

### Acceptance

- WebGLなしで棚へ移動可能
- same Feature IDs
- pixel hard-code非依存
- accessibilityと同じIDs

---

## MT-SP-018 RLS / Ownership Negative Tests

### Required

- missing user context
- another user layout ID
- another user instance ID
- locked system mutation
- unknown definition
- disabled definition placement
- oversized command batch

### Acceptance

全てfail closed。

---

## MT-SP-019 Export / Reset Contract

### Scope

- feature progress
- layout
- bindings
- paths
- environment preferences
- version set

### Acceptance

- Import Preview
- unsupported object stored
- reset scope Preview
- account deletion全削除
- Memory data sectionと分離

---

## MT-SP-020 Migration / Recovery Harness

### Scope

- three-way merge
- catalog migration
- growth envelope migration
- stored state
- last valid snapshot

### Acceptance

- instance消失なし
- feature binding維持
- repair report
- rollback
- audit

---

## MT-SP-021 PixiJS Renderer Adapter

### Prerequisite

MT-SP-001〜020の契約が固定済み。

### Scope

PixiJSはTownSceneSnapshotを描画するだけ。

### Acceptance

- DB accessなし
- growth thresholdなし
- logical projection
- deterministic z sort
- instance ID tap event
- route leave ticker停止
- context loss fallback

---

## MT-SP-022 Spatial Contract Test Suite

### Required

```txt
gridToScreen / screenToGrid
footprint pivot rotation
collision
parcel bounds
growth envelope
entrance clearance
derived path mask
deterministic sort
layout revision conflict
three-way template merge
deprecated object preservation
feature / visual separation
progress / projection separation
private field non-leak
```

### Acceptance

- PixiJSなしでdomain test
- property tests
- fuzz tests
- migration golden fixtures
- multiple viewport snapshots

---

# Initial Implementation Order

```txt
MT-SP-001 IDs / versions
→ MT-SP-002 state ownership
→ MT-SP-003 feature registry / binding
→ MT-SP-004 feature progress
→ MT-SP-005 coordinates
→ MT-SP-006 footprint pivot
→ MT-SP-007 map / terrain / parcel
→ MT-SP-008 growth envelope
→ MT-SP-009 object catalog
→ MT-SP-010 layout template
→ MT-SP-011 merge contract
→ MT-SP-012 validator
→ MT-SP-013 path foundation
→ MT-SP-014 persistence / revision
→ MT-SP-018 RLS tests
→ MT-SP-019 export / reset
→ MT-SP-020 migration harness
→ MT-SP-016 scene composition
→ MT-SP-017 fallback
→ MT-SP-021 Pixi renderer
→ MT-SP-022 full contract tests
```

PixiJSを先に起動して座標を後から直す順番は禁止。

---

# MVP Exit Gate

```txt
[ ] 5-state separation
[ ] stable Feature IDs / bindings
[ ] non-shrinking progress / reset
[ ] logical coordinates / pivot
[ ] terrain / parcel / envelope
[ ] immutable template / three-way merge
[ ] object origin / placement state / lock policy
[ ] path mask derived
[ ] validator structured errors
[ ] current-state source of truth
[ ] layout revision / command idempotency
[ ] RLS negative tests
[ ] export / deletion / recovery
[ ] renderer reads SceneSnapshot only
[ ] static fallback uses same Feature IDs
[ ] screen pixel coordinates non-persistent
```

---

# No-Go Review Findings

```txt
<Building x={320} y={180} /> を正本にする
cinemaPositionをcomponent定数だけで管理
featureIdをcinema definition IDへ直結
TownProjectionにseason / camera / decorationを保存
source='projection' instance
record削除でstage縮小
connectionMaskをDB正本に保存
new templateでuser layoutを再生成
holding objectを(-999,-999)へ配置
silent last-write-wins
client validationだけで保存
cross-user IDsをserverで再検証しない
```

---

## Final Rule

```txt
MVPの見た目は固定でも、内部まで固定にしない。

Featureの意味、解除済み成長、配置、環境、描画を分離する。
Editorを後から足せるようにするのではなく、
Editorを足しても壊れない基盤を最初から定義する。
```
