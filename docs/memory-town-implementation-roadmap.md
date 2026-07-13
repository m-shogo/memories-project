# Memory Town Implementation Roadmap

最終更新: 2026-07-13

## 目的

Memory Townを、既存のImport・棚・振り返り計画を壊さず段階的に実装する。

町だけを先に作り込みすぎない。

```txt
棚の価値を証明
→ 静止した町へ投影
→ WebGLで触れる
→ Import結果が町へ反映
→ 季節・生活感・connectionを足す
```

## Product Gate

Memory TownはMVPに含めるが、Import基盤より先行しない。

町は以下が成立してから本格接続する。

- safe commit可能
- shelf countを取得可能
- projection用aggregateが存在
- delete / rollback後に再計算可能
- hidden / sealed / restricted exclusionが成立

## Phase T0: Design Contract

### Deliverables

- current product direction
- visual design direction
- WebGL architecture
- building definition schema
- initial map layout
- asset naming contract
- performance budget
- fallback rules

### Exit Criteria

- 町と棚の責務が分離されている
- 5建物とrouteが決定している
- 3 growth stagesが定義されている
- raw memoryをrendererへ渡さない方針が固定されている

## Phase T1: Static Town Prototype

WebGL導入前に、1枚背景＋DOM hotspotで体験を確認する。

### Scope

- fixed 2.5D map image
- cinema
- story house
- market
- port
- inbox warehouse
- building labels
- summary bottom sheet
- route navigation
- shelf fixture counts

### Purpose

検証すること:

- 町がmenuとして理解できるか
- 建物と棚の対応が分かるか
- スマホでtapしやすいか
- shelf gridより町を見たいと思うか

### Acceptance

- 390px幅で主要建物をtap可能
- labelなし / labelありを比較可能
- townを使わず通常navigationでも到達可能
- summary cardから棚へ遷移可能

## Phase T2: PixiJS Scene Foundation

### Scope

- PixiJS application bootstrap
- renderer lifecycle
- scene graph
- asset manifest
- texture loading
- building sprites
- hit areas
- overview / focus camera
- React bridge
- static fallback

### No-Go

- citizens
- weather
- free pan
- free zoom
- growth animation
- dynamic roads

### Acceptance

- 5建物をWebGL表示
- tapでDOM card表示
- route leaveでticker停止
- context lossでfallback
- reduced motionでfocus animationを省略

## Phase T3: TownProjection

### Scope

- versioned TownProjection DTO
- building stage resolver
- policy-filtered aggregate
- projection cache
- rebuild command
- old/new projection diff

### Initial Growth Bands

仮値。user test後に調整する。

| Building | Stage 0 | Stage 1 | Stage 2 |
|---|---:|---:|---:|
| cinema | 0 | 1〜24 | 25以上 |
| story house | 0 | 1〜14 | 15以上 |
| market | 0 | 1〜9 | 10以上 |
| port | 0 | 1 travel box | 2以上 |
| inbox warehouse | always visible | inbox available | multiple source types |

Inbox件数を成長条件に直接使わない。
未整理を増やすほど得になる構造を避ける。

### Acceptance

- projectionをmemory tableと独立して生成可能
- delete後にstageが再計算される
- restricted recordsを除外可能
- ruleset versionを保持
- threshold変更migration testがある

## Phase T4: Import to Town Feedback

### Flow

```txt
Quick Add / Import
→ Preview
→ Safe Commit
→ shelf count update
→ TownProjection regenerate
→ scene diff
→ aggregate growth feedback
```

### Visual Feedback

- 対応建物が短く光る
- stage change時のみ建物差し替え
- summary copy

例:

```txt
漫画・アニメ棚に12件追加しました
物語館ができました
```

### Acceptance

- 100件Importでもanimationは1回
- animation skip可能
- town画面を開いていなくてもstate更新
- 次回open時に新しい姿が反映
- Import成功を町演出完了へ依存させない

## Phase T5: Season and Time

### Scope

- four-season overlays
- day / evening / night palette
- local date-based season resolver
- manual theme override optional
- low power toggle

### Acceptance

- season changeでbuilding assetを再生成しない
- overlayのみ差し替え可能
- hit areas不変
- no-record期間でも町が荒れない

## Phase T6: Ambient Life

### First Additions

- water loop
- one boat
- tree movement
- building light
- smoke

### Later

- generic citizens 3〜5人
- deterministic short routes
- simple schedule by time mode

### Acceptance

- user identityをcitizenへ割り当てない
- citizenとのchatなし
- route navigationへ干渉しない
- low powerで全停止可能
- 30分idleでmemory leakなし

## Phase T7: Capsules and Decorations

### Weekly Box

中央広場へ小さな一時装飾を出す。

### Month Capsule

- monthly flag
- lantern
- flower bed
- seasonal object

### Rules

- month qualityを評価しない
- record amountの競争にしない
- 月が空でも失敗表示しない
- user-selected event boxだけ特別装飾可能

## Phase T8: Connections as Roads

### Scope

confirmed relationだけを対象にする。

- fixed decorative road variants
- bridge / route overlays
- relation reason panel
- accessibility list

### Initial Relation Types

- movie ↔ music
- travel ↔ food
- travel ↔ photo
- manga/anime ↔ audio

### No-Go

- personality inference road
- emotional relation
- hidden graph relation
- unexplained AI-generated connection

### Acceptance

- 道の理由を確認可能
- graphなしでもrelation一覧が使える
- weak candidateを実線表示しない
- color-only encoding禁止

## Phase T9: Future Anticipation

「未来の楽しみ」を町へ追加する。

### Examples

- story houseに新刊旗
- cinemaに配信開始poster frame
- portに旅行予定の船
- central squareに今月の楽しみbox

### Rules

- userがfollowした対象だけ
- general recommendationを混ぜない
- ad placement禁止
- notification default OFF

## Initial Ticket Backlog

### MT-001 Town domain contract

- TownProjection types
- stable building IDs
- projection schema version

### MT-002 Static map wireframe

- 390x844
- 430x932
- desktop narrow panel

### MT-003 Building route map

- cinema → movie shelf
- story house → manga/anime shelf
- market → food list/map
- port → travel box
- warehouse → Inbox

### MT-004 Asset manifest

- stage 0〜2
- anchors
- hit areas
- texture keys

### MT-005 Pixi bootstrap

- lazy load town bundle
- application lifecycle
- fallback boundary

### MT-006 Building selection bridge

- pointer event
- React state
- DOM summary sheet
- route open

### MT-007 Projection projector

- aggregate counts
- exclusion policy
- ruleset version

### MT-008 Projection diff

- stage changed
- recent delta
- capsule change

### MT-009 Growth animation

- one aggregate event
- skip / reduced motion

### MT-010 Performance guard

- ticker pause
- low power
- context loss
- telemetry without private data

### MT-011 Visual regression matrix

- all stages
- four seasons
- overview / focused
- fallback

### MT-012 User test

Tasks:

1. 映画棚を開く
2. 未整理Inboxを探す
3. どの建物が何か説明する
4. 最近成長した建物を見つける
5. 通常menuから同じ場所へ移動する

## Performance Gates

Before T2 complete:

- route leaveで描画停止
- static fallback動作
- initial bundleを通常棚画面から分離
- town asset failureでapp全体が落ちない

Before T6 complete:

- 低性能端末profileで操作可能
- reduced motion確認
- long idle leak test
- background / foreground復帰test

## Visual Production Gates

本番asset量産前に、以下3点をprototypeで比較する。

1. 完全pixel art
2. high-resolution dot-style
3. soft miniature illustration

現時点の推奨は2。

比較対象:

- スマホでの可読性
- asset差分の作りやすさ
- animationの自然さ
- 3年後の古さ
- AI生成後の人間修正量

## MVP Go / No-Go

### Go

- fixed map
- WebGL / PixiJS
- 5 buildings
- 3 stages
- DOM summary sheet
- static fallback
- projection aggregate
- short growth feedback

### No-Go

- free placement
- city editor
- social visit
- multiplayer
- citizen dialogue
- virtual currency
- quests
- building timers
- content importance scoring
- paid growth acceleration
- mandatory daily interaction

## Definition of Success

Memory Town成功の判断は、町を長く眺めた時間だけではない。

見る指標:

- town open率
- building tap率
- townからshelfへの遷移率
- Import後にtown changeを確認した率
- townなしnavigationの成功率
- fallback率
- performance complaint率
- 「もっと記録を入れたい」と感じたuser interview反応

## Final Rule

```txt
町の完成度より先に、棚の実用性を完成させる。
ただし、棚だけでは生まれない愛着を、町で早い段階から検証する。
```
