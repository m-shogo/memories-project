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

## Memory Town Round 1 Status

Adversarial Review Round 1で、設計書が揃っていても破綻する重大点を発見し、v2契約へ修正した。

修正済み:

- current countとReset後のgrowth contributionを分離
- `growthOriginCursor`と`resetEpoch`でunlock raceを防止
- React / DOMを唯一のaccessibility interaction treeに固定
- Pixi Canvasは視覚rendererとして`aria-hidden`
- Functional / Layered Visual / Cached Snapshot fallbackを分離
- renderer session generationとAbortController
- account deletion epochによるworker resurrection防止
- entranceだけでなくphysical path graphからaccess rootまで検証
- primary visualが消えてもportal / DOM routeを維持

現在:

```txt
Round 1 P0 contract correction:
completed

schemas / fixtures:
created, machine validation pending

static visual prototype:
specification completed, evidence pending

implementation:
NO-GO
```

古いv1 growth / scene / reset fixtureを実装へ使用しない。

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
- Reset前の件数を表示しつつ、町はStage 0から育て直せる
- season / time / cameraをMemory Projectionへ混ぜない
- physical pathとsemantic connectionを分離
- path connection maskは導出値
- template更新でuser layoutを上書きしない
- account deletionでTown state・job・cacheを残さない

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

## Non-goals

- ChatGPT代替
- AI恋人・AI家族・故人再現
- 人格診断・幸福度・人生ランキング
- streakや未利用ペナルティ
- social feed中心
- 一般ニュース・無関係な商品推薦
- MVPからの自由配置editor
- アバター操作中心
- 仮想通貨・素材集め・クラフト
- 建築待ち時間・成長課金
- multiplayer town

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

### Memory Town Round 1 — 最初に読む

1. [Current Authority Order — Round 1](docs/memory-town-current-authority-order-round-1.md)
2. [Adversarial Review Round 1](docs/memory-town-adversarial-review-round-1.md)
3. [Feature Reset and Unlock Race Contract](docs/memory-town-feature-reset-and-unlock-race-contract.md)
4. [P0 Runtime, Accessibility and Fallback Contract](docs/memory-town-p0-runtime-accessibility-fallback-contract.md)
5. [Worker Fencing and Account Deletion Contract](docs/memory-town-worker-fencing-and-account-deletion-contract.md)
6. [Access Connectivity and Binding Recovery Contract](docs/memory-town-access-connectivity-and-binding-recovery-contract.md)
7. [Static Visual Prototype Specification](docs/memory-town-static-visual-prototype-spec.md)
8. [Design Readiness Gate — Round 1](docs/memory-town-design-readiness-gate-round-1.md)

### Memory Town foundation

- [Architecture Hardening Contract](docs/memory-town-architecture-hardening-contract.md)
- [Design Audit and Risk Register](docs/memory-town-design-audit-and-risk-register.md)
- [Long-term Spatial Model](docs/memory-town-long-term-spatial-model.md)
- [WebGL Architecture](docs/memory-town-webgl-architecture.md)
- [Visual Design Direction](docs/memory-town-visual-design-direction.md)
- [Concrete Data Contract](docs/memory-town-concrete-data-contract.md)
- [Growth Envelope and Access Contract](docs/memory-town-growth-envelope-and-access-contract.md)
- [Persistence, RLS and Recovery Contract](docs/memory-town-persistence-rls-and-recovery-contract.md)
- [Fixture Validation Harness Plan](docs/memory-town-fixture-validation-harness-plan.md)
- [Prototype Metric Matrix](docs/memory-town-prototype-metric-matrix.md)
- [Implementation Roadmap](docs/memory-town-implementation-roadmap.md)

Schema / fixture entrypoints:

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/fixtures/memory-town/fixture-index.v2.json
docs/fixtures/memory-town/fixture-index.round1-extension.v1.json
```

### Product

- [Current Product Direction](docs/current-product-direction.md)
- [Concrete MVP Product Scope](docs/concrete-mvp-product-scope.md)
- [Concrete MVP Ticket Backlog](docs/concrete-mvp-ticket-backlog.md)
- [Adopted Product Patterns Registry](docs/adopted-product-patterns-registry.md)
- [Future Anticipation and Following](docs/future-anticipation-and-following-spec.md)

### Core Product and Safety

- [Concept](docs/concept.md)
- [Product Principles](docs/product-principles.md)
- [Product Boundaries](docs/product-boundaries.md)
- [Memory Constitution v1](docs/memory-constitution-v1.md)
- [Personal Context Model](docs/personal-context-model.md)
- [Sensitive Response Guardrails](docs/sensitive-response-guardrails.md)
- [Privacy and Ethics](docs/privacy-and-ethics.md)
- [Healthy Attachment and Dependency Design](docs/healthy-attachment-and-dependency-design.md)

### Import / Export

- [Import / Export Strategy](docs/import-export-strategy.md)
- [Import Security Checklist](docs/import-security-checklist.md)
- [Import Medium Roadmap](docs/import-medium-roadmap.md)
- [Import Service Adapter Registry](docs/import-service-adapter-registry.md)
- [Import Preview Mobile Wireframes](docs/import-preview-mobile-wireframes.md)
- [Export Format Research](docs/export-format-research.md)

### DB Implementation Contracts

- [DB Table Design v1](docs/db-table-design-v1.md)
- [Migration 001 Foundation Contract](docs/migration-001-foundation-contract.md)
- [SafeMetadataGuard Spec](docs/safe-metadata-guard-spec.md)
- [Account Deletion and Tombstone Decision](docs/account-deletion-and-tombstone-decision.md)
- [RLS Policy and Negative Tests](docs/rls-policy-and-negative-tests.md)
- [Token Encryption and OAuth Security](docs/token-encryption-and-oauth-security.md)
- [DB Implementation Preflight Checklist](docs/db-implementation-preflight-checklist.md)

---

## Current Implementation Order

```txt
1. Synthetic fixtures
2. Import detection / Preview / policy snapshots
3. First migration slice and RLS
4. Universal Paste + Import Preview
5. Safe Commit
6. Manga / Anime Vertical Slice
7. Food regional list
8. Home / Shelf navigation
9. Memory Town Round 1 machine contract validation
10. Static Memory Town visual prototype
11. External multidisciplinary review
12. Critical finding correction
13. Memory Town implementation authorization judgment
14. Spatial domain foundation
15. Feature Progress / Layout / Environment composition
16. Town persistence / RLS / recovery skeleton
17. PixiJS / WebGL renderer adapter
18. Import → Feature unlock → Town feedback
19. Weekly / Month Capsule
20. Environment / ambient life
21. Decoration slots
22. Semantic connection overlays
23. User editor only after transaction / concurrency / demand gates
24. API connectors after provider/security gates
```

---

## Product Statement

```txt
保存したものが棚になる。
棚の機能が建物へ結びつく。
通常削除では、解除した成長を罰のように失わせない。
明示Resetでは、現在の記録を残したまま町を育て直せる。
配置と記憶は別々に守られる。
箱が町の風景になる。
確定したつながりは、生活道路とは別の光として見える。
少しずつ、自分の町として手を入れられる。
必要な時は、すべて持ち出せる。
```
