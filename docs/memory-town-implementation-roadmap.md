# Memory Town Implementation Roadmap

最終更新: 2026-07-13

## 目的

Memory Townを、既存のImport・棚・振り返り計画を壊さず、かつ将来の編集可能な箱庭へ拡張しても作り直しにならない順番で進める。

実装はまだ開始しない。

優先参照:

- `docs/memory-town-architecture-hardening-contract.md`
- `docs/memory-town-hardening-tickets.md`
- `docs/memory-town-spatial-foundation-tickets.md`
- `docs/memory-town-design-audit-and-risk-register.md`

---

## Product Gate

Memory TownはMVPに含めるが、Import基盤より先行しない。

本格接続の前提:

- safe commit可能
- shelf aggregate取得可能
- hidden / sealed / restricted exclusion成立
- delete / rollback契約成立
- town stateがmemoryの正本ではない

---

# Phase T0: Contract Hardening

## Scope

- fixed-view terminology
- five-state separation
- TownFeatureId registry
- feature binding
- non-shrinking feature progress
- reset / privacy erasure
- canonical coordinates
- footprint pivot
- terrain / path source of truth
- growth envelope
- object origin / placement / lock policy
- immutable versions
- three-way template merge
- atomic command batch
- RLS / export / recovery

## Exit

`memory-town-hardening-tickets.md`のP0 Exit Gateを満たす。

PixiJS本実装はまだ開始しない。

---

# Phase T1: Design Fixtures

## Deliverables

```txt
initial feature registry fixture
initial map definition fixture
initial terrain fixture
initial parcel fixture
initial growth envelope fixture
initial object catalog fixture
initial layout template fixture
initial feature binding fixture
initial feature progress fixture
initial scene snapshot fixture
```

## Required variants

- empty data
- low data
- Stage 1
- Stage 2
- current count 0 / unlocked Stage 2
- missing asset
- deprecated object
- stored object
- hidden / sealed exclusion

## Exit

- schema validation
- deterministic serialization
- stable IDs
- no private fields

---

# Phase T2: Static Town Experience Prototype

WebGL導入前に、静止表示とDOM hotspotで体験を確認する。

## Scope

- fixed-view 2.5D map image or generated static layers
- cinema
- story house
- market
- port
- warehouse
- central square
- feature labels
- summary bottom sheet
- route navigation
- shelf fixture counts

## Purpose

- 町がmenuとして理解できるか
- featureとvisualの対応が分かるか
- smartphoneでtapしやすいか
- Shelf Gridと併存できるか
- bottom sheetで対象が隠れないか

## Acceptance

- 6 viewportで主要featureをtap可能
- labelあり / なし比較
- normal navigationでも到達可能
- summary cardから棚へ遷移
- fallback IDsがFeature IDsと一致

---

# Phase T3: Spatial Domain Foundation

## Scope

- coordinate convention
- gridToScreen / screenToGrid
- footprint pivot / rotation
- terrain
- parcel
- growth envelope
- object definitions
- object instances
- feature bindings
- layout template
- placement validator
- derived path mask

## No-Go

- renderer内business rules
- screen x/y persistence
- free editor UI
- stageごとの別instance

## Acceptance

- PixiJSなしで全domain test
- property tests
- invalid layout rejected
- deterministic scene input

---

# Phase T4: Progress / Layout / Environment Composition

## Scope

```txt
Memory Domain
→ TownFeatureProjection

FeatureProgress
+ FeatureProjection
+ FeatureBinding
+ Layout
+ Environment
→ TownSceneSnapshot
```

## Acceptance

- current eligible count正確
- max unlocked stage維持
- record削除でuser decoration維持
- skin変更でfeature progress維持
- environment変更でprojection不変
- path mask導出
- private content非流入

---

# Phase T5: Persistence / RLS / Recovery Skeleton

## Scope

- current-state tables contract
- user_id / RLS
- layout revision
- snapshot
- event audit
- stored state
- reset command
- export manifest

## Acceptance

- missing user context fail closed
- cross-user IDs拒否
- locked object mutation拒否
- account deletion全削除契約
- corrupted layout recovery fixture

まだuser editorは公開しない。

---

# Phase T6: PixiJS Scene Foundation

## Prerequisite

T0〜T5完了。

## Scope

- PixiJS bootstrap
- renderer lifecycle
- scene graph
- asset manifest
- texture loading
- terrain / path layers
- structure / prop sprites
- hit areas
- overview / focus camera
- React bridge
- static fallback

## No-Go

- citizens
- weather animation
- free pan / zoom
- growth animation
- path editor
- user placement

## Acceptance

- 5主要建物表示
- tapでDOM card
- route leaveでticker停止
- context loss fallback
- reduced motion
- deterministic z sort
- missing asset placeholder

---

# Phase T7: Import to Feature Growth Feedback

## Flow

```txt
Quick Add / Import
→ Preview
→ Safe Commit
→ shelf aggregate update
→ Feature Projection
→ unlock check
→ Feature Progress update
→ TownSceneSnapshot diff
→ visual feedback
```

## Rules

- Import成功をanimationへ依存させない
- 100件Importでもanimationは1回
- animation skip可能
- townを開いていなくてもstate更新
- record rollbackで建物を自動縮小しない
- current countは正確に更新

## Visual

- 対応建物が短く光る
- unlock stage change時のみ建物差し替え
- summary copy

---

# Phase T8: Season and Time

## Scope

- TownEnvironmentState
- four-season overlays
- day / evening / night palette
- manual override
- low power / reduced motion

## Acceptance

- Feature Projectionへ混ぜない
- season changeでfootprint / hit area不変
- no-record期間でも荒れない
- precise location不要

---

# Phase T9: Ambient Life

## First

- water loop
- one boat
- tree movement
- building light
- smoke

## Later

- generic citizens 3〜5人
- fixed short routes
- time-mode schedule

## Acceptance

- user identityを割り当てない
- citizen chatなし
- low powerで停止
- route navigationへ干渉しない
- long idle leak test

---

# Phase T10: Decoration Slots

自由配置より先にslot式で価値検証する。

## Scope

- building-owned slots
- central square slots
- flower / flag / bench / sign
- month capsule decoration

## Acceptance

- growth envelope外
- stage changeで削除なし
- slot selectionはDOM UI
- layout revision対応
- reset / export対応

---

# Phase T11: Semantic Connections

## Scope

confirmed relationのみ。

- soft glow
- footprints
- signs
- route light
- relation reason panel
- accessibility list

## Rules

- physical roadを変更しない
- weak candidateを確定表示しない
- personality inference禁止
- color-only encoding禁止

---

# Phase T12: Editor Transaction Foundation

Free editor公開前に実装する。

## Scope

- local draft
- command batch
- undo / redo
- server revalidation
- compare-and-swap
- conflict response
- revision snapshot

## Acceptance

- all-or-nothing
- idempotency
- stale revision拒否
- last-write-wins禁止
- multi-device fixture

---

# Phase T13: Editable Decoration Zone

## Scope

- designated zones
- tree / flower / furniture
- placement preview
- valid / invalid visualization
- list-based accessibility editor

## Acceptance

- Memory data不変
- RLS
- undo / redo
- export
- migration preservation
- low-end device操作可能

---

# Phase T14: Physical Path Editor

## Scope

- road / footpath painting
- derived autotile
- batch command
- entrance connectivity warning

## Acceptance

- connection mask非永続
- multi-cell paint atomic
- semantic overlay不変
- path deletionでmemory relation不変

---

# Phase T15: Structure Relocation

## Scope

- allowed parcel間移動
- feature binding維持
- growth envelope validation
- route不変

## Acceptance

- current feature progress維持
- user decorationの影響Preview
- invalid move拒否
- migration / export対応

---

# Phase T16: Map / District Expansion

## Scope

- new chunk / district
- existing origin維持
- district camera preset
- lazy asset load
- template three-way merge

## Acceptance

- old coordinates不変
- user layout上書きなし
- new feature placement safe
- missing spaceはstored
- rollback snapshot

---

# Phase T17: Future Anticipation

Examples:

- story house新刊旗
- cinema配信poster
- port旅行予定船
- square未来の楽しみbox

Rules:

- user follow対象のみ
- general recommendationを混ぜない
- ad禁止
- notification default OFF

---

# Cross-cutting Gates

## Performance

Before T6 complete:

- route leave描画停止
- static fallback
- bundle分離
- asset failureでapp全体が落ちない

Before T9 complete:

- low-end device profile
- reduced motion
- long idle leak
- background / foreground復帰

Before T13 complete:

- object count budget
- hit test budget
- command batch size limit
- editor battery / heat test

## Security

Before persistence:

- user_id / RLS
- cross-user negative tests
- server validator
- audit content redaction

Before editor:

- lock policy
- rate limit
- batch limit
- stale revision handling

## Portability

Before customization:

- Town export schema
- Import Preview
- unsupported object stored
- reset scopes
- account deletion

---

# P1 Decisions Requiring Prototype

- tile metric
- map dimensions
- parcel dimensions
- growth envelope dimensions
- touch target
- camera fit
- art style
- atlas size
- performance budget
- non-shrinking copy
- decoration slot value

文書だけで数値を決めない。

---

# MVP Go / No-Go

## Go

- fixed-view map
- logical grid
- Feature IDs / bindings
- feature progress
- growth envelope
- WebGL / PixiJS
- 5 buildings
- 3 stages
- DOM summary sheet
- static fallback
- scene composition
- short growth feedback

## No-Go

- free placement UI
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

---

# Definition of Success

見る指標:

- town open率
- feature tap率
- townからshelfへの遷移率
- Import後にchange確認率
- normal navigation成功率
- fallback率
- performance complaint率
- feature / visual対応理解率
- 「もっと記録を入れたい」反応

Editor追加後も、編集時間だけを成功指標にしない。

Memory OS本体の検索・保存・振り返り価値を弱めないことを優先する。

---

# Final Rule

```txt
町の完成度より先に、棚とImportの価値を証明する。

ただし町を作り始める時は、
MVP専用のpixel配置を作らず、
長期契約を満たした空間基盤から始める。
```
