# Memory Town WebGL Architecture

最終更新: 2026-07-13

## 目的

固定2.5DのMemory TownをWebGLで実装する際の責務境界、data flow、performance、fallback、test方針を固定する。

## Technology Decision

採用:

```txt
PixiJS
+ WebGL renderer
+ React/DOM UI
+ fixed 2.5D sprites
+ config-driven building definitions
```

採用しない:

- 生WebGLによる直接実装
- Three.jsによる本格3D
- 自由camera
- physics engine
- user-controlled avatar
- free placement city builder
- WebGL内のform / long text / list UI

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

### PixiJS / Town Renderer

- terrain
- roads
- buildings
- props
- passive citizens
- boats
- seasonal overlays
- ambient effects
- selection highlight
- short camera focus

WebGL rendererはmemoryの正本を直接読まない。

## Data Flow

```txt
Domain records
→ policy filter
→ aggregate projector
→ TownProjection JSON
→ PixiJS scene
```

### TownProjection

```ts
interface TownProjection {
  schemaVersion: string;
  generatedAt: string;
  season: 'spring' | 'summer' | 'autumn' | 'winter';
  timeMode: 'day' | 'evening' | 'night';
  buildings: TownBuildingProjection[];
  connections: TownConnectionProjection[];
  ambient: TownAmbientProjection;
}

interface TownBuildingProjection {
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
  fromBuildingId: string;
  toBuildingId: string;
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

## Projection Rules

TownProjectionは再計算可能なread modelとする。

- source of truthではない
- transactionの正本ではない
- user編集対象ではない
- memory削除時に再計算可能
- policy変更時に再計算可能
- renderer versionと独立してversion管理する

### Growth Example

```ts
function resolveCinemaStage(movieCount: number): number {
  if (movieCount <= 0) return 0;
  if (movieCount < 25) return 1;
  return 2;
}
```

閾値はremote configまたはversioned rulesetとして管理する。

既存ユーザーの町が突然縮小しないよう、変更時はmigration strategyを定義する。

## Scene Graph

```txt
TownRoot
├─ TerrainLayer
├─ RoadLayer
├─ RearPropLayer
├─ BuildingLayer
├─ FrontPropLayer
├─ CitizenLayer
├─ VehicleLayer
├─ SeasonalLayer
├─ AmbientEffectLayer
└─ SelectionLayer
```

### Z Ordering

- static terrainは固定zIndex
- building / citizen / propは基準点のY座標でsort
- decorative overlaysは親buildingに追従
- hit targetとvisual boundsを分離

```ts
sprite.zIndex = sprite.y + spriteSortOffset;
```

## Building Definition

```ts
interface TownBuildingDefinition {
  id: string;
  label: string;
  shelfType: string;
  route: string;
  position: { x: number; y: number };
  anchor: { x: number; y: number };
  hitArea: Array<{ x: number; y: number }>;
  stages: TownBuildingStageDefinition[];
  allowedBadges: string[];
}

interface TownBuildingStageDefinition {
  stage: number;
  textureKey: string;
  width: number;
  height: number;
  sortOffset: number;
  overlaySlots: string[];
}
```

新しい建物はrenderer codeを大きく変更せず、definitionとassetsの追加で対応する。

## Asset Loading

### MVP

- texture atlasを1〜2個にまとめる
- initial town assetsをpreload
- seasonal assetsはlazy load可能
- high-density mobile向けに複数解像度を用意

### Rules

- atlas keyを安定ID化
- file nameをUI表示名に依存させない
- texture missing時はplaceholderを表示
- asset manifestをversion管理
- CDN failure時に静止画fallbackへ移行可能

## Interaction Bridge

PixiJSはbuilding IDだけをapplicationへ返す。

```txt
pointertap
→ onBuildingSelected('cinema')
→ React state update
→ DOM summary sheet
→ route navigation
```

重要操作はDOM sheet側で行う。

町内で直接許可する操作:

- building select
- focus
- overviewへ戻る
- optional ambient toggle

町内で禁止する操作:

- record削除
- bulk edit
- text input
- permission change
- export confirmation
- security-sensitive action

## Camera

MVP camera state:

```ts
interface TownCameraState {
  mode: 'overview' | 'focused';
  focusedBuildingId?: string;
}
```

- overviewは全体表示
- focusはscale / position interpolationのみ
- navigation中断可能
- focus完了を待たずDOM sheetを開ける
- reduced motionでは即時切替

## Animation

### Event Types

```txt
BUILDING_STAGE_CHANGED
BUILDING_RECENT_DELTA
CAPSULE_COMPLETED
CONNECTION_CONFIRMED
SEASON_CHANGED
```

### Rules

- animationは事実の変化を示す
- reward currencyを生成しない
- forced full-screen celebrationなし
- 1〜2秒以内
- queue上限を設定
- 古いanimationはまとめる

Import 100件で100回光らせず、一つのaggregate animationにする。

## Performance Budget

初期目標:

- building: 5〜8
- citizen: 0〜5
- moving vehicles: 0〜2
- ambient particles: 30以下
- texture atlas: 2048px中心、端末に応じて分割
- scene active時のみticker稼働
- background tab / hidden routeでは停止
- 低電力modeで30fps上限
- 通常modeで60fpsを目標、必須条件にはしない

### Lifecycle

```txt
route enter → renderer start
route hidden → ticker pause
route leave → renderer stop / release optional assets
app background → pause
app foreground → projection diff apply
```

## Low Power Mode

設定または端末状況により以下を停止できる。

- citizen movement
- weather particles
- water animation
- smoke
- dynamic lighting

建物tapとnavigationは維持する。

## Fallback

WebGL unavailable / context lost / unsupported deviceの場合:

```txt
static town image
+ DOM building buttons
+ same summary cards
```

Fallbackでも機能到達性を失わない。

### Context Loss

- webglcontextlostを検知
- automatic retryは回数制限
- projection stateを保持
- failure telemetryにmemory内容を含めない
- retry失敗後はstatic fallback

## Accessibility

- townと同内容のbuilding listをDOMで提供
- building labelを読み上げ可能
- colorだけで状態を表さない
- focus indicatorをDOM / canvas両方で表現
- keyboard / switch accessをDOM list経由で保証
- reduced motion
- high contrast label option

町は必須navigation pathにしない。

## Privacy and Security

Renderer inputへ含めない:

- raw memory
- private title
- person name
- precise location
- private photo
- relationship data
- hidden / sealed content

Telemetry:

```txt
allowed:
- renderer init success
- fps band
- context lost count
- building selection ID
- fallback activation

not allowed:
- record title
- memory text
- user note
- source raw value
```

## State Synchronization

町を開いたままImportが完了した場合:

```txt
safe commit
→ projection regenerated
→ old/new diff
→ scene patch
→ one aggregate growth animation
```

full scene reloadを必須にしない。

## Testing

### Unit

- growth rule boundaries
- projection policy exclusions
- stable building IDs
- stage migration
- connection mapping

### Integration

- projection → scene object creation
- tap → DOM sheet
- route change → ticker stop
- reduced motion
- context loss fallback

### Visual Regression

- supported viewport sizes
- all building stages
- all four seasons
- overview / focused state
- low-data town
- maximum MVP town

### Performance

- low-end mobile profile
- repeated route enter/leave
- 30-minute idle
- context loss simulation
- large import aggregate update

## Observability

- init duration
- asset load failure rate
- average fps band
- context loss rate
- fallback rate
- town open rate
- building selection rate
- town → shelf transition rate

町の利用率が低くても、棚機能の利用を妨げないことを優先する。

## Architecture Decision

```txt
WebGLは、町を3Dゲームにするためではない。
固定2.5Dの世界へ、軽い生活感・成長・季節を足すために使う。
```
