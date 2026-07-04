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

## Existing Core Docs

- `docs/memory-philosophy.md`
- `docs/memory-constitution-v1.md`
- `docs/memory-constitution-audit-v1.md`
- `docs/memory-risk-engine.md`
- `docs/memory-casebook-v1.md`
- `docs/red-team-worst-cases-100.md`
- `docs/third-party-data-policy.md`
- `docs/minor-and-family-policy.md`
- `docs/legacy-and-deceased-policy.md`
- `docs/anti-pattern-library.md`
- `docs/import-specification.md`
- `docs/memory-schema-v1.md`
- `docs/data-lifecycle.md`
- `docs/trust-and-provenance.md`
- `docs/ai-contract.md`
- `docs/memory-query-language.md`
- `docs/memory-graph.md`
- `docs/time-engine.md`
- `docs/policy-engine.md`
- `docs/explainability.md`

## Newly Added / Updated Docs

- `docs/source-adapter-sdk.md`
- `docs/export-specification.md`
- `docs/memory-rfc-series.md`
- `docs/cost-engine.md`
- `docs/search-ranking-engine.md`
- `docs/deletion-backup-semantics.md`
- `docs/security-architecture.md`
- `docs/privacy-architecture.md`
- `docs/ux-guidelines.md`
- `docs/next-chat-handoff.md`

## Design Summary

### Source Adapter SDK

`docs/source-adapter-sdk.md`

- Adapter は分析器ではなく変換器。
- Save First は人生価値判断ではない。
- Inspect Before Analyze を固定。
- unknown source は inspect only。
- SourceRef / RawRecord / NormalizedRecord / SafetyHint / CostEstimate を生成。
- LINE / Gmail / Slack / Photos / GitHub の危険境界を明記。
- 削除tombstoneと再インポート復活防止を含む。
- 15カテゴリの必須テストを定義。

### Export Specification

`docs/export-specification.md`

- Export はユーザーの権利だが raw leak tool ではない。
- personal_archive / migration_package / readable_markdown / source_index_only / safe_family_share などを定義。
- secrets / company / third-party raw / minor / crisis raw は除外またはsummary-only。
- manifest / JSONL envelope / redaction log / audit log / short-lived download を固定。
- 人生ランキング風Markdown見出しは禁止。

### Memory RFC Series

`docs/memory-rfc-series.md`

- Constitution first。
- Safety before convenience。
- Cost is product safety。
- Philosophy / Safety / Data / Cost / UX / Reversibility gates を定義。
- RFCの必須セクションと拒否例を定義。
- 人格チャット、家族診断、人生ランキングは reject 例。

### Cost Engine

`docs/cost-engine.md`

- Cost is consent。
- Inspect is cheap, analyze is expensive。
- Full history import は自動にしない。
- unknown source full analysis は blocked。
- paid plan でも safety policy は越えられない。
- CostLedger は raw text を含めない。
- コスト攻撃、再インポート攻撃、export raw dumpを防ぐ。

### Search & Ranking Engine

`docs/search-ranking-engine.md`

- Ranking is relevance, not worth。
- importanceScore 的な設計は禁止。
- Policy filters before scoring。
- Snippet は show_raw_quote policy を通す。
- surveillance/blame query は deny/redirect。
- Tip は検索より厳しい。
- 「AIが重要と判断」は禁止。

### Deletion / Backup Semantics

`docs/deletion-backup-semantics.md`

- Delete means do not resurrect。
- pending_deletion は即座に search/tip/LLM/export を止める。
- tombstone で再インポート復活を防ぐ。
- raw-only delete を明記。
- backup restore は deletion markers を replay する。
- 削除UIは罪悪感を煽らない。

### Security Architecture

`docs/security-architecture.md`

- Do not become a secret manager。
- raw exposure 最小化。
- admin cannot casually read memories。
- archive safe extraction / secret scan / encryption / key management / break-glass を定義。
- LLM boundary は imported content を untrusted content として扱う。
- embedding vector も漏洩面として扱う。

### Privacy Architecture

`docs/privacy-architecture.md`

- Purpose limitation。
- Data minimization。
- Contextual privacy。
- Third-party dignity。
- LINE/DM, Photos, Gmail, Slack, family, minor, deceased, corporate data の境界を定義。
- family/partner/personality profiling を禁止。

### UX Guidelines

`docs/ux-guidelines.md`

- Calm memory, not addictive chat。
- Index, not judge。
- captureで importance を必須にしない。
- import preview before analysis。
- search explanation は人生価値を言わない。
- Tip は敏感データを proactive に出さない。
- deletion UI は guilt-free。
- empty state は「重要な記憶がない」と言わない。

## Important Design Tensions

### 小さな記録 vs コスト

小さな記録を捨てない。ただし全部LLM解析しない。

解決:

- metadata / source / date / searchable text を先に保存。
- LLM/embedding はユーザー選択・低リスク・範囲限定。

### 持ち出す権利 vs 第三者保護

ユーザーの記憶はExportできるべき。ただし他人の秘密や会社情報は漏らさない。

解決:

- ExportEnvelope + Redaction + Policy gate。
- rawは既定OFF。

### 忘れないサービス vs 忘れる権利

Memory OS は文脈を守るが、削除権を弱めない。

解決:

- pending_deletion 即時遮断。
- tombstone。
- backup restore replay。

### 検索の便利さ vs 人生ランキング化

関連度検索は必要。ただしAIが人生価値を決めてはいけない。

解決:

- importanceScore禁止。
- Ranking explanation は query relevance / source / time / evidence に限定。

### 家族・故人の大切さ vs シミュレーション化

家族や故人の記憶は大切。ただし本人再現や手紙生成はしない。

解決:

- values reference / memory summary は許可。
- speak as / persona profile / simulation は deny。

## Next Recommended Work

次にやるなら、設計をさらに実装に近づけるため以下が良い。

1. `docs/rfcs/0000-template.md` を作る。
2. `docs/rfcs/0001-source-adapter-sdk.md` を Source Adapter SDK から起こす。
3. `docs/rfcs/0002-export-specification.md` を Export Specification から起こす。
4. `docs/implementation-roadmap.md` を作り、MVP順序を固定する。
5. `docs/test-strategy.md` を作り、Policy / Import / Export / Search / Deletion のP0自動テスト表を作る。
6. `docs/data-model-delta.md` を作り、既存 Memory Schema に足すべき型差分を整理する。
7. `docs/mvp-scope.md` を作り、最初にやる/やらないを固定する。

## Recommended MVP Scope

### P0

- manual paste
- share text
- small safe memory capture
- SourceRef
- date/source/search text
- safe summary only
- hide/seal/delete/raw-delete
- basic search
- markdown/json export without raw
- policy gate
- cost estimate

### P1

- ChatGPT selected export subset
- LINE text summary-only
- Google Calendar
- photos metadata only
- search explanation
- tombstone re-import guard

### Post-MVP

- Gmail
- Slack/Discord
- image content analysis
- large archive import
- family share
- legacy/deceased workflows

### Blocked / Never

- AI companion chat
- deceased simulation
- family/partner roleplay
- personality diagnosis
- life score/ranking
- password manager
- company search
- surveillance/evidence search

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
- docs/policy-engine.md
- docs/memory-schema-v1.md
- docs/third-party-data-policy.md

次にやる優先順位:
1. docs/rfcs/0000-template.md
2. docs/rfcs/0001-source-adapter-sdk.md
3. docs/rfcs/0002-export-specification.md
4. docs/implementation-roadmap.md
5. docs/test-strategy.md
6. docs/data-model-delta.md
7. docs/mvp-scope.md

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

- `4ab911dd8bc63772fc1ee642d116d5cdcef1a490` docs: harden source adapter sdk design
- `d8db162a052f1c9ce6dc704ecb980439580ab857` docs: add export specification
- `2c515bb055aa2e21548732e12cdd989ac30fa17e` docs: complete memory rfc series process
- `b172126a0d139f1c7b65257e279d4f65b305549b` docs: add cost engine design
- `19e956eba4ec1d56b204598c50d29b00f1d5afc9` docs: add search and ranking engine design
- `145a9c4661c075fdc7489d5034cce6b249208a2e` docs: add deletion and backup semantics
- `ba443e0d29011c45952311742332b39ccba9203e` docs: add security architecture
- `8db01cbe973e0148d7d7977c28ad6810baeba9e5` docs: add privacy architecture
- `86abe8e037c0ca6130b4990a85cf12543f15ee14` docs: add ux guidelines

## Current State

The project now has a strong design backbone for:

- import adapters
- export
- RFC governance
- cost control
- search/ranking safety
- deletion/backup
- security
- privacy
- UX

Next work should convert these into RFCs, roadmap, tests, and schema deltas so implementation can start without philosophical drift.
