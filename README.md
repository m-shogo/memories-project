# memories-project

AI時代に「自分の人生の文脈」を持ち続けるための **Memory OS** の構想・仕様・実装方針をまとめるリポジトリ。

このサービスは ChatGPT / Claude / Gemini / Character.AI の代替ではない。

## 一言で言うと

**保存した人生の断片を、自分の棚・地図・箱・町として持ち続け、必要な時に探し、振り返り、外へ持ち出せるMemory OS。**

AIは変わる。モデルもサービスも変わる。

ユーザー自身の人生の文脈だけは、特定のAIサービスへ閉じ込めない。

## Current Product Direction

```txt
軽く取り込む
→ 保存前にPreviewする
→ 媒体に合う棚として見える
→ 検索・更新・振り返りができる
→ 記録の積み重ねが固定2.5Dの「記憶の町」として育つ
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
- 続刊・配信など、ユーザーが明示的に追う対象の「続き」

### ワクワクの副次成果物

固定2.5Dの **記憶の町** を採用する。

```txt
棚 → 建物
箱 → 町の風景
確定したつながり → 道・橋・航路
Importの積み重ね → 建物の成長
月・季節 → 装飾と空気の変化
```

町はゲーム本体ではなく、見て楽しく機能を覚えやすい「感情的なメニュー」。
編集・検索・入力は通常のDOM UIで行う。

技術方針:

```txt
React / DOM UI
+ PixiJS / WebGL
+ fixed 2.5D sprites
+ dot-style visual
+ modular asset structure
```

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
- social feed中心のサービス
- 一般ニュース・無関係な商品推薦
- 町の自由配置ゲーム
- 仮想通貨・建築待ち時間・成長課金

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

## Current Authoritative Docs

最初に読むこと。

- [Current Product Direction](docs/current-product-direction.md)
- [Concrete MVP Product Scope](docs/concrete-mvp-product-scope.md)
- [Concrete MVP Ticket Backlog](docs/concrete-mvp-ticket-backlog.md)
- [Adopted Product Patterns Registry](docs/adopted-product-patterns-registry.md)
- [Adopted Patterns Implementation Plan](docs/adopted-patterns-implementation-plan.md)
- [Future Anticipation and Following](docs/future-anticipation-and-following-spec.md)

### Memory Town / WebGL

- [Memory Town Visual Design Direction](docs/memory-town-visual-design-direction.md)
- [Memory Town WebGL Architecture](docs/memory-town-webgl-architecture.md)
- [Memory Town Implementation Roadmap](docs/memory-town-implementation-roadmap.md)

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
9. Static Memory Town prototype
10. PixiJS / WebGL interactive town
11. Import → TownProjection → growth feedback
12. Weekly / Month Capsule
13. Future anticipation
14. Confirmed connections as roads
15. API connectors after provider/security gates
```

## Product Statement

```txt
保存したものが棚になる。
棚が建物になる。
箱が町の風景になる。
つながった記憶が道になる。
必要な時は、すべて持ち出せる。
```
