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

## Product Boundaries

このサービスは以下ではない。

- 汎用AIチャット代替
- キャラクター会話アプリ
- 故人や家族の本人再現
- AI恋人サービス
- 人格診断
- 人生ランキング
- パスワード管理
- 会社情報検索
- 他人の秘密の記憶化
- 監視 / 証拠探し

## Core Docs

必ず読む:

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

## RFC Docs Added

- `docs/rfcs/0000-template.md`
- `docs/rfcs/0001-source-adapter-sdk.md`
- `docs/rfcs/0002-export-specification.md`
- `docs/rfcs/0003-cost-engine.md`

## Latest Work Summary

### RFC Template

`docs/rfcs/0000-template.md`

- RFC必須セクションを固定。
- Constitution Check を必須化。
- Policy / Privacy / Security / Third-party / Minor / Legacy / Corporate / Cost / UX / Deletion / Export を必ず見る。
- abuse cases 最低10件を必須化。
- accepted判断前にCost Impactを必須化。

### RFC-0001 Source Adapter SDK

`docs/rfcs/0001-source-adapter-sdk.md`

- `accepted_with_limits`。
- Adapterは分析器ではなく変換器。
- detect -> inspect -> estimateCost -> userScope -> extract -> normalize -> policy -> index。
- unknown source full analysis blocked。
- Gmail/Slack/Discord full import はMVP外。

### RFC-0002 Export Specification

`docs/rfcs/0002-export-specification.md`

- `accepted_with_limits`。
- Exportは権利だがraw leak toolではない。
- secrets / corporate / third-party raw / minor raw は除外またはsummary-only。
- Markdownは人生ランキング・人格診断見出し禁止。
- short-lived download + audit。

### RFC-0003 Cost Engine

`docs/rfcs/0003-cost-engine.md`

- `accepted_with_limits`。
- Cost is consent。
- Planや課金でPolicy denyは越えられない。
- CostLedgerはraw text禁止。
- full history processing default off。

### Implementation Roadmap

`docs/implementation-roadmap.md`

- Safe core before smart AI。
- Manual capture -> Policy -> Adapter -> Search -> Export -> Deletion -> Cost -> Safe integrations -> Reflection。
- AI分析より前に削除・出典・Export・Policyを作る。
- Never Buildリストを固定。

### Test Strategy

`docs/test-strategy.md`

- Policy / Adapter / Search / Export / Deletion / Security / Privacy / Cost / UX copy / Red Team をP0化。
- dangerous success is failure。
- forbidden phrase scan を定義。
- Red Team cases を回帰テストへ変換する方針。

### Data Model Delta

`docs/data-model-delta.md`

- schema v1 に対する追加差分。
- AdapterMetadata / ImportScope / DeletionTombstone / PolicyDecisionRecord / CostEstimateRecord / ExportJob / EmbeddingLifecycle / PrivacyContext。
- forbidden field names: importanceScore, lifeScore, personalityScore 等。

### MVP Scope

`docs/mvp-scope.md`

- MVP North Star: 小さな記録を、AIに評価されず、安全に残し、後から探せて、消せて、持ち出せる。
- P0: manual/share capture, SourceRef/Evidence, Policy P0, basic adapter, safe search, visibility/deletion, safe export, cost estimate, UX boundary。
- Out of MVP: Gmail, Slack, full imports, AI-heavy features, family share, risky search。
- Never Build: AI companion, deceased simulation, personality diagnosis, life score, surveillance, company search。

## Next Recommended Work

次にやるなら、設計から実装準備へさらに進める。

1. `docs/rfcs/0004-search-ranking-engine.md`
2. `docs/rfcs/0005-deletion-backup-semantics.md`
3. `docs/rfcs/0006-security-architecture.md`
4. `docs/rfcs/0007-privacy-architecture.md`
5. `docs/rfcs/0008-ux-guidelines.md`
6. `docs/adapter-implementation-plan.md`
7. `docs/policy-test-cases.md`
8. `docs/schema-v1-1-proposal.md`
9. `docs/engineering-tasks-mvp.md`

## Current Implementation Direction

最初に実装する順番:

1. schema additive types
2. Policy Engine P0
3. manual/share adapter
4. SourceRef + Memory create
5. hide/seal/delete/tombstone
6. basic search
7. safe export
8. cost estimate
9. fixture tests

## Copy-paste Prompt For Next Chat

```txt
https://github.com/m-shogo/memories-project.git

このrepoの `so` ブランチで、AI記憶体サービス Memory OS の設計を続けてください。
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
- docs/source-adapter-sdk.md
- docs/export-specification.md
- docs/memory-rfc-series.md
- docs/cost-engine.md
- docs/search-ranking-engine.md
- docs/deletion-backup-semantics.md
- docs/security-architecture.md
- docs/privacy-architecture.md
- docs/ux-guidelines.md
- docs/implementation-roadmap.md
- docs/test-strategy.md
- docs/data-model-delta.md
- docs/mvp-scope.md

次にやる優先順位:
1. docs/rfcs/0004-search-ranking-engine.md
2. docs/rfcs/0005-deletion-backup-semantics.md
3. docs/rfcs/0006-security-architecture.md
4. docs/rfcs/0007-privacy-architecture.md
5. docs/rfcs/0008-ux-guidelines.md
6. docs/adapter-implementation-plan.md
7. docs/policy-test-cases.md
8. docs/schema-v1-1-proposal.md
9. docs/engineering-tasks-mvp.md

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

- `a532794cfdc84b25692f0fa4312a2b79805e9374` docs: add memory rfc template
- `47f7f90cf1649f4ecf30bdbefb09eea008cb941e` docs: add rfc for source adapter sdk
- `2428670de45a3c0bde0452a133ecaab76278dd14` docs: add rfc for export specification
- `89cda9706d191474fa7d62fe9591b125dc60311f` docs: add rfc for cost engine
- `484b152891f27f05fb909f9b084c20f5e4c2e7a0` docs: add implementation roadmap
- `ed902c97bad0f78c3b45b3906785b80aa43f3585` docs: add test strategy
- `125fc306be64fbb8db784791e1c97c64341c5bba` docs: add data model delta
- `78ed1d4db7db76f6e7bd0b640d496a2e5dd68743` docs: add mvp scope

## Current State

設計の土台は、思想 → RFC → Roadmap → Test → Schema Delta → MVP Scope まで繋がった。

次は残りの主要設計をRFC化し、その後 `schema-v1-1-proposal` と `engineering-tasks-mvp` で実装着手できる粒度へ落とす。
