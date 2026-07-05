# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計を続けるための実務用引き継ぎである。

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業したら毎回 GitHub に commit / push する

## Important Current Instruction

実装はまだ始めない。

現在のフェーズは、Memory OS の設計を100点に近づけるための最終設計・学習・仕様固定フェーズである。

## Product Goal

ChatGPT / Claude / Gemini の代替ではなく、AI時代に「自分の人生の文脈」を持ち続ける Memory OS を作る。

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

## Latest Final Design Layers Added

今回追加した、実装前に入れた上位設計レイヤー:

- `docs/formal-invariants.md`
- `docs/state-machine.md`
- `docs/threat-model.md`
- `docs/data-governance.md`
- `docs/compatibility-policy.md`
- `docs/api-design-guide.md`
- `docs/performance-budget.md`
- `docs/reliability-sre.md`
- `docs/failure-injection.md`
- `docs/adr.md`

## What They Add

### Formal Invariants

Memory OSで絶対に破ってはいけない法則。

Examples:

- Memory must have SourceRef.
- Interpretation is not fact.
- Policy before LLM.
- Deleted never appears.
- Raw must not be logged.
- No life ranking fields.
- Admin is not owner.
- AuthZ allow cannot override Policy deny.

### State Machine

active / hidden / sealed / pending_deletion / deleted / tombstoned の遷移を固定。

ImportJob / ExportJob / RawRecord / Embedding の状態遷移も定義。

### Threat Model

STRIDE風に、攻撃者・資産・境界・脅威・対策を整理。

Import / LLM / Export / Search / Deletion / Admin / Cost の境界を見る。

### Data Governance

データ定義・変更・保持・削除・移行の運営ルール。

Schema change review, retention, lineage, migration governance を定義。

### Compatibility Policy

schema / export / adapter / policy / API / event / backup の互換性ルール。

5年後・10年後も読めるMemory OSにするための時間軸設計。

### API Design Guide

REST/GraphQL以前のAPI境界設計。

Idempotency、stable error codes、safe errors、job-based import/export、paginationを定義。

### Performance Budget

manual capture, search, delete, import, export の性能・容量・コスト目標。

Delete access block immediate、LLM not on hot path を固定。

### Reliability / SRE

Safety over availability。

LLMやVectorが落ちてもcore capture/search/deleteを守る。

Policy/Export/Search lifecycleなど安全系はerror budget zero。

### Failure Injection

LLM down, vector down, object storage down, policy error, stale search, backup restore issueなどを意図的に壊すテスト計画。

### ADR

小さな設計判断を残す仕組み。

RFCより小さく、SQLite/JSONL/raw default off/keyword before vectorなどの判断を記録する。

## Architecture Learning Docs Already Added

- `docs/domain-driven-design.md`
- `docs/clean-hexagonal-architecture.md`
- `docs/event-driven-design.md`
- `docs/authn-authz-model.md`
- `docs/observability-model.md`
- `docs/architecture-learning-map.md`

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

## Core Docs To Read First

- `docs/memory-constitution-v1.md`
- `docs/memory-schema-v1.md`
- `docs/schema-v1-1-proposal.md`
- `docs/formal-invariants.md`
- `docs/state-machine.md`
- `docs/threat-model.md`
- `docs/policy-test-cases.md`
- `docs/engineering-tasks-mvp.md`
- `docs/storage-architecture.md`
- `docs/data-governance.md`
- `docs/compatibility-policy.md`
- `docs/incident-response-playbook.md`

## Current State

Design readiness is extremely high.

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
Formal Invariants
State Machines
Threat Model
Data Governance
Compatibility Policy
API Design
Performance Budget
Reliability/SRE
Failure Injection
ADR Process
MVP Engineering Tasks
Policy P0 Tests
Schema v1.1 Proposal
```

## Next Recommended Non-Implementation Work

If still not implementing, useful remaining docs:

1. `docs/adrs/0000-template.md`
2. initial ADRs:
   - JSONL + Markdown export
   - raw default off
   - keyword search before vector
   - PolicyEvaluator as pure domain service
   - no LLM in capture path
3. `docs/design-review-checklist.md`
4. `docs/pre-implementation-readiness-review.md`

## If Implementation Starts Later

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

## Last Known Commits From This Session

- `27bdd7af0a57d20c5b64c6a3a06a98cb96696459` docs: add formal invariants
- `b271a54d2c31791da474170b53300be53d56ec65` docs: add state machine specification
- `d1923c9309db0d4ee90bdefe4a1841419d26fac0` docs: add threat model
- `5238e304308517a2f396b25f6a0c3f70fb2757ab` docs: add data governance policy
- `502e7c531cfd926de7c5ba4425be8bc1f80f8b4f` docs: add compatibility policy
- `ac01a1bfa3aa4621522b9f12bc7c4fb46b5ee094` docs: add api design guide
- `18a143b54f6650c14d68bbb6846ef453d835f7cd` docs: add performance budget
- `a4f770a843b730a77e3fa017013b3c11b9d56161` docs: add reliability sre guide
- `ff7546ee41627d92600ee2270c628bc25d49d4ee` docs: add failure injection plan
- `8dca138e714905fbd818e2bda2074751acd0939e` docs: add adr process

## Final Note

ここまでで、設計はほぼ実装前レビューに耐えるレベルまで来ている。

実装はまだ始めない場合でも、次はADR初期セットと設計レビューchecklistを作るのが良い。
