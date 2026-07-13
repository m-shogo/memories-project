# Memory Town WebGL Architecture

最終更新: 2026-07-13

## 目的

固定2.5DのMemory TownをWebGLで実装する際の責務境界、data flow、logical grid、performance、fallback、test方針を固定する。

空間モデルの正本:

- `docs/memory-town-long-term-spatial-model.md`

## Technology Decision

採用:

```txt
PixiJS
+ WebGL renderer
+ React / DOM UI
+ fixed 2.5D sprites
+ logical isometric grid
+ parcel / footprint placement
+ config-driven object definitions
```

MVPでは採用しない:

- 生WebGLによる直接実装
- Three.jsによる本格3D
- 自由camera
- physics engine
- user-controlled avatar
- free placement editor
- path painting UI
- WebGL内のform / long text / list UI

重要:

```txt
free placement UIをMVPで作らない
≠
内部を固定pixel座標で作る
```

内部は最初からlogical gridで管理する。

---

## Responsibility Boundary

### DOM / Application UI

- navigation
- shelf grid
- search
- import preview
- forms
- dialogs
- building summary card
- accessibility alternative
- settings
- reduced motion / low power controls
- 将来のtown editor controls
- undo / redo UI

### PixiJS / Town Renderer

- terrain
- paths
- buildings
- props
- passive citizens
- boats
- seasonal overlays
- ambient effects
- selection highlight
- short camera focus
- placement preview
- valid / invalid placement visualization

WebGL rendererはmemoryの正本を直接読まない。

---

## State Separation

```txt
Memory Domain State
Town Projection State
Town Layout State
Town Render State
```

### Memory Domain State

棚、Import、進行、箱、確定したconnectionの正本。

### Town Projection State

建物stage、badge、recent deltaなど、Memory Domainから導出される状態。

### Town Layout State

map上に何がどこへ配置されているか。

MVPの固定配置もlayout templateから生成する。

### Town Render State

camera、selection、animation、loaded textureなど、その描画sessionだけの状態。

永続化しない。

---

## Data Flow

```txt
Domain records
→ policy filter
→ aggregate projector
→ TownProjection

Town layout template / user layout
→ spatial validator
→ TownLayoutSnapshot

TownProjection + TownLayoutSnapshot
→ TownSceneSnapshot
→ PixiJS scene
```

ProjectionとLayoutを混ぜない。

- memory削除でuser decorationを消さない
- building移動でmemory recordを変えない
- stage変更でinstance IDを変えない

---

## TownProjection

```ts
interface TownProjection {
  schemaVersion: string;
  rulesetVersion: string;
  generatedAt: string;
  season: 'spring' | 'summer' | 'autumn' | 'winter';
  timeMode: 'day' | 'evening' | 'night';
  structures: TownStructureProjection[];
  semanticConnections: TownConnectionProjection[];
  ambient: TownAmbientProjection;
}

interface TownStructureProjection {
  structureInstanceId: string;
  buildingId: string;
  stage: number;
  itemCount: number;
  recentDelta: number;
  pendingCount?: number;
  hasNewVisualChange: boolean;
  route: string;
  badges: Array<'new' | 'continued' | 'capsule'>;
}

interface TownConnectionProjection {
  id: string;
  fromStructureInstanceId: string;
  toStructureInstanceId: string;
  relationType: string;
  strengthBand: 'weak' | 'normal' | 'strong';
  confirmed: boolean;
}

interface TownAmbientProjection {
  citizenDensity: 'none' | 'low' | 'normal';
  boatVisible: boolean;
  lightsEnabled: boolean;
  weather: 'clear' | 'rain' | 'snow';
}
```

町へraw title、本文、人名、会話内容、private image URLを渡さない。

---

## TownLayoutSnapshot

```ts
interface TownLayoutSnapshot {
  spatialSchemaVersion: string;
  layoutId: string;
  layoutRevision: number;
  mapDefinitionId: string;
  mapDefinitionVersion: number;
  layoutTemplateId: string;
  layoutTemplateVersion: number;
  objectCatalogVersion: number;
  objects: TownObjectInstance[];
  pathCells: TownPathCell[];
}

interface TownObjectInstance {
  instanceId: string;
  definitionId: string;
  definitionVersion: number;
  parcelId?: string;
  position: {
    cellX: number;
    cellY: number;
    elevation: number;
  };
  orientation: 0 | 90 | 180 | 270;
  source: 'system' | 'projection' | 'user';
  locked: boolean;
  variantKey?: string;
}
```

MVPではすべてsystem template由来でも、この形式を使う。

`position: { x, y }` の画面座標は永続化しない。

---

## TownSceneSnapshot

```ts
interface TownSceneSnapshot {
  sceneSchemaVersion: string;
  map: TownMapRenderProjection;
  terrain: TownTerrainRenderProjection[];
  paths: TownPathRenderProjection[];
  objects: TownObjectRenderProjection[];
  semanticConnections: TownSemanticConnectionRenderProjection[];
  ambient: TownAmbientProjection;
}
```

rendererはTownSceneSnapshotだけで描画できる。

business rule、growth threshold、privacy filteringをrendererへ入れない。

---

## Logical Grid Projection

```ts
interface TownGridMetric {
  tileWidth: number;
  tileHeight: number;
  elevationStepPx: number;
}

function gridToScreen(
  cellX: number,
  cellY: number,
  elevation: number,
  metric: TownGridMetric,
): { x: number; y: number } {
  return {
    x: (cellX - cellY) * (metric.tileWidth / 2),
    y:
      (cellX + cellY) * (metric.tileHeight / 2) -
      elevation * metric.elevationStepPx,
  };
}
```

camera scaleやviewport offsetは、この結果へ後から適用する。

logical coordinateとscreen coordinateを混ぜない。

---

## Object Definition

```ts
interface TownObjectDefinition {
  definitionId: string;
  definitionVersion: number;
  category:
    | 'terrain'
    | 'path'
    | 'water'
    | 'structure'
    | 'tree'
    | 'flower'
    | 'ground_decor'
    | 'raised_decor'
    | 'furniture'
    | 'vehicle'
    | 'seasonal'
    | 'semantic_overlay';
  footprint: TownFootprint;
  placementRules: TownPlacementRules;
  renderVariants: TownRenderVariant[];
  interaction?: TownInteractionDefinition;
  deprecatedAt?: string;
}

interface TownFootprint {
  occupiedCells: Array<{ dx: number; dy: number }>;
  walkableCells?: Array<{ dx: number; dy: number }>;
  entranceCells?: Array<{ dx: number; dy: number }>;
  clearanceCells?: Array<{ dx: number; dy: number }>;
  depthAnchor: { dx: number; dy: number };
}
```

新しいobjectはrenderer codeを大きく変更せず、definitionとassetsの追加で対応する。

---

## Building Contract

建物は1cellごとのブロックへ分解しない。

```txt
terrain / road / flower = tile
small prop / tree / furniture = object
building = multi-cell completed sprite
```

主要建物はparcelを持つ。

- 最大stage footprintを最初から予約
- stage変更でinstanceIdを維持
- routeを維持
- entrance contractを維持
- user decorationを黙って削除しない

### Initial Structure Definition

```ts
interface TownStructureDefinition extends TownObjectDefinition {
  buildingId: string;
  shelfType: string;
  route: string;
  stageVariants: Array<{
    stage: number;
    textureKey: string;
    visualAnchor: { x: number; y: number };
    hitPolygon: Array<{ x: number; y: number }>;
    overlaySlots: string[];
  }>;
}
```

---

## Path System

物理的な道はgrid cellで持つ。

```ts
interface TownPathCell {
  position: {
    cellX: number;
    cellY: number;
    elevation: number;
  };
  pathType: 'road' | 'footpath' | 'plaza' | 'bridge';
  connectionMask: number;
}
```

N/E/S/W接続maskからautotile spriteを選択する。

### Physical Path and Semantic Connection

```txt
Physical Path
= templateまたはuserが配置した生活道路

Semantic Connection
= 記憶同士の確定関係を示す演出
```

同じDB rowや同じlayerにしない。

---

## Scene Graph

```txt
TownRoot
├─ TerrainLayer
├─ PathLayer
├─ RearPropLayer
├─ StructureLayer
├─ FrontPropLayer
├─ CitizenLayer
├─ VehicleLayer
├─ SeasonalLayer
├─ SemanticConnectionLayer
├─ AmbientEffectLayer
└─ SelectionLayer
```

### Z Ordering

- static terrainはgrid order
- building / citizen / propはdepthAnchorのscreen Yでsort
- decorative overlaysは親instanceに追従
- hit targetとvisual boundsを分離

```ts
sprite.zIndex = projectedDepthAnchorY + sortOffset;
```

sprite画像のbottom edgeだけでsortしない。

---

## Layout Template

固定mapもcodeへ座標を直書きしない。

```ts
interface TownLayoutTemplate {
  templateId: string;
  templateVersion: number;
  mapDefinitionId: string;
  placements: Array<{
    definitionId: string;
    instanceIdSeed: string;
    parcelId?: string;
    position: {
      cellX: number;
      cellY: number;
      elevation: number;
    };
    orientation: 0 | 90 | 180 | 270;
    locked: boolean;
  }>;
}
```

MVPはtemplateから同じ町を生成する。

将来はuser layoutとの差分またはcurrent object instancesを保存する。

---

## Placement Validation

将来editorを開放する前から、validatorはdomain serviceとして独立させる。

Validation order:

```txt
schema
→ permission
→ map bounds
→ parcel rule
→ footprint collision
→ placement layer
→ entrance clearance
→ category restriction
→ apply
```

rendererのdrag結果をそのまま保存しない。

---

## Interaction Bridge

PixiJSはinstance IDだけをapplicationへ返す。

```txt
pointertap
→ onTownObjectSelected(instanceId)
→ React state update
→ DOM summary sheet
→ route navigation
```

重要操作はDOM側で行う。

### 町内で直接許可する操作

MVP:

- structure select
- focus
- overviewへ戻る
- optional ambient toggle

将来editor:

- placement preview
- move preview
- rotate preview
- valid / invalid indication

### 町内で禁止する操作

- record削除
- memory bulk edit
- text input
- permission change
- export confirmation
- security-sensitive action

---

## Camera

MVP:

```ts
interface TownCameraState {
  mode: 'overview' | 'focused';
  focusedInstanceId?: string;
}
```

- overviewは全体表示
- focusはscale / position interpolationのみ
- navigation中断可能
- reduced motionでは即時切替

将来map拡張時も、保存されるのはcamera pixel座標ではなくlogical focus targetとzoom presetにする。

---

## Asset Loading

### MVP

- texture atlasを1〜2個にまとめる
- initial town assetsをpreload
- seasonal assetsはlazy load可能
- high-density mobile向けに複数解像度

### Long-term

- object catalog単位のasset manifest
- chunk / district asset lazy load
- orientation variant
- missing asset placeholder
- deprecated definition fallback

### Rules

- atlas keyをstable ID化
- file nameをUI表示名に依存させない
- CDN failure時にstatic fallback
- asset manifestをversion管理

---

## Renderer Lifecycle

- route enter時にinitialize / resume
- route leave時にticker停止
- hidden tabでanimation停止
- context lossでstatic fallback
- context restore時にTownSceneSnapshotから再構築
- renderer stateを正本にしない

---

## Performance Budget

MVP guideline:

```txt
structures: 5〜8
small props: 30〜60
active citizens: 0〜5
active vehicles: 0〜2
simultaneous effects: 20以下
```

Long-term対応:

- chunk culling
- static tile cache
- visible chunk hit testing
- sprite pooling
- offscreen animation pause
- low power mode
- atlas split by district

常時60fpsを絶対条件にせず、操作可能性と発熱を優先する。

---

## Fallback

WebGL unavailable / context loss / asset failure時:

```txt
static town image
+ DOM building buttons
+ object list alternative
```

同じTownProjectionとTownLayoutSnapshotからfallback表示を作る。

WebGLが使えなくても棚、検索、Import、振り返りは全て利用できる。

---

## Privacy

TownSceneSnapshotへ渡さないもの:

- raw memory
- private title
- person name
- chat body
- private image URL
- precise location history

町は集計・stable IDs・視覚状態だけを扱う。

---

## Version Set

```ts
interface TownVersionSet {
  spatialSchemaVersion: string;
  mapDefinitionVersion: number;
  layoutTemplateVersion: number;
  objectCatalogVersion: number;
  projectionSchemaVersion: string;
  growthRulesetVersion: string;
  assetManifestVersion: string;
}
```

一つのversionへまとめない。

---

## Test Contract

### Spatial

- grid-to-screen
- screen-to-grid hit conversion
- footprint rotation
- collision
- parcel bounds
- entrance clearance
- path mask / autotile
- stable depth ordering

### Projection Separation

- memory削除後もuser decoration保持
- layout変更でmemory不変
- stage変更でinstanceId不変
- hidden / sealed data非流入

### Rendering

- multiple viewport deterministic render
- missing asset fallback
- context loss
- route leave ticker pause
- reduced motion
- large map chunk culling

### Migration

- definition upgrade
- deprecated object preservation
- template upgrade
- invalid placement recovery
- layout revision conflict

---

## Initial Implementation Contract

最初から実装する:

```txt
logical grid
map definition
parcel definition
layout template
object definition catalog
object instance
multi-cell footprint
grid-to-screen projection
placement validator foundation
layout revision
static fallback
```

最初は実装しないUI:

```txt
free placement editor
path painting
building relocation
terrain editing
inventory
currency
crafting
```

---

## Final Decision

```txt
見た目は固定2.5D。
保存形式はlogical grid。
主要建物はparcel内のmulti-cell sprite。
道路・花・地形はtile単位。
木・家具はobject単位。

MVPでは町を編集できない。
しかし将来の装飾、道、植栽、建物移動のために、
最初から固定pixel座標へ依存しない。
```
