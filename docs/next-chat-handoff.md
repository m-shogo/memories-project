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

## Latest Additions

### RFC-0006 Security Architecture

- Security is not only encryption.
- Do not store/search/export/send dangerous raw.
- Admin metadata-only default.
- LLM boundary requires security + policy + cost preflight.
- Prompt injection from imported text must not override policy.
- Embedding lifecycle must respect hidden/sealed/deleted.

### RFC-0007 Privacy Architecture

- User context is allowed; other people's secrets are not value.
- third-party raw no/default.
- minor data stricter than family data.
- deceased/legacy memory allowed, simulation denied.
- corporate data excluded by default.

### RFC-0008 UX Guidelines

- UX must not make Memory OS look like diagnosis, ranking, AI companion, or deceased simulation.
- Capture must not require importance score.
- Search explanations cannot say AI judged importance.
- Deletion copy must be guilt-free.
- Export must show exclusions and raw status.

### Storage Architecture

`docs/storage-architecture.md`

- relational core vs raw object storage vs search index vs vector index vs audit/export/backup separated.
- raw is dangerous.
- metadata is durable.
- vector is derived.
- lifecycle is source of truth.
- delete propagates across DB/search/vector/object/export/backup.

### Local-first Backup Strategy

`docs/local-first-backup-strategy.md`

- User keeps context.
- Export is not enough; backup strategy needed.
- open formats: JSONL / Markdown / SQLite later.
- emergency exit package defined.
- raw optional/default off.
- no vendor/LLM dependency required to read backup.

### Incident Response Playbook

`docs/incident-response-playbook.md`

- Playbooks for secrets, third-party leak, corporate leak, deleted resurrection, hidden/sealed exposure, wrong export, LLM policy bypass, admin access violation, cost attack.
- Stop exposure first.
- Preserve evidence without raw spreading.
- Add regression tests after incident.

### Adapter Implementation Plan

`docs/adapter-implementation-plan.md`

- Adapter core implementation order.
- MVP adapters: manual.paste, manual.share_text, generic.conversation_text, ChatGPT subset later/flagged.
- Post-MVP: LINE summary-only, Calendar, Photos metadata, GitHub metadata.
- Deferred: Gmail/Slack/Discord full import, image analysis, face recognition.

## Current State

The design is now close to implementation-ready.

Architecture chain:

```txt
Constitution
-> RFC Process
-> RFC-0001〜0008
-> Schema v1.1 Proposal
-> Policy P0 Test Cases
-> Storage Architecture
-> Adapter Implementation Plan
-> MVP Engineering Tasks
-> Test Strategy
-> Incident Response
-> Local-first Backup
```

## Completion Assessment

Design readiness: 97〜98%。

まだ100%と言い切らない理由:

- 実装コードがまだない。
- actual repository structure / package manager / runtime が未確認。
- DB migration files が未作成。
- CI scripts が未実装。
- fixture files が未作成。

ただし、思想・安全・削除・Export・Privacy・Cost・Search・Storage・Incident の設計穴はかなり潰れている。

## Next Work: Start Implementation Safely

次は設計追加より、実装準備に入ってよい。

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

- `a3b490e21f7cff7906847f92f7ceddf08d703ffb` docs: add rfc for security architecture
- `e55894889ee40c0681149067578270e177ac1893` docs: add rfc for privacy architecture
- `cceb68a7f0ca6bd1296fa0101ec64b6fab91c1c7` docs: add rfc for ux guidelines
- `24f803ecf825bfab92c3ae6a8d0ad3105b918ec1` docs: add storage architecture
- `8341801a9d4c76e42b832db0ac48c00707b1862f` docs: add local first backup strategy
- `021d8b886150406df8b7b1743218dd089dd90d2d` docs: add incident response playbook
- `4531a55d1246326f849854f1101d11fd32a2793c` docs: add adapter implementation plan

## Final Note

ここから先は、設計を増やし続けるより、P0 guardrails と Policy tests から実装に入るのが良い。

100点に近い設計とは、完璧な文章ではなく、危険な実装をテストで止められる状態である。
