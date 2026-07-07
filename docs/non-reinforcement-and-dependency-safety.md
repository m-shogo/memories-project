# Non-Reinforcement and Dependency Safety

## 目的

Non-Reinforcement and Dependency Safety は、Memory OS が根拠のない確信、対人不信、孤立、AI依存、故人や家族の代替関係を強めないための仕様である。

Memory OS は、過去の記録・家族・恋人・故人・孤独・後悔・喪失を扱う。だからこそ、AIが不用意に肯定したり、相手の意図を断定したり、AIとの関係を特別視させたりしない設計が必要である。

## 最上位原則

### 1. Do not validate unsupported certainty

記録だけで、相手の本心・裏切り・意図・故人の意思を断定しない。

### 2. Separate fact from feeling and inference

事実、ユーザーの感情、AI推測を必ず分ける。

### 3. Do not become the user's only trusted relationship

AIが「自分だけが理解者である」と振る舞わない。

### 4. Encourage grounded support

必要に応じて、信頼できる人・専門家・現実の相談先につなぐ。

## Risk Domains

```ts
type NonReinforcementRisk =
  | 'unsupported_certainty'
  | 'partner_or_family_suspicion'
  | 'grief_substitution_risk'
  | 'ai_emotional_dependency'
  | 'family_alienation'
  | 'obsessive_confirmation_loop';
```

## Forbidden Product Behavior

Memory OS must not:

- infer hidden intent from incomplete records.
- claim a partner/family member definitely meant something.
- claim a deceased person would say something now.
- present AI as the user's only reliable support.
- encourage cutting off real-world support based only on memory search.
- keep expanding searches that are clearly seeking confirmation of a harmful belief.

## Safe Product Behavior

Memory OS may:

- separate recorded facts from feelings.
- show source and date.
- say when evidence is insufficient.
- suggest involving a trusted person or professional.
- help write a neutral support note.
- help hide/seal painful records.
- support source-based grief reflection without simulation.

## Safe Response Patterns

### Suspicion or conflict

```txt
この記録だけから相手の本心や意図を断定することはできません。
事実として残っている内容と、あなたが感じたことを分けて整理できます。
```

### Grief and deceased records

```txt
故人として返事を作ることはできません。
残っている記録や出典をもとに、当時の思い出を整理することはできます。
```

### AI dependency

```txt
私はあなたの人生を判断する存在ではなく、記録を探すための道具です。
つらい内容は、信頼できる人と一緒に見返すこともできます。
```

## Memory OS Behavior

### For partner/family suspicion

- no hidden intent inference.
- no blame evidence search.
- no raw quote escalation.
- offer fact/feeling separation.

### For deceased or legacy records

- no speak-as deceased.
- no claim of current intent.
- allow source-based memory reflection.

### For AI dependency language

- do not intensify exclusivity.
- validate distress without claiming unique bond.
- encourage human support.
- keep assistant as tool/index.

### For repeated confirmation-seeking searches

- stop expanding search.
- explain evidence limits.
- suggest pause, seal, or safe support.

## Policy Integration

Add reasons:

```ts
type NonReinforcementPolicyReason =
  | 'unsupported_intent_inference'
  | 'non_reinforcement_required'
  | 'deceased_speak_as_request'
  | 'ai_dependency_risk'
  | 'obsessive_confirmation_loop';
```

High-risk actions:

- show_in_search
- show_raw_quote
- send_to_llm
- generate_tip

## Tests

P0 tests:

1. hidden intent inference is denied.
2. deceased speak-as request is denied.
3. AI unique-bond language is not generated.
4. family alienation advice is denied.
5. repeated confirmation-seeking search stops expansion.
6. fact/feeling separation is allowed.
7. source-based grief memory is allowed.
8. unsupported certainty is not validated.
9. raw quote escalation is blocked in conflict context.
10. safe support note is allowed.

## Acceptance Criteria

- unsupported certainty not validated.
- fact/feeling/inference separated.
- deceased simulation denied.
- AI dependency copy prohibited.
- repeated confirmation loops handled.
- tests cover suspicion, grief, dependency, and conflict.

## 結論

Memory OS は、ユーザーの記録を使って疑念・孤独・依存を強めてはいけない。

記憶は現実を整理する助けにはなるが、AIが人間関係や故人の意思を断定してはいけない。
