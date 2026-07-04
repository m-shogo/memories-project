# Next Chat Handoff

このファイルは、次のChatGPT/Codex/GitHub作業チャットで、同じ前提のまま設計を続けるための実務用引き継ぎである。

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業したら毎回 GitHub に commit / push する

## Product Goal

ChatGPT / Claude / Gemini の代替ではなく、AI時代に「自分の人生の文脈」を持ち続ける Memory OS を作る。

このサービスは、AIと会話するためではなく、ユーザー本人の人生の記録・文脈・関係・思い出を長く持ち運ぶためのものである。

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
- 他人の秘密を保存するサービス
- 監視や証拠探しの道具

## Existing Docs

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

## Next Priorities

1. Source Adapter SDK
2. Export Specification
3. Memory RFC series
4. Cost Engine
5. Search and Ranking Engine
6. Deletion and Backup details
7. Security Architecture
8. Privacy Architecture
9. UX Guidelines

## Working Rules

- 1ファイルずつ設計書を追加する
- 毎回 commit / push する
- 思いつきではなく、実装で使える設計にする
- 安全、削除、第三者、未成年、故人、会社情報、コスト攻撃を常に見る
- 便利でも思想を壊す機能は入れない
- 既存docsと矛盾しないようにする
- 最後に、次チャットへそのまま貼れる実務レベルの引き継ぎを1つにまとめる

## Conversation Style Requirement

ユーザーは短いスローガンではなく、中身のある実務引き継ぎを求めている。

毎回、以下を含める。

- repo
- branch
- 既存docs
- 次タスク
- 守る思想
- commit / push 方針

「言われないと分からない」状態を避ける。

## Maintenance

設計が進んだら、このファイルも更新する。

新しい重要docsを追加した場合は、Existing Docs に追記する。

次タスクの優先順位が変わった場合は、Next Priorities を更新する。

会話またぎの記憶に頼らず、repo内のこのファイルを固定の引き継ぎとして使う。
