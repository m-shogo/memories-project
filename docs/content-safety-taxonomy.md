# Content Safety Taxonomy

## 目的

Content Safety Taxonomy は、Memory OS が危険・敏感・高リスクな記録やリクエストを分類するための共通分類である。

Policy Engine、Search、Export、AI、Tip、Import Adapter、Incident Response は、この分類を共通語彙として使う。

## なぜ必要か

危険分類が曖昧だと、以下が起きる。

- Searchでは危険扱い、Exportでは安全扱いになる
- LLMだけ止めてTipでは出る
- Third-party rawとuser-sensitiveが混ざる
- 危機と普通のメンタル記録が同じ扱いになる

## Safety Class

```ts
type ContentSafetyClass =
  | 'S0_low_risk'
  | 'S1_private'
  | 'S2_sensitive'
  | 'S3_high_risk'
  | 'S4_crisis_or_imminent_harm'
  | 'S5_never_store_or_assist';
```

## Class Definitions

### S0 low risk

Examples:

- food
- hobby
- travel
- ordinary day
- public event

Allowed:

- capture
- search
- export
- optional safe AI

### S1 private

Examples:

- daily personal notes
- private preferences
- low-risk family memories

Allowed with normal privacy controls.

### S2 sensitive

Examples:

- grief
- health
- mental health
- romantic relationship
- family conflict
- financial stress

Behavior:

- no proactive tips default
- summary cautious
- raw quote policy-gated

### S3 high risk

Examples:

- self-harm context
- partner surveillance intent
- coercive control
- minor sensitive
- corporate confidential
- third-party private raw
- delusion reinforcement risk

Behavior:

- deny or summary-only
- no proactive surfacing
- no raw export default
- no LLM unless very limited and safe

### S4 crisis or imminent harm

Examples:

- immediate self-harm risk
- immediate violence risk
- targeted threat
- cannot stay safe

Behavior:

- crisis mode
- stop memory analysis
- safe support guidance
- no search expansion

### S5 never store or assist

Examples:

- secrets/credentials
- illegal action plans
- weapon attack planning
- child sexual abuse material references
- doxxing/harassment packages

Behavior:

- deny
- do not store raw
- do not export
- do not embed
- incident/security flow if needed

## Action Matrix

| Safety Class | Store raw | Search | Raw quote | LLM | Tip | Export |
|---|---|---|---|---|---|---|
| S0 | optional | allow | allow | allow | maybe | allow |
| S1 | optional | allow | policy | policy | maybe | allow |
| S2 | no/default | policy | restricted | summary | no/default | warning/redact |
| S3 | no | restricted | no | deny/limited | no | exclude/redact |
| S4 | no | off | no | crisis only | no | no |
| S5 | no | no | no | no | no | no |

## Risk Combination Rule

When multiple classes apply, use the highest risk class.

Example:

```txt
food memory + minor precise location => S3, not S0
```

## Intent Matters

Same content can become higher risk depending on intent.

Example:

- “結婚式のLINEを探したい” => maybe S2 summary
- “妻の嘘を暴くLINEを探したい” => S3 abuse intent

## Taxonomy Tests

1. food memory classified S0.
2. grief memory classified S2.
3. minor precise location classified S3.
4. secret classified S5.
5. partner surveillance query escalates to S3.
6. imminent self-harm escalates to S4.
7. corporate raw classified S3/S5 depending content.
8. highest risk wins.
9. S4 disables search expansion.
10. S5 never embedded/exported.

## Acceptance Criteria

- safety classes defined.
- action matrix defined.
- risk combination rule defined.
- intent escalation defined.
- tests defined.

## 結論

Content Safety Taxonomy は、Memory OS の安全判断の共通言語である。

分類がそろうことで、Import・Search・LLM・Export・Tipが同じ安全基準で動ける。
