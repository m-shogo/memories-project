# Memory Town Architecture Hardening Contract

最終更新: 2026-07-13

## 目的

この文書は、Memory Town をMVPの固定表示から、将来の装飾配置・道路編集・建物移動・地区拡張まで発展させても、データ消失、意味の混線、全面作り直しを起こさないためのP0設計契約である。

既存文書と矛盾する場合、以下の順で優先する。

```txt
1. 本書
2. current-product-direction.md
3. memory-town-long-term-spatial-model.md
4. memory-town-webgl-architecture.md
5. visual / roadmap / ticket documents
```

実装はまだ開始しない。

---

# 1. 用語の固定

## 1.1 「固定2.5D」の意味

今後は曖昧さを避け、次の言葉を使う。

```txt
固定視点2.5D
```

意味:

- camera angleは固定
- perspective rotationなし
- objectはlogical gridへ配置
- MVPではlayout編集UIなし
- 将来は同じ固定視点のまま配置を編集可能

禁止される誤解:

```txt
固定視点
=
配置座標まで永久に固定
```

ではない。

## 1.2 参考イメージ

```txt
どうぶつの森のように、自分の場所へ愛着を持てる箱庭
```

ただし、アバター移動、素材集め、クラフト、経済、マルチプレイを意味しない。

---

# 2. 状態を5つに分離する

従来の4状態では、縮まない成長と季節・時間の責務が混ざるため、以下の5状態へ分離する。

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

## 2.1 Memory Domain State

正本:

- shelf
- collection item
- import
- progress
- month capsule
- confirmed relation
- follow target

町の座標やassetを持たない。

## 2.2 Town Feature Progress State

建物や町機能の、解除済み成長段階を持つ。

```ts
interface TownFeatureProgress {
  featureId: TownFeatureId;
  maxUnlockedStage: number;
  unlockedAtByStage: Record<number, string>;
  growthRulesetVersion: string;
  resetEpoch: number;
  updatedAt: string;
}
```

これはMemory Domainから毎回完全再計算する一時Projectionではない。

理由:

- 記録削除で建物を縮ませない
- threshold変更で町を突然縮ませない
- Import取り消しで罰のような退化を見せない

## 2.3 Town Layout State

町に何がどこへ置かれているか。

- map
- parcel
- object instance
- path cell
- decoration slot
- stored object
- layout revision

Memory内容を持たない。

## 2.4 Town Environment State

記憶内容とは無関係な表示環境。

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

Rules:

- weatherVisualは実際のGPS weatherである必要はない
- precise locationを要求しない
- season / time / themeをTownProjectionへ混ぜない
- low power / reduced motion設定を尊重する

## 2.5 Town Render State

PixiJS session内だけの状態。

- camera
- selected instance
- hover / focus
- loaded texture
- animation clock
- placement preview

永続化しない。

---

# 3. 建物の「役割」と「見た目」を分離する

## 3.1 問題

映画棚の成長を`cinema instanceId`へ直接結びつけると、将来以下で破綻する。

- 映画館skinを変更
- 映画館を別の建物へ差し替え
- 同じ役割を別地区へ移動
- 建物instanceをmigrationで再生成

## 3.2 TownFeatureId

町の機能をstable semantic IDで定義する。

```ts
type TownFeatureId =
  | 'shelf.movie'
  | 'shelf.story'
  | 'shelf.food'
  | 'box.travel'
  | 'system.inbox'
  | 'reflection.square';
```

表示名や建物asset名から生成しない。

## 3.3 Feature Projection

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

`candidateStage`は現在のeligible countから計算した候補値。

実際の表示stageは次で決める。

```ts
displayStage = max(
  featureProgress.maxUnlockedStage,
  featureProjection.candidateStage,
);
```

候補stageが既存のmaxUnlockedStageを超えた時だけ、unlock eventを保存する。

## 3.4 Feature Binding

TownObjectInstanceは見た目のdefinitionだけでなく、必要に応じてfeatureへbindingする。

```ts
interface TownFeatureBinding {
  bindingId: string;
  featureId: TownFeatureId;
  objectInstanceId: string;
  bindingRole: 'primary' | 'secondary' | 'portal';
}
```

Rules:

- featureIdはMemory OSの意味
- definitionIdは見た目
- instanceIdは配置された個体
- skin変更でfeatureIdを変えない
- building移動でfeatureIdを変えない
- definition差し替えでfeature progressを失わない

---

# 4. 建物が縮まない契約と削除権

## 4.1 通常削除

個別recordの削除、Import取り消し、重複統合では、建物を自動縮小しない。

表示件数は現在値へ更新する。

```txt
映画館 Stage 2
現在の映画棚 8件
```

は許容する。

過去に解除した町の姿を残すためであり、削除したrecordの本文やtitleを保持するわけではない。

## 4.2 明示的Reset

ユーザーは以下を個別に実行可能にする。

```txt
町の見た目だけ初期化
配置だけ初期化
特定featureの成長を初期化
装飾だけ初期化
町全体を初期化
```

Memory dataは変更しない。

## 4.3 Shelf deletion / privacy reset

棚自体を削除する操作では、次を明示する。

```txt
[ ] 対応する町の成長履歴も初期化する
```

restricted / sealed / deleted dataを推測可能な表示として残したくないユーザーのために、feature progress resetを提供する。

## 4.4 Account deletion

account deletionでは以下を全削除対象にする。

- layout
- object instances
- feature progress
- environment preferences
- layout events
- snapshots
- stored objects

Townだけを残さない。

---

# 5. Canonical Coordinate Contract

## 5.1 Logical axes

```txt
origin: map logical north-west = (0, 0)
+X: east
+Y: south
```

isometric projectionでは:

```txt
+X = screen down-right
+Y = screen down-left
```

## 5.2 Elevation

`elevation`はpixel値ではなく、整数のlogical levelとする。

```ts
interface TownGridPosition {
  cellX: number;
  cellY: number;
  elevationLevel: number;
}
```

描画時のみ:

```ts
screenY -= elevationLevel * metric.elevationStepPx;
```

保存データへ`elevationPx`を入れない。

## 5.3 Orientation

```txt
0   = North (-Y)
90  = East  (+X)
180 = South (+Y)
270 = West  (-X)
```

角度はlogical plane上のorientationであり、camera angleではない。

## 5.4 Footprint pivot

footprintはcanonical pivot `(0,0)`を持つ。

```ts
interface TownFootprint {
  pivotCell: { dx: 0; dy: 0 };
  occupiedCells: TownRelativeCell[];
  walkableCells?: TownRelativeCell[];
  entranceCells?: TownRelativeCell[];
  clearanceCells?: TownRelativeCell[];
  reservedGrowthCells?: TownRelativeCell[];
  depthAnchor: TownRelativePoint;
}
```

- negative offsetを許可する
- rotationはpivotを中心に行う
- rotation後に勝手にmin座標へnormalizeしない
- positionは常にpivotのmap位置

これにより回転前後でobjectが不意に移動しない。

## 5.5 Deterministic depth sort

sort key:

```txt
1. placement layer order
2. projected depthAnchor Y
3. elevationLevel
4. definition sortOffset
5. instanceId
```

同じ入力から必ず同じ順序を得る。

---

# 6. Terrain / Water / Pathの正本

## 6.1 Base terrain

各map cellは必ず一つのbase terrainを持つ。

```ts
type TownTerrainKind =
  | 'grass'
  | 'soil'
  | 'sand'
  | 'stone'
  | 'coast'
  | 'water';
```

waterをterrainとは別のsolid objectとして二重管理しない。

## 6.2 Path persistence

永続化するのはpathの存在と種類のみ。

```ts
interface TownPathCellState {
  position: TownGridPosition;
  pathType: 'road' | 'footpath' | 'plaza' | 'bridge';
}
```

`connectionMask`は保存しない。

周囲のpath cellからscene composition時に導出する。

理由:

- 隣の道を消した時のmask不整合を防ぐ
- migrationを簡単にする
- asset variant変更へ耐える

## 6.3 Physical path / Semantic connection

完全に別データとする。

```txt
Physical path
= 町の生活道路

Semantic connection overlay
= 記憶の確定したつながりを示す視覚演出
```

semantic connectionは物理道路の有無を変更しない。

---

# 7. Growth Envelopeと配置保護

## 7.1 Growth envelope

主要建物には、現行stageのfootprintとは別に、承認済み将来stageまでのreserved growth cellsを定義する。

```ts
interface TownGrowthEnvelope {
  featureId: TownFeatureId;
  envelopeVersion: number;
  reservedCells: TownRelativeCell[];
  supportedStages: number[];
}
```

## 7.2 MVP placement rule

主要建物周辺でユーザーが選べる装飾は、以下のどちらかに限定する。

- envelope外のdecoration slot
- stage変更で影響しないoverlay slot

将来成長予定地へ恒久objectを自由配置させない。

## 7.3 New stageがenvelopeを超える場合

自動適用禁止。

```txt
new stage proposal
→ compatibility validation
→ map migration plan
→ affected object preview
→ safe relocation or stored state
→ atomic apply
→ rollback snapshot
```

asset追加だけで既存layoutを壊さない。

---

# 8. Object Instanceの修正

## 8.1 source enum

`source: 'projection'`は禁止する。

Projectionはlayout objectを生成する正本ではない。

```ts
type TownObjectOrigin =
  | 'template'
  | 'user'
  | 'migration'
  | 'system_unlock';
```

## 8.2 placement state

保管箱をmagic coordinateで表現しない。

```ts
type TownPlacementState =
  | 'placed'
  | 'stored'
  | 'retired';
```

`stored` objectはpositionを必須にしない。

## 8.3 lock policy

boolean `locked`だけでは将来不足する。

```ts
type TownLockPolicy =
  | 'system_fixed'
  | 'decor_editable'
  | 'relocatable_later'
  | 'user_owned';
```

permissionはphase feature flagとlock policyの両方で判定する。

---

# 9. Layout Template Evolution

## 9.1 Immutable versions

以下は公開後にin-place変更しない。

- map definition version
- layout template version
- object definition version
- object catalog version
- growth envelope version

修正は新versionを作る。

## 9.2 Baseline tracking

TownLayoutは生成元を持つ。

```ts
interface TownLayoutBaseline {
  templateId: string;
  templateVersion: number;
  generatedAt: string;
}
```

## 9.3 Three-way merge

template更新では次を比較する。

```txt
old template baseline
current user layout
new template
```

Rules:

- userが変更していないtemplate objectだけ自動更新可能
- userが移動・差し替え・削除したobjectを上書きしない
- 新しいsystem featureはreserved parcelへ置く
- 置けなければstored stateへ入れる
- removed definitionはplaceholderまたはreplacement mapping
- migration previewを生成する

単純な「new templateで町を再生成」は禁止。

---

# 10. Editor Save / Undo / Concurrency

## 10.1 Draft session

将来editorはdragごとにserver rowを更新しない。

```txt
load revision R
→ local draft
→ local validate
→ undo / redo
→ Save
→ server atomic revalidate
→ compare-and-swap revision R
→ revision R+1
```

## 10.2 Command batch

```ts
interface TownLayoutCommandBatch {
  batchId: string;
  expectedLayoutRevision: number;
  commands: TownLayoutCommand[];
  clientSessionId: string;
  createdAt: string;
}
```

Rules:

- batch全体をtransactionで適用
- 一部だけ成功させない
- batchIdでidempotency
- server側で全commandを再検証
- permission / ownership / lock policyを確認

## 10.3 Undo / Redo

編集中:

- local command stack
- inverse commandを生成
- Save前は自由にundo / redo

保存後:

- revision snapshotがある期間のみ「前の配置へ戻す」
- rollbackも新revisionとして記録
- event historyを書き換えない

## 10.4 Multi-device conflict

初期はCRDTを採用しない。

禁止:

- silent last-write-wins
- stale revisionの上書き
- 端末Aの編集を端末Bが黙って消す

Conflict response:

```txt
latest layout
+ submitted command batch
+ conflict reason codes
```

安全にrebaseできない場合は、最新layoutを再取得して再編集する。

---

# 11. Persistence Source of Truth

## 11.1 Event sourcingにしない

初期の正本は現在状態のtableとする。

```txt
town_layout
town_layout_object
town_path_cell
town_feature_progress
town_environment_preference
```

`towm_layout_event`は監査・復旧補助であり、唯一の正本ではない。

## 11.2 Revision and snapshot

snapshotを作るタイミング:

- migration前
- user save前後
- town reset前
- object catalog major upgrade前

retentionは運用設計で固定するが、永久に無制限保存しない。

## 11.3 Corruption recovery

```txt
validate current layout
→ repairable issueを自動修復
→ invalid objectをstoredへ退避
→ last valid snapshotから復旧候補
→ userへ説明
```

町の破損でMemory OS全体を起動不能にしない。

---

# 12. RLS / Security Contract

全user town tableに`user_id`を持たせる。

必須:

- RLS fail closed
- cross-user instance ID参照を拒否
- server authoritative validation
- locked system object mutation拒否
- catalogにないdefinition ID拒否
- deprecated / disabled definitionの新規配置拒否
- command batch size limit
- rate limit
- audit eventへmemory titleや本文を入れない

Support roleはuserの町を通常閲覧できない。

必要時も、既存のsupport access ceremonyと監査を適用する。

---

# 13. Export / Import / Portability

## 13.1 Separate export sections

```txt
memory data
feature progress
layout
preferences
```

を分離する。

Town exportに必要:

- spatial schema version
- map definition ID / version
- object catalog version
- layout revision
- object instances
- path cells
- feature bindings
- feature progress
- environment preferences

## 13.2 Re-import

直接適用しない。

```txt
parse
→ version compatibility
→ definition availability
→ placement validation
→ Preview
→ unsupported objectをstoredへ
→ atomic import
```

## 13.3 Asset data

標準exportへ著作権asset本体を無条件同梱しない。

- stable definition ID
- user-owned custom metadata where allowed
- fallback representation

を中心とする。

---

# 14. Responsive Camera Contract

map座標をviewportへ合わせて変更しない。

```txt
logical world bounds
→ camera fit calculation
→ safe area inset
→ DOM bottom sheet reserved area
→ zoom preset
```

MVP:

- overviewで主要parcelが見える
- selected buildingへfocus
- bottom sheetで対象が完全に隠れない

Map expansion後:

- `overview`
- `district`
- `focused`

のlogical camera presetを使う。

camera pixel positionを永続化しない。

---

# 15. Asset and Catalog Compatibility

各render variantに必要:

```txt
textureKey
contentHash
assetManifestVersion
supportedOrientation
visualAnchor
hitPolygon
depthAnchor
renderBounds
footprintContractVersion
seasonOverlayCompatibility
fallbackTextureKey
provenance / license record
```

Rules:

- asset変更でfootprintを黙って変えない
- orientation asset不足時に看板文字を鏡像反転しない
- missing assetでもinstanceを削除しない
- atlas組み替えでtextureKeyを変えない
- user-uploaded arbitrary executable contentを許可しない

---

# 16. Validation Result Contract

booleanだけを返さない。

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

Stable error codes例:

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

UI文言とdomain error codeを分離する。

---

# 17. Test Hardening

## 17.1 Property-based tests

- footprintを4回rotateすると元へ戻る
- valid layoutのobject順を変えてもcollision結果同一
- path追加削除後のderived maskが整合
- snapshot serialize / deserializeで同値
- gridToScreen / screenToGrid round trip

## 17.2 Fuzz tests

- 巨大座標
- negative coordinate
- duplicate instance ID
- unknown definition version
- malformed footprint
- command replay
- stale revision
- cyclic connector

## 17.3 Migration golden fixtures

最低限:

```txt
v1 template untouched
v1 template user decorated
v1 user moved building
v1 deprecated object
v1 invalid after new envelope
v1 missing asset
v1 stored object
```

## 17.4 Privacy tests

TownSceneSnapshot / event / telemetryに以下が入らないこと。

- title
- person name
- raw note
- private URL
- precise location
- chat body

---

# 18. Telemetry Contract

許可:

- renderer startup success
- fallback reason code
- object count band
- command validation error code
- migration result counts
- frame time band
- context loss count

禁止:

- object label derived from private title
- memory content
- exact user-created town name without consent
- precise coordinate historyを行動追跡目的で保存

---

# 19. Feature Flags

以下を独立flagにする。

```txt
town_webgl_renderer
town_ambient_motion
town_decoration_slots
town_free_decor_editor
town_path_editor
town_structure_relocation
town_map_expansion
```

一つの巨大な`townEditorEnabled`にしない。

段階的rolloutとrollbackを可能にする。

---

# 20. P0 No-Go Patterns

以下を実装レビューで拒否する。

```txt
TownProjectionにseasonやcameraを保存
TownProjectionからlayout objectを再生成
source='projection'の配置instance
featureの意味をdefinitionIdへ直結
建物stageを現在件数だけで毎回縮小
connectionMaskをpath rowの正本として保存
new templateでuser layoutを丸ごと上書き
last-write-winsで端末競合を解決
holding areaを(-999,-999)で表現
locked booleanだけで全権限を表現
layout event logだけを唯一の正本にする
client validationだけで配置保存
account deletion後にtown stateを残す
```

---

# 21. Design Completion Gate

Memory Town設計を「実装着手可能」とするには、以下が必要。

```txt
[ ] 5-state separationが全docsで一致
[ ] TownFeatureIdとfeature bindingが固定
[ ] non-shrinking progress / reset契約が固定
[ ] logical axes / elevation / rotation pivotが固定
[ ] terrain / path正本が固定
[ ] growth envelopeが固定
[ ] object origin / placement state / lock policyが固定
[ ] template three-way mergeが固定
[ ] atomic command batch / revision conflictが固定
[ ] current-state source of truthが固定
[ ] RLS / permission negative testsが定義
[ ] export / reset / account deletionが定義
[ ] responsive cameraが定義
[ ] asset compatibility fieldsが定義
[ ] structured validation error codesが定義
[ ] migration golden fixturesが定義
[ ] P0 No-Go review checklistが定義
```

このGateを満たすまで、PixiJS rendererの本実装へ進まない。

---

# Final Decision

```txt
Memory Townは、固定視点2.5Dの編集可能なジオラマ基盤として作る。

MVPでは編集UIを閉じる。
しかし内部は最初から、意味・成長・配置・環境・描画を分離する。

ユーザーの記憶も、町の配置も、template更新やasset変更で失わせない。
```
