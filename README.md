# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・仕様・実装方針をまとめるリポジトリ。

このサービスは ChatGPT / Claude / Gemini / Character.AI の代替ではない。

## 一言で言うと

**保存した人生の断片を、自分の棚・地図・箱・町として持ち続け、必要な時に探し、振り返り、外へ持ち出せるMemory OS。**

AI・モデル・サービスが変わっても、ユーザー自身の人生の文脈を特定サービスへ閉じ込めない。

---

## Current Product Direction

```txt
軽く取り込む
→ 保存前にPreviewする
→ 媒体に合う棚として見える
→ 検索・更新・振り返りができる
→ 記録の積み重ねが固定視点2.5Dの「記憶の町」として育つ
→ 必要なら標準形式で持ち出せる
```

```txt
Memory is the product.
Town is the visible side effect.
```

ユーザーは町を育てるために人生を記録しない。忘れたくない作品、場所、日常、進行を残し、その積み重ねが後から町として見える。

### 実用の本体

- Universal Quick Add
- Import Preview
- 漫画・アニメ進行
- 映画・視聴棚
- 食の地図
- 未整理Inbox
- Search
- Export
- Weekly Box / Month Capsule
- ユーザーが明示的に追う「続き」

### 記憶の町

固定視点2.5Dの **Memory Town** を採用する。

```txt
棚の機能 → 建物へbinding
箱 → 町の風景
確定したつながり → semantic overlay
Reset後の新しい積み重ね → 建物の育ち直し
月・季節 → 装飾と空気の変化
```

町はゲーム本体ではなく、保存された記憶が後から見える感情的な可視化・入口。
編集・検索・入力・重要操作は通常のReact / DOM UIで行う。

参考イメージは、**どうぶつの森のように、自分の場所へ愛着を持てる箱庭**。ただし特定作品のUI・art・game economyは複製しない。

```txt
MVP: fixed layout / editorなし
内部: logical grid / parcel / footprint / growth envelope
将来: decoration → 道 → 植栽 → 建物移動 → district expansion
```

Minecraft型の1block建築ではない。

```txt
地形・道・花 = tile単位
木・家具 = object単位
建物 = multi-cell完成sprite
```

技術方針:

```txt
React / DOM UI
+ PixiJS / WebGL
+ fixed-view 2.5D sprites
+ logical isometric grid
+ data-driven object catalog
```

---

## Memory Town Current Status

### Round 5 — Memory-first hierarchy

Townの全採用案は、記憶保存の価値へ従属する。

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

保存体験の順番:

```txt
1. 保存した記憶の確認
2. 棚・進行への反映
3. optionalな小さなTown反応
4. 次の実用的な操作
```

禁止:

- あと何件で建物が育つかの表示
- 建物成長progress bar
- daily capture quest
- Townを育てるための保存文言
- duplicate / filler / AI生成fake recordによる成長
- Town専用mandatory tag / category
- bulk Importの報酬爆発

### Round 1 — Architecture hardening

- current countとReset後のgrowth contributionを分離
- `growthOriginCursor`と`resetEpoch`でunlock raceを防止
- React / DOMを唯一のaccessibility interaction treeに固定
- Pixi Canvasは視覚rendererとして`aria-hidden`
- Functional / Layered Visual / Cached Snapshot fallbackを分離
- renderer session generationとAbortController
- account deletion epochによるworker resurrection防止
- physical path graphからaccess rootまで検証

### Round 2 — Environment

```txt
朝 / 昼 / 夜 / 夜中
+ device local time連動
+ manual time / season preview
+ 雲・太陽・月
+ ビーチ・海岸・波
+ 情報量で育つ四季樹
+ 春の桜 / 秋のモミジ調紅葉
+ 夜・夜中の建物灯り
+ 季節の地面cue
+ unified wind field
```

正式な4時間帯:

```txt
morning   05:00–10:59 candidate
day       11:00–16:59 candidate
night     17:00–22:59 candidate
midnight  23:00–04:59 candidate
```

`evening`は独立した第5状態ではなく、nightへのvisual transitionとして扱う。

Memory Tree:

```txt
Stage 0: sapling
Stage 1: rooted tree
Stage 2: landmark tree

spring: sakura motif
summer: deep green
autumn: momiji motif
winter: dormant but warm, never punitive
```

### Round 3 / 4 — Box-garden patterns fully adopted

以下13パターンをすべて正式採用する。P0 / P1 / P2は採否ではなく導入順を表す。

```txt
MT-ADOPT-001 Derived Micro-details
MT-ADOPT-002 Draft Town
MT-ADOPT-003 Negative Space and Sightline
MT-ADOPT-004 Empty Town Baseline Life
MT-ADOPT-005 Curated Style Packs
MT-ADOPT-006 Private Postcard / Town History
MT-ADOPT-007 District Identity
MT-ADOPT-008 Ambient Nature
MT-ADOPT-009 Personal Display Slot
MT-ADOPT-010 Gentle Change Summary
MT-ADOPT-011 Quiet Surprise
MT-ADOPT-012 One-tap Beautify
MT-ADOPT-013 On-demand Memory Window
```

重要:

```txt
正式採用
≠
今すぐ実装
```

全13案はMemory-first testへ合格した範囲で導入する。

### Current verdict

```txt
Memory-first authority: locked
contracts and adoption decisions: completed
machine validation: pending
visual assets and viewport evidence: pending
implementation: NO-GO
```

---

## Memory Town State Model

```txt
1. Memory Domain State
2. Town Feature Progress State
3. Town Layout State
4. Town Environment State
5. Town Render State
```

重要:

- 建物の意味と見た目を分離
- 通常削除で解除済みstageを罰のように縮ませない
- current countは正確に表示
- 明示Resetでは現在projection cursorを新しい成長原点にする
- season / time / cameraをMemory Projectionへ混ぜない
- environmentはMemoryの重要度・感情・streakを使わない
- physical pathとsemantic connectionを分離
- template更新でuser layoutを上書きしない
- account deletionでTown state・job・cacheを残さない
- derived detailsをuser layoutの正本にしない
- Draft Townはserver validationを迂回しない
- Town OFFでもCapture / Search / Export能力を変えない

---

## Core Philosophy

- AIは人生を評価しない
- AIは人生を忘れないための索引になる
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生
- 重要度をAIが決めない
- 保存時に分析しすぎない
- 保存時は安全チェック、source、日付、検索性を中心にする
- 分析はユーザーが求めた時だけ行う
- 小さな記録を捨てない
- 大きなイベントも押し付けない
- 本人の記憶を作るサービスであり、本人をシミュレーションしない

## Permanent Non-goals

箱庭ゲームの定番であっても、以下はMemory Townへ採用しない。

- 毎日の依頼 / daily quests
- ログイン報酬
- 通貨
- 素材集め / crafting
- 家具ガチャ
- 住人の好感度
- 空腹・病気・世話義務
- 町の荒廃 / decay
- 片付け義務 / forced cleaning
- 隣接点数 / placement score
- 町ランキング / 人生ランキング
- 期間限定イベント報酬・装飾FOMO
- 公開Town feed・follower競争
- streak・未利用ペナルティ
- inactivityで住人が去る演出
- 建築待ち時間
- 成長加速課金
- next stageまでの件数表示
- 建物成長progress bar
- Town成長目的のcapture prompt
- Town専用mandatory record field
- AI恋人・AI家族・故人再現
- 人格診断・幸福度評価
- multiplayer town
- 実天気・実潮汐・天文位置の厳密再現

変更には明示ADR、Memory Constitution整合、wellbeing / privacy / adversarial review、owner承認が必要。

---

## First Experience

初回にZIPや複雑なAPI連携を要求しない。

```txt
SPY×FAMILY 12巻まで
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

保存前にImport Previewを表示する。

保存後は次の順で見せる。

```txt
保存した内容
→ 入った棚・進行
→ optionalな小さな町の反応
→ 棚を見る / 続きを更新 / 閉じる
```

API connectorや大規模Importは、安全なPreview・Policy Evaluation・token管理・Export設計が成立した後に追加する。

---

## Current Authoritative Docs

### Memory Town Round 5 — 最初に読む

1. [Current Authority Order — Round 5 Memory-first](docs/memory-town-current-authority-order-round-5-memory-first.md)
2. [Memory-first Capture Motivation Contract](docs/memory-first-capture-motivation-contract-round-5.md)
3. [Full Pattern Adoption and Permanent Non-goals](docs/memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md)
4. [Round 5 Handoff](docs/next-chat-memory-town-round-5-memory-first-addendum.md)

### Memory Town Round 3 / 4

- [Current Authority Order — Round 3 / 4](docs/memory-town-current-authority-order-round-3-box-garden-patterns.md)
- [Adopted Box-Garden Patterns](docs/memory-town-adopted-box-garden-patterns-round-3.md)
- [Design Readiness Gate — Box-Garden Patterns](docs/memory-town-design-readiness-gate-round-3-box-garden-patterns.md)

### Memory Town Round 2 Environment

- [Current Authority Order — Round 2 Environment](docs/memory-town-current-authority-order-round-2-environment.md)
- [Environment and Seasonal Life Contract](docs/memory-town-environment-and-seasonal-life-contract.md)
- [Environment Asset Brief](docs/memory-town-environment-asset-brief.md)
- [Static Visual Prototype — Environment Addendum](docs/memory-town-static-visual-prototype-environment-addendum.md)

### Memory Town Round 1

- [Current Authority Order — Round 1](docs/memory-town-current-authority-order-round-1.md)
- [Adversarial Review Round 1](docs/memory-town-adversarial-review-round-1.md)
- [Feature Reset and Unlock Race Contract](docs/memory-town-feature-reset-and-unlock-race-contract.md)
- [P0 Runtime, Accessibility and Fallback Contract](docs/memory-town-p0-runtime-accessibility-fallback-contract.md)
- [Worker Fencing and Account Deletion Contract](docs/memory-town-worker-fencing-and-account-deletion-contract.md)
- [Access Connectivity and Binding Recovery Contract](docs/memory-town-access-connectivity-and-binding-recovery-contract.md)
- [Static Visual Prototype Specification](docs/memory-town-static-visual-prototype-spec.md)

### Foundation

- [Architecture Hardening Contract](docs/memory-town-architecture-hardening-contract.md)
- [Long-term Spatial Model](docs/memory-town-long-term-spatial-model.md)
- [WebGL Architecture](docs/memory-town-webgl-architecture.md)
- [Visual Design Direction](docs/memory-town-visual-design-direction.md)
- [Concrete Data Contract](docs/memory-town-concrete-data-contract.md)
- [Growth Envelope and Access Contract](docs/memory-town-growth-envelope-and-access-contract.md)
- [Persistence, RLS and Recovery Contract](docs/memory-town-persistence-rls-and-recovery-contract.md)
- [Fixture Validation Harness Plan](docs/memory-town-fixture-validation-harness-plan.md)
- [Implementation Roadmap](docs/memory-town-implementation-roadmap.md)

Schema / fixture entrypoints:

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/fixtures/memory-town/fixture-index.v2.json
docs/fixtures/memory-town/fixture-index.round1-extension.v1.json
docs/fixtures/memory-town/fixture-index.round2-environment-extension.v1.json
```

### Product and Safety

- [Current Product Direction](docs/current-product-direction.md)
- [Concrete MVP Product Scope](docs/concrete-mvp-product-scope.md)
- [Adopted Product Patterns Registry](docs/adopted-product-patterns-registry.md)
- [Concept](docs/concept.md)
- [Product Principles](docs/product-principles.md)
- [Product Boundaries](docs/product-boundaries.md)
- [Memory Constitution v1](docs/memory-constitution-v1.md)
- [Privacy and Ethics](docs/privacy-and-ethics.md)
- [Healthy Attachment and Dependency Design](docs/healthy-attachment-and-dependency-design.md)

---

## Current Implementation Order

```txt
1. Memory-first save confirmation prototype
2. Quiet Town response ON / OFF comparison
3. Town OFF / static / list mode core-utility equivalence
4. Duplicate / filler growth exclusion contract
5. Bulk Import summary reaction contract
6. Home hierarchy comparison
7. Round 1 / 2 schema and fixture machine validation
8. Derived-detail rule catalog
9. Draft Town revision / expiry / atomic apply contract
10. Negative-space metric candidates
11. Postcard privacy projection
12. Ambient-nature shortlist and emotional-safety contract
13. District visual token brief
14. Personal-display catalog
15. Quiet Surprise deterministic fixture
16. One-tap Beautify safe-slot / undo fixture
17. Memory Window privacy / consent / disclosure contract
18. Environment-inclusive P0〜P21 static visual prototype
19. Four time-mode palette roughs
20. Memory Tree Stage 0〜2 × four-season roughs
21. Beach / port / Tree placement comparison
22. Six viewport / fallback / accessibility evidence
23. Permanent non-goal documentation scan
24. External multidisciplinary review
25. Critical finding correction
26. Memory Town implementation authorization judgment
27. Spatial domain foundation
28. Feature Progress / Layout / Environment composition
29. Town persistence / RLS / recovery skeleton
30. PixiJS / WebGL renderer adapter
31. Import → Feature unlock → Town feedback
32. User editor only after transaction / concurrency / demand gates
```

---

## Product Statement

```txt
記憶を入れたいと思えることが先。
保存したものが棚になる。
必要な時に探せて、続きを更新できる。
町は、その積み重ねが後から見える副次的な結果。

通常削除では、解除した成長を罰のように失わせない。
明示Resetでは、現在の記録を残したまま町を育て直せる。
配置と記憶は別々に守られる。
朝・昼・夜・夜中の光が現在時刻に寄り添う。
海と波と四季樹が、町へ静かな時間の流れを作る。
ユーザーは大きな意図を選び、町は小さな細部を整える。
本番を壊さず試せて、過去の町を私的に残せる。
戻らなくても、町は荒れず、責めず、損をさせない。
必要な時は、すべて持ち出せる。
```
