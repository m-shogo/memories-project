# Memory Town Spatial Foundation Tickets

最終更新: 2026-07-13

## 目的

Memory Townの最初の実装で、MVPの固定配置だけに最適化したpixel座標実装を作り、将来の道路、木、花、家具、建物移動で作り直しになることを防ぐ。

本書は実装順と完了条件を固定する。

参照正本:

- `docs/memory-town-long-term-spatial-model.md`
- `docs/memory-town-webgl-architecture.md`
- `docs/current-product-direction.md`

---

## Non-negotiable Rules

実装開始時から守る。

```txt
1. screen x/yを永続化しない
2. PixiJS spriteをdomain stateにしない
3. layoutをTownProjectionへ混ぜない
4. 建物を1block単位へ分解しない
5. 固定mapをcomponent内へ直書きしない
6. stable IDを表示名から生成しない
7. user配置をmemory aggregateから再生成しない
8. renderer内でcollisionやgrowth ruleを決めない
9. physical roadとsemantic connectionを同じmodelにしない
10. MVPでeditorを作らなくてもvalidatorを省略しない
```

---

## Recommended Module Boundary

```txt
src/town/
├─ domain/
│  ├─ coordinates.ts
│  ├─ footprint.ts
│  ├─ placement.ts
│  ├─ layout.ts
│  ├─ objectDefinition.ts
│  ├─ parcel.ts
│  ├─ path.ts
│  ├─ commands.ts
│  └─ versions.ts
├─ application/
│  ├─ createLayoutFromTemplate.ts
│  ├─ validatePlacement.ts
│  ├─ applyLayoutCommand.ts
│  ├─ buildTownSceneSnapshot.ts
│  └─ migrateTownLayout.ts
├─ projection/
│  ├─ buildTownProjection.ts
│  └─ growthRules.ts
├─ infrastructure/
│  ├─ layoutRepository.ts
│  ├─ objectCatalogRepository.ts
│  └─ assetManifestRepository.ts
├─ renderer/
│  ├─ PixiTownRenderer.ts
│  ├─ layers/
│  ├─ sprites/
│  └─ fallback/
└─ ui/
   ├─ TownScreen.tsx
   ├─ TownSummarySheet.tsx
   └─ TownAccessibilityList.tsx
```

実際のframework構成に合わせて変更可能だが、責務分離は維持する。

---

## MT-SP-001 Stable IDs and Version Set

### Scope

定義する。

```txt
mapDefinitionId
layoutTemplateId
parcelId
definitionId
instanceId
layoutId
commandId
```

Version:

```txt
spatialSchemaVersion
mapDefinitionVersion
layoutTemplateVersion
objectCatalogVersion
projectionSchemaVersion
growthRulesetVersion
assetManifestVersion
```

### Acceptance

- 表示名変更でIDが変わらない
- deprecated definitionを保持できる
- versionを一つのtownVersionへまとめない
- test fixtureで同一IDを再現可能

---

## MT-SP-002 Logical Coordinate System

### Scope

- `TownGridPosition`
- `TownOrientation`
- `TownGridMetric`
- `gridToScreen`
- 将来の`screenToGrid`

### Acceptance

- viewportサイズを変えてもlogical position不変
- camera zoomで保存値不変
- grid-to-screenがdeterministic
- elevationを含む
- screen pixel座標をlayout JSONへ保存しない

---

## MT-SP-003 Map and Parcel Definitions

### Scope

- `TownMapDefinition`
- initial grid bounds
- initial parcels
- expansion zones

Initial parcels:

```txt
cinema-main
story-house-main
market-main
port-main
warehouse-main
central-square
```

### Acceptance

- parcel IDがstable
- parcel bounds testがある
- system reserved / editable laterを区別
- 最大stage footprintがparcelへ収まる
- expansion zoneを後から追加可能

---

## MT-SP-004 Object Definition Catalog

### Scope

初期category:

```txt
terrain
path
structure
tree
flower
ground_decor
raised_decor
seasonal
semantic_overlay
```

初期structure:

```txt
cinema
story_house
market
port
warehouse
central_square
```

### Acceptance

- definitionとinstanceを分離
- footprintを持つ
- depth anchorを持つ
- orientation enumを持つ
- missing asset fallbackを持つ
- deprecated definitionを削除せず保持

---

## MT-SP-005 Footprint and Layer Model

### Scope

- occupied cells
- walkable cells
- entrance cells
- clearance cells
- depth anchor
- placement layer

### Acceptance

- 1x1 treeとmulti-cell buildingを同じvalidatorで扱える
- overlayとsolid objectが共存可能
- structure同士の重なりを拒否
- entrance clearanceを検証
- sprite transparent boundsへ依存しない

---

## MT-SP-006 Versioned Layout Template

### Scope

initial fixed townをtemplateとして定義する。

```txt
template file / config
→ layout generator
→ TownLayoutSnapshot
```

### Acceptance

- React component / Pixi sceneへ配置を直書きしない
- template versionを持つ
- instance IDをdeterministic生成
- system placementはlocked
- 同じtemplateから同じlayoutを生成

---

## MT-SP-007 Placement Validator Foundation

### Scope

MVPではeditorを公開しないが、配置作成時にvalidatorを通す。

Validation:

```txt
map bounds
parcel rules
footprint collision
placement layer
entrance clearance
category restriction
```

### Acceptance

- invalid templateがtestで落ちる
- buildingがparcel外へ出ると失敗
- overlapping solid objectを拒否
- valid overlayは許可
- rendererなしでunit test可能

---

## MT-SP-008 Layout Revision and Commands

### Scope

- layout revision
- idempotent command ID
- place / move / rotate / remove command type
- MVPではsystem commandのみ利用可能

### Acceptance

- duplicate commandを二重適用しない
- stale revisionを検出
- command validationとapplyを分離
- user editor追加時にAPI contractを作り直さない

---

## MT-SP-009 Projection and Layout Composition

### Scope

```txt
TownProjection
+ TownLayoutSnapshot
→ TownSceneSnapshot
```

### Acceptance

- shelf count変更でstageだけ変わる
- building positionは変わらない
- layout変更でmemory record不変
- user decorationはprojection rebuildで消えない
- hidden / sealedをprojectionから除外可能

---

## MT-SP-010 PixiJS Renderer Adapter

### Scope

PixiJSはTownSceneSnapshotを描画するだけにする。

### Acceptance

- rendererにgrowth thresholdなし
- rendererにDB accessなし
- logical gridからscreenへ変換
- depth anchorでz sort
- instance IDをtap eventで返す
- route leaveでticker停止

---

## MT-SP-011 Path Model Foundation

### Scope

MVPでは固定道路だけだが、path cellとconnection maskで定義する。

### Acceptance

- straight / corner / T / cross / endをmaskで選べる
- road asset IDを座標へ直書きしない
- physical pathとsemantic connectionを別modelにする
- future path paint UIでmodel変更不要

---

## MT-SP-012 Static Fallback

### Scope

- static background
- DOM hotspots / object list
- same layout IDs

### Acceptance

- WebGLなしでも建物から棚へ移動可能
- fallbackがpixel hard-codeへ依存しない
- layout templateからhotspotを生成可能
- accessibility listと同じobject IDsを使う

---

## MT-SP-013 Migration Harness

### Scope

- layout snapshot
- catalog migration
- template migration
- invalid placement recovery
- safe holding area

### Acceptance

- definition廃止でinstanceを消さない
- migration前snapshotを保持
- invalid objectを退避可能
- rollback testがある
- migration結果を監査可能

---

## MT-SP-014 Spatial Contract Test Suite

### Required Tests

```txt
gridToScreen
screenToGrid
footprint rotation
collision
parcel bounds
entrance clearance
placement layer
path autotile mask
stable depth sorting
layout revision conflict
deprecated object preservation
projection/layout separation
```

### Acceptance

- PixiJSを起動せずdomain test可能
- multiple viewport snapshot test
- same input produces same scene snapshot
- private memory fieldsがsceneへ入らない

---

## Initial Implementation Order

```txt
MT-SP-001 IDs / versions
→ MT-SP-002 coordinates
→ MT-SP-003 map / parcel
→ MT-SP-004 object catalog
→ MT-SP-005 footprint / layers
→ MT-SP-006 layout template
→ MT-SP-007 validator
→ MT-SP-009 scene composition
→ MT-SP-010 Pixi renderer
→ MT-SP-012 fallback
```

Commands、道路、migration harnessは、基礎と並行して契約を作り、editor公開前に完成させる。

---

## MVP Exit Gate

Town static / WebGL prototypeを完了扱いにする条件:

```txt
[ ] 配置がlogical gridで保存される
[ ] map / parcel / object IDsがstable
[ ] initial layoutがversioned template
[ ] 全structureにfootprintがある
[ ] placement validatorを通る
[ ] projectionとlayoutが分離
[ ] rendererがscene snapshotのみ読む
[ ] static fallbackが同じIDsを使う
[ ] pixel x/yを永続化していない
[ ] future editor導入時にschema変更が不要
```

---

## No-Go Review Findings

以下の実装がPRに含まれた場合、修正対象とする。

```txt
<Building x={320} y={180} /> を正本として使用
cinemaPositionをcomponent内定数だけで管理
sprite boundsをcollision判定に使用
building stageごとに別instanceを作成
TownProjectionにuser decorationを保存
memory record削除で町全体を再生成
roadとmemory relationを同じ配列で管理
object display nameをdefinition IDに使用
```

---

## Final Rule

```txt
MVPの見た目は固定でも、内部まで固定にしない。

編集機能を後から足す。
空間モデルは最初から作る。
```
