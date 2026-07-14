# Memory Town Editable Landscape Model Contract — Round 7

最終更新: 2026-07-14

## Decision

Memory Townの地形は、将来次を編集・増築できるようにする。

- 海岸線・砂浜
- 川・池・水路
- 道・広場・橋
- 草地・土・石・森床
- 森・木・花
- 家・主要建物
- 地区・岬・小島

採用方式:

```txt
Hierarchical Editable Diorama
```

```txt
semantic landscape source of truth
→ rule-based projection
→ 2.5D sprite composition
```

一枚絵や最終tile IDを正本にしない。

実装はまだ開始しない。

---

# 1. Landscape state hierarchy

```txt
Town World Frame
Town District Graph
Town Terrain Region State
Town Linear Feature State
Town Parcel / Anchor State
Town Object State
Town Derived Landscape Projection
```

## 1.1 Town World Frame

町全体の外周・遠景・環境。

```ts
interface TownWorldFrameDefinition {
  worldFrameId: string;
  version: number;
  horizonProfileId: string;
  distantSeaProfileId: string;
  distantIslandProfileId?: string;
  skyProfileId: string;
  editableLandscapeBounds: TownLogicalBounds;
}
```

Rules:

- sky / horizon / distant seaはuser layoutの正本へ混ぜない
- time / seasonでvariantを変更できる
- userは近景の海岸を編集できるが、遠景海面をcellで埋めない
- world frame変更でMemory Domainを変更しない

## 1.2 Town District Graph

町の大きな増築単位。

```ts
type TownDistrictKind =
  | 'central'
  | 'culture'
  | 'market'
  | 'river'
  | 'harbor'
  | 'forest'
  | 'coast'
  | 'residential'
  | 'reflection'
  | 'custom';

interface TownDistrictInstance {
  districtInstanceId: string;
  districtDefinitionId: string;
  districtDefinitionVersion: number;
  districtKind: TownDistrictKind;
  origin: TownGridPosition;
  orientation: TownOrientation;
  attachedSocketIds: string[];
  layoutRevisionCreated: number;
}
```

Districtは一枚の画像plateではない。

District definitionが持つもの:

- logical bounds
- expansion sockets
- protected scenic corridors
- initial terrain regions
- initial linear features
- parcel candidates
- landmark anchors
- allowed coast / river exits

## 1.3 Expansion Socket

```ts
type TownExpansionSocketKind =
  | 'land'
  | 'road'
  | 'river'
  | 'coast'
  | 'harbor'
  | 'view';

interface TownExpansionSocket {
  socketId: string;
  districtInstanceId: string;
  kind: TownExpansionSocketKind;
  position: TownGridPosition;
  outwardDirection: TownOrientation;
  connectionProfileId: string;
  occupiedByDistrictInstanceId?: string;
}
```

Rules:

- new districtはapproved socketへ接続する
- existing map originを移動しない
- 既存user layoutを再生成しない
- road socket同士、river socket同士などcompatible profileだけ接続
- attach前にPreview / validation / rollbackを行う

---

# 2. Semantic terrain regions

既存の`TownTerrainCellDefinition`は描画・互換projectionとして残せるが、将来の編集source of truthはsemantic regionとする。

```ts
type TownTerrainKind =
  | 'grass'
  | 'soil'
  | 'sand'
  | 'stone'
  | 'forest_floor'
  | 'plaza'
  | 'shallow_water'
  | 'marsh';

interface TownTerrainRegionState {
  terrainRegionId: string;
  districtInstanceId: string;
  terrainKind: TownTerrainKind;
  cells: TownGridPosition[];
  styleProfileId: string;
  createdBy: 'template' | 'user' | 'migration';
  lockedBoundary?: boolean;
}
```

Initial implementation may persist normalized cells rather than polygons, but public contract must preserve region identity and semantic terrain kind.

Rules:

- userはterrain意味をbrushで塗る
- transition spriteは周辺から導出
- region IDをasset nameから作らない
- season変更でterrainKindを変えない
- grass→winter grassはrender variant
- sandとseaの間へshoreline projectionを生成
- terrain editでbuildingをsilent deleteしない

---

# 3. Water model

水を一種類の`water cell`で済ませない。

```ts
type TownWaterBodyKind =
  | 'sea'
  | 'river'
  | 'canal'
  | 'pond'
  | 'stream';

interface TownWaterBodyState {
  waterBodyId: string;
  districtInstanceIds: string[];
  kind: TownWaterBodyKind;
  profileId: string;
  sourceNodeId?: string;
  outletNodeId?: string;
  widthProfileId: string;
  flowDirection?: TownOrientation;
  editablePhase: 'never' | 'reshape_later' | 'user_editable';
}
```

## 3.1 Sea

```txt
Distant sea:
  World Frame

Near sea / coast:
  editable district landscape
```

Near coastで変更可能:

- sand width
- small cove shape
- pier position at approved anchor
- coast vegetation
- small rock cluster
- beach object

Initial prohibition:

- world horizonの自由変形
- seaを町中央へ無制限にpaint
- building下のlandを自動で海へ変換

## 3.2 River / stream / canal

河川はlinear feature graphを正本にする。

```ts
interface TownLinearNode {
  nodeId: string;
  position: TownGridPosition;
  nodeKind: 'endpoint' | 'junction' | 'crossing' | 'source' | 'outlet';
}

interface TownLinearSegment {
  segmentId: string;
  featureId: string;
  fromNodeId: string;
  toNodeId: string;
  controlPoints: TownGridPosition[];
  widthProfileId: string;
  styleProfileId: string;
}
```

River validation:

- river sourceからoutlet / pondへ到達する
- segment同士が不正に交差しない
- riverbank clearanceを持つ
- building footprintを横断しない
- road crossingにはbridge / culvert anchorが必要
- district boundaryを越える時はriver socketを使う
- isolated water cellをriverとして作らない

---

# 4. Road and path model v2

既存`TownPathCellState`はrender projection / v1 compatibilityとし、将来editorはlinear featureを編集する。

```ts
type TownPathKind =
  | 'road'
  | 'footpath'
  | 'promenade'
  | 'boardwalk'
  | 'plaza_link';

interface TownPathFeatureState {
  pathFeatureId: string;
  kind: TownPathKind;
  nodes: TownLinearNode[];
  segments: TownLinearSegment[];
  surfaceProfileId: string;
  accessibilityProfileId: string;
}
```

Projectionで導出:

- straight
- curve
- T junction
- cross junction
- dead end
- plaza join
- bridge approach
- stairs / ramp candidate
- boardwalk edge

Rules:

- userは線を引く
- systemがcell pathとjunction spriteを導出
- primary feature routeを切断しない
- access rootへの到達性を保存前に検証
- semantic connection overlayと分離

---

# 5. Forest and vegetation model

森は木を一つずつ大量配置するだけにしない。

```ts
interface TownVegetationRegionState {
  vegetationRegionId: string;
  districtInstanceId: string;
  vegetationKind: 'forest' | 'grove' | 'flower_field' | 'shrub_border';
  cells: TownGridPosition[];
  density: 'sparse' | 'medium' | 'dense';
  speciesProfileId: string;
  deterministicSeed: string;
  pinnedObjectInstanceIds: string[];
}
```

Rules:

- userは森の範囲と密度をpaintする
- tree clusterはderived projection
- 気に入った木はpinしてuser objectへ昇格可能
- region変更でpinned treeをsilent deleteしない
- 道、川、建物clearanceを避ける
- 四季variantはspecies profileで切り替える
- 記録数で森を強制拡大しない

---

# 6. Buildings and houses

建物は完成sprite / multi-cell objectを維持する。

変更可能:

- parcel間移動
- 0 / 90 / 180 / 270 rotation
- approved visual skin
- entrance side candidate
- surrounding style pack

変更しない:

- 壁1cell単位の建築
- building footprintを無視したpixel placement
- feature routeを失う移動
- growth envelopeを超える自由resize

```ts
interface TownParcelV2 {
  parcelId: string;
  districtInstanceId: string;
  cells: TownGridPosition[];
  allowedCategories: TownObjectCategory[];
  allowedFeatureIds?: TownFeatureId[];
  entranceConnectionNodeIds: string[];
  scenicWeight: number;
  editablePhase: 'fixed' | 'decor' | 'relocatable';
}
```

---

# 7. Derived landscape projection

```txt
semantic state
→ normalized cells / graphs
→ adjacency masks
→ transition rules
→ render variants
→ micro-details
```

Derived only:

- coastline edge
- beach foam
- riverbank
- shallow-water blend
- road corner
- bridge approach
- fence joins
- forest edge shrubs
- building contact shadow
- path-side flower / sign

Rules:

- deterministic for same scene input
- user object non-destructive
- cache invalidation可能
- asset catalog migrationで再生成可能
- user exportの正本へ必須ではない
- accessibility targetにしない

---

# 8. Edit command model

```ts
type TownLandscapeCommand =
  | PaintTerrainCommand
  | DrawPathCommand
  | DrawWaterCommand
  | PaintVegetationCommand
  | MoveObjectCommand
  | AttachDistrictCommand
  | RemoveDistrictCommand
  | ChangeStyleProfileCommand;
```

一つのbrush stroke / draw gestureを一つのcommandとして扱う。

Flow:

```txt
canonical revision load
→ Draft Town
→ user edit
→ local semantic validation
→ affected chunks only re-project
→ before / after compare
→ server atomic validation
→ apply or discard
```

Required:

- undo / redo
- before / after
- affected area preview
- warning without destructive auto-fix
- server revalidation
- stale revision rejection
- idempotent batch
- rollback snapshot

---

# 9. Chunk and dirty-region model

大きな町全体を毎回再生成しない。

```ts
interface TownLandscapeChunk {
  chunkId: string;
  districtInstanceId: string;
  bounds: TownLogicalBounds;
  projectionVersion: number;
}
```

Edit時:

```txt
changed semantic entities
→ affected chunks
→ one-cell / rule-radius neighbor chunks
→ local reprojection
```

海、川、道の長いfeatureはsegment単位でdirty範囲を計算する。

---

# 10. Protected scenic constraints

自由編集でも愛着景観を壊しにくくする。

```ts
interface TownScenicConstraint {
  constraintId: string;
  type:
    | 'view_corridor'
    | 'open_ground'
    | 'coast_visibility'
    | 'landmark_silhouette'
    | 'water_continuity'
    | 'access_route';
  cells: TownGridPosition[];
  severity: 'hard' | 'soft';
}
```

Hard:

- access route
- water continuity
- growth envelope
- building collision
- district socket compatibility

Soft:

- coast visibility
- landmark silhouette
- open ground
- visual density

Soft violationはPreviewで説明し、勝手にuser objectを消さない。

---

# 11. Initial editable boundaries

## Initial map

System authored:

- central grove
- basic river route
- coast / harbor relationship
- six feature parcels
- access graph
- initial district sockets

User editable from later phases:

- ground surface
- sand width within coast band
- vegetation regions
- minor footpaths
- decorative bridges at approved crossings
- house / feature building parcel selection
- district style

Later:

- river reshaping
- new canal / pond
- coast reshaping
- district expansion
- terrace / elevation bands

## Free elevation sculpt

Initial / medium-term No-Go.

Reasons:

- cliff edge asset multiplication
- building elevation clearance
- stairs / ramps / accessibility
- water flow
- 2.5D sorting
- mobile editing complexity

Future candidate:

```txt
terrace region
+ fixed elevation levels
+ automatic cliff edge
+ approved ramp / stair anchors
```

not arbitrary height brush.

---

# 12. Compatibility with existing contracts

Supersedes for future authoring:

- `TownTerrainCellDefinition` as sole terrain source of truth
- `TownPathCellState` as sole path authoring model

Retains:

- canonical logical grid
- stable IDs
- parcels
- growth envelopes
- feature bindings
- command batch
- atomic validation
- three-way template merge
- account deletion / export / RLS contracts

Compatibility projection:

```txt
Terrain Region / Linear Feature
→ v1 terrain cells / path cells
```

until v2 persistence is authorized.

---

# 13. Acceptance direction

画像生成前に、以下をdiagram / fixtureで確認する。

1. grassをsandへpaintするとshore transitionだけが変わる
2. riverを曲げるとbank / bridge候補が再計算される
3. roadを伸ばすとjunctionが自動更新される
4. forest regionを縮めてもpinned treeが守られる
5. buildingをparcel間移動してもfeature bindingが維持される
6. harbor districtを追加して既存座標が変わらない
7. district削除時にuser objectが失われずstoredへ移る
8. asset styleを変更してsemantic stateが変わらない
9. motion offでも海岸・川・道が判別できる
10. Town OFFでもMemory OS機能が変わらない
