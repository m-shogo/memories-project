# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計を続けるための実務用引き継ぎである。

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

## Core Docs To Read

- `docs/memory-constitution-v1.md`
- `docs/memory-schema-v1.md`
- `docs/policy-engine.md`
- `docs/third-party-data-policy.md`
- `docs/source-adapter-sdk.md`
- `docs/export-specification.md`
- `docs/memory-rfc-series.md`
- `docs/cost-engine.md`
- `docs/search-ranking-engine.md`
- `docs/deletion-backup-semantics.md`
- `docs/security-architecture.md`
- `docs/privacy-architecture.md`
- `docs/ux-guidelines.md`
- `docs/implementation-roadmap.md`
- `docs/test-strategy.md`
- `docs/data-model-delta.md`
- `docs/mvp-scope.md`
- `docs/schema-v1-1-proposal.md`
- `docs/policy-test-cases.md`
- `docs/engineering-tasks-mvp.md`

## RFC Docs

- `docs/rfcs/0000-template.md`
- `docs/rfcs/0001-source-adapter-sdk.md`
- `docs/rfcs/0002-export-specification.md`
- `docs/rfcs/0003-cost-engine.md`
- `docs/rfcs/0004-search-ranking-engine.md`
- `docs/rfcs/0005-deletion-backup-semantics.md`

## Latest Additions

### RFC-0004 Search & Ranking Engine

- Search ranking is relevance, not worth.
- importanceScore/lifeScore/personImportance forbidden.
- Policy filter before scoring.
- hidden/sealed/deleted excluded by default.
- surveillance/blame search denied or redirected.
- Tip policy stricter than search.

### RFC-0005 Deletion / Backup Semantics

- Delete means do not resurrect.
- pending_deletion blocks search/tip/LLM/export immediately.
- tombstone prevents re-import resurrection.
- raw-only delete supported.
- backup restore must replay tombstones.
- deletion UI must not guilt-frame.

### Schema v1.1 Proposal

`docs/schema-v1-1-proposal.md`

Additive MVP schema proposal:

- AdapterMetadata
- ImportScope
- SurfaceVisibility
- PrivacyContext
- PolicyDecisionRecord
- DeletionTombstone
- CostEstimateRecord
- CostLedgerEntry
- ExportJob
- EmbeddingRecord

Forbidden fields:

- importanceScore
- lifeScore
- personalityScore
- personRank
- topMemory
- bestMemory
- deceasedPersona

### Policy Test Cases

`docs/policy-test-cases.md`

P0-001〜P0-020 concrete cases added:

- secret storage/embedding/export deny
- corporate raw LLM deny
- third-party raw quote deny
- surveillance/blame deny
- deceased impersonation deny
- minor tip/export deny
- self-harm tip deny
- AI roleplay persona creation deny
- hidden/sealed/deleted restrictions
- low-risk manual memory allow

### Engineering Tasks MVP

`docs/engineering-tasks-mvp.md`

Implementation tasks broken into phases:

0. repo guardrails / forbidden phrase scanner / fixtures
1. schema v1.1 additive types
2. Policy Engine P0
3. manual/share adapters
4. memory creation MVP
5. visibility/deletion/tombstone
6. search MVP
7. export MVP
8. cost MVP
9. UX copy
10. MVP CI gate

## Current State

Design is now connected from philosophy to implementation:

```txt
Constitution
-> RFC process
-> Source/Export/Cost/Search/Delete RFCs
-> Roadmap
-> Test strategy
-> Schema v1.1 proposal
-> Policy concrete test cases
-> MVP engineering tasks
```

This is no longer only concept docs. It is close to implementation-ready.

## Next Recommended Work

Continue with remaining RFCs and implementation prep:

1. `docs/rfcs/0006-security-architecture.md`
2. `docs/rfcs/0007-privacy-architecture.md`
3. `docs/rfcs/0008-ux-guidelines.md`
4. `docs/adapter-implementation-plan.md`
5. `docs/storage-architecture.md`
6. `docs/local-first-backup-strategy.md`
7. `docs/incident-response-playbook.md`
8. then start actual implementation from `docs/engineering-tasks-mvp.md` T0-001.

## First Implementation Order

When implementation starts, do this order:

1. T0-002 forbidden phrase scanner
2. T0-003 fixture directory structure
3. T1-001 schema v1.1 additive types
4. T1-002 lifecycle helpers
5. T2-001 PolicyContext and PolicyDecision
6. T2-002 hard deny rules
7. T2-004 P0 policy tests
8. T3-001 adapter interface
9. T3-002 manual paste adapter
10. T5-003 delete memory + tombstone

Do not begin with LLM summaries, semantic search, Gmail/Slack, or proactive tips.

## Copy-paste Prompt For Next Chat

```txt
https://github.com/m-shogo/memories-project.git

このrepoの `so` ブランチで、AI記憶体サービス Memory OS の設計/実装準備を続けてください。
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

既存docsを必ず読んで整合してください。
特に以下を重視:
- docs/memory-constitution-v1.md
- docs/schema-v1-1-proposal.md
- docs/policy-test-cases.md
- docs/engineering-tasks-mvp.md
- docs/mvp-scope.md
- docs/test-strategy.md
- docs/rfcs/0004-search-ranking-engine.md
- docs/rfcs/0005-deletion-backup-semantics.md

次にやる優先順位:
1. docs/rfcs/0006-security-architecture.md
2. docs/rfcs/0007-privacy-architecture.md
3. docs/rfcs/0008-ux-guidelines.md
4. docs/adapter-implementation-plan.md
5. docs/storage-architecture.md
6. docs/local-first-backup-strategy.md
7. docs/incident-response-playbook.md

進め方:
- 1ファイルずつ設計書を追加
- 毎回 commit / push
- 思いつきではなく実装で使える設計にする
- 安全・削除・第三者・未成年・故人・会社情報・コスト攻撃を常に見る
- 便利でも思想を壊す機能は入れない
- 既存docsと矛盾しないようにする
- 最後に、次チャットへそのまま貼れる実務レベルの引き継ぎを更新する
```

## Last Known Commits From This Session

- `c206b98cfec93b87c2304439d63af59a24a3c497` docs: add rfc for search ranking engine
- `a1d235b4991ebe31a51ce1662b1063875f759fe4` docs: add rfc for deletion backup semantics
- `f665c02a823aae41b54d3f81e6c0744203d20170` docs: add schema v1.1 proposal
- `4257d5e6c95b71d6cba0ffb10c859ec6759c4fbf` docs: add policy test cases
- `3d98a0307068509ecabdf668c5f8ac0174dcb55a` docs: add mvp engineering tasks

## Current Assessment

Completion is roughly 92-94% for design readiness.

Remaining before implementation should be:

- security/privacy/UX RFCs
- storage architecture
- local-first backup/export strategy
- incident response playbook
- adapter implementation plan

Then implementation can safely start with guardrails and Policy P0 tests.
