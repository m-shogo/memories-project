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
その蓄積は、固定2.5Dの「記憶の町」として視覚的に育つ。

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

- 固定2.5Dの記憶の町
- WebGL / PixiJS
- ドット調の温かいアート
- 内部構造は部品式・設定駆動
- 町は感情的なメニュー
- 棚画面は実用的な本体

## Navigation

推奨ナビゲーション:

```txt
町
棚
振り返り
追加
```

「発見」は独立タブとして固定せず、以下へ分散してもよい。

- 町の道・建物間の関係
- 棚内の関連記録
- 振り返り内のつながり
- 検索結果

情報設計の検証後に、発見タブを残すか判断する。

## Memory Town Role

町はゲーム本体ではない。

```txt
町 = 見て楽しく、機能を覚えやすい入口
棚 = 検索・更新・編集を行う通常UI
```

建物をタップすると概要カードを表示し、その後、対応する棚へ移動する。

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

## Visual Direction

```txt
固定2.5D
ドット調
柔らかい輪郭
低彩度を基調
季節と時間帯で表情が変わる
眺める8 : 操作2
```

カイロソフトの親しみやすさは参考にするが、経営ゲーム風の密度、数値UI、ランキング、効率化ゲームには寄せない。

見た目はドット調、実装構造はブロック式にする。

## Technology Direction

```txt
React / DOM
├─ Navigation
├─ Import Preview
├─ Search
├─ Shelf detail
├─ Forms and dialogs
└─ Accessibility list

PixiJS / WebGL
└─ Memory Town
   ├─ terrain
   ├─ roads
   ├─ buildings
   ├─ seasonal overlays
   ├─ passive residents
   └─ light effects
```

WebGL内でフォーム、長文、一覧、検索、重要操作を実装しない。

## MVP Boundary

Memory TownはMVPの価値検証に含めるが、最初から大規模にしない。

### Town Slice

- 1つの固定map
- 5建物
- 各3段階: 未開放 / 小 / 成長
- 建物タップ
- 概要カード
- 棚へのroute
- Import後の小さな成長演出
- 1つの時間帯表現
- 静止画fallback

### Not MVP

- 自由配置
- 街づくり編集
- 3D model
- 住人との会話
- 経済system
- resource消費
- 建築待ち時間
- streak
- ランキング
- 他人の町への訪問
- multiplayer

## Return Value

毎日開くことを要求しない。

戻る理由:

- 棚を更新する
- 続きを確認する
- 月の箱を見る
- 町の小さな変化を見る
- 新しい建物や道が現れる
- 必要な情報を探す
- Export / AI Context Packを作る

## Product Safety

- 町は放置で荒れない
- 建物は縮まない
- 住人や生物は寂しがらない
- 未整理Inboxが多くても罰表現をしない
- sensitiveな棚名や記憶本文を町に直接表示しない
- rendererへ渡すのは集計済みtown projectionのみ
- hidden / sealed / restrictedは成長集計から除外可能にする

## Source of Truth Separation

```txt
Memory data
→ policy-filtered aggregate
→ town projection
→ WebGL rendering
```

町の状態を記憶データの正本にしない。

削除・修正・Import取り消しに対応できるよう、町は常に再計算可能なprojectionとする。

## Current Priority

1. 安全なImport基盤
2. Import Preview
3. 棚として見えるVertical Slice
4. 漫画・アニメ進行
5. 食の地域list
6. Home / Shelf navigation
7. Memory Town static prototype
8. PixiJS interactive prototype
9. Import → town growth feedback
10. Month Capsule / future anticipation

## Final Statement

```txt
保存したものが棚になる。
棚が建物になる。
箱が町の風景になる。
つながった記憶が道になる。
必要な時は、すべて持ち出せる。
```
