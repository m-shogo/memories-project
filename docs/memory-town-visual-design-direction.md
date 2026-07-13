# Memory Town Visual Design Direction

最終更新: 2026-07-13

## 目的

Memory Townの見た目、空気感、画面役割、asset規格を固定する。

詳細な状態・空間・migration契約は以下を優先する。

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-long-term-spatial-model.md`

目標は「ゲームを遊ばせること」ではない。

```txt
記録を積み重ねた結果、自分だけの小さな町に暮らしが生まれる。
```

この副次的な成果物が、保管・検索とは別のワクワクを作る。

---

## Terminology

今後の正式表現:

```txt
固定視点2.5D
```

意味:

- camera angleは固定
- map rotationなし
- MVPは固定layout
- 将来は同じ視点のまま配置編集可能

固定視点と固定配置を混同しない。

---

## Art Direction

### Core Style

- 固定視点2.5D
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
+ どうぶつの森のような自分の場所への愛着
+ 生活している町の静けさ
```

特定作品のUI、asset、建物、character、配色を複製しない。

避ける方向:

- 経営ゲームの過密UI
- 数字が常時飛び交う演出
- ガチャ風の発光
- 放置ゲーム風の報酬回収
- 本物のLEGOに近すぎる玩具感
- 写実的すぎる街
- 3Dゲームとしての自由移動
- Minecraft型の1block建築
- アバター操作中心

---

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

Townを使わなくても全機能へ到達できる。

---

## Feature and Visual Separation

建物の役割と見た目を分離する。

```txt
TownFeatureId
= shelf.movie

visual definition
= cinema_classic / cinema_small / cinema_theme_x
```

Rules:

- 映画棚の意味を`cinema`というasset IDへ固定しない
- skin変更でrouteや成長を失わない
- 建物移動で棚とのbindingを失わない
- 同じfeatureへ別visualを割り当て可能
- generic fallback buildingを用意する

---

## Camera

### MVP

- camera rotationなし
- perspective変更なし
- map全体を1画面で確認可能
- 建物選択時のみ短いfocus animation
- pinch zoomなし
- drag移動なし、または狭い範囲の補助panのみ
- bottom sheetで選択建物を完全に隠さない

### Later

Map拡張時はlogical presetを使う。

```txt
overview
district
focused
```

自由探索を中心にしない。

camera pixel positionを町の正本として保存しない。

---

## Initial Map Layout

MVPは固定layout templateを使う。

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

配置は画像内へ焼き込まず、versioned layout templateで定義する。

---

## Building Growth

各建物はMVPで3段階。

```txt
Stage 0: 未開放の土地・看板
Stage 1: 小さな建物
Stage 2: 成長した建物
```

将来Stage 3以降を追加可能にする。

### Non-shrinking Visual Rule

一度解除したstageは、通常のrecord削除では罰のように縮小しない。

表示件数は現在値を正しく表示する。

```txt
これまでに育った映画館
現在の映画棚 8件
```

ユーザーはfeature growth resetを明示的に実行できる。

### Growth Envelope

各主要建物は、承認済み将来stageまでのreserved growth cellsを持つ。

- decorationはenvelope外slotへ置く
- stage変更でuser decorationを消さない
- envelopeを超える新stageはmap migration対象
- assetだけを差し替えて既存layoutへ食い込ませない

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

未整理件数が多い場合でも、汚れ、崩壊、赤警告、罰表現を使わない。

---

## Physical Paths and Semantic Connections

二つを同じ道として扱わない。

### Physical Path

町の生活道路。

MVP:

- fixed layout template
- road / footpath / plaza
- path typeをlogical cellへ保存
- connection maskは周囲から導出

Later:

- user path editor
- autotile
- entrance connectivity validation

### Semantic Connection Overlay

説明可能で確定した記憶関係を示す視覚演出。

候補:

- 淡い光
- 足跡
- 小さな標識
- 一時的な線
- 航路の光

物理道路そのものを勝手に作成・削除しない。

例:

- 映画と音楽のconnection → 映画館と音楽広場の光
- 旅行箱と食の記録 → 港と市場を結ぶ足跡
- 写真と旅行箱 → 港と写真館の航路表示

理由をDOM詳細画面で確認可能にする。

弱いcandidateを確定表現として出さない。

---

## Life and Ambient Motion

生活感は常時操作ではなく、短いloopで作る。

### MVP Candidate

- 海面の揺れ
- 木の揺れ
- 映画館の看板灯
- 港の小船
- 煙突の煙

### P1 Candidate

- generic citizen最大3〜5人
- 昼夜で移動先が変わる
- 市場へ歩く
- 映画館へ入る
- 港で立ち止まる

住人はユーザー本人、家族、故人、実在人物を模倣しない。

user inactivityで寂しがる、倒れる、離れる演出をしない。

---

## Seasons and Environment

季節、時間帯、weather visualはTown Environment Stateとして扱う。

Memory Projectionへ混ぜない。

### Initial

- spring overlay
- summer overlay
- autumn overlay
- winter overlay
- day / evening / night palette

季節差分は建物本体を書き換えずoverlayで表現する。

例:

- 花びら
- 深い緑
- 紅葉
- 雪
- ランタン
- 窓明かり

利用しない期間があっても季節だけ自然に変化する。

記録がないために枯れる、暗くなる、荒れる表現は禁止。

Actual weather同期を必須にせず、precise locationを要求しない。

---

## Asset Architecture

見た目はドット調、構造は部品式。

```txt
assets/memory-town/
├─ terrain/
├─ paths/
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

### Required Asset Metadata

- stable texture key
- content hash
- asset manifest version
- supported orientation
- visual anchor
- depth anchor
- hit polygon
- render bounds
- footprint contract version
- shadow definition
- season overlay compatibility
- fallback texture key
- provenance / license record

### Asset Rules

- transparent WebPまたはPNG
- source canvas sizeをbuilding classごとに規格化
- contact shadowは同一方向
- light direction固定
- UI文字を画像へ焼き込まない
- building stateとseason overlayを分離
- hit area metadataをassetと別管理
- atlas再編でstable texture keyを変えない
- missing assetでinstanceを削除しない
- 文字入り看板を鏡像反転しない
- asset差し替えでfootprintを黙って変えない

---

## Pixel Treatment

完全なpixel-perfect低解像度ではなく、ドット感のあるhigh-resolution spriteを基本とする。

- citizenと小物: nearest-neighborに向くpixel sprite
- building: 少し高精細なdot-style illustration
- UI: 通常の高解像度DOM

本番量産前に比較する。

1. strict pixel art
2. high-resolution dot style
3. soft miniature illustration

現時点の推奨は2だが、prototypeで固定する。

---

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

### Future Share Privacy

町の共有機能を作る前に検討する。

- count hide
- badge hide
- label hide
- generic building mode
- private screenshot mode

初期は他人の町訪問・social sharingを実装しない。

---

## Sound

初期は無音でも成立させる。

後続候補:

- 建物選択音
- 成長時の短い音
- 港、風、鳥などの環境音

初期設定は環境音OFFまたは非常に控えめにする。

自動再生でユーザーを驚かせない。

---

## Motion Rules

- 常時激しく動かさない
- focus animation 200〜400ms程度をprototypeで検証
- growth animation 1〜2秒以内をprototypeで検証
- reduced motion対応
- 低電力modeではambient motionを停止可能
- navigationをanimation完了待ちにしない
- hidden tab / route leaveでticker停止

数値は実機検証後に確定する。

---

## Personalization Roadmap

MVPでは配置変更を提供しない。

```txt
Phase 0: fixed layout
Phase 1: predefined decoration slot
Phase 2: editable zone内の木・花・家具
Phase 3: physical path / planting editor
Phase 4: structure relocation
Phase 5: district expansion
```

配置編集より先に、見た目のpersonalizationを検討できる。

- 昼 / 夜
- 海辺 / 森 / 雪国theme
- building skin
- 季節装飾
- 船や街灯

成長速度、容量、建築待ち時間を課金対象にしない。

---

## Responsive Acceptance

対象viewport:

```txt
360x800
375x812
390x844
393x852
412x915
430x932
```

確認:

- overviewで主要buildingを認識可能
- tap targetが小さすぎない
- bottom sheetでselected buildingが隠れない
- safe area対応
- label表示でも破綻しない
- fallbackでも同じfeatureへ到達可能

---

## Design Acceptance Criteria

- 初見で主要建物の役割が想像できる
- label表示で役割を確認できる
- 町を使わなくても全機能へ到達できる
- 小さい画面でも建物をタップできる
- 建物が成長してもmap silhouetteが崩れない
- growth envelope内でstage差し替え可能
- 四季差分がhit areaを変えない
- reduced motionで機能が失われない
- dataが少なくても空虚ではなく、これから育つ場所に見える
- 現在件数が少なくても、解除済みstageが罰に見えない
- physical pathとsemantic overlayを視覚的に区別できる
- user customizationをmigrationで黙って失わない

---

## Design Statement

```txt
町を完成させるのではない。

自分の記録が、棚になり、建物へ結びつき、
長い時間をかけて、自分の場所になっていく。

その場所は、使わない日に荒れない。
削除やAIの評価で罰のように縮まない。
そして将来、少しずつ自分の手で整えられる。
```
