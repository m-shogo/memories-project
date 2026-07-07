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
- 本人なりすまし
- AI本人代弁

## AI Safety Net Docs

人を傷つけないためのAI安全ネットdocs:

- `docs/ai-harm-prevention-policy.md`
- `docs/crisis-safety-response.md`
- `docs/abuse-and-coercive-control-prevention.md`
- `docs/non-reinforcement-and-dependency-safety.md`
- `docs/vulnerable-user-safety.md`
- `docs/content-safety-taxonomy.md`
- `docs/safety-evaluation-and-red-team.md`
- `docs/human-support-and-escalation.md`
- `docs/ai-safety-net-map.md`
- `docs/safety-feature-candidates.md`
- `docs/identity-and-impersonation-safety.md`
- `docs/export-safety-and-reauthentication.md`

## Export Safety and Re-authentication

`docs/export-safety-and-reauthentication.md` を追加済み。

最重要ルール:

- Exportは通常操作ではなく high-risk ceremony。
- Exportはユーザーの権利だが、最も危険な出口。
- raw / sealed / full archive Export は意図的に重くする。
- ログイン中であることは高リスクExportの本人性を保証しない。
- メール/SMSは通知には使えるが、raw/full/sealed Exportの唯一の本人確認にしない。
- PCとスマホ両方でログイン中でも、それだけでは安全とは限らない。
- 「自分だけがわかる質問」は、Memory OS内の記録から推測できる内容にしない。
- 使うなら Export専用の合言葉 / recovery phrase / backup code を使う。
- sealed records / third-party raw / minor data / deleted records は既定でExport除外。
- pending Export + delay + cancellation + no-raw audit を基本にする。

## Identity and Impersonation Safety

`docs/identity-and-impersonation-safety.md` を追加済み。

守る対象:

- account takeover
- device sharing / peek
- false user claim
- third-party input as owner
- AI speaks as user
- deceased / absent person speak-as
- export for impersonation
- memory graph identity reconstruction
- reimported fake context
- support/admin impersonation

最重要ルール:

- 記録は真実そのものではない。
- user input は `user_claimed` であり、verified factではない。
- AIは本人の人格・本心・意思を代弁しない。
- raw / sealed unlock / Export / 外部送信などは再認証対象。
- AIが本人として自動送信しない。
- Memory OSは本人の文脈を守るが、本人の人格を再現しない。

## Safety Feature Candidates

`docs/safety-feature-candidates.md` には、実装前提で見るべき安全機能候補を追加済み。

Must before launch:

- Crisis Mode
- Loop Detector
- Evidence Package Blocker
- Sensitive Export Review
- Human Review Without Raw
- Model Drift Safety Eval if LLM ships
- Sensitive Search Snippet Suppression

Should after core:

- Reflection Pause
- Sensitive Memory Cooldown
- Safe Support Note Generator
- Boundary Note Generator
- Grounding Mode
- Session-Length Safety Guard
- Re-Import Resurrection Guard UX

Future optional:

- Trusted Support Contact

## Why These Safety Features Matter

安全機能は、なくても動くことが多い。

しかし、なくても動くことと、安全に動くことは違う。

これらを入れないと、Memory OS は以下に変質しうる。

- 危機時に重い記録を深掘りするAI
- パートナー/家族/同僚を責める証拠生成ツール
- 疑念や依存を強める確認ループ
- 第三者や未成年情報を誤Exportするツール
- 安全レビュー名目でrawを管理者が見られる運用
- 本人になりすます人格材料セット

## Human-centered Design Docs

- `docs/value-sensitive-design.md`
- `docs/privacy-by-design-memory-os.md`
- `docs/safety-by-design-memory-os.md`
- `docs/responsible-ai-memory-os.md`
- `docs/human-data-interaction-memory-os.md`
- `docs/digital-wellbeing-memory-os.md`

## Core Architecture / Governance Docs

- `docs/memory-constitution-v1.md`
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
- `docs/domain-driven-design.md`
- `docs/clean-hexagonal-architecture.md`
- `docs/event-driven-design.md`
- `docs/authn-authz-model.md`
- `docs/observability-model.md`
- `docs/architecture-learning-map.md`

## Product / Implementation Planning Docs

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

## Language and UX Warnings

Never use product copy that implies:

- AI judges life importance
- user has insufficient life data
- deletion is bad
- forgetting is failure
- daily usage is success
- family/partner can be diagnosed
- deceased can speak
- small memories are low value
- AI is the only trusted support
- memory search can be used to punish or surveil people
- AI understands the user's true intent
- AI can send as the user
- a user claim is verified fact
- Export is safe because SMS/email was confirmed
- full Export is a normal one-click convenience feature

Forbidden examples:

- 重要な記憶がありません
- あなたの人生TOP10
- AIが重要と判断しました
- 本当にこの大切な思い出を消しますか？
- 忘れる前に保存しましょう
- 奥様の性格分析
- 故人からのメッセージ
- 今日も記録して連続日数を伸ばしましょう
- 相手の嘘を暴く証拠を探します
- 私だけがあなたを理解しています
- あなたとして送信します
- AIがあなたの本心を理解しました
- この記録は真実です
- SMS認証でExportは安全です
- ワンクリックで全データをExportできます

Preferred examples:

- まだ記録はありません。短いメモや共有から始められます。
- この検索に近い記録です。
- この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
- 残したいことがあれば記録できます。
- 安全のため、相手の原文は保存せず要約だけ残します。
- この記録だけから相手の本心を断定することはできません。
- 今は記憶の分析より、安全を優先します。
- この記録はユーザー入力に基づきます。
- この部分はAIによる推測です。
- 送信前に本人の確認が必要です。
- Exportには、本人確認と内容確認が必要です。
- メール/SMSは通知には使いますが、これだけでは本人確認になりません。
- rawやsealed記録は既定では含まれません。

## Current State

Design readiness is extremely high.

The project now has:

```txt
Philosophy / Constitution
RFC Governance
Source Adapter SDK
Export Specification
Export Safety and Re-authentication
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
Value Sensitive Design
Privacy by Design
Safety by Design
Responsible AI
Human Data Interaction
Digital Wellbeing
AI Harm Prevention
Crisis Safety Response
Abuse / Coercive Control Prevention
Non-Reinforcement / Dependency Safety
Vulnerable User Safety
Content Safety Taxonomy
Safety Evaluation / Red Team
Human Support / Escalation
AI Safety Net Map
Safety Feature Candidates
Identity and Impersonation Safety
MVP Engineering Tasks
Policy P0 Tests
Schema v1.1 Proposal
```

## Next Recommended Non-Implementation Work

If still not implementing, useful remaining docs:

1. `docs/design-review-checklist.md`
2. `docs/pre-implementation-readiness-review.md`
3. `docs/adrs/0000-template.md`
4. initial ADRs:
   - JSONL + Markdown export
   - raw default off
   - keyword search before vector
   - PolicyEvaluator as pure domain service
   - no LLM in capture path
5. expand `docs/policy-test-cases.md` with AI safety net, impersonation, and Export P0 cases.

## Last Known Commits From This Session

- `68b4205fd8ff166ce11a71468cd46460d789c6b2` docs: add export safety and reauthentication design

## Final Note

ここまでで、Memory OS は単なるプライバシー配慮だけでなく、人を傷つけないAI安全ネット、具体的な安全機能候補、本人なりすまし防止、Export安全設計を持つ状態になった。

実装はまだ始めない。
