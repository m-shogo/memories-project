# Memory Town Long-term Spatial Model

最終更新: 2026-07-13

## 目的

Memory Town を、MVPでは固定2.5Dの町として軽く実装しながら、将来的にはユーザーが道路、木、花、ベンチ、建物などを配置できる箱庭へ拡張しても破綻しない空間モデルとして定義する。

参考イメージは「どうぶつの森のような、自分の場所へ愛着を持てる箱庭」である。

ただし、以下を意味しない。

- どうぶつの森のUIやアートを複製する
- 最初から自由配置ゲームを作る
- アバター操作を中心にする
- 経済、素材集め、クラフト、建築待ち時間を導入する

Memory Town の役割は、Memory OS に蓄積された棚・箱・つながりが、見て楽しい自分の町として育つことである。

---

## Product Metaphor

Minecraft型のボクセル世界ではない。

```txt
見た目: 温かい2.5Dの編集可能なジオラマ
内部: 論理グリッド上の配置システム
MVP: 運営が決めた固定配置
将来: 一部の装飾・道・建物をユーザーが編集可能
```

一言で表す。

```txt
どうぶつの森的な箱庭感
+ 固定2.5D
+ データ駆動の配置システム
```

---

## 最重要アーキテクチャ判断

町を画面座標 `x / y` の集合として保存しない。

最初から以下で保存する。

```txt
logical grid position
+ footprint
+ layer
+ elevation
+ orientation
+ stable definition ID
```

描画時だけ論理座標を画面座標へ変換する。

```ts
function gridToScreen(
  cellX: number,
  cellY: number,
  tileWidth: number,
  tileHeight: number,
  elevationPx: number,
): { x: number; y: number } {
  return {
    x: (cellX - cellY) * (tileWidth / 2),
    y: (cellX + cellY) * (tileHeight / 2) - elevationPx,
  };
}
```

画面解像度、ズーム、アートサイズが変わっても、町の保存データは変えない。

---

## 4つの状態を分離する

```txt
Memory Domain State
Town Projection State
Town Layout State
Town Render State
```

### 1. Memory Domain State

記憶、棚、Import、進行、箱、確定したつながりの正本。

### 2. Town Projection State

Memory Domain State を安全に集計して得る、建物の成長段階や新着状態。

例:

```txt
映画棚 42件
→ cinema stage 2
```

### 3. Town Layout State

町のどこに何が置かれているか。

例:

```txt
cinema instance
→ parcel cinema-main
→ cell 10, 6
→ orientation south-east
```

### 4. Town Render State

PixiJSがそのフレームで使うsprite、animation、camera、selection状態。

Render Stateは永続化しない。

## 分離ルール

- 記憶を削除してもlayoutを壊さない
- 建物が成長しても配置を失わない
- アセットを差し替えてもgrid座標を変えない
- rendererを変更してもtown layoutを移行しない
- user decorationはmemory dataから再計算しない
- system growthとuser customizationを混ぜない

---

## Logical Map Model

```ts
interface TownMapDefinition {
  mapDefinitionId: string;
  schemaVersion: string;
  gridWidth: number;
  gridHeight: number;
  tileMetric: {
    logicalTileWidth: number;
    logicalTileHeight: number;
  };
  parcels: TownParcelDefinition[];
  expansionZones: TownExpansionZoneDefinition[];
}
```

初期mapの実サイズはprototype後に決める。

重要なのは、座標系と単位を途中で変えないことである。

### Chunk

大きくなった町は内部的にchunkへ分割できる。

```ts
interface TownChunkCoordinate {
  chunkX: number;
  chunkY: number;
}
```

MVPでは全体を一度に描画してよい。

将来はchunk単位で、表示、保存、衝突検査、lazy loadを行えるようにする。

---

## Parcel Model

主要建物は、1マス単位で無制限に置くのではなく、最初は区画を持つ。

```ts
interface TownParcelDefinition {
  parcelId: string;
  origin: TownGridPosition;
  width: number;
  height: number;
  allowedCategories: TownObjectCategory[];
  systemReserved: boolean;
  userEditablePhase: 'never' | 'decor_only' | 'relocatable_later';
}
```

初期例:

- cinema parcel
- story house parcel
- market parcel
- port parcel
- central square parcel
- warehouse parcel

## なぜ区画を持つか

映画館が成長しても隣の木や道路へ食い込ませないため。

建物は、最大成長時に必要な面積を最初から予約する。

```txt
parcel size = 最大stageのfootprint + 周辺余白
```

小さいstageでは空いた部分を植栽や一時装飾に使えるが、主要建物の成長を妨げる恒久物は置かない。

---

## Grid Position

```ts
interface TownGridPosition {
  cellX: number;
  cellY: number;
  elevation: number;
}

type TownOrientation = 0 | 90 | 180 | 270;
```

MVPではorientationを固定しても、schemaには最初から持たせる。

---

## Object Categories

```ts
type TownObjectCategory =
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
```

### Terrain Tile

- grass
- soil
- sand
- stone
- coast
- water

1cell単位を基本にする。

### Path Tile

- road
- footpath
- plaza
- bridge connector

接続方向を見て自動的に見た目を変える。

### Small Prop

- flower
- lamp
- bench
- sign
- fence

1x1または小さな複数cell。

### Natural Object

- tree
- shrub
- rock

見た目より広いclearanceを持てる。

### Structure

- cinema
- story house
- market
- port facility
- warehouse

複数cellを占有する完成スプライト。

建物を1cellごとの壁や屋根に分解しない。

```txt
地形・道・花 = tile単位
木・家具 = object単位
建物 = multi-cell完成sprite
```

これを基本とする。

---

## Object Definition and Instance

アセット定義と、ユーザーの町に置かれたinstanceを分離する。

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
}

interface TownObjectInstance {
  instanceId: string;
  definitionId: string;
  definitionVersion: number;
  mapId: string;
  parcelId?: string;
  position: TownGridPosition;
  orientation: TownOrientation;
  source: 'system' | 'projection' | 'user';
  locked: boolean;
  variantKey?: string;
  createdAt: string;
  updatedAt: string;
}
```

### Stable ID Rule

- `definitionId`を別の意味で再利用しない
- アセット差し替えでIDを変えない
- 廃止時はdeleteではなくdeprecatedにする
- user instanceを無断で削除しない

---

## Footprint

```ts
interface TownFootprint {
  occupiedCells: Array<{ dx: number; dy: number }>;
  walkableCells?: Array<{ dx: number; dy: number }>;
  entranceCells?: Array<{ dx: number; dy: number }>;
  clearanceCells?: Array<{ dx: number; dy: number }>;
  depthAnchor: { dx: number; dy: number };
}
```

### occupiedCells

他のsolid objectを置けない。

### walkableCells

建物内に見える通路、桟橋など、見た目は占有していても住人が通れる場所。

### entranceCells

将来、道接続や住人routeに使う。

### clearanceCells

木の枝、建物前の入口、成長予定地など、完全占有ではないが他の大物を置けない場所。

### depthAnchor

2.5Dの前後関係を決める基準点。

spriteの画像サイズや透明余白からsort順を決めない。

---

## Layer and Collision Model

同じcellでも、layerが違えば共存できる場合がある。

```ts
type TownPlacementLayer =
  | 'base_terrain'
  | 'surface_path'
  | 'ground_object'
  | 'solid_object'
  | 'raised_object'
  | 'semantic_overlay'
  | 'ambient_effect';
```

例:

```txt
grass + footpath = possible
footpath + flower = rule-dependent
footpath + cinema = impossible
cinema + seasonal flag overlay = possible
road + semantic connection glow = possible
```

衝突はsprite boundsではなく、grid footprintとplacement layerで判定する。

---

## Road and Path System

道路は画像を自由配置するのではなく、cell接続情報からautotileする。

```ts
interface TownPathCell {
  position: TownGridPosition;
  pathType: 'road' | 'footpath' | 'plaza' | 'bridge';
  connectionMask: number;
}
```

接続mask:

```txt
N = 1
E = 2
S = 4
W = 8
```

周囲からmaskを再計算し、直線、角、T字、交差点、終端spriteを選ぶ。

## 重要な分離

ユーザーが配置する生活道路と、記憶同士の関係を示すsemantic connectionは別データにする。

```txt
Physical Path
= ユーザーまたはtemplateが配置した道

Semantic Connection Overlay
= 確定した記憶関係を示す光、線、橋の演出
```

物理道路を編集しても記憶の関係は消えない。

記憶関係が消えてもユーザーが作った道路は消えない。

---

## Building Growth Contract

建物stageは、同じ建物instanceのvariantとして扱う。

```ts
interface TownStructureProjection {
  instanceId: string;
  stage: number;
  renderVariantKey: string;
  badges: string[];
}
```

### 原則

- stage変更でinstanceIdを変えない
- routeを変えない
- parcelを変えない
- entranceの基本位置を変えない
- 最大footprintをparcel内に予約する
- user decorationを勝手に削除しない

### Footprint変更

可能な限りstage間で同じreserved footprintを使う。

どうしても変更が必要な場合は、versioned placement migrationを用意する。

```txt
validate
→ preview affected objects
→ safe relocation
→ user notification
→ rollback data保持
```

---

## Default Layout and User Customization

最初の町も、固定座標をcodeへ直書きしない。

```ts
interface TownLayoutTemplate {
  templateId: string;
  templateVersion: number;
  mapDefinitionId: string;
  placements: TownObjectTemplatePlacement[];
}
```

新規ユーザーはtemplateからlayoutを生成する。

### MVP

- system templateで固定配置
- user editorなし
- system placementはlocked
- 季節overlayのみ変化

### 将来Phase 1

- 建物周辺のdecoration slotを選べる
- 花、旗、看板、ベンチ
- predefined slot placement

### 将来Phase 2

- designated editable zone内で木、花、家具を自由配置
- undo / redo
- placement validation

### 将来Phase 3

- 道路と植栽の編集
- autotile
- entrance接続validation

### 将来Phase 4

- 主要建物を許可されたparcel間で移動
- map expansion
- district template変更

### 当面のNo-Go

- terrain heightの自由編集
- voxel破壊
- 建物を1blockごとに建築
- multiplayer同時編集
- 他人の町から物を盗む
- 仮想通貨や素材消費

---

## Decoration Slot Model

自由配置より前に、slot式で安全に拡張できる。

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

- 映画館前のposter slot
- 市場横のflower slot
- 港の船slot
- 中央広場のmonth capsule slot

slot式はMVPの固定配置と将来の自由配置の間をつなぐ。

---

## Placement Commands

町の変更は、DB rowを画面から直接書き換えない。

commandとして扱う。

```ts
type TownLayoutCommand =
  | PlaceTownObjectCommand
  | MoveTownObjectCommand
  | RotateTownObjectCommand
  | RemoveTownObjectCommand
  | PaintTownPathCommand
  | ReplaceTownTerrainCommand;
```

```ts
interface PlaceTownObjectCommand {
  commandId: string;
  expectedLayoutRevision: number;
  definitionId: string;
  position: TownGridPosition;
  orientation: TownOrientation;
}
```

Validation:

```txt
schema
→ permission
→ map bounds
→ parcel rules
→ footprint collision
→ entrance clearance
→ category limits
→ apply
→ revision increment
```

### Idempotency

`commandId`を使い、通信再送で同じ物が二重配置されないようにする。

### Optimistic Concurrency

`expectedLayoutRevision`が一致しない場合、最新layoutを取得して再編集する。

---

## Persistence Contract

初期Import migrationへ無理に入れないが、町実装時は以下の責務を分ける。

```txt
town_map
town_layout
town_layout_object
town_layout_revision
town_layout_event
town_projection_snapshot
```

### town_map

map definitionとexpansion状態。

### town_layout

ユーザーの現在layoutとrevision。

### town_layout_object

配置instance。

### town_layout_revision

保存時点のlayout version。

### town_layout_event

配置、移動、削除などの監査可能な操作。

### town_projection_snapshot

Memory Domainから導出した建物stageなど。

### Separation Rule

```txt
town_layout_object
≠ memory_record
≠ collection_item
≠ town_projection_snapshot
```

---

## Versioning

最低限、以下を別々にversion管理する。

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

一つの`townVersion`へまとめない。

変更理由とmigration対象が異なるためである。

---

## Migration Rules

### 原則

- user配置を黙って削除しない
- 定義廃止でinstanceを消さない
- 代替assetまたはplaceholderを用意する
- migration前snapshotを保持する
- invalid objectを安全なholding areaへ移す
- migration結果を監査可能にする

### Invalid Placement Recovery

```txt
1. 新ルールでvalidate
2. 影響instanceを列挙
3. 同parcel内でsafe relocationを試す
4. 失敗時は町の保管箱へ退避
5. userへ変更理由を表示
6. rollback snapshotを保持
```

記憶データを失わせないことは当然として、ユーザーが選んだ町の配置も長期資産として扱う。

---

## Rendering Contract

PixiJSはlogical scene snapshotを受け取る。

```ts
interface TownSceneSnapshot {
  map: TownMapRenderProjection;
  objects: TownObjectRenderProjection[];
  paths: TownPathRenderProjection[];
  semanticConnections: TownSemanticConnectionRenderProjection[];
  ambient: TownAmbientProjection;
}
```

renderer内でbusiness ruleを決めない。

```txt
DB / Domain
→ spatial projector
→ scene snapshot
→ PixiJS renderer
```

---

## Asset Contract

すべてのobject assetに必要:

- stable texture key
- grid footprint
- depth anchor
- visual anchor
- hit polygon
- shadow definition
- orientation variants
- season overlay compatibility
- low-resolution fallback
- missing asset placeholder

### Building Asset

建物は完成spriteとして作る。

各stageで以下を揃える。

```txt
same parcel contract
same entrance contract
compatible depth anchor
known max bounds
```

### Small Object Asset

木、花、家具は、grid cellに対するanchorを共通化する。

---

## Citizens and Pathfinding

MVPでは固定短経路でよい。

将来path編集へ対応する場合、住人はsprite座標ではなくwalkability gridを使う。

```ts
interface TownNavigationCell {
  position: TownGridPosition;
  walkable: boolean;
  movementCost: number;
  connectors: TownGridPosition[];
}
```

建物入口、橋、桟橋はnavigation connectorを持つ。

住人の経路と、記憶relationの道は別物である。

---

## Performance Strategy

長期拡張を見据え、以下を可能にする。

- chunk culling
- static tile layer cache
- sprite atlas
- object pooling
- offscreen animation pause
- visible chunkだけのhit test
- low power mode
- maximum active citizen budget
- seasonal overlay lazy load

MVPで全機能を実装する必要はない。

ただし、scene graphとinstance modelが後からchunk化を妨げないようにする。

---

## Security and Privacy

町へraw memoryを渡さない既存方針を維持する。

User customizationの配置情報にも、以下を入れない。

- private title
- person name
- chat text
- location raw history
- private image URL

町のobjectや装飾へ記憶本文を直接埋め込まない。

建物タップ後の情報はDOM側でpolicy check後に表示する。

---

## Accessibility

町編集を導入しても、WebGLだけを唯一の操作方法にしない。

必要:

- object list alternative
- keyboard / switch操作可能なDOM editor
- object名、位置、状態の読み上げ
- reduced motion
- high contrast selection
- undo可能な重要操作
- static fallback

---

## Test Contract

### Spatial Unit Tests

- grid to screen変換
- screen hit to grid変換
- footprint rotation
- collision mask
- parcel bounds
- entrance clearance
- path autotile mask
- stage footprint compatibility

### Migration Tests

- catalog definition upgrade
- deprecated object preservation
- invalid placement recovery
- template version upgrade
- layout revision conflict
- rollback snapshot

### Projection Separation Tests

- memory削除後もuser decorationが残る
- shelf count変更でbuilding stageだけ更新
- layout移動でmemory recordが変わらない
- hidden / sealed記録がprojectionへ漏れない

### Renderer Tests

- scene snapshotのdeterministic render
- same layout at multiple resolutions
- context loss fallback
- missing asset placeholder
- large map chunk culling

---

## Initial Implementation Definition

MVPで実装するもの:

```txt
1. logical grid coordinate
2. map definition
3. parcel definition
4. layout template
5. object definition catalog
6. object instances
7. multi-cell building footprint
8. locked system placements
9. grid-to-screen projection
10. static fallback
```

MVPでUIとして実装しないもの:

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

つまり、内部は最初から将来型、表面は最小構成にする。

---

## First Stable Contracts

実装前に固定するID:

```txt
mapDefinitionId
layoutTemplateId
parcelId
building definitionId
object category
tile metric
orientation enum
placement layer
layout revision contract
```

これらを曖昧にしたままPixiJSへ座標を直書きしない。

---

## Decision Summary

```txt
Minecraftのような1block建築ではない。
どうぶつの森のように、自分の町へ愛着を持てる箱庭を目指す。

地面・道・花はtile単位。
木・家具はobject単位。
建物はmulti-cellの完成sprite。

MVPは固定配置。
内部は最初からlogical gridとparcelで管理。
将来、装飾、道、植栽、建物移動を段階的に解放できる。
```

この構造をMemory Town空間実装の正本とする。
