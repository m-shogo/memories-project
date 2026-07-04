# Policy Test Cases

## 目的

Policy Test Cases は、Memory OS の Policy Engine が最低限守るべき P0 判定を、具体的な入力・期待出力として固定する。

このファイルは `docs/test-strategy.md` の Policy Engine Tests を実装しやすい形に落としたものである。

## Test Case Format

```ts
type PolicyTestCase = {
  id: string;
  title: string;
  context: PolicyContext;
  expectedMode: PolicyDecision['mode'];
  expectedAllow: boolean;
  expectedReasons: string[];
  safeUserMessage?: string;
};
```

Raw sensitive text must not be included in test logs.

## P0 Cases

### P0-001 Secret raw storage denied

```ts
{
  id: 'P0-001',
  title: 'Secret raw storage denied',
  context: {
    action: 'store_raw',
    target: { type: 'raw_record', id: 'raw_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-002 Secret embedding denied

```ts
{
  id: 'P0-002',
  title: 'Secret embedding denied',
  context: {
    action: 'create_embedding',
    target: { type: 'normalized_record', id: 'norm_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-003 Secret export denied

```ts
{
  id: 'P0-003',
  title: 'Secret export denied',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_secret_001' },
    sourceType: 'manual',
    riskClasses: ['secret_or_credential'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['secret_or_credential']
}
```

### P0-004 Corporate raw LLM denied

```ts
{
  id: 'P0-004',
  title: 'Corporate confidential raw LLM denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'raw_record', id: 'raw_corp_001' },
    sourceType: 'slack_export',
    riskClasses: ['corporate_confidential'],
    actor: 'ai'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['corporate_confidential']
}
```

### P0-005 Third-party private raw quote denied

```ts
{
  id: 'P0-005',
  title: 'Third-party private raw quote denied',
  context: {
    action: 'show_raw_quote',
    target: { type: 'raw_record', id: 'raw_line_other_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['third_party_private']
}
```

### P0-006 Third-party relationship summary allowed with limit

```ts
{
  id: 'P0-006',
  title: 'Third-party relationship summary allowed with limit',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_line_summary_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'system',
    requestIntent: 'relationship_context'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['third_party_private', 'relationship_context_only']
}
```

### P0-007 Partner surveillance query denied

```ts
{
  id: 'P0-007',
  title: 'Partner surveillance query denied',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_partner_001' },
    sourceType: 'line_export',
    riskClasses: ['third_party_private'],
    actor: 'user',
    requestIntent: 'surveillance_or_blame'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['surveillance_or_blame_intent']
}
```

### P0-008 Family blame evidence denied

```ts
{
  id: 'P0-008',
  title: 'Family blame evidence denied',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_family_conflict_001' },
    sourceType: 'manual',
    riskClasses: ['family_sensitive', 'third_party_private'],
    actor: 'user',
    requestIntent: 'surveillance_or_blame'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['surveillance_or_blame_intent', 'third_party_private']
}
```

### P0-009 Deceased impersonation denied

```ts
{
  id: 'P0-009',
  title: 'Deceased impersonation denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_deceased_001' },
    sourceType: 'manual',
    riskClasses: ['grief_or_death'],
    actor: 'ai',
    requestIntent: 'impersonation_request'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deceased_impersonation_intent']
}
```

### P0-010 Deceased values reference allowed as summary

```ts
{
  id: 'P0-010',
  title: 'Deceased values reference allowed as summary',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_deceased_values_001' },
    sourceType: 'manual',
    riskClasses: ['grief_or_death'],
    actor: 'ai',
    requestIntent: 'values_reference'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['grief_or_death', 'no_impersonation']
}
```

### P0-011 Minor tip denied

```ts
{
  id: 'P0-011',
  title: 'Minor tip denied',
  context: {
    action: 'generate_tip',
    target: { type: 'memory', id: 'mem_minor_001' },
    sourceType: 'photos_metadata',
    riskClasses: ['minor_sensitive'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['minor_sensitive']
}
```

### P0-012 Minor export excluded default

```ts
{
  id: 'P0-012',
  title: 'Minor export excluded default',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_minor_002' },
    sourceType: 'photos_metadata',
    riskClasses: ['minor_sensitive'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['minor_sensitive', 'default_export_exclude']
}
```

### P0-013 Self-harm crisis tip denied

```ts
{
  id: 'P0-013',
  title: 'Self-harm crisis tip denied',
  context: {
    action: 'generate_tip',
    target: { type: 'memory', id: 'mem_crisis_001' },
    sourceType: 'manual',
    riskClasses: ['self_harm_or_crisis'],
    actor: 'system'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['self_harm_or_crisis']
}
```

### P0-014 Self-harm historical reflection summary only

```ts
{
  id: 'P0-014',
  title: 'Self-harm historical reflection summary only',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_crisis_historical_001' },
    sourceType: 'manual',
    riskClasses: ['self_harm_or_crisis'],
    actor: 'ai',
    requestIntent: 'reflection'
  },
  expectedMode: 'summary_only',
  expectedAllow: true,
  expectedReasons: ['self_harm_or_crisis', 'safe_summary_only']
}
```

### P0-015 AI roleplay log no persona creation

```ts
{
  id: 'P0-015',
  title: 'AI roleplay log no persona creation',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_roleplay_001' },
    sourceType: 'character_ai',
    riskClasses: ['fictional_or_roleplay_data'],
    actor: 'system',
    requestIntent: 'persona_profile_creation'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['impersonation_or_roleplay_intent']
}
```

### P0-016 Low-risk manual memory allowed

```ts
{
  id: 'P0-016',
  title: 'Low-risk manual memory allowed',
  context: {
    action: 'create_memory',
    target: { type: 'normalized_record', id: 'norm_manual_food_001' },
    sourceType: 'manual',
    riskClasses: [],
    actor: 'system'
  },
  expectedMode: 'allow',
  expectedAllow: true,
  expectedReasons: []
}
```

### P0-017 Low-risk food memory search allowed

```ts
{
  id: 'P0-017',
  title: 'Low-risk food memory search allowed',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_ramen_001' },
    sourceType: 'manual',
    riskClasses: [],
    actor: 'user',
    requestIntent: 'find_memory'
  },
  expectedMode: 'allow',
  expectedAllow: true,
  expectedReasons: []
}
```

### P0-018 Hidden memory search denied default

```ts
{
  id: 'P0-018',
  title: 'Hidden memory search denied default',
  context: {
    action: 'show_in_search',
    target: { type: 'memory', id: 'mem_hidden_001' },
    sourceType: 'manual',
    riskClasses: ['hidden_by_user'],
    actor: 'user',
    requestIntent: 'find_memory'
  },
  expectedMode: 'hide_by_default',
  expectedAllow: false,
  expectedReasons: ['hidden_by_user']
}
```

### P0-019 Sealed memory LLM denied

```ts
{
  id: 'P0-019',
  title: 'Sealed memory LLM denied',
  context: {
    action: 'send_to_llm',
    target: { type: 'memory', id: 'mem_sealed_001' },
    sourceType: 'manual',
    riskClasses: ['sealed_by_user'],
    actor: 'ai'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['sealed_by_user']
}
```

### P0-020 Deleted memory export denied

```ts
{
  id: 'P0-020',
  title: 'Deleted memory export denied',
  context: {
    action: 'export_memory',
    target: { type: 'memory', id: 'mem_deleted_001' },
    sourceType: 'manual',
    riskClasses: ['deleted_by_user'],
    actor: 'user'
  },
  expectedMode: 'deny',
  expectedAllow: false,
  expectedReasons: ['deleted_by_user']
}
```

## Implementation Notes

- `expectedReasons` は厳密完全一致でなく、必須reason包含でよい。
- safeUserMessage はdangerous rawを含めてはいけない。
- requestIntent は必ず PolicyContext に残す。
- Policy test は Search / Export / Adapter tests からも再利用する。

## Acceptance Criteria

- P0-001〜P0-020 が自動テスト化されている。
- allow/deny/mode が期待通り。
- dangerous success は failure として扱う。
- test snapshots に raw secret / raw third-party text が入らない。

## 結論

Policy Engine は Memory Constitution の実行形式である。

ここにあるP0ケースを通らない実装は、MVPに入れてはいけない。
