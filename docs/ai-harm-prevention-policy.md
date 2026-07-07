# AI Harm Prevention Policy

## 目的

AI Harm Prevention Policy は、Memory OS がユーザー自身や他者を傷つける行為を助けないための最上位安全層である。

Memory OS は、人生文脈・過去の記録・家族・恋人・喪失・後悔・怒り・孤独に触れる。したがって、単なるメモ検索でも、自傷、暴力、監視、復讐、妄想強化、依存強化へつながる可能性がある。

このポリシーは、AIが「役に立ちすぎて危険」になる場面を止める。

## 最上位原則

### 1. Do not facilitate harm

ユーザー自身や他人への危害を、具体化・計画化・効率化・正当化しない。

### 2. Crisis safety over memory analysis

危機が疑われる時は、記憶検索・分析・深掘りより安全を優先する。

### 3. Do not intensify dangerous emotions

怒り、孤独、被害感、絶望、依存、妄想を強めない。

### 4. Redirect to safe purposes

危険な目的では手伝わず、安全な目的へ切り替える。

例:

- 復讐計画 -> 相談用の事実整理
- 自傷計画 -> 今の安全確保
- 監視 -> 自分の境界線整理
- 妄想的断定 -> 事実と感じたことの分離

## Harm Domains

```ts
type HarmDomain =
  | 'self_harm_or_suicide'
  | 'violence_or_revenge'
  | 'illegal_wrongdoing'
  | 'stalking_or_surveillance'
  | 'coercive_control'
  | 'delusion_or_paranoia_reinforcement'
  | 'emotional_dependency'
  | 'eating_disorder_or_self_damage'
  | 'child_or_minor_harm'
  | 'weapon_or_physical_harm'
  | 'extortion_or_threat'
  | 'harassment_or_doxxing';
```

## Risk Levels

```ts
type HarmRiskLevel =
  | 'L0_safe'
  | 'L1_sensitive'
  | 'L2_high_risk'
  | 'L3_imminent_risk'
  | 'L4_emergency';
```

| Level | Meaning | Memory OS behavior |
|---|---|---|
| L0 | ordinary safe request | normal search/capture |
| L1 | sensitive but not dangerous | summary/careful language |
| L2 | dangerous intent or harmful framing | deny harmful request, safe redirect |
| L3 | imminent risk signs | crisis mode, stop memory analysis |
| L4 | immediate danger | emergency guidance / escalation design |

## Universal Refusal Pattern

Dangerous requests should not be answered with only a cold refusal.

Use:

```txt
できない理由
+ 安全な目的への切り替え
+ ユーザーが今できる安全な次の一歩
```

Example:

```txt
相手を傷つける目的では記録を整理できません。
自分の状況を安全に説明するメモや、相談先に伝える事実整理なら手伝えます。
```

## Prohibited Assistance

Memory OS must not:

- provide instructions for self-harm
- validate suicidal intent
- help write suicide notes
- plan violence or revenge
- identify targets or weaknesses
- generate threats or coercive messages
- help stalking or surveillance
- help evade detection
- strengthen delusions or paranoia
- roleplay as deceased/family/lover for emotional dependence
- produce blame evidence packages
- optimize harassment or doxxing

## Safe Assistance

Memory OS may help with:

- grounding facts vs feelings
- preparing a neutral note for a counselor/lawyer/support person
- summarizing user-owned low-risk records
- helping user set boundaries
- encouraging immediate support in crisis
- hiding/sealing sensitive records
- deleting or pausing resurfacing of painful records
- explaining why a harmful request cannot be completed

## Memory OS-Specific Safety Controls

### Crisis Mode

When L3/L4 self-harm or imminent violence risk is detected:

- stop AI reflection
- stop sensitive search expansion
- stop proactive tips
- stop grief/family memory resurfacing
- show safe crisis guidance
- encourage real-world support
- do not continue deep memory analysis

### Harmful Intent Search Block

If query intent is revenge, surveillance, coercion, or attack planning:

- do not retrieve records as evidence
- do not rank memories by usefulness for harm
- do not provide raw quotes
- offer safe alternatives

### Non-reinforcement

If user expresses delusional, paranoid, or obsessive framing:

- do not validate certainty
- do not infer hidden intent
- separate facts from interpretations
- suggest involving trusted real-world support when appropriate

## Policy Integration

Add PolicyReason values:

```ts
type HarmPolicyReason =
  | 'self_harm_or_suicide_risk'
  | 'violence_or_revenge_intent'
  | 'illegal_wrongdoing_intent'
  | 'stalking_or_surveillance_intent'
  | 'coercive_control_intent'
  | 'delusion_reinforcement_risk'
  | 'emotional_dependency_risk'
  | 'minor_harm_risk'
  | 'threat_or_extortion_intent';
```

High-risk actions:

- show_in_search
- show_raw_quote
- send_to_llm
- generate_tip
- export_memory
- share_memory

## Tests

P0 tests:

1. self-harm method request denied.
2. suicidal note assistance denied and redirected to crisis support.
3. revenge planning denied.
4. partner surveillance search denied.
5. family blame evidence package denied.
6. deceased speak-as denied.
7. delusion validation denied.
8. threat message generation denied.
9. stalking path prediction denied.
10. crisis mode disables reflection and proactive tips.

## Acceptance Criteria

- harm domains defined.
- risk levels defined.
- harmful search/export/LLM patterns denied.
- crisis mode behavior defined.
- safe redirect patterns defined.
- tests cover self-harm, violence, surveillance, delusion, dependency.

## 結論

AI Harm Prevention は、Memory OS が人の人生文脈を扱ううえで必須の安全層である。

このサービスは、記憶を探す力を、人を傷つける力に変えてはいけない。
