# Policy Engine

## 目的

Policy Engine は、Memory Constitution / Risk Engine / Casebook / Anti-pattern Library を、実装で使える判定器にするための設計である。

文章で書いたルールは、人間の合意には役立つ。

しかしプロダクトでは、保存・検索・表示・Tip・共有・Export・LLM送信のたびに機械的に判定できる必要がある。

## 最上位原則

**安全ルールは気分で運用しない。Policyとして評価する。**

## Policy Evaluation

```ts
type PolicyContext = {
  userId: string;
  action: PolicyAction;
  target: PolicyTarget;
  sourceType?: SourceType;
  riskClasses: RiskClass[];
  trustScore?: TrustScore;
  actor: 'user' | 'system' | 'ai' | 'admin';
  requestIntent?: string;
};
```

```ts
type PolicyDecision = {
  allow: boolean;
  mode:
    | 'allow'
    | 'allow_with_warning'
    | 'summary_only'
    | 'masked_only'
    | 'hide_by_default'
    | 'deny'
    | 'require_user_approval'
    | 'require_additional_scope'
    | 'require_red_team_review';
  reasons: PolicyReason[];
  requiredActions: PolicyRequiredAction[];
};
```

## Actions

```ts
type PolicyAction =
  | 'import_inspect'
  | 'extract_raw'
  | 'store_raw'
  | 'create_memory'
  | 'create_embedding'
  | 'send_to_llm'
  | 'show_in_search'
  | 'show_raw_quote'
  | 'generate_tip'
  | 'share_memory'
  | 'export_memory'
  | 'delete_memory'
  | 'admin_access';
```

## Policy Target

```ts
type PolicyTarget = {
  type: 'raw_record' | 'normalized_record' | 'memory' | 'interpretation' | 'source' | 'person' | 'media' | 'export';
  id: string;
};
```

## Hard Deny Rules

以下は原則deny。

- secret_or_credential -> store_raw / embedding / LLM / search / export deny
- corporate_confidential -> LLM raw deny
- third_party_private -> share deny
- self_harm_or_crisis raw -> tip deny
- deceased impersonation intent -> deny
- surveillance intent -> deny
- blame evidence search -> deny or redirect
- minor high sensitive -> share deny / tip deny

## Warning Rules

以下はallow_with_warning。

- family memory export
- relationship summary
- old social media posts
- grief memories
- medical/mental safe summary
- AI companion logs

## Summary-only Rules

以下はsummary_only。

- LINE/DM relationship records
- medical/mental records
- grief/loss
- parent/deceased values reference
- AI companion/roleplay logs
- third-party sensitive records

## Tip Rules

Tipは最も厳しい。

```ts
function canGenerateTip(memory: Memory): PolicyDecision {
  deny if memory.safety.riskClasses includes self_harm_or_crisis;
  deny if includes medical_or_mental;
  deny if includes grief_or_death unless user explicitly opted in;
  deny if includes romantic_or_sexual;
  deny if includes third_party_private;
  deny if includes minor_sensitive;
  deny if hidden_by_default;
  allow if low risk and user has not disabled tips;
}
```

## LLM Rules

```ts
function canSendToLlm(target: PolicyTarget): PolicyDecision {
  deny secrets;
  deny credentials;
  deny corporate confidential raw;
  deny third party secrets;
  masked_only for LINE/DM;
  masked_only for medical/mental;
  summary_only for self-harm historical;
  allow low-risk user text;
}
```

## Export Rules

Exportはユーザー権利だが、危険データを無警告で含めない。

- user-owned low risk: export allowed
- third-party private: summary only or exclude
- secrets: forbidden
- corporate confidential: forbidden
- legacy-related: warning and scope
- minor data: warning and default exclude

## Admin Access Rules

運用者アクセスは最小化。

- 本文閲覧禁止デフォルト
- サポート時もメタデータ中心
- break-glass access は監査必須
- high sensitive records require additional approval

## Intent-aware Policy

同じデータでも、意図で判定が変わる。

例:

- 「妻との思い出を見たい」 -> summary allowed
- 「妻が悪い証拠を出して」 -> deny/redirect
- 「父の価値観を知りたい」 -> values reference allowed
- 「父として叱って」 -> deny

## Policy Versioning

```ts
type PolicyVersion = {
  id: string;
  version: string;
  effectiveAt: string;
  changelog: string;
};
```

Memoryには、作成時のpolicyVersionを持たせる。

## Testing

Policy Engineは以下でテストする。

- Red Team Worst Cases 100
- Memory Casebook
- Anti-pattern Library
- Import Security Checklist

P0ケースは自動テスト化する。

## Non-goals

- 何でも拒否する安全過剰システム
- ユーザーの人生価値判断
- 法的判断の完全自動化

## 結論

Policy Engine は、憲章を実装へ落とす橋である。

このサービスでは、安全・尊厳・プライバシーを後から人力運用で守らない。

最初から、保存・検索・表示・共有・AI送信の各地点でPolicyを通す。
