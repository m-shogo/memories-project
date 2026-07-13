# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・仕様・実装方針をまとめるリポジトリ。

このサービスは ChatGPT / Claude / Gemini / Character.AI の代替ではない。

## 一言で言うと

**保存した人生の断片を、自分の棚・地図・箱・町として持ち続け、必要な時に探し、振り返り、外へ持ち出せるMemory OS。**

AIは変わる。モデルもサービスも変わる。

ユーザー自身の人生の文脈だけは、特定のAIサービスへ閉じ込めない。

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

### ワクワクの副次成果物

固定視点2.5Dの **記憶の町** を採用する。

```txt
棚の機能 → 建物へbinding
箱 → 町の風景
確定したつながり → semantic overlay
Importの積み重ね → 解除済み建物stage
月・季節 → 装飾と空気の変化
```

町はゲーム本体ではなく、見て楽しく機能を覚えやすい「感情的なメニュー」。

編集・検索・入力は通常のDOM UIで行う。

### Long-term Town Direction

参考イメージは、**どうぶつの森のように、自分の場所へ愛着を持てる箱庭**。

ただし、特定作品のUIやアートを複製しない。

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
- 一度解除した建物stageは通常削除で罰のように縮ませない
- current countは正確に表示
- userはfeature growthを明示的にreset可能
- season / time / cameraをMemory Projectionへ混ぜない
- physical pathとsemantic connectionを分離
- path connection maskは導出値
- template更新でuser layoutを上書きしない
- account deletionでTown stateを全削除

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

---

## Non-goals

- ChatGPT代替
- AI恋人・AI家族・故人再現
- 人格診断・幸福度・人生ランキング
- streakや未利用ペナルティ
- social feed中心のサービス
- 一般ニュース・無関係な商品推薦
- MVPからの自由配置editor
- アバター操作中心
- 仮想通貨・素材集め・クラフト
- 建築待ち時間・成長課金
- multiplayer town

---

## First Experience

初回にZIPや複雑なAPI連携を要求しない。

最初は、タイトル・URL・進行・短いメモを貼る。

```txt
SPY×FAMILY 12巻まで
PERFECT DAYS 見た
鎌倉のカレー屋 行きたい
```

保存前にImport Previewを表示し、保存後は棚と町の変化を見せる。

API connectorや大規模Importは、安全なPreview・Policy Evaluation・token管理・Export設計が成立した後に追加する。

---

## Current Authoritative Docs

### Product

- [Current Product Direction](docs/current-product-direction.md)
- [Concrete MVP Product Scope](docs/concrete-mvp-product-scope.md)
- [Concrete MVP Ticket Backlog](docs/concrete-mvp-ticket-backlog.md)
- [Adopted Product Patterns Registry](docs/adopted-product-patterns-registry.md)
- [Future Anticipation and Following](docs/future-anticipation-and-following-spec.md)

### Memory Town / WebGL

読む順番:

1. [Memory Town Architecture Hardening Contract](docs/memory-town-architecture-hardening-contract.md)
2. [Memory Town Design Audit and Risk Register](docs/memory-town-design-audit-and-risk-register.md)
3. [Memory Town Long-term Spatial Model](docs/memory-town-long-term-spatial-model.md)
4. [Memory Town WebGL Architecture](docs/memory-town-webgl-architecture.md)
5. [Memory Town Visual Design Direction](docs/memory-town-visual-design-direction.md)
6. [Memory Town Hardening Tickets](docs/memory-town-hardening-tickets.md)
7. [Memory Town Spatial Foundation Tickets](docs/memory-town-spatial-foundation-tickets.md)
8. [Memory Town Implementation Roadmap](docs/memory-town-implementation-roadmap.md)

### Product Research and Retention

- [Long-term User Research Synthesis](docs/long-term-user-research-synthesis.md)
- [Persona Feature Fit Matrix](docs/persona-feature-fit-matrix.md)
- [Retention, Resurfacing and Notification Policy](docs/retention-resurfacing-and-notification-policy.md)
- [Similar App Evidence and Feature Map](docs/similar-app-evidence-and-feature-map.md)

### Core Product and Safety

- [Concept](docs/concept.md)
- [Product Principles](docs/product-principles.md)
- [Product Boundaries](docs/product-boundaries.md)
- [Memory Constitution v1](docs/memory-constitution-v1.md)
- [Personal Context Model](docs/personal-context-model.md)
- [Personal Memory Extraction Rules](docs/personal-memory-extraction-rules.md)
- [Sensitive Response Guardrails](docs/sensitive-response-guardrails.md)
- [Privacy and Ethics](docs/privacy-and-ethics.md)
- [Healthy Attachment and Dependency Design](docs/healthy-attachment-and-dependency-design.md)

### Import / Export

- [Import / Export Strategy](docs/import-export-strategy.md)
- [Import Security Checklist](docs/import-security-checklist.md)
- [Import Medium Roadmap](docs/import-medium-roadmap.md)
- [Import Service Adapter Registry](docs/import-service-adapter-registry.md)
- [Import Detector Confidence Ranking](docs/import-detector-confidence-ranking.md)
- [Import Preview Mobile Wireframes](docs/import-preview-mobile-wireframes.md)
- [Export Format Research](docs/export-format-research.md)

### DB Implementation Contracts

実装エージェントはコードを書く前にここから読むこと。

- [DB Table Design v1](docs/db-table-design-v1.md)
- [Migration 001 Foundation Contract](docs/migration-001-foundation-contract.md)
- [SafeMetadataGuard Spec](docs/safe-metadata-guard-spec.md)
- [Account Deletion and Tombstone Decision](docs/account-deletion-and-tombstone-decision.md)
- [First Migration Slice Plan](docs/first-migration-slice-plan.md)
- [RLS Policy and Negative Tests](docs/rls-policy-and-negative-tests.md)
- [Token Encryption and OAuth Security](docs/token-encryption-and-oauth-security.md)
- [DB Implementation Preflight Checklist](docs/db-implementation-preflight-checklist.md)

---

## Current Implementation Order

```txt
1. Synthetic fixtures
2. Import detection / preview / policy snapshots
3. First migration slice and RLS
4. Universal Paste + Import Preview
5. Safe Commit for low-risk manual/paste
6. Manga / Anime Vertical Slice
7. Food regional list
8. Home / Shelf navigation
9. Memory Town P0 hardening contracts / fixtures
10. Static Memory Town experience prototype
11. Spatial domain foundation
12. Feature Progress / Layout / Environment composition
13. Town persistence / RLS / recovery skeleton
14. PixiJS / WebGL renderer adapter
15. Import → Feature unlock → Town feedback
16. Weekly / Month Capsule
17. Environment / ambient life
18. Decoration slots
19. Semantic connection overlays
20. Future anticipation
21. User editor only after transaction / concurrency gates
22. API connectors after provider/security gates
```

---

## Current Memory Town Verdict

```txt
strong_design_not_complete
```

強い:

- product role
- spatial model
- state separation
- long-term migration principle
- privacy boundary

Prototype / 実機確認が必要:

- tile metric
- map dimensions
- growth envelope dimensions
- art direction
- touch comprehension
- mobile performance
- asset production cost
- non-shrinking visual copy
- editor product value

---

## Product Statement

```txt
保存したものが棚になる。
棚の機能が建物へ結びつく。
解除した町の成長は、罰のように失われない。
配置と記憶は別々に守られる。
箱が町の風景になる。
確定したつながりは、生活道路とは別の光として見える。
少しずつ、自分の町として手を入れられる。
必要な時は、すべて持ち出せる。
```
