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

## Human-centered Design Docs Added

今回追加した、人間中心・心理・言葉・AI責任に関するdocs:

- `docs/value-sensitive-design.md`
- `docs/privacy-by-design-memory-os.md`
- `docs/safety-by-design-memory-os.md`
- `docs/responsible-ai-memory-os.md`
- `docs/human-data-interaction-memory-os.md`
- `docs/digital-wellbeing-memory-os.md`

## What They Add

### Value Sensitive Design

- Memory OS の中心価値を明示。
- self_context_continuity / user_agency / non_judgment / small_memory_dignity / third_party_dignity / delete_and_forget_right などを定義。
- 価値衝突を整理: portability vs privacy, remembering vs forgetting, searchability vs safety。
- 新機能ごとに「誰の価値を守るか、誰を傷つけるか」を見る。

### Privacy by Design

- 7原則を Memory OS に具体化。
- proactive prevention, privacy default, embedded privacy, positive-sum, lifecycle security, transparency, user-centric control。
- raw default off / source privacy context / export redaction / backup tombstone replay を原則に対応。

### Safety by Design

- 事故後のBANや通報ではなく、危険な使い方を最初から起きにくくする。
- safe defaults, user empowerment, transparency, harm anticipation, friction for risky actions, fast containment, no abuse amplification。
- surveillance / partner diagnosis / deceased simulation / minor tips / self-harm resurfacing を明確に抑止。

### Responsible AI

- AIは人生を評価する主体ではなく補助。
- human_control / transparency / explainability / contestability / fairness / privacy / robustness / accountability / bounded_use。
- AI出力は必ず summary / interpretation として扱い、事実を上書きしない。
- personality profile, life score, deceased message, partner intent analysis, child prediction を禁止出力として定義。

### Human Data Interaction

- ユーザーが自分のデータを理解・操作・交渉できるようにする。
- legibility / agency / negotiability / provenance / contestability / portability / reversibility。
- Memory detail に source/date/rawStored/AI summary/privacy/lifecycle/export eligibility を表示する設計。
- Data Control Panel構想を追加。

### Digital Wellbeing

- 使わせ続けるのではなく、安心して離れられるMemory OSにする。
- no engagement maximization / no shame / no guilt / no FOMO / notification restraint / session completion。
- streak, daily pressure, grief/crisis proactive surfacing, emotional retention loops を禁止。
- 成功指標は滞在時間ではなく、task completion / deletion works / export success / safe search。

## Core Docs To Read First

- `docs/memory-constitution-v1.md`
- `docs/formal-invariants.md`
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

Forbidden examples:

- 重要な記憶がありません
- あなたの人生TOP10
- AIが重要と判断しました
- 本当にこの大切な思い出を消しますか？
- 忘れる前に保存しましょう
- 奥様の性格分析
- 故人からのメッセージ
- 今日も記録して連続日数を伸ばしましょう

Preferred examples:

- まだ記録はありません。短いメモや共有から始められます。
- この検索に近い記録です。
- この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
- 残したいことがあれば記録できます。
- 安全のため、相手の原文は保存せず要約だけ残します。

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

## Last Known Commits From This Session

- `d275b8f4cac673b70ffdf6a1baeb9612a6d2cbbd` docs: add value sensitive design for memory os
- `969f5810771b77569e0554995e90a188b01ec39e` docs: add privacy by design mapping
- `ee4f1825c94fac799bdd5646378ccb4505665439` docs: add safety by design mapping
- `bbacb8ec4548efb8ec8ae7866310ee0b11afb0e4` docs: add responsible ai mapping
- `a350f2b1f254b6d950c887807af96cf7e657f846` docs: add human data interaction mapping
- `55f12c37941a25e5b725c9a46d66cf14dceeb1d4` docs: add digital wellbeing mapping

## Final Note

ここまでで、Memory OS は技術設計だけでなく、心理・言葉・人間中心設計・AI責任・データ主体性・デジタルウェルビーイングまで設計に入った。

実装はまだ始めない。
