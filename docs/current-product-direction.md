# Current Product Direction

最終更新: 2026-07-13

この文書は、Memory OS の現時点のプロダクト方向性を一枚で確認するための正本である。

Memory Townの詳細契約は、以下を最優先する。

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-long-term-spatial-model.md`
- `docs/memory-town-webgl-architecture.md`

---

## Product Promise

```txt
軽く取り込む
→ 自分の棚として見える
→ 必要な時に探せる
→ 月・年・つながりとして再発見できる
→ 記録の積み重ねが、自分だけの町として育つ
→ 必要なら外へ持ち出せる
```

Memory OS は単なる保管庫ではない。

保存した情報は実用的な棚になる。
その蓄積は、固定視点2.5Dの「記憶の町」として視覚的に育つ。

町はMVPでは固定layoutだが、内部空間は最初からlogical gridで定義し、将来は道路、木、花、家具、建物などを段階的に編集できる構造にする。

---

## Core Product Layers

### 1. Practical Layer

- Universal Quick Add
- Import Preview
- 媒体別の棚
- 漫画・アニメ進行
- 映画・視聴棚
- 食の地図
- 未整理Inbox
- Search
- Export

### 2. Reflection Layer

- Weekly Box
- Month Capsule
- Year / season view
- Safe resurfacing
- Confirmed cross-source connections

### 3. Anticipation Layer

- 続刊待ち
- 新刊・配信開始など、自分が明示的に追う対象の続き
- 未来の楽しみ箱
- 発売日カレンダー

一般的なレコメンドや広告中心の推薦は中心にしない。

### 4. Emotional Visualization Layer

- 固定視点2.5Dの記憶の町
- WebGL / PixiJS
- ドット調の温かいアート
- 町は感情的なメニュー
- 棚画面は実用的な本体
- MVPは固定layout template
- 内部はlogical grid / parcel / footprint
- 将来はdecoration、道、植栽、建物移動を段階的に解放可能

---

## Product Metaphor

Minecraftのような1block建築ではない。

「どうぶつの森のように、自分の場所へ愛着を持てる箱庭」の方が近い。

ただし、特定作品のUIやアートを複製しない。

```txt
見た目: 温かい固定視点2.5Dのジオラマ
MVP操作: 建物をタップするmenu
内部構造: logical grid上の配置system
将来操作: 木、花、道、家具、建物を段階的に編集
```

ゲームの再現ではなく、Memory OSの蓄積を自分の場所へ変える。

---

## Navigation

推奨ナビゲーション:

```txt
町
棚
振り返り
追加
```

「発見」は独立タブとして固定せず、以下へ分散してもよい。

- 町のsemantic connection
- 棚内の関連記録
- 振り返り内のつながり
- 検索結果

情報設計の検証後に、発見タブを残すか判断する。

---

## Memory Town Role

町はゲーム本体ではない。

```txt
町 = 見て楽しく、機能を覚えやすい入口
棚 = 検索・更新・編集を行う通常UI
```

建物をタップすると概要カードを表示し、その後、対応する棚へ移動する。

将来town editorを導入しても、棚・検索・Import・Exportの本体UIをWebGLへ移さない。

### Initial Features and Buildings

建物の意味と見た目を分離する。

| TownFeatureId | Initial visual | Opens |
|---|---|---|
| `shelf.movie` | 映画館 | 映画・視聴棚 |
| `shelf.story` | 物語館 | 漫画・アニメ棚 |
| `shelf.food` | 市場 | 食の地図 |
| `box.travel` | 港 | 旅行箱 |
| `system.inbox` | 倉庫 | 未整理Inbox |
| `reflection.square` | 中央広場 | Weekly / Month Box |

音楽広場、写真館、時計塔は後続候補。

TownFeatureIdはMemory OS上の意味であり、建物skin、asset、instance IDとは別にする。

---

## Spatial Architecture Principle

町を画面pixel座標の集合として保存しない。

最初から以下を正本にする。

```txt
logical grid position
+ parcel
+ footprint
+ placement layer
+ elevation level
+ orientation
+ stable definition ID
+ stable feature ID
+ layout revision
```

描画時だけscreen x / yへ変換する。

### Coordinate Contract

```txt
origin = logical north-west
+X = east
+Y = south
0° = north
90° = east
180° = south
270° = west
```

`elevation`はpixelではなくlogical levelで保存する。

### Object Granularity

```txt
地形・道・花 = tile単位
木・家具・街灯 = object単位
映画館などの建物 = multi-cellの完成sprite
```

建物を壁や屋根の1block単位には分解しない。

### Parcel and Growth Envelope

主要建物は、承認済み将来stageまでのgrowth envelopeを収める区画を予約する。

これにより、建物が大きくなった際に道路や装飾へ食い込む問題を防ぐ。

新stageがenvelopeを超える場合、asset差し替えだけで自動適用せず、versioned map migrationを必要とする。

### Layout Template

MVPの固定配置もcodeへpixel座標を直書きしない。

versioned layout templateから町を生成する。

Template更新時は、old baseline / current user layout / new templateのthree-way mergeを行う。

### Long-term Editing Phases

```txt
Phase 0: 固定layout。editorなし
Phase 1: predefined decoration slot
Phase 2: 指定zone内で木・花・家具を配置
Phase 3: 道路と植栽を編集
Phase 4: 主要建物をparcel間で移動
Phase 5: map / district expansion
```

---

## Five-state Separation

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

### Memory Domain State

棚、Import、進行、箱、確定したconnectionの正本。

### Town Feature Progress State

建物機能の解除済みstageを持つ。

通常のrecord削除やImport取り消しで建物を罰のように縮ませない。

### Town Layout State

建物、道、木、花、家具の配置。

Memory dataから再生成しない。

### Town Environment State

季節、時間帯、theme、motion、sound。

Memory Projectionへ混ぜない。

### Town Render State

camera、selection、texture、animationなど、そのsessionだけの状態。

永続化しない。

### Composition

```txt
Memory Domain
→ policy-filtered TownFeatureProjection

TownFeatureProgress
+ TownFeatureProjection
→ display stage / badge

Town Layout
+ Town Environment
+ feature bindings
→ TownSceneSnapshot
→ PixiJS
```

Required separation:

- memory削除後もuser decorationを保持
- building移動でmemory recordは不変
- asset / skin変更でfeature progressを失わない
- stage変更でinstanceIdを変えない
- hidden / sealed / restrictedはprojectionから除外可能
- rendererの再実装でlayout migrationを不要にする

---

## Growth Principle

成長はAIの価値判断で決めない。

使用可能な条件:

- 確定した記録件数
- 棚内のユニークitem数
- Import source数
- 完成した月の箱数
- ユーザーが確定したconnection数
- 利用年数

使用禁止:

- 感動度
- 幸福度
- 重要な人生イベント判定
- 性格分類
- 人間関係の評価
- sensitive内容の量

小さな記録も同じ蓄積として扱う。

### Non-shrinking Growth

```txt
candidate stage
= current eligible aggregateから計算

max unlocked stage
= Town Feature Progressへ保存

display stage
= max(candidate stage, max unlocked stage)
```

個別record削除では縮小しない。

ただしuserは、特定featureの成長、配置、装飾、町全体を明示的にresetできる。

Shelf deletion時は、対応する町の成長履歴も初期化する選択肢を出す。

Account deletionでは町の全stateを削除する。

---

## Road Model

物理的な道路と記憶のつながりを分離する。

```txt
Physical Path
= templateまたはuserが作る生活道路

Semantic Connection Overlay
= 確定した記憶関係を示す光、線、橋の演出
```

Physical Pathの永続データにはpath typeだけを保存する。

connection maskは周囲のcellから描画時に導出する。

物理道路を編集しても記憶関係は消えない。
記憶関係が変わってもユーザーの道路は勝手に消えない。

---

## Editor Persistence Principle

将来のeditorはdragごとにserver stateを書き換えない。

```txt
layout revisionをload
→ local draft
→ local validation
→ undo / redo
→ atomic command batch save
→ server revalidation
→ compare-and-swap
```

Rules:

- silent last-write-wins禁止
- stale revision上書き禁止
- command batchはall-or-nothing
- batch IDでidempotency
- server authoritative validation
- multi-device conflictは明示
- initial implementationでCRDTは採用しない

---

## Technology Direction

```txt
React / DOM
├─ Navigation
├─ Import Preview
├─ Search
├─ Shelf detail
├─ Forms and dialogs
├─ Accessibility list
└─ Future town editor controls

PixiJS / WebGL
└─ Memory Town
   ├─ logical isometric grid
   ├─ terrain tiles
   ├─ derived path autotile
   ├─ multi-cell buildings
   ├─ props / trees / flowers
   ├─ seasonal overlays
   ├─ passive residents
   └─ light effects
```

WebGL内でフォーム、長文、一覧、検索、重要操作を実装しない。

---

## MVP Boundary

Memory TownはMVPの価値検証に含めるが、最初から大規模にしない。

### Town Slice

- 1つのmap definition
- 1つのlayout template
- logical grid
- parcels
- growth envelopes
- 5主要建物
- 各3段階: 未開放 / 小 / 成長
- multi-cell footprint
- locked system placement
- stable TownFeatureId / binding
- 建物タップ
- 概要カード
- 棚へのroute
- Import後の小さな成長演出
- 1つの時間帯表現
- 静止画fallback

### MVP UIに含めない

- 自由配置editor
- 道路paint UI
- 建物移動UI
- 地形編集
- rotation UI
- 住人との会話
- 経済system
- resource消費
- 建築待ち時間
- streak
- ranking
- 他人の町への訪問
- multiplayer

### ただしMVP内部に含める契約

- grid coordinate
- footprint pivot
- parcel
- growth envelope
- placement layer
- orientation enum
- layout revision
- object definition catalog
- feature binding
- feature progress
- placement validator foundation
- immutable template versions
- RLS / ownership
- export / reset contract
- static fallback

---

## Product Safety

- 町は放置で荒れない
- 建物は罰として縮まない
- 住人や生物は寂しがらない
- 未整理Inboxが多くても罰表現をしない
- sensitiveな棚名や記憶本文を町に直接表示しない
- hidden / sealed / restrictedは成長集計から除外可能
- userが配置したobjectをmigrationで黙って削除しない
- 成長を早める課金をしない
- client validationだけで配置を保存しない
- town tableはuser_id + RLS fail closed
- account deletion後にtown stateを残さない

---

## Export / Reset

Town exportは以下を分離する。

```txt
feature progress
layout
environment preference
```

Memory dataと同じJSONへ無秩序に混ぜない。

Re-importはPreview、version compatibility、placement validationを通す。

unsupported objectはmagic coordinateではなく`stored` stateへ退避する。

---

## Versioning Principle

以下を別々にversion管理する。

```txt
spatial schema
map definition
layout template
object definition / catalog
growth envelope
feature projection schema
growth ruleset
asset manifest
scene schema
```

一つの`townVersion`へまとめない。

公開済みdefinitionをin-placeで意味変更しない。

---

## Design Completion Gate

PixiJS本実装へ進む前に以下を満たす。

```txt
[ ] 5-state separationが全docsで一致
[ ] TownFeatureId / bindingが固定
[ ] non-shrinking progress / resetが固定
[ ] coordinate / elevation / rotation pivotが固定
[ ] terrain / path正本が固定
[ ] growth envelopeが固定
[ ] object origin / placement state / lock policyが固定
[ ] template three-way mergeが固定
[ ] atomic batch / revision conflictが固定
[ ] RLS / export / account deletionが固定
[ ] asset compatibilityとmigration fixtureが固定
```

---

## Current Priority

1. 安全なImport基盤
2. Import Preview
3. 棚として見えるVertical Slice
4. 漫画・アニメ進行
5. 食の地域list
6. Home / Shelf navigation
7. Memory Town hardening contractsの整合確認
8. stable IDs / feature IDs / version sets
9. logical gridによるMemory Town static prototype
10. PixiJS interactive prototype
11. Import → town growth feedback
12. Month Capsule / future anticipation
13. decoration slot
14. user customization validation

---

## Final Statement

```txt
保存したものが棚になる。
棚の機能が建物へ結びつく。
解除した町の成長は、罰のように失われない。
配置と記憶は別々に守られる。
箱が町の風景になる。
つながった記憶は、生活道路とは別の光として見える。
少しずつ、自分の町として手を入れられる。
必要な時は、すべて持ち出せる。
```
