# Memory Town Visual Design Direction

最終更新: 2026-07-13

## 目的

Memory Townの見た目、空気感、画面役割、asset規格を固定する。

目標は「ゲームを遊ばせること」ではない。

```txt
記録を積み重ねた結果、自分だけの小さな町に暮らしが生まれる。
```

この副次的な成果物が、保管・検索とは別のワクワクを作る。

## Art Direction

### Core Style

- 固定2.5D
- 斜め見下ろし
- ドット調のイラスト
- 完全な低解像度pixel artより少し高精細
- 輪郭は柔らかい
- 過度なネオン、派手なゲームHUDを避ける
- 白、生成り、木、植物、空、水を基調にする
- 建物ごとに識別色を持つが、全体の彩度を揃える

### Reference Balance

```txt
カイロソフトの分かりやすさ
+ ミニチュア・ジオラマの所有感
+ 絵本の温かさ
+ 生活している町の静けさ
```

避ける方向:

- 経営ゲームの過密UI
- 数字が常時飛び交う演出
- ガチャ風の発光
- 放置ゲーム風の報酬回収
- 本物のLEGOに近すぎる玩具感
- 写実的すぎる街
- 3Dゲームとしての自由移動

## Town as Menu

町は視覚的なメニューとして機能する。

### Interaction

```txt
建物を1回タップ
→ カメラが少し寄る
→ DOM概要カードを表示
→ 「棚を開く」で通常画面へ
```

概要カード例:

```txt
映画館
映画棚 126件
見たい作品 8件
今月追加 3件
[映画棚を開く]
```

町に不慣れな人向けに、建物名ラベルと通常の棚一覧を必ず提供する。

## Camera

### MVP

- camera rotationなし
- perspective変更なし
- map全体を1画面で確認可能
- 建物選択時のみ短いfocus animation
- pinch zoomなし
- drag移動なし、または狭い範囲の補助panのみ

### Later

必要性が確認できた場合のみ、3区画程度の横移動を検討する。

自由探索は採用しない。

## Initial Map Layout

固定区画を使う。

```txt
             物語館

     映画館       時計塔候補

          中央広場

       市場       倉庫

             港
~~~~~~~~~~~~ 海 ~~~~~~~~~~~~
```

地形と建物の役割を一致させる。

- 港は海辺
- 市場は広場に近い
- 倉庫は港または外周
- 映画館と物語館は町中心寄り
- 中央広場はWeekly / Month Capsule

## Building Growth

各建物はMVPで3段階。

```txt
Stage 0: 未開放の土地・看板
Stage 1: 小さな建物
Stage 2: 成長した建物
```

将来Stage 3以降を追加可能にするが、asset pathとdata schemaは任意段階に対応させる。

### Cinema

- Stage 0: 空地と映画ポスター看板
- Stage 1: 小さな上映小屋
- Stage 2: 街の映画館
- Later: 記憶劇場、映画祭の旗、夜の看板

### Story House

- Stage 0: 本箱と案内板
- Stage 1: 小さな書店
- Stage 2: 物語館
- Later: 塔、増築書庫、新刊旗

### Market

- Stage 0: 一つの屋台
- Stage 1: 小さな市場
- Stage 2: 食の通り
- Later: 地域ごとの屋台、小さな看板

### Port

- Stage 0: 桟橋
- Stage 1: 船着場
- Stage 2: 港
- Later: 灯台、航路、旅行箱の小島

### Inbox Warehouse

- Stage 0: 小さな受取所
- Stage 1: 倉庫
- Stage 2: 整理された物流所

未整理件数が多い場合でも、汚れ・崩壊・警告色で罰しない。

## Roads and Connections

道はrelationの視覚表現にも使う。

### MVP

道は固定mapの一部。

### Later

説明可能なrelationが一定数成立した時のみ、装飾的な道・橋・航路を追加する。

例:

- 映画と音楽の作品connection → 映画館と音楽広場の小道
- 旅行箱と食の記録 → 港と市場の道
- 写真と旅行箱 → 港と写真館の遊歩道

道の生成理由を詳細画面で確認可能にする。

## Life and Ambient Motion

生活感は常時操作ではなく、短いloopで作る。

### MVP Candidate

- 海面の揺れ
- 木の揺れ
- 映画館の看板灯
- 港の小船
- 煙突の煙

### P1 Candidate

- 住人最大5人
- 昼夜で移動先が変わる
- 市場へ歩く
- 映画館へ入る
- 港で立ち止まる

住人はユーザー本人、家族、故人、実在人物を模倣しない。generic citizenのみ。

## Seasons and Time

季節は現実の日付に同期する。

### Initial

- spring overlay
- summer overlay
- autumn overlay
- winter overlay

季節差分は建物本体を書き換えずoverlayで表現する。

例:

- 花びら
- 深い緑
- 紅葉
- 雪
- ランタン
- 窓明かり

利用しない期間があっても、季節だけ自然に変化する。

記録がないために枯れる、暗くなる、荒れる表現は禁止。

## Asset Architecture

見た目はドット調、構造は部品式。

```txt
assets/memory-town/
├─ terrain/
├─ roads/
├─ buildings/
│  ├─ cinema/
│  │  ├─ stage-0.webp
│  │  ├─ stage-1.webp
│  │  ├─ stage-2.webp
│  │  └─ overlays/
│  ├─ story-house/
│  ├─ market/
│  ├─ port/
│  └─ inbox-warehouse/
├─ props/
├─ citizens/
├─ vehicles/
├─ seasons/
├─ effects/
└─ atlases/
```

### Asset Rules

- transparent WebPまたはPNG
- anchor pointを規格化
- source canvas sizeを建物classごとに固定
- contact shadowは同一方向
- light direction固定
- UI文字を画像へ焼き込まない
- building stateとseason overlayを分離
- hit area metadataをassetと別管理

## Pixel Treatment

完全なpixel-perfect低解像度ではなく、ドット感のあるhigh-resolution spriteを基本とする。

- citizenと小物: nearest-neighborに向くpixel sprite
- building: 少し高精細なdot-style illustration
- UI: 通常の高解像度DOM

これによりスマホでの可読性とasset差し替えの容易さを両立する。

## Information Density

町の中へ直接表示する情報は少なくする。

許可:

- 建物名
- 小さな新着印
- 成長変化
- 1行の状態

禁止:

- 長いタイトル一覧
- sensitiveな記憶本文
- 人名
- private写真の自動掲示
- 多数のbadge
- notification center化

## Sound

初期は無音でも成立させる。

後続候補:

- 建物選択音
- 成長時の短い音
- 港、風、鳥などの環境音

初期設定は環境音OFFまたは非常に控えめにする。
自動再生でユーザーを驚かせない。

## Motion Rules

- 常時激しく動かさない
- focus animation 200〜400ms程度
- growth animation 1〜2秒以内
- reduced motion対応
- 低電力modeではambient motionを停止可能
- navigationをanimation完了待ちにしない

## Personalization

MVPでは配置変更を提供しない。

将来的なpersonalizationは、構造ではなく見た目から始める。

- 昼 / 夜
- 海辺 / 森 / 雪国theme
- 建物skin
- 季節装飾
- 船や街灯

成長速度や容量を課金対象にしない。

## Design Acceptance Criteria

- 初見で主要建物の役割が想像できる
- label表示で役割を確認できる
- 町を使わなくても全機能へ到達できる
- 小さい画面でも建物をタップできる
- 建物が成長してもmapのsilhouetteが崩れない
- 四季差分が建物hit areaを変えない
- reduced motionで機能が失われない
- dataが少なくても空虚ではなく、これから育つ場所に見える

## Design Statement

```txt
町を完成させるのではない。
記録を重ねた結果、少しずつ暮らしが増える。
```
