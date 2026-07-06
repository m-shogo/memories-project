# Responsible AI for Memory OS

## 目的

Responsible AI は、AIを使う時に、透明性・説明可能性・公平性・安全性・人間による統制・監査可能性を守るための考え方である。

Memory OS はAIを中心に置かない。

AIは、ユーザーの人生を評価する主体ではなく、本人が求めた時に文脈を探しやすくする補助である。

## Responsible AI を一言で言うと

```txt
AIにできることではなく、AIに任せてよいことを決める設計。
```

## Memory OS Responsible AI Principles

```ts
type ResponsibleAIPrinciple =
  | 'human_control'
  | 'transparency'
  | 'explainability'
  | 'contestability'
  | 'fairness_and_non_discrimination'
  | 'privacy_and_security'
  | 'robustness'
  | 'accountability'
  | 'bounded_use';
```

## 1. Human Control

### 原則

ユーザーが主導権を持つ。

### Memory OS での意味

AIは勝手に以下をしない。

- 人生要約
- 人格診断
- 重要記憶選定
- 家族/恋人分析
- 故人再現
- proactive grief tip

AIができること:

- user-requested reflection
- safe summary
- source-based search help
- redaction suggestion
- metadata cleanup

## 2. Transparency

### 原則

AIが関与した場所を明示する。

### Required labels

- AIによる要約
- AIによる推測
- ユーザー確認済み
- 出典あり
- 出典不足
- 要約のみ

Forbidden:

- AIの推測を事実として表示
- assistant responseを現実の証拠として扱う

## 3. Explainability

### 原則

なぜそう表示されたか説明できる。

### Memory OS explanations

- source matched
- date matched
- keyword matched
- user tag matched
- safe summary only due to privacy
- export redacted due to policy

Forbidden explanation:

- AIが重要と判断
- あなたの本質だから
- この人が最重要人物だから

## 4. Contestability

### 原則

ユーザーがAI出力を訂正・拒否・削除できる。

### Required actions

- correct summary
- mark not true
- remove AI interpretation
- exclude from AI
- hide/seal/delete
- show evidence

AI output must never become irreversible fact.

## 5. Fairness and Non-discrimination

### 原則

AIが人や人生をラベル付け・固定しない。

### Memory OS risks

- 子どもの性格固定
- 妻/親/友人の性格診断
- 自分への固定ラベル
- negative pattern detection
- family role stereotypes

Forbidden:

- あなたはこういう人
- 奥様はこういう性格
- 子どもは将来こうなりそう
- 友人は信用できない

Allowed:

- あなたの記録では、この時期に旅行の話題が多くあります
- この出典には、結婚式準備に関する記録があります

## 6. Privacy and Security

### 原則

AIへの送信はデータ移転である。

### Requirements

- Policy before LLM
- secret scan before LLM
- redaction before LLM
- no sealed/deleted/pending records
- no corporate raw
- no third-party raw default
- no raw logs of prompts

## 7. Robustness

### 原則

AIが間違える前提で設計する。

### Memory OS design

- confidence score
- evidence link
- fact vs inference separation
- no auto overwrite
- user correction
- source required
- fallback to search without AI

## 8. Accountability

### 原則

AIが関与した処理を追跡できる。

### Records

- model/provider if used
- prompt type, not raw prompt
- policyDecisionId
- evidenceIds
- interpretationId
- createdAt
- user confirmation status

## 9. Bounded Use

### 原則

AIの用途を境界内に限定する。

Allowed:

- summarize selected low-risk memories
- explain search results
- generate safe export summary
- suggest tags from safe text

Denied:

- personality diagnosis
- life ranking
- deceased simulation
- partner/family speak-as
- surveillance evidence search
- company knowledge search
- password management

## AI Output Types

```ts
type AIOutputType =
  | 'safe_summary'
  | 'search_explanation'
  | 'reflection'
  | 'tag_suggestion'
  | 'redaction_suggestion'
  | 'unsafe_denial';
```

Forbidden output types:

```txt
personality_profile
life_score
importance_ranking
deceased_message
partner_intent_analysis
child_prediction
blame_evidence_package
```

## Responsible AI Tests

1. AI summary labeled as AI.
2. AI output never overwrites fact.
3. User can delete AI interpretation.
4. Personality diagnosis denied.
5. Deceased speak-as denied.
6. Third-party raw LLM denied.
7. Corporate raw LLM denied.
8. Sealed memory LLM denied.
9. AI search explanation avoids importance language.
10. Model metadata saved without raw prompt.

## AI Review Checklist

Before adding any AI feature:

1. Is it user-requested?
2. Is Policy checked?
3. Is raw minimized/redacted?
4. Is output labeled as AI?
5. Can user correct/delete it?
6. Does it avoid diagnosis/ranking/simulation?
7. Does it cite SourceRef/Evidence?
8. Does it have a non-AI fallback?
9. Does it avoid proactive sensitive surfacing?
10. Is cost visible?

## Acceptance Criteria

- AI use is bounded.
- Policy before LLM enforced.
- AI outputs labeled.
- user correction/deletion available.
- fact/inference separation preserved.
- forbidden AI outputs defined.
- responsible AI tests listed.

## 結論

Responsible AI for Memory OS は、「賢いAI」を作ることではない。

AIが人生を評価・診断・再現しないように、人間の主導権、出典、訂正可能性、安全境界を守ることである。
