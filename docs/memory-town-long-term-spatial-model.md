# Memory Town Long-term Spatial Model

最終更新: 2026-07-13

## 目的

Memory Townを、MVPでは固定視点2.5Dの町として軽く実装しながら、将来的にはユーザーが道路、木、花、ベンチ、建物などを配置できる箱庭へ拡張しても破綻しない空間モデルとして定義する。

最優先契約:

- `docs/memory-town-architecture-hardening-contract.md`

参考イメージ:

```txt
どうぶつの森のように、自分の場所へ愛着を持てる箱庭
```

ただし、以下を意味しない。

- 特定作品のUIやアートの複製
- 最初から自由配置ゲームを作る
- アバター操作を中心にする
- 経済、素材集め、クラフト、建築待ち時間
- Minecraft型の1block建築

Memory Townの役割は、Memory OSに蓄積された棚・箱・つながりが、見て楽しい自分の町として育つことである。

---

## Product Metaphor

```txt
見た目: 温かい固定視点2.5Dの編集可能なジオラマ
内部: 論理グリッド上の配置システム
MVP: system templateによる固定layout
将来: 装飾・道・植栽・建物を段階的に編集可能
```

固定視点と固定配置を混同しない。

---

# 1. Five-state Model

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

## 1.1 Memory Domain State

正本:

- memory / collection item
- shelf
- import
- progress
- month capsule
- confirmed relation
- follow target

町の座標、asset、cameraを持たない。

## 1.2 Town Feature Progress State

町機能の解除済み成長段階。

```ts
type TownFeatureId =
  | 'shelf.movie'
  | 'shelf.story'
  | 'shelf.food'
  | 'box.travel'
  | 'system.inbox'
  | 'reflection.square';

interface TownFeatureProgress {
  featureId: TownFeatureId;
  maxUnlockedStage: number;
  unlockedAtByStage: Record<number, string>;
  growthRulesetVersion: string;
  resetEpoch: number;
  updatedAt: string;
}
```

通常のrecord削除、Import取り消し、threshold変更で自動縮小しない。

## 1.3 Town Layout State

町のどこに何が置かれているか。

- map
- parcel
- terrain
- object instance
- path cell
- feature binding
- decoration slot
- stored object
- layout revision

Memory内容を持たない。

## 1.4 Town Environment State

```ts
interface TownEnvironmentState {
  themeId: string;
  seasonMode: 'auto' | 'manual';
  effectiveSeason: 'spring' | 'summer' | 'autumn' | 'winter';
  timeMode: 'day' | 'evening' | 'night';
  weatherVisual: 'clear' | 'rain' | 'snow';
  motionLevel: 'off' | 'reduced' | 'full';
  soundEnabled: boolean;
}
```

Memory Projectionへ混ぜない。

## 1.5 Town Render State

PixiJS session内だけの状態。

- camera
- selection
- loaded asset
- animation
- placement preview

永続化しない。

---

# 2. Feature / Visual Identity Separation

## 2.1 TownFeatureProjection

```ts
interface TownFeatureProjection {
  featureId: TownFeatureId;
  eligibleItemCount: number;
  recentDelta: number;
  candidateStage: number;
  badges: Array<'new' | 'continued' | 'capsule'>;
  route: string;
}
```

## 2.2 Display stage

```ts
displayStage = Math.max(
  featureProgress.maxUnlockedStage,
  featureProjection.candidateStage,
);
```

candidate stageがmaxUnlockedStageを超えた時だけ、unlock eventを保存する。

## 2.3 Feature binding

```ts
interface TownFeatureBinding {
  bindingId: string;
  featureId: TownFeatureId;
  objectInstanceId: string;
  bindingRole: 'primary' | 'secondary' | 'portal';
}
```

Rules:

- featureId = Memory OS上の意味
- definitionId = visual definition
- instanceId = map上の個体
- skin変更でfeatureId不変
- building移動でfeatureId不変
- definition差し替えでfeature progress不変

---

# 3. Canonical Logical Grid

町を画面座標`x / y`の集合として保存しない。

保存するもの:

```txt
logical position
+ footprint
+ layer
+ elevation level
+ orientation
+ stable IDs
```

## 3.1 Axes

```txt
origin: logical north-west = (0, 0)
+X: east
+Y: south
```

isometric projection:

```txt
+X = screen down-right
+Y = screen down-left
```

## 3.2 Position

```ts
interface TownGridPosition {
  cellX: number;
  cellY: number;
  elevationLevel: number;
}
```

`elevationLevel`は整数のlogical level。

pixel値を保存しない。

## 3.3 Orientation

```ts
type TownOrientation = 0 | 90 | 180 | 270;
```

```txt
0   = North (-Y)
90  = East  (+X)
180 = South (+Y)
270 = West  (-X)
```

## 3.4 Projection

```ts
interface TownGridMetric {
  tileWidthPx: number;
  tileHeightPx: number;
  elevationStepPx: number;
}

function gridToScreen(
  position: TownGridPosition,
  metric: TownGridMetric,
): { x: number; y: number } {
  return {
    x: (position.cellX - position.cellY) * (metric.tileWidthPx / 2),
    y:
      (position.cellX + position.cellY) * (metric.tileHeightPx / 2) -
      position.elevationLevel * metric.elevationStepPx,
  };
}
```

camera scale / viewport offsetは後から適用する。

---

# 4. Map Definition

```ts
interface TownMapDefinition {
  mapDefinitionId: string;
  mapDefinitionVersion: number;
  spatialSchemaVersion: string;
  gridWidth: number;
  gridHeight: number;
  terrain: TownTerrainCellDefinition[];
  parcels: TownParcelDefinition[];
  expansionZones: TownExpansionZoneDefinition[];
  chunkMetric?: {
    width: number;
    height: number;
  };
}
```

公開済みversionをin-place変更しない。

## Expansion rule

Map拡張で既存座標原点を移動しない。

既存cell座標を保持したまま、新chunk / districtを追加する。

---

# 5. Terrain Model

各cellは必ず一つのbase terrainを持つ。

```ts
type TownTerrainKind =
  | 'grass'
  | 'soil'
  | 'sand'
  | 'stone'
  | 'coast'
  | 'water';

interface TownTerrainCellDefinition {
  position: TownGridPosition;
  terrainKind: TownTerrainKind;
}
```

waterをterrainと別solid objectで二重管理しない。

Terrain heightの自由編集は当面No-Go。

---

# 6. Parcel Model

```ts
interface TownParcelDefinition {
  parcelId: string;
  origin: TownGridPosition;
  width: number;
  height: number;
  allowedCategories: TownObjectCategory[];
  systemReserved: boolean;
  userEditablePhase: 'never' | 'decor_only' | 'relocatable_later';
  allowedFeatureIds?: TownFeatureId[];
}
```

初期parcel:

- cinema-main
- story-house-main
- market-main
- port-main
- warehouse-main
- central-square

主要建物はparcel内へ置く。

---

# 7. Growth Envelope

```ts
interface TownGrowthEnvelope {
  featureId: TownFeatureId;
  envelopeVersion: number;
  reservedCells: TownRelativeCell[];
  supportedStages: number[];
}
```

Rules:

- 承認済みstageの最大領域を予約
- user decorationはenvelope外slotへ
- overlay slotはstageと共存可能
- envelopeを超えるstageはmap migration対象
- stage変更でuser objectを削除しない

---

# 8. Object Categories

```ts
type TownObjectCategory =
  | 'structure'
  | 'tree'
  | 'flower'
  | 'ground_decor'
  | 'raised_decor'
  | 'furniture'
  | 'vehicle'
  | 'seasonal'
  | 'semantic_overlay';
```

Base terrainとphysical pathは専用stateで扱う。

```txt
地形・道・花 = tile単位
木・家具 = object単位
建物 = multi-cell完成sprite
```

建物を1cellごとの壁や屋根に分解しない。

---

# 9. Object Definition

```ts
interface TownObjectDefinition {
  definitionId: string;
  definitionVersion: number;
  category: TownObjectCategory;
  footprint: TownFootprint;
  placementRules: TownPlacementRules;
  renderVariants: TownRenderVariant[];
  interaction?: TownInteractionDefinition;
  tags: string[];
  deprecatedAt?: string;
  replacementDefinitionId?: string;
}
```

Rules:

- definitionIdを別の意味で再利用しない
- display nameからID生成しない
- asset差し替えでIDを変えない
- 廃止はdeleteではなくdeprecated
- published versionをin-place変更しない

---

# 10. Footprint Contract

```ts
interface TownRelativeCell {
  dx: number;
  dy: number;
}

interface TownFootprint {
  pivotCell: { dx: 0; dy: 0 };
  occupiedCells: TownRelativeCell[];
  walkableCells?: TownRelativeCell[];
  entranceCells?: TownRelativeCell[];
  clearanceCells?: TownRelativeCell[];
  reservedGrowthCells?: TownRelativeCell[];
  depthAnchor: { dx: number; dy: number };
}
```

Rules:

- negative offset許可
- pivot中心にrotation
- rotation後にnormalizeしない
- positionはpivotのmap位置
- collisionはsprite boundsではなくfootprint
- transparent余白をsort根拠にしない

---

# 11. Placement Layers

```ts
type TownPlacementLayer =
  | 'surface_path'
  | 'ground_object'
  | 'solid_object'
  | 'raised_object'
  | 'semantic_overlay'
  | 'ambient_effect';
```

Base terrainは別state。

例:

```txt
grass + footpath = possible
footpath + flower = rule-dependent
footpath + cinema = impossible
cinema + seasonal flag overlay = possible
road + semantic glow = possible
```

---

# 12. Town Object Instance

```ts
type TownObjectOrigin =
  | 'template'
  | 'user'
  | 'migration'
  | 'system_unlock';

type TownPlacementState =
  | 'placed'
  | 'stored'
  | 'retired';

type TownLockPolicy =
  | 'system_fixed'
  | 'decor_editable'
  | 'relocatable_later'
  | 'user_owned';

interface TownObjectInstance {
  instanceId: string;
  definitionId: string;
  definitionVersion: number;
  mapId: string;
  parcelId?: string;
  placementState: TownPlacementState;
  position?: TownGridPosition;
  orientation: TownOrientation;
  origin: TownObjectOrigin;
  lockPolicy: TownLockPolicy;
  variantKey?: string;
  createdAt: string;
  updatedAt: string;
}
```

禁止:

- `source: 'projection'`
- stored objectをmagic coordinateへ置く
- boolean lockedだけで権限判断

---

# 13. Physical Path Model

永続化するのはpathの種類だけ。

```ts
interface TownPathCellState {
  position: TownGridPosition;
  pathType: 'road' | 'footpath' | 'plaza' | 'bridge';
}
```

connection maskは周囲からscene composition時に導出する。

```txt
N = 1
E = 2
S = 4
W = 8
```

maskをDB正本にしない。

## Physical vs Semantic

```txt
Physical Path
= templateまたはuserが配置した生活道路

Semantic Connection Overlay
= 確定した記憶関係を示す光、線、航路
```

同じtable / modelにしない。

---

# 14. Decoration Slot

自由配置より前にslot式で拡張する。

```ts
interface TownDecorationSlot {
  slotId: string;
  ownerInstanceId?: string;
  position: TownGridPosition;
  allowedCategories: TownObjectCategory[];
  allowedTags?: string[];
  occupiedByInstanceId?: string;
}
```

例:

- 映画館前poster slot
- 市場横flower slot
- 港の船slot
- 中央広場month capsule slot

Growth envelope内へ危険な恒久objectを置かせない。

---

# 15. Default Layout Template

```ts
interface TownLayoutTemplate {
  templateId: string;
  templateVersion: number;
  mapDefinitionId: string;
  mapDefinitionVersion: number;
  placements: TownObjectTemplatePlacement[];
  pathCells: TownPathCellState[];
  featureBindings: TownFeatureBinding[];
}
```

MVPの固定layoutもcodeへ直書きしない。

新規ユーザーはtemplateからlayoutを生成する。

Instance IDはlayout namespace + stable seedからdeterministic生成する。

---

# 16. Template Evolution

TownLayoutはbaselineを持つ。

```ts
interface TownLayoutBaseline {
  templateId: string;
  templateVersion: number;
  generatedAt: string;
}
```

更新時:

```txt
old template baseline
+ current user layout
+ new template
→ three-way merge
```

Rules:

- user未変更のtemplate objectのみ自動更新
- user変更を上書きしない
- new featureはreserved parcelへ
- placement失敗はstoredへ
- deprecated objectを消さない
- preview / audit / rollback

Townをnew templateから丸ごと再生成しない。

---

# 17. Building Growth

Stageは同じfeature / instanceのvisual variantとして扱う。

```ts
interface TownStructureSceneState {
  featureId: TownFeatureId;
  objectInstanceId: string;
  displayStage: number;
  renderVariantKey: string;
  badges: string[];
}
```

Rules:

- stage変更でinstanceId不変
- route不変
- feature binding不変
- parcel不変
- entrance contract維持
- growth envelope内
- user decoration削除なし

---

# 18. Placement Validation

```ts
interface TownPlacementValidationResult {
  valid: boolean;
  errors: TownPlacementIssue[];
  warnings: TownPlacementIssue[];
  affectedInstanceIds: string[];
}

interface TownPlacementIssue {
  code: string;
  cell?: TownGridPosition;
  instanceId?: string;
  messageKey: string;
}
```

Validation order:

```txt
schema
→ ownership / permission
→ definition availability
→ map bounds
→ parcel rules
→ footprint collision
→ placement layer
→ growth envelope
→ entrance clearance
→ category limits
→ apply
```

Stable code例:

- OUT_OF_MAP_BOUNDS
- PARCEL_CATEGORY_DENIED
- SOLID_COLLISION
- GROWTH_ENVELOPE_RESERVED
- ENTRANCE_BLOCKED
- LOCK_POLICY_DENIED
- UNKNOWN_DEFINITION
- STALE_LAYOUT_REVISION

Renderer内でvalidator ruleを決めない。

---

# 19. Editor Command Batch

町の変更はrowを直接書き換えない。

```ts
interface TownLayoutCommandBatch {
  batchId: string;
  expectedLayoutRevision: number;
  commands: TownLayoutCommand[];
  clientSessionId: string;
  createdAt: string;
}
```

Flow:

```txt
load revision R
→ local draft
→ local validation
→ undo / redo
→ Save
→ server atomic revalidation
→ compare-and-swap revision R
→ revision R+1
```

Rules:

- batch all-or-nothing
- batchId idempotency
- silent last-write-wins禁止
- stale revision拒否
- server authoritative validation
- CRDTは初期採用しない

---

# 20. Persistence Contract

Current stateを正本とする。

```txt
town_map
town_layout
town_layout_object
town_path_cell
town_feature_binding
town_feature_progress
town_environment_preference
town_layout_revision
town_layout_event
town_projection_snapshot
```

`towm_layout_event`は監査・復旧補助であり、唯一の正本ではない。

全user tableに`user_id`を持たせる。

## Snapshot

作成タイミング:

- migration前
- saved layout変更前後
- reset前
- catalog major upgrade前

永久無制限保存はしない。

---

# 21. Migration and Recovery

## Invalid placement recovery

```txt
new ruleでvalidate
→ affected instance列挙
→ same parcel safe relocation
→ 失敗時stored state
→ user explanation
→ rollback snapshot保持
```

Magic coordinateを使わない。

町の破損でMemory OS本体を起動不能にしない。

## Definition migration

- deprecated instanceを保持
- replacement mapping
- missing asset placeholder
- feature binding維持
- user layout維持

---

# 22. RLS / Security

必須:

- user_id
- RLS fail closed
- cross-user layout ID拒否
- cross-user instance ID拒否
- unknown definition拒否
- locked system object mutation拒否
- command batch size limit
- rate limit
- auditへmemory本文を入れない

Client validationだけで保存しない。

---

# 23. Export / Import / Reset

Town export section:

```txt
feature progress
layout
feature bindings
paths
environment preferences
version set
```

Memory dataと分離する。

Re-import:

```txt
parse
→ compatibility
→ definition availability
→ placement validation
→ Preview
→ unsupported objectをstored
→ atomic import
```

Reset options:

- visual growth
- layout
- decorations
- feature progress
- whole town

Account deletionではTown stateを全削除する。

---

# 24. Rendering Contract

```ts
interface TownSceneSnapshot {
  sceneSchemaVersion: string;
  map: TownMapRenderProjection;
  terrain: TownTerrainRenderProjection[];
  paths: TownPathRenderProjection[];
  objects: TownObjectRenderProjection[];
  semanticConnections: TownSemanticConnectionRenderProjection[];
  environment: TownEnvironmentState;
}
```

```txt
Memory Domain
→ feature projection

Feature Progress
+ Layout
+ Environment
+ feature binding
→ spatial scene projector
→ TownSceneSnapshot
→ PixiJS
```

Renderer内でbusiness ruleを決めない。

---

# 25. Deterministic Z Ordering

sort key:

```txt
1. placement layer order
2. projected depthAnchor Y
3. elevationLevel
4. definition sortOffset
5. instanceId
```

同じ入力から同じscene順を得る。

---

# 26. Citizens and Navigation

MVPでは固定短経路でよい。

将来:

```ts
interface TownNavigationCell {
  position: TownGridPosition;
  walkable: boolean;
  movementCost: number;
  connectors: TownGridPosition[];
}
```

- building entrance
- bridge
- pier

はnavigation connectorを持つ。

住人route、physical path、semantic connectionは別物。

---

# 27. Performance Strategy

長期対応:

- chunk culling
- static terrain / path cache
- sprite atlas
- object pooling
- offscreen animation pause
- visible chunk hit test
- low power mode
- citizen budget
- seasonal lazy load

MVPで全最適化を実装しない。

Scene modelが後からchunk化を妨げないことを必須にする。

---

# 28. Accessibility

WebGLだけを唯一の操作方法にしない。

必要:

- object list alternative
- DOM editor alternative
- keyboard / switch操作
- object名、状態の読み上げ
- reduced motion
- high contrast selection
- undo
- static fallback

---

# 29. Test Contract

## Spatial unit

- gridToScreen / screenToGrid
- footprint rotation
- collision
- parcel bounds
- growth envelope
- entrance clearance
- path derived mask
- deterministic depth sort

## Property

- 4 rotationで元へ戻る
- serialize round trip
- path add/remove後mask整合
- input order変更でcollision結果不変

## Migration

- catalog upgrade
- deprecated object preservation
- three-way template merge
- invalid placement recovery
- stored object
- rollback snapshot
- layout revision conflict

## Separation

- memory削除後もuser decoration保持
- skin変更でfeature progress保持
- layout移動でmemory不変
- environment変更でfeature projection不変
- hidden / sealed非流入

## Security

- cross-user references拒否
- missing user context拒否
- locked object mutation拒否
- private fields非流入

---

# 30. Initial Implementation Definition

内部契約として最初から必要:

```txt
TownFeatureId
feature binding
feature progress
logical grid
coordinate convention
map definition
terrain
parcel
growth envelope
layout template
object catalog
object instance
footprint pivot
path state
placement validator
layout revision
RLS ownership
static fallback
```

MVP UIでは実装しない:

```txt
free placement editor
path painting
building relocation
terrain editing
rotation UI
inventory
currency
crafting
```

内部は最初から将来型、表面は最小構成にする。

---

# Decision Summary

```txt
Minecraftのような1block建築ではない。
どうぶつの森のように、自分の町へ愛着を持てる箱庭を目指す。

固定するのはcamera viewpoint。
配置schemaは最初から編集可能なlogical grid。

地面・道・花はtile単位。
木・家具はobject単位。
建物はmulti-cellの完成sprite。

Featureの意味、解除済み成長、配置、環境、描画を分離する。
MVPは固定layout。
将来、装飾、道、植栽、建物移動を段階的に解放できる。
```

この構造をMemory Town空間実装の正本とする。
