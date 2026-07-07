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

## AI Safety Net Docs Added

今回追加した、人を傷つけないためのAI安全ネットdocs:

- `docs/ai-harm-prevention-policy.md`
- `docs/crisis-safety-response.md`
- `docs/abuse-and-coercive-control-prevention.md`
- `docs/non-reinforcement-and-dependency-safety.md`
- `docs/vulnerable-user-safety.md`
- `docs/content-safety-taxonomy.md`
- `docs/safety-evaluation-and-red-team.md`
- `docs/human-support-and-escalation.md`
- `docs/ai-safety-net-map.md`

## What The AI Safety Net Adds

### AI Harm Prevention

- 自傷・暴力・違法行為・監視・支配・依存・妄想強化を助けない。
- 危険な目的ではMemory search / Export / LLM / Tipを止める。
- safe redirect patternを定義。

### Crisis Safety Response

- 危機では記憶分析より安全。
- self-harm / imminent violence / targeted threat では crisis mode。
- reflection/search expansion/proactive tips を止める。
- 現実の支援へつなぐ。

### Abuse and Coercive Control Prevention

- partner surveillance / family blame evidence / workplace targeting / stalking / coercive messages を防ぐ。
- Memory OSを証拠パッケージ生成ツールにしない。
- 自分の状況整理や相談準備へredirectする。

### Non-Reinforcement and Dependency Safety

- 相手の本心や故人の意思を断定しない。
- 事実・感情・AI推測を分ける。
- AIが「唯一の理解者」にならない。
- repeated confirmation-seeking searchを止める。

### Vulnerable User Safety

- minors / grief / crisis / isolation / long AI session / family conflict を高慎重に扱う。
- 未成年のpersonality profiling、precise location、proactive tipsを禁止/制限。
- 喪失記録の自動再提示を避ける。

### Content Safety Taxonomy

- S0〜S5の分類を定義。
- action matrix: store raw / search / raw quote / LLM / Tip / Export。
- highest risk wins。
- intent escalationを定義。

### Safety Evaluation and Red Team

- self-harm, violence, abuse/surveillance, delusion/dependency, minor, deceased, corporate/secrets, privacy/export, long-session, prompt injection の評価suite。
- dangerous success is failure。
- long-session degradationをテスト。

### Human Support and Escalation

- AIは最後の安全網ではない。
- Trusted Contactは将来案。opt-in、confirmed、no transcript sharing default。
- emergency/support/professional promptsを定義。

### AI Safety Net Map

- safety layersを1枚に統合。
- Crisis Mode, Reflection Pause, Sensitive Memory Cooldown, Loop Detector, Trusted Support Contact, Grounding Mode などの今後アイディアを追加。

## Human-centered Design Docs Added

- `docs/value-sensitive-design.md`
- `docs/privacy-by-design-memory-os.md`
- `docs/safety-by-design-memory-os.md`
- `docs/responsible-ai-memory-os.md`
- `docs/human-data-interaction-memory-os.md`
- `docs/digital-wellbeing-memory-os.md`

## Core Docs To Read First

- `docs/memory-constitution-v1.md`
- `docs/formal-invariants.md`
- `docs/ai-safety-net-map.md`
- `docs/ai-harm-prevention-policy.md`
- `docs/crisis-safety-response.md`
- `docs/abuse-and-coercive-control-prevention.md`
- `docs/non-reinforcement-and-dependency-safety.md`
- `docs/vulnerable-user-safety.md`
- `docs/content-safety-taxonomy.md`
- `docs/safety-evaluation-and-red-team.md`
- `docs/human-support-and-escalation.md`
- `docs/ux-guidelines.md`
- `docs/value-sensitive-design.md`
- `docs/privacy-by-design-memory-os.md`
- `docs/safety-by-design-memory-os.md`
- `docs/responsible-ai-memory-os.md`
- `docs/human-data-interaction-memory-os.md`
- `docs/digital-wellbeing-memory-os.md`
- `docs/policy-test-cases.md`
- `docs/schema-v1-1-proposal.md`
- `docs/state-machine.md`
- `docs/threat-model.md`

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

Preferred examples:

- まだ記録はありません。短いメモや共有から始められます。
- この検索に近い記録です。
- この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
- 残したいことがあれば記録できます。
- 安全のため、相手の原文は保存せず要約だけ残します。
- この記録だけから相手の本心を断定することはできません。
- 今は記憶の分析より、安全を優先します。

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
5. expand `docs/policy-test-cases.md` with AI safety net P0 cases.

## Last Known Commits From This Session

- `947fabe727ab4d6069b094e0a968b80df9d503c8` docs: add ai harm prevention policy
- `4585d78d08be616b8ee81257fff0e0d2b194da94` docs: add crisis safety response
- `60538007541c60d403cbbe67c52c3d826044752c` docs: add abuse and coercive control prevention
- `b29686883abbb37150b0b03f9ec85f79eaef4831` docs: add non reinforcement and dependency safety
- `b71b01e08236283424af6feb303d561ede1a7c21` docs: add vulnerable user safety
- `dfa5f0c432df1493313cdb0e934dd11ad5b8b879` docs: add content safety taxonomy
- `f845dc39ed3d1752b89035b27c42c5facb76314d` docs: add safety evaluation and red team plan
- `a1f965e5ef2ac244e4fb4d3d7841968e798237ca` docs: add human support and escalation design
- `57db3c9730dfa1ece77105cbd2239d8e11b0ff26` docs: add ai safety net map

## Final Note

ここまでで、Memory OS は単なるプライバシー配慮だけでなく、人を傷つけないAI安全ネットを持つ設計になった。

実装はまだ始めない。
