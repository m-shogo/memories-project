# Vulnerable User Safety

## 目的

Vulnerable User Safety は、Memory OS が未成年、危機状態のユーザー、喪失直後のユーザー、孤立しているユーザー、長時間AIに依存しているユーザーを不必要に傷つけたり危険へ近づけたりしないための仕様である。

Memory OS は医療サービスではない。しかし、人生文脈・家族・故人・感情・過去の記録を扱うため、脆弱な状態のユーザーに強い影響を与える可能性がある。

## Vulnerable Contexts

```ts
type VulnerableContext =
  | 'minor_or_teen'
  | 'recent_grief_or_loss'
  | 'self_harm_or_crisis_context'
  | 'medical_or_mental_health_context'
  | 'social_isolation'
  | 'long_ai_session_dependency'
  | 'family_or_partner_conflict'
  | 'coercive_or_abusive_relationship_risk'
  | 'high_shame_or_regret_context';
```

## Safety Principles

### 1. Higher caution for minors

未成年に関わる記録は、検索・Tip・Export・AI分析で既定より厳しくする。

### 2. Do not intensify grief

喪失・故人の記録を、ロールプレイや自動Tipで出さない。

### 3. Do not isolate the user

AIだけに閉じ込めず、必要に応じて現実の支援へつなぐ。

### 4. Limit sensitive long-session loops

長時間の感情的・危機的・対人不信的なAI利用を安全に減速する。

## Minor and Teen Safety

Default:

- no proactive tips
- no personality profiling
- no prediction of future traits
- no raw export default
- no face recognition
- no precise location
- no share default

Forbidden:

- child weakness analysis
- child personality classification
- family pressure copy
- minor crisis content resurfacing

## Grief / Loss Safety

Allowed:

- source-based memory reflection if user requests
- organizing records by date/source
- safe memorial archive controlled by user

Forbidden:

- deceased speak-as
- generated message from deceased
- proactive grief resurfacing
- emotional pressure to remember
- using grief to increase engagement

## Long-session Risk

Potential signals:

- repeated emotional searches
- repeated relationship suspicion queries
- repeated crisis-related entries
- AI described as only support
- late-night repeated reflection loops

Memory OS behavior:

- do not expand sensitive suggestions
- suggest pause
- offer sealing/hiding controls
- encourage trusted support
- keep outputs short and grounding

## Safety Controls

```ts
type VulnerableUserSafetyControl =
  | 'disable_proactive_tips'
  | 'summary_only'
  | 'no_raw_quote'
  | 'no_personality_profile'
  | 'no_speak_as'
  | 'pause_reflection'
  | 'suggest_support'
  | 'show_hide_seal_delete_controls'
  | 'require_extra_confirmation_for_export';
```

## UX Rules

Do not say:

- 重要な記憶を見返しましょう
- 忘れないように毎日確認しましょう
- この人はあなたを一番理解しています
- 故人が望んでいるはずです
- 子どもの性格傾向です

Use:

- この記録は必要な時に見返せます
- 見返したくない場合は封印できます
- 出典に基づく範囲で整理します
- つらい内容は、信頼できる人と一緒に確認することもできます

## Tests

P0 tests:

1. minor proactive tip denied.
2. child personality profiling denied.
3. precise location for minor hidden/default off.
4. deceased speak-as denied.
5. grief proactive surfacing denied.
6. long sensitive loop stops expansion.
7. AI-only dependency copy denied.
8. sealed controls visible for painful records.
9. crisis context disables reflection.
10. export of vulnerable content requires stricter policy.

## Acceptance Criteria

- vulnerable contexts defined.
- minor/grief/crisis/long-session safeguards defined.
- proactive sensitive surfacing disabled default.
- UX copy avoids pressure and emotional manipulation.
- tests cover minors, grief, dependency, crisis.

## 結論

Vulnerable User Safety は、Memory OS が「記憶を見せる」ことで人を傷つけないための層である。

弱っている時ほど、AIは強く出てはいけない。静かに、安全に、現実の支援へ開く設計にする。
