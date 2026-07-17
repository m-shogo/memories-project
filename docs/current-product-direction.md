# Current Product Direction

最終更新: 2026-07-17

This document summarizes the current product direction. Security and implementation status are governed by:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `README.md`

Detailed Memory Town contracts remain valid design inputs, but do not override the current Capture / Import priority or native iOS technology direction.

---

# Product promise

```txt
軽く取り込む
→ 保存前にPreviewする
→ 自分の棚として見える
→ 必要な時に探して更新できる
→ 月・年・つながりとして再発見できる
→ 記録の積み重ねが自分だけの町として後から見える
→ 必要なら外へ持ち出せる
```

Memory OS is not just storage, but the practical value starts with reliable capture, retrieval, correction and portability.

```txt
Memory is the product.
Town is the visible side effect.
```

---

# Product hierarchy

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

A Town feature is not allowed to delay, weaken or distort core Memory behavior.

---

# Core product layers

## 1. Practical layer

- Universal Quick Add
- iOS Share Extension intake
- local Files intake
- Import Preview
- media-specific shelves
- manga/anime progress
- movie/viewing shelf
- food map
- unorganized Inbox
- Search
- Export

## 2. Reflection layer

- Weekly Box
- Month Capsule
- year/season views
- safe resurfacing
- user-confirmed cross-source connections

## 3. Anticipation layer

- user-explicit “continue following” targets
- future release/distribution dates
- future enjoyment box
- release calendar

General recommendation feeds and advertising-driven discovery are not the center of the product.

## 4. Emotional visualization layer

- fixed-view 2.5D Memory Town
- warm sprite-based art
- Town as an emotional entry/menu
- shelves as the practical editing/search interface
- fixed-layout MVP; logical grid internally
- optional future decoration, path, planting and building movement

Town does not become the authority for memories, permissions, deletion, search or export.

---

# First experience

The first run must not require ZIP files, API tokens or complex migration.

```txt
SPY×FAMILY 12巻まで
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

Before saving, show a clear Preview.

After saving:

```txt
保存した内容
→ 入った棚・進行
→ optionalな小さなTown反応
→ 棚を見る / 続きを更新 / 閉じる
```

Town growth is never the reason presented to pressure the user into capturing more.

---

# Binding platform direction

```txt
iOS canonical client:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain + App Group

limited bulk migration:
Desktop Import Portal
Vite + React + TypeScript

canonical backend:
Go API
PostgreSQL with FORCE RLS
private versioned S3-compatible quarantine
isolated parser supervisor / worker

Memory Town after backend P0:
SpriteKit
Metal only after a measured blocker
```

Earlier PixiJS/WebGL architecture documents are retained as useful spatial/rendering design exploration, but are not the binding runtime choice for the current iOS-only product.

Parser, adapter, dedupe, Preview and Apply logic are canonical in the backend and must not be independently duplicated in Swift and browser code.

---

# Navigation direction

Candidate iOS navigation:

```txt
ホーム / 棚
振り返り
追加
町
```

The exact tab arrangement remains subject to usability testing. “Discovery” may remain distributed across shelf relations, reflection, search results and Town overlays rather than becoming a mandatory standalone feed.

The Add and Search paths must remain accessible without entering Town.

---

# Memory Town role

```txt
町 = 見て楽しく、機能を覚えやすい入口
棚 = 検索・更新・編集を行う通常UI
```

Initial semantic features may bind to visuals such as:

| Town feature | Example visual | Opens |
|---|---|---|
| `shelf.movie` | 映画館 | 映画・視聴棚 |
| `shelf.story` | 物語館 | 漫画・アニメ棚 |
| `shelf.food` | 市場 | 食の地図 |
| `box.travel` | 港 | 旅行箱 |
| `system.inbox` | 倉庫 | 未整理Inbox |
| `reflection.square` | 中央広場 | Weekly / Month Box |

Feature meaning, visual definition, asset and placed instance remain separate identifiers.

## Spatial state separation

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

- memory deletion does not automatically delete user decoration;
- building movement does not mutate Memory records;
- asset/skin changes do not lose feature progress;
- hidden/sealed/restricted records may be excluded from Town projection;
- renderer replacement does not require Memory migration;
- account deletion removes all Town state.

## Growth principle

Town growth may use neutral, user-visible aggregates such as confirmed records or unique shelf items. It must not use happiness, emotional intensity, personality, sensitive content volume or an AI-defined life-event score.

Normal record deletion does not punish the user by shrinking already unlocked Town stages. Explicit Reset is separate, reversible where possible and never deletes Memory records implicitly.

## Environment direction

- morning / day / night / midnight;
- device local time with manual preview;
- cloud, sun, moon, beach and wave ambience;
- four-season Memory Tree;
- optional unified wind field;
- no exact real-weather/tide/astronomy dependency.

Environment state is not Memory authority.

---

# Current implementation status

```txt
Town design contracts:
ADVANCED

Town runtime:
NOT IMPLEMENTED

Town implementation priority:
DEFERRED

reason:
Capture / Import P0 security and reliability blockers remain
```

The current implementation order is defined in `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`.

---

# Product non-goals

- LLM/chat assistant replacement
- simulated deceased/family/partner personalities
- AI romantic dependency
- happiness/personality scoring
- daily quests, login rewards and streak punishment
- currency, crafting and furniture gacha
- care obligations, decay or forced cleaning
- placement score and Town ranking
- limited-time reward/FOMO
- public Town feed/follower competition
- construction timers or paid acceleration
- progress bars showing records needed for the next building stage
- capture prompts whose purpose is Town growth
- mandatory Town-only fields
- multiplayer Town

---

# Product statement

```txt
記憶を入れたいと思えることが先。
保存したものが棚になる。
必要な時に探せて、続きを更新できる。
町は、その積み重ねが後から見える副次的な結果。
戻らなくても、町は荒れず、責めず、損をさせない。
必要な時は、すべて持ち出せる。
```
