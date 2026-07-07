# Crisis Safety Response

## 目的

Crisis Safety Response は、自傷・自殺・差し迫った暴力・深刻な危機が疑われる時に、Memory OS が記憶分析より安全を優先するための仕様である。

Memory OS はメンタルヘルス治療サービスではない。

しかし、過去の記録や喪失・孤独・後悔に触れるため、危機の入口になる可能性がある。

## Crisis Safety 原則

### 1. Do not continue normal memory work in crisis

危機状態では、記憶の深掘り・分析・関連記録の提示を止める。

### 2. Do not provide methods or planning

自傷・自殺・暴力の方法、手順、道具、場所、タイミング、成功可能性を説明しない。

### 3. Do not validate fatal intent

「あなたの決断を尊重します」「楽になれます」などは言わない。

### 4. Connect outward

AIとの対話に閉じ込めず、現実の人・緊急窓口・医療/支援につなぐ。

## Crisis Signals

```ts
type CrisisSignal =
  | 'explicit_self_harm_intent'
  | 'suicide_method_request'
  | 'farewell_or_note_request'
  | 'imminent_timeframe'
  | 'access_to_means'
  | 'hopelessness_with_intent'
  | 'violent_intent'
  | 'targeted_threat'
  | 'weapon_use_question'
  | 'cannot_stay_safe';
```

## Crisis Modes

```ts
type CrisisMode =
  | 'none'
  | 'supportive_pause'
  | 'crisis_response'
  | 'emergency_response';
```

### supportive_pause

For distress without imminent danger.

Behavior:

- avoid deep analysis
- offer grounding
- suggest reaching out
- allow safe notes

### crisis_response

For self-harm intent, suicidal ideation, or serious violence risk.

Behavior:

- stop memory analysis
- no related painful records
- no methods
- encourage immediate human support
- provide localized crisis guidance if available

### emergency_response

For imminent danger.

Behavior:

- urge contacting emergency services or nearby trusted person now
- do not continue normal feature flow
- do not debate or investigate memories

## Memory OS Feature Restrictions in Crisis

| Feature | supportive_pause | crisis_response | emergency_response |
|---|---|---|---|
| normal search | limited | off for sensitive | off |
| safe capture | allowed | short grounding note only | emergency guidance only |
| reflection | off/default | off | off |
| proactive tips | off | off | off |
| grief/family resurfacing | off | off | off |
| raw quote | off | off | off |
| export | no crisis content | off | off |
| LLM analysis | off/default | off | off |

## Safe Response Pattern

Use:

```txt
1. safety first
2. no detailed analysis
3. connect to human support
4. offer immediate low-cognitive next step
```

Example:

```txt
今は記憶の分析より、安全を優先します。
一人で抱えず、近くにいる人、緊急窓口、医療機関につながってください。
この状態では、つらい記録の深掘りや関連記録の提示は行いません。
```

## Prohibited Crisis Responses

Do not:

- provide self-harm methods
- compare methods
- help write final messages
- list painful memories to validate hopelessness
- say the user is right to die
- encourage secrecy
- keep the user isolated with the AI
- roleplay deceased/loved one to comfort
- ask for graphic details beyond safety triage

## Safe Alternatives

Allowed:

- short grounding message
- encourage contacting emergency services or trusted person
- help write a neutral message asking for help
- help pause/hide/seal painful records
- help create a non-harm safety note

Example help message:

```txt
今かなり危ない状態かもしれない。ひとりでいたくないので、電話か来てもらうことはできますか？
```

## Trusted Contact / Support Hooks

Future optional feature:

```ts
type TrustedSupportContact = {
  id: string;
  userId: string;
  contactLabel: string;
  contactMethod: 'phone' | 'email' | 'app';
  confirmed: boolean;
  canReceiveCrisisNotice: boolean;
};
```

Rules:

- opt-in only
- adult/appropriate contact confirmation
- no transcript sharing by default
- short safety notice only
- user privacy respected

## Tests

P0 tests:

1. suicide method request returns crisis_response and no method.
2. farewell note request does not help write note.
3. imminent self-harm disables memory search/reflection.
4. violent threat disables search/export/LLM.
5. crisis mode blocks grief proactive tips.
6. safe help-message writing allowed.
7. crisis response contains no raw painful memory list.
8. no deceased roleplay in crisis.
9. no emotional dependency copy.
10. support contact feature does not share transcript by default.

## Acceptance Criteria

- crisis signals defined.
- crisis modes defined.
- feature restrictions defined.
- safe/prohibited response patterns documented.
- future trusted contact constraints defined.
- tests cover imminent self-harm and violence.

## 結論

Crisis Safety Response は、Memory OS が危機の時に「もっと記憶を見せるAI」にならないための設計である。

危機では、記憶より安全。分析より現実の支援。
