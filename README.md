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

町はゲーム本体ではなく、見て楽しく機能を覚えやすい「感情的なメニュー」。
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

P2も長期方針として落とさない。ただし安全・性能・privacy Gateを通過するまで実装しない。

### Current verdict

```txt
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

保存前にImport Previewを表示し、保存後は棚と町の変化を見せる。
API connectorや大規模Importは、安全なPreview・Policy Evaluation・token管理・Export設計が成立した後に追加する。

---

## Current Authoritative Docs

### Memory Town Round 4 — 最初に読む

1. [Full Pattern Adoption and Permanent Non-goals](docs/memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md)
2. [Current Authority Order — Round 3 / 4](docs/memory-town-current-authority-order-round-3-box-garden-patterns.md)
3. [Adopted Box-Garden Patterns](docs/memory-town-adopted-box-garden-patterns-round-3.md)
4. [Design Readiness Gate — Box-Garden Patterns](docs/memory-town-design-readiness-gate-round-3-box-garden-patterns.md)
5. [Round 4 Handoff](docs/next-chat-memory-town-round-4-full-adoption-addendum.md)

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
1. Round 1 / 2 schema and fixture machine validation
2. Derived-detail rule catalog
3. Draft Town revision / expiry / atomic apply contract
4. Negative-space metric candidates
5. Postcard privacy projection
6. Ambient-nature shortlist and emotional-safety contract
7. District visual token brief
8. Personal-display catalog
9. Quiet Surprise deterministic fixture
10. One-tap Beautify safe-slot / undo fixture
11. Memory Window privacy / consent / disclosure contract
12. Environment-inclusive P0〜P21 static visual prototype
13. Four time-mode palette roughs
14. Memory Tree Stage 0〜2 × four-season roughs
15. Beach / port / Tree placement comparison
16. Six viewport / fallback / accessibility evidence
17. Permanent non-goal documentation scan
18. External multidisciplinary review
19. Critical finding correction
20. Memory Town implementation authorization judgment
21. Spatial domain foundation
22. Feature Progress / Layout / Environment composition
23. Town persistence / RLS / recovery skeleton
24. PixiJS / WebGL renderer adapter
25. Import → Feature unlock → Town feedback
26. User editor only after transaction / concurrency / demand gates
```

---

## Product Statement

```txt
保存したものが棚になる。
棚の機能が建物へ結びつく。
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
