# Current Product Direction

最終更新: 2026-07-13

この文書は、Memory OS の現時点のプロダクト方向性を一枚で確認するための正本である。

既存の詳細仕様がこの文書と矛盾する場合、明示的な更新が入るまで本書を優先する。

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
その蓄積は、固定2.5Dで見える「記憶の町」として視覚的に育つ。

町はMVPでは固定配置だが、内部空間は最初からlogical gridで定義し、将来は道路、木、花、家具、建物などを段階的に編集できる構造にする。

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

- 固定2.5Dで見える記憶の町
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
見た目: 温かい2.5Dのジオラマ
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

### Initial Buildings

| Building | Opens | Initial meaning |
|---|---|---|
| 映画館 | 映画・視聴棚 | 見た・見たい・お気に入り |
| 物語館 | 漫画・アニメ棚 | 進行・続刊待ち |
| 市場 | 食の地図 | 行った・行きたい店 |
| 港 | 旅行箱 | 旅行・未来の予定 |
| 倉庫 | 未整理Inbox | 後から整理する記録 |
| 中央広場 | Weekly / Month Box | 今週・今月の変化 |

音楽広場、写真館、時計塔は後続候補。

---

## Spatial Architecture Principle

町を画面pixel座標の集合として保存しない。

最初から以下を正本にする。

```txt
logical grid position
+ parcel
+ footprint
+ placement layer
+ elevation
+ orientation
+ stable definition ID
+ layout revision
```

描画時だけscreen x / yへ変換する。

### Object Granularity

```txt
地形・道・花 = tile単位
木・家具・街灯 = object単位
映画館などの建物 = multi-cellの完成sprite
```

建物を壁や屋根の1block単位には分解しない。

### Parcel

主要建物は、最大成長時のfootprintを収める区画を最初から予約する。

これにより、建物が大きくなった際に道路や装飾へ食い込む問題を防ぐ。

### Layout Template

MVPの固定配置もcodeへpixel座標を直書きしない。

versioned layout templateから町を生成する。

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

### Growth and Layout Separation

```txt
building stage
= Memory Domainから導出されるTown Projection

building position
= Town Layout State
```

建物が成長しても配置instance ID、route、parcelを維持する。

ユーザーが配置を変えてもMemory Domainを変更しない。

---

## Visual Direction

```txt
固定cameraの2.5D
ドット調
柔らかい輪郭
低彩度を基調
季節と時間帯で表情が変わる
眺める8 : 操作2
```

カイロソフトの親しみやすさは参考にするが、経営ゲーム風の密度、数値UI、ランキング、効率化ゲームには寄せない。

どうぶつの森的な愛着と編集余地は参考にするが、アバター操作、経済、素材集め、クラフトを中心にしない。

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
   ├─ path autotile
   ├─ multi-cell buildings
   ├─ props / trees / flowers
   ├─ seasonal overlays
   ├─ passive residents
   └─ light effects
```

WebGL内でフォーム、長文、一覧、検索、重要操作を実装しない。

空間設計の正本:

- `docs/memory-town-long-term-spatial-model.md`
- `docs/memory-town-webgl-architecture.md`

---

## State Separation

```txt
Memory Domain State
→ policy-filtered Town Projection

Town Layout State
→ logical position / user customization

Town Projection + Town Layout
→ Town Scene Snapshot
→ WebGL Rendering
```

町の状態を記憶データの正本にしない。

町のlayoutもrenderer stateにしない。

### Required Separation

- memory削除後もuser decorationを保持
- shelf count変更はbuilding stageへ反映
- building移動でmemory recordは不変
- hidden / sealed / restrictedはprojectionから除外可能
- rendererの再実装でlayout migrationを不要にする

---

## MVP Boundary

Memory TownはMVPの価値検証に含めるが、最初から大規模にしない。

### Town Slice

- 1つのmap definition
- 1つのlayout template
- logical grid
- parcels
- 5建物
- 各3段階: 未開放 / 小 / 成長
- multi-cell footprint
- locked system placement
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
- footprint
- parcel
- placement layer
- orientation enum
- layout revision
- object definition catalog
- placement validator foundation

---

## Road Model

物理的な道路と記憶のつながりを分離する。

```txt
Physical Path
= templateまたはuserが作る生活道路

Semantic Connection Overlay
= 確定した記憶関係を示す光、線、橋の演出
```

物理道路を編集しても記憶関係は消えない。

記憶関係が変わってもユーザーの道路は勝手に消えない。

---

## Return Value

毎日開くことを要求しない。

戻る理由:

- 棚を更新する
- 続きを確認する
- 月の箱を見る
- 町の小さな変化を見る
- 新しい建物や道が現れる
- 町を少し飾る
- 必要な情報を探す
- Export / AI Context Packを作る

---

## Product Safety

- 町は放置で荒れない
- 建物は罰として縮まない
- 住人や生物は寂しがらない
- 未整理Inboxが多くても罰表現をしない
- sensitiveな棚名や記憶本文を町に直接表示しない
- rendererへ渡すのは集計済みtown projectionのみ
- hidden / sealed / restrictedは成長集計から除外可能
- userが配置したobjectをmigrationで黙って削除しない
- 成長を早める課金をしない

---

## Versioning Principle

以下を別々にversion管理する。

```txt
spatial schema
map definition
layout template
object catalog
projection schema
growth ruleset
asset manifest
```

一つの`townVersion`へまとめない。

user layout migrationは、preview、safe relocation、rollback snapshotを持つ。

---

## Current Priority

1. 安全なImport基盤
2. Import Preview
3. 棚として見えるVertical Slice
4. 漫画・アニメ進行
5. 食の地域list
6. Home / Shelf navigation
7. spatial model contractsとstable IDs
8. logical gridによるMemory Town static prototype
9. PixiJS interactive prototype
10. Import → town growth feedback
11. Month Capsule / future anticipation
12. decoration slot
13. user customization validation

---

## Final Statement

```txt
保存したものが棚になる。
棚が建物になる。
箱が町の風景になる。
つながった記憶が道になる。
少しずつ、自分の町として手を入れられる。
必要な時は、すべて持ち出せる。
```
