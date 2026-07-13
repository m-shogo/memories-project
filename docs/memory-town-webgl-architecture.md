# Memory Town WebGL Architecture

最終更新: 2026-07-13

## 目的

固定視点2.5DのMemory TownをWebGLで実装する際の責務境界、data flow、logical grid、performance、fallback、test方針を固定する。

優先正本:

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-long-term-spatial-model.md`

---

## Technology Decision

採用:

```txt
PixiJS
+ WebGL renderer
+ React / DOM UI
+ fixed-view 2.5D sprites
+ logical isometric grid
+ parcel / footprint placement
+ config-driven definitions
```

MVPでは採用しない:

- 生WebGLの直接実装
- Three.jsによる本格3D
- camera rotation
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

# 1. Responsibility Boundary

## React / DOM

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
- future town editor controls
- undo / redo
- conflict resolution UI
- migration / reset Preview

## PixiJS Renderer

- terrain
- physical paths
- structures
- props
- passive citizens
- boats
- seasonal overlays
- ambient effects
- semantic connection overlays
- selection highlight
- short camera focus
- placement preview
- valid / invalid placement visualization

RendererはMemory Domain、DB、growth rulesへ直接accessしない。

---

# 2. Five-state Ownership

```txt
Memory Domain State
Town Feature Progress State
Town Layout State
Town Environment State
Town Render State
```

Rendererが受け取るのは、上位4状態から生成された`TownSceneSnapshot`だけ。

## Prohibited mixing

- season / timeをTownFeatureProjectionへ入れない
- cameraをTownLayoutへ入れない
- user decorationをMemory Domainへ入れない
- max unlocked stageをrendererで計算しない
- layout objectをProjectionから生成しない

---

# 3. Data Flow

```txt
Memory Domain records
→ policy filter
→ TownFeatureProjection

TownFeatureProgress
→ unlocked stage state

Town Layout current state
→ spatial validation
→ TownLayoutSnapshot

Town Environment preference
→ TownEnvironmentSnapshot

FeatureProjection
+ FeatureProgress
+ FeatureBinding
+ TownLayoutSnapshot
+ TownEnvironmentSnapshot
→ TownSceneSnapshot
→ PixiJS
```

Memory deletion、layout editing、theme変更が互いの正本を書き換えない。

---

# 4. Feature Projection

```ts
interface TownFeatureProjection {
  schemaVersion: string;
  rulesetVersion: string;
  generatedAt: string;
  features: TownFeatureProjectionItem[];
  semanticConnections: TownSemanticConnectionProjection[];
}

interface TownFeatureProjectionItem {
  featureId: TownFeatureId;
  eligibleItemCount: number;
  recentDelta: number;
  candidateStage: number;
  route: string;
  badges: Array<'new' | 'continued' | 'capsule'>;
}

interface TownSemanticConnectionProjection {
  connectionId: string;
  fromFeatureId: TownFeatureId;
  toFeatureId: TownFeatureId;
  relationType: string;
  strengthBand: 'weak' | 'normal' | 'strong';
  confirmed: boolean;
}
```

含めない:

- raw title
- body
- person name
- chat text
- private image URL
- precise location
- season
- time
- camera

---

# 5. Feature Progress

```ts
interface TownFeatureProgressSnapshot {
  schemaVersion: string;
  features: Array<{
    featureId: TownFeatureId;
    maxUnlockedStage: number;
    growthRulesetVersion: string;
    resetEpoch: number;
  }>;
}
```

Scene composition時:

```ts
displayStage = Math.max(candidateStage, maxUnlockedStage);
```

Rendererはこのmax計算結果だけを受け取り、unlock persistenceを行わない。

Unlock event保存はapplication layerの責務。

---

# 6. Town Layout Snapshot

```ts
interface TownLayoutSnapshot {
  spatialSchemaVersion: string;
  layoutId: string;
  userId: string;
  layoutRevision: number;
  baseline: {
    templateId: string;
    templateVersion: number;
  };
  mapDefinitionId: string;
  mapDefinitionVersion: number;
  objectCatalogVersion: number;
  growthEnvelopeVersion: number;
  objects: TownObjectInstance[];
  featureBindings: TownFeatureBinding[];
  pathCells: TownPathCellState[];
}
```

## Object Instance

```ts
interface TownObjectInstance {
  instanceId: string;
  definitionId: string;
  definitionVersion: number;
  parcelId?: string;
  placementState: 'placed' | 'stored' | 'retired';
  position?: {
    cellX: number;
    cellY: number;
    elevationLevel: number;
  };
  orientation: 0 | 90 | 180 | 270;
  origin: 'template' | 'user' | 'migration' | 'system_unlock';
  lockPolicy:
    | 'system_fixed'
    | 'decor_editable'
    | 'relocatable_later'
    | 'user_owned';
  variantKey?: string;
}
```

禁止:

- screen x / y永続化
- `source: 'projection'`
- magic coordinate storage
- boolean lockedだけのpermission

---

# 7. Feature Binding

```ts
interface TownFeatureBinding {
  bindingId: string;
  featureId: TownFeatureId;
  objectInstanceId: string;
  bindingRole: 'primary' | 'secondary' | 'portal';
}
```

Scene composerはfeatureIdをbindingからvisual instanceへ解決する。

Skin、definition、positionが変わってもfeatureIdを維持する。

---

# 8. Environment Snapshot

```ts
interface TownEnvironmentSnapshot {
  schemaVersion: string;
  themeId: string;
  effectiveSeason: 'spring' | 'summer' | 'autumn' | 'winter';
  timeMode: 'day' | 'evening' | 'night';
  weatherVisual: 'clear' | 'rain' | 'snow';
  motionLevel: 'off' | 'reduced' | 'full';
  soundEnabled: boolean;
}
```

Actual weather / GPS連携は必須にしない。

---

# 9. Town Scene Snapshot

```ts
interface TownSceneSnapshot {
  sceneSchemaVersion: string;
  generatedAt: string;
  map: TownMapRenderProjection;
  terrain: TownTerrainRenderProjection[];
  paths: TownPathRenderProjection[];
  objects: TownObjectRenderProjection[];
  semanticConnections: TownSemanticConnectionRenderProjection[];
  environment: TownEnvironmentSnapshot;
}
```

Rendererはこのsnapshotだけで描画できる。

Snapshotには互換性確認用version setを含めてもよい。

---

# 10. Logical Grid Projection

```ts
interface TownGridMetric {
  tileWidthPx: number;
  tileHeightPx: number;
  elevationStepPx: number;
}

function gridToScreen(
  cellX: number,
  cellY: number,
  elevationLevel: number,
  metric: TownGridMetric,
): { x: number; y: number } {
  return {
    x: (cellX - cellY) * (metric.tileWidthPx / 2),
    y:
      (cellX + cellY) * (metric.tileHeightPx / 2) -
      elevationLevel * metric.elevationStepPx,
  };
}
```

Coordinate rule:

```txt
origin = logical north-west
+X = east
+Y = south
```

camera scale / viewport offsetはprojection後に適用する。

---

# 11. Footprint and Pivot

```ts
interface TownFootprint {
  pivotCell: { dx: 0; dy: 0 };
  occupiedCells: Array<{ dx: number; dy: number }>;
  walkableCells?: Array<{ dx: number; dy: number }>;
  entranceCells?: Array<{ dx: number; dy: number }>;
  clearanceCells?: Array<{ dx: number; dy: number }>;
  reservedGrowthCells?: Array<{ dx: number; dy: number }>;
  depthAnchor: { dx: number; dy: number };
}
```

- negative relative coordinate許可
- pivot中心rotation
- rotation後normalize禁止
- sprite boundsをcollisionへ使用しない

---

# 12. Object Definition

```ts
interface TownObjectDefinition {
  definitionId: string;
  definitionVersion: number;
  category:
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
  replacementDefinitionId?: string;
}
```

Base terrainとphysical pathは専用stateで扱う。

New objectはrenderer code変更ではなくdefinition / asset追加で対応する。

---

# 13. Structure Contract

```ts
interface TownStructureDefinition extends TownObjectDefinition {
  supportedFeatureIds: TownFeatureId[];
  stageVariants: Array<{
    stage: number;
    textureKey: string;
    visualAnchor: { x: number; y: number };
    hitPolygon: Array<{ x: number; y: number }>;
    overlaySlots: string[];
    footprintContractVersion: number;
  }>;
}
```

Rules:

- structureはmulti-cell完成sprite
- building functionをdefinitionIdへ固定しない
- max approved stageはgrowth envelope内
- stage変更でinstanceId不変
- entrance contract維持
- user decoration削除なし

---

# 14. Terrain and Path

## Terrain

各cellに一つのbase terrain。

```ts
type TownTerrainKind =
  | 'grass'
  | 'soil'
  | 'sand'
  | 'stone'
  | 'coast'
  | 'water';
```

## Path

```ts
interface TownPathCellState {
  position: {
    cellX: number;
    cellY: number;
    elevationLevel: number;
  };
  pathType: 'road' | 'footpath' | 'plaza' | 'bridge';
}
```

connection maskはpersistしない。

Scene composerが隣接cellから導出する。

Physical pathとsemantic connectionを同じlayer / modelにしない。

---

# 15. Scene Composition

```txt
validate layout snapshot
→ resolve feature bindings
→ resolve display stages
→ resolve render variants
→ derive path masks
→ apply environment overlays
→ build deterministic sort keys
→ TownSceneSnapshot
```

Composition failure時:

- missing assetはplaceholder
- invalid objectはrendererで消さず、stored / repair対象
- scene全体を落とさない
- error codeをtelemetryへ送る

Memory contentをlogへ出さない。

---

# 16. Deterministic Sort

sort key:

```txt
1. layer order
2. projected depthAnchor Y
3. elevationLevel
4. definition sortOffset
5. instanceId
```

Stable sort前提に依存せず、instanceIdまでkeyに含める。

---

# 17. Layout Template

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

MVP固定mapもcomponentへ直書きしない。

User layout更新時はthree-way mergeを使う。

```txt
old baseline
+ current layout
+ new template
```

new templateで町を丸ごと再生成しない。

---

# 18. Placement Validation

Application domain serviceとして独立。

```txt
schema
→ ownership
→ permission
→ definition availability
→ map bounds
→ parcel
→ footprint collision
→ layer
→ growth envelope
→ entrance clearance
→ category limit
```

Structured result:

```ts
interface TownPlacementValidationResult {
  valid: boolean;
  errors: TownPlacementIssue[];
  warnings: TownPlacementIssue[];
  affectedInstanceIds: string[];
}
```

Rendererのdrag結果をそのまま保存しない。

---

# 19. Editor Interaction Bridge

PixiJSはinstance IDとpreview intentだけをapplicationへ返す。

```txt
pointertap
→ onTownObjectSelected(instanceId)
→ React state
→ DOM sheet
```

Future editor:

```txt
drag preview
→ screenToGrid
→ local draft command
→ local validation result
→ Pixi valid / invalid visualization
→ Save button
→ atomic command batch
```

重要操作はDOM側。

町内で禁止:

- record deletion
- memory bulk edit
- permission change
- export confirmation
- security-sensitive action

---

# 20. Editor Save Contract

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
→ undo / redo
→ Save
→ server revalidation
→ atomic transaction
→ CAS revision R
→ revision R+1
```

- last-write-wins禁止
- batch all-or-nothing
- batch ID idempotency
- CRDT初期採用なし

---

# 21. Camera

```ts
interface TownCameraState {
  mode: 'overview' | 'district' | 'focused';
  focusedInstanceId?: string;
  districtId?: string;
}
```

MVP:

- overview
- focused

Rules:

- camera pixel position非永続
- logical target / presetだけを扱う
- bottom sheet reserveを考慮
- reduced motionでは即時切替
- navigationはanimation完了待ちにしない

---

# 22. Asset Loading

## Required metadata

- stable texture key
- content hash
- asset manifest version
- supported orientation
- visual anchor
- depth anchor
- hit polygon
- render bounds
- footprint contract version
- overlay compatibility
- fallback texture key
- provenance / license

## Loading

MVP:

- initial atlas 1〜2個
- seasonal asset lazy load可
- high-density mobile向け解像度

Long-term:

- catalog / district split
- chunk lazy load
- orientation variants
- deprecated fallback

Rules:

- atlas再編でtexture key不変
- CDN failureでstatic fallback
- missing assetでinstance消失なし
- mirrored text禁止

---

# 23. Renderer Lifecycle

- route enterでinitialize / resume
- route leaveでticker停止
- hidden tabでanimation停止
- context lossでfallback
- context restoreでSceneSnapshotから再構築
- renderer stateを正本にしない
- low powerでambient停止

---

# 24. Performance Budget

MVP guideline:

```txt
structures: 5〜8
small props: 30〜60
active citizens: 0〜5
active vehicles: 0〜2
simultaneous effects: 20以下
```

数値は実機検証で固定する。

Long-term:

- chunk culling
- static terrain / path cache
- visible chunk hit test
- sprite pooling
- offscreen animation pause
- atlas split by district

常時60fpsより、操作可能性、発熱、batteryを優先する。

---

# 25. Fallback

WebGL unavailable / context loss / asset failure時:

```txt
static town image
+ DOM feature buttons
+ object list alternative
```

同じTownFeatureProjection、FeatureProgress、Layoutからfallbackを作る。

WebGLが使えなくても棚、検索、Import、振り返りを利用可能。

---

# 26. Privacy / Security

TownSceneSnapshotへ渡さない:

- raw memory
- title
- person name
- chat body
- private image URL
- precise location history

全user town table:

- user_id
- RLS fail closed
- cross-user reference拒否
- server authoritative validation

Telemetryへprivate contentを送らない。

---

# 27. Version Set

```ts
interface TownVersionSet {
  spatialSchemaVersion: string;
  featureRegistryVersion: number;
  mapDefinitionVersion: number;
  layoutTemplateVersion: number;
  objectCatalogVersion: number;
  growthEnvelopeVersion: number;
  featureProjectionSchemaVersion: string;
  growthRulesetVersion: string;
  assetManifestVersion: string;
  sceneSchemaVersion: string;
}
```

一つのversionへまとめない。

---

# 28. Test Contract

## Spatial

- gridToScreen / screenToGrid
- footprint pivot rotation
- collision
- parcel bounds
- growth envelope
- entrance clearance
- derived path mask
- deterministic depth sort

## State separation

- memory削除後もuser decoration保持
- skin変更でfeature progress保持
- environment変更でfeature projection不変
- layout変更でmemory不変
- hidden / sealed非流入

## Rendering

- multiple viewport deterministic render
- missing asset fallback
- context loss
- route leave ticker pause
- reduced motion
- large map culling

## Migration

- definition upgrade
- deprecated preservation
- three-way template merge
- stored object recovery
- layout revision conflict

## Security

- cross-user layout拒否
- locked mutation拒否
- unknown definition拒否
- private field snapshot拒否

---

# Initial Implementation Contract

最初から内部契約として必要:

```txt
TownFeatureId
feature binding
feature progress
logical grid
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

# Final Decision

```txt
見た目は固定視点2.5D。
保存形式はlogical grid。
主要建物はparcel内のmulti-cell sprite。
道路はcell state、maskは導出。

Featureの意味、解除済み成長、配置、環境、描画を分離する。
MVPでは町を編集できない。
しかし将来の装飾、道、植栽、建物移動のために、
最初から固定pixel座標へ依存しない。
```
