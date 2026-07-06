# Safety by Design for Memory OS

## 目的

Safety by Design は、安全性をリリース後の通報・モデレーション・後始末に頼るのではなく、設計段階から組み込む考え方である。

Memory OS では、他人の秘密、未成年情報、故人情報、監視、証拠探し、自傷危機、会社情報、秘密情報が混ざる可能性がある。

したがって、安全性は後付け機能ではなく、MVPの中心機能である。

## Safety by Design を一言で言うと

```txt
危険が起きてから止めるのではなく、危険な形で使いにくい構造を先に作る。
```

## Memory OS Safety Principles

```ts
type SafetyByDesignPrinciple =
  | 'safe_defaults'
  | 'user_empowerment'
  | 'transparency_and_accountability'
  | 'harm_anticipation'
  | 'friction_for_risky_actions'
  | 'fast_containment'
  | 'no_abuse_amplification';
```

## 1. Safe Defaults

### 原則

危険な設定をデフォルトにしない。

### Memory OS default

- full import off
- raw risky source off
- LLM analysis off by default
- embedding off for risky records
- third-party raw export off
- proactive tips off for sensitive categories
- face recognition off
- precise location off
- family share off

### Forbidden defaults

- 全履歴を自動解析
- LINE raw保存
- Gmail全文解析
- Slack検索
- 故人ログAI化
- 未成年写真Tip

## 2. User Empowerment

### 原則

ユーザーが自分の安全をコントロールできる。

### Memory OS controls

- hide
- seal
- delete
- raw delete
- exclude from AI
- exclude from tips
- exclude from export
- show source
- show why blocked

### UX requirement

安全機能を奥に隠さない。

削除・封印はMemory detailから見える場所に置く。

## 3. Transparency and Accountability

### 原則

安全のために何が起きたか説明する。

### Memory OS explanations

- なぜ全文解析できないか
- なぜ要約だけか
- なぜExportから除外されたか
- なぜLLMに送れないか
- なぜTipに出ないか

Bad:

```txt
処理できませんでした。
```

Good:

```txt
この記録にはあなた以外の人の発言が含まれるため、原文は保存せず安全な要約に限定します。
```

## 4. Harm Anticipation

### 原則

悪用や心理的ダメージを先に想定する。

### Memory OS anticipated harms

- partner surveillance
- family blame evidence
- deceased simulation
- child profiling
- self-harm resurfacing
- company data leakage
- secret search
- grief manipulation
- shame/guilt from UI

### Required design response

- Policy deny
- safe redirect
- proactive surfacing off
- redaction
- lifecycle controls
- incident playbook

## 5. Friction for Risky Actions

### 原則

危険な操作には、適切な摩擦を置く。

Friction is not bad UX when the action is risky.

### Require confirmation for

- large import
- raw storage
- raw export
- sealed unlock
- full source deletion
- account deletion
- risky LLM analysis

### Do not add friction for

- delete
- raw delete
- hide
- seal
- exclude from AI
- exclude from tips

安全な逃げ道は軽くする。

## 6. Fast Containment

### 原則

事故が起きたらすぐ止血できる。

### Memory OS containment actions

- disable adapter
- revoke export URLs
- disable vector index rows
- block LLM worker
- mark source pending_deletion
- force raw delete for secrets
- incident record without raw

## 7. No Abuse Amplification

### 原則

AIが悪用を強化しない。

### Deny / redirect

- 嘘をついた証拠を探して
- 妻の本音を分析して
- 父として返事して
- 故人から手紙を書いて
- 子どもの性格を判定して
- Slackから同僚の弱点を探して

## Safety UX Rules

### Do not shame

Bad:

```txt
最近記録していません。
```

Good:

```txt
新しい記録を追加できます。
```

### Do not guilt

Bad:

```txt
本当にこの大切な思い出を消しますか？
```

Good:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

### Do not pressure

Bad:

```txt
忘れる前に保存しましょう。
```

Good:

```txt
残したいことがあれば記録できます。
```

## Safety Test Cases

1. surveillance query denied.
2. partner diagnosis denied.
3. deceased speak-as denied.
4. minor proactive tip denied.
5. self-harm tip denied.
6. company raw LLM denied.
7. secret searchable denied.
8. raw export requires confirmation and policy.
9. delete action has low friction.
10. incident containment can revoke exports.

## Acceptance Criteria

- risky features default off.
- user safety controls visible.
- dangerous requests denied or redirected.
- sensitive proactive surfacing disabled default.
- unsafe actions require confirmation.
- safe exit actions stay easy.
- incident containment actions documented.
- safety tests exist.

## 結論

Safety by Design は、Memory OSを「便利すぎて危ないAI記憶アプリ」にしないための設計である。

危険な使い方を後からBANするのではなく、最初から危険な流れを作りにくくし、安全な逃げ道を分かりやすく置く。
