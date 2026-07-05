# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計/実装を続けるための実務用引き継ぎである。

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業したら毎回 GitHub に commit / push する

## Product Goal

ChatGPT / Claude / Gemini の代替ではなく、AI時代に「自分の人生の文脈」を持ち続ける Memory OS を作る。

このサービスは、AIと会話するためではなく、ユーザー本人の人生の記録・文脈・関係・思い出を長く持ち運ぶためのものである。

本人の記憶を作るサービスであり、本人を分析するサービスではない。

## Core Philosophy

- AIは人生を評価しない
- AIは人生を忘れないための索引になる
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生
- 重要度をAIが決めない
- 保存時に分析しすぎない
- 保存時は安全チェック、ソース、日付、検索性が中心
- 分析はユーザーが求めた時だけ行う
- 小さな記録を捨てない
- 大きなイベントも押し付けない
- 本人の記憶を作るサービスであり、本人を分析するサービスではない

## Absolute Non-goals

- ChatGPT代替
- Character.AI化
- 故人再現
- 親/妻/恋人の本人シミュレーション
- AI恋人化
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視/証拠探し

## Core Docs To Read First

- `docs/memory-constitution-v1.md`
- `docs/memory-schema-v1.md`
- `docs/schema-v1-1-proposal.md`
- `docs/policy-engine.md`
- `docs/policy-test-cases.md`
- `docs/engineering-tasks-mvp.md`
- `docs/mvp-scope.md`
- `docs/test-strategy.md`
- `docs/storage-architecture.md`
- `docs/adapter-implementation-plan.md`
- `docs/local-first-backup-strategy.md`
- `docs/incident-response-playbook.md`

## Architecture Learning Docs

今回追加した、業界設計ルールをMemory OS向けに学べるdocs:

- `docs/domain-driven-design.md`
- `docs/clean-hexagonal-architecture.md`
- `docs/event-driven-design.md`
- `docs/authn-authz-model.md`
- `docs/observability-model.md`
- `docs/architecture-learning-map.md`

## What These Architecture Docs Add

### Domain-driven Design

- RawRecord / Memory / Interpretation / Evidence / SourceRef を混ぜない。
- Capture / Import / Memory / Policy / Search / Export / Deletion のBounded Contextを整理。
- AdapterをAnti-corruption Layerとして定義。

### Clean / Hexagonal Architecture

- PolicyEvaluator / Domain rules をDB・UI・LLMから独立させる。
- UseCase / Port / Infrastructure の責務を定義。
- OpenAIやPostgreSQLを変えても思想が変わらない構造。

### Event-driven Design

- MemoryDeleted / RawDeleted / PolicyDenied / ExportExpired などをraw-free Domain Eventとして扱う。
- 完全Event SourcingはMVPでは不要。
- DB Outbox Patternで削除・Export・Search/Vector更新の副作用を安全に処理。

### AuthN / AuthZ Model

- AuthN = 誰か。
- AuthZ = それをしてよいか。
- owner / system_worker / ai_worker / support_admin / security_admin を分離。
- AuthZ allow でも Policy deny ならdeny。
- Adminはownerではない。

### Observability Model

- raw contentをログ・メトリクス・トレースに入れない。
- Policy deny / Export redaction / Deletion lag / LLM block を観測。
- dangerous successをalertする。

### Architecture Learning Map

- RFC / DDD / Clean Architecture / Event-driven / AuthZ / Storage / Observability / Incident Response / Local-first / Guardrails の学習地図。
- Memory OSでなぜ必要かを一覧化。

## RFC Docs

- `docs/rfcs/0000-template.md`
- `docs/rfcs/0001-source-adapter-sdk.md`
- `docs/rfcs/0002-export-specification.md`
- `docs/rfcs/0003-cost-engine.md`
- `docs/rfcs/0004-search-ranking-engine.md`
- `docs/rfcs/0005-deletion-backup-semantics.md`
- `docs/rfcs/0006-security-architecture.md`
- `docs/rfcs/0007-privacy-architecture.md`
- `docs/rfcs/0008-ux-guidelines.md`

## Current State

The project now has:

```txt
Philosophy / Constitution
RFC Governance
Source Adapter SDK
Export Specification
Cost Engine
Search Ranking
Deletion Backup
Security
Privacy
UX
Storage
Local-first Backup
Incident Response
DDD
Clean Architecture
Event-driven Design
AuthZ
Observability
MVP Engineering Tasks
Policy P0 Tests
Schema v1.1 Proposal
```

Design readiness is extremely high. The remaining gap is no longer conceptual; it is implementation/CI/fixtures.

## Next Work: Start Implementation Safely

Start from `docs/engineering-tasks-mvp.md`.

Recommended exact order:

1. inspect repo structure and package manager
2. add forbidden phrase scanner
3. add fixture directory structure
4. add schema v1.1 TypeScript types
5. add lifecycle helper functions
6. add PolicyContext / PolicyDecision types
7. implement hard deny rules
8. convert `docs/policy-test-cases.md` P0-001〜P0-020 into tests
9. add adapter core interface
10. add manual.paste.v1 adapter

Do not start with:

- LLM summaries
- semantic search
- Gmail
- Slack
- image analysis
- proactive tips
- family share
- deceased/legacy workflows

## Copy-paste Prompt For Next Chat

```txt
https://github.com/m-shogo/memories-project.git

このrepoの `so` ブランチで、AI記憶体サービス Memory OS の実装準備/実装を始めてください。
作業したら毎回 GitHub に commit / push してください。

目的:
ChatGPT/Claudeの代替ではなく、AI時代に「自分の人生の文脈」を持ち続ける Memory OS を作る。
本人の記憶を作るサービスであり、本人を分析するサービスではない。

最重要思想:
- AIは人生を評価しない
- AIは人生を忘れないための索引
- ラーメン、焼肉、帰り道、卒業式後の写真も全部人生
- 重要度をAIが決めない
- 保存時に分析しすぎない
- 保存時は安全チェック、ソース、日付、検索性が中心
- 分析はユーザーが求めた時だけ
- 小さな記録を捨てない
- 大きなイベントも押し付けない

絶対やらない:
- ChatGPT代替
- Character.AI化
- 故人再現
- 親/妻/恋人の本人シミュレーション
- AI恋人化
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視/証拠探し

必ず読む:
- docs/engineering-tasks-mvp.md
- docs/schema-v1-1-proposal.md
- docs/policy-test-cases.md
- docs/adapter-implementation-plan.md
- docs/storage-architecture.md
- docs/domain-driven-design.md
- docs/clean-hexagonal-architecture.md
- docs/event-driven-design.md
- docs/authn-authz-model.md
- docs/observability-model.md
- docs/mvp-scope.md
- docs/test-strategy.md
- docs/memory-constitution-v1.md

最初にやる順番:
1. repo構造とpackage manager確認
2. forbidden phrase scanner追加
3. fixture directory structure追加
4. schema v1.1 additive types追加
5. lifecycle helper追加
6. PolicyContext / PolicyDecision types追加
7. hard deny rules追加
8. P0 policy tests追加

進め方:
- 小さく実装
- 1作業ごとに commit / push
- raw textをログに出さない
- importanceScore / lifeScore / personalityScore など禁止語をコードに入れない
- LLM/semantic search/Gmail/Slack/画像解析/proactive tips はまだ実装しない
- 最後に next-chat-handoff を更新する
```

## Last Known Commits From This Session

- `9f8f8c9dcdfc6077b8cd7062d5c771424c53dac2` docs: add domain driven design guide
- `69d36c826ded1aeeacf62210e71ab49931deaf33` docs: add clean hexagonal architecture guide
- `2a7300e1062bc7978c89aa9c1aef12744351fe67` docs: add event driven design guide
- `87e682bb4307825b040316a8f2eab2f31129a517` docs: add authn authz model
- `9605c1038f87fb66927ce1da302618cad118f3c3` docs: add observability model
- `2e9ef0ddccb0a8bffc7f2d73a1a623a8058554c1` docs: add architecture learning map

## Final Note

ここまでで「世界/業界の設計ルール」をMemory OS用にかなり綺麗に翻訳できた。

次は実装に入ってよいが、最初は必ず guardrails / tests から始める。
