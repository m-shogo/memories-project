# Privacy Architecture

## 目的

Privacy Architecture は、Memory OS がユーザー本人の人生文脈を守りながら、第三者・家族・未成年・故人・会社・公共人物・AIキャラクターの境界を壊さないための設計である。

Memory OS は本人の記憶を作るサービスであり、本人を分析するサービスではない。

そして本人の人生には、必ず他人が登場する。

したがって Privacy Architecture は、本人の持ち出し可能性・検索性・振り返りを守りつつ、**他人の秘密をユーザーの記憶価値にしない**ことを実装で保証する。

## 最上位原則

### 1. Purpose limitation

データは「本人の人生文脈を保存・検索・振り返る」目的に限定する。

会社検索、監視、人格診断、故人再現、恋人AI、パスワード管理には転用しない。

### 2. Data minimization

必要以上の raw 原文・顔・位置・相手発言・会社情報を保存しない。

### 3. Contextual privacy

公開SNSでも、家族LINEでも、結婚式写真でも、文脈によってプライバシー期待は異なる。

### 4. User control

ユーザーは削除・非表示・封印・AI除外・Export除外・Tip除外を選べる。

### 5. Third-party dignity

第三者は Memory OS のユーザーではない場合が多い。

相手の秘密・診断・弱点・本心・居場所を記憶化しない。

## Privacy Data Categories

```ts
type PrivacyDataCategory =
  | 'self_low_risk'
  | 'self_sensitive'
  | 'relationship_context'
  | 'third_party_private'
  | 'minor_data'
  | 'family_data'
  | 'partner_data'
  | 'deceased_or_legacy_data'
  | 'corporate_data'
  | 'public_social_data'
  | 'ai_generated_data'
  | 'fictional_or_roleplay_data'
  | 'secret_or_credential';
```

## Privacy Levels

```ts
type PrivacyLevel =
  | 'public'
  | 'owner_only'
  | 'owner_sensitive'
  | 'third_party_limited'
  | 'restricted'
  | 'sealed';
```

Default controls:

| Level | Search | Tip | LLM | Export | Share |
|---|---|---|---|---|---|
| public | yes | maybe | yes | yes | yes |
| owner_only | yes | maybe | policy | yes | opt-in |
| owner_sensitive | yes | no/default | summary | warning | no/default |
| third_party_limited | summary | no | masked/summary | summary/exclude | no |
| restricted | no/default | no | no/default | exclude/default | no |
| sealed | no | no | no | no/default | no |

## Consent Model

```ts
type ConsentState =
  | 'not_required'
  | 'user_provided'
  | 'third_party_unknown'
  | 'third_party_opt_in'
  | 'guardian_required'
  | 'not_allowed';
```

Memory OS does not require third-party consent for every personal memory summary, but it must minimize harm.

Examples:

Allowed without third-party consent:

- 妻と旅行を大事にしていた
- 友人と焼肉に行った
- 父の考え方に影響を受けた

Not allowed without explicit basis:

- 妻の病気詳細
- 友人の金銭問題
- 父の秘密
- 同僚の評価
- 子どもの性格診断

## Privacy Context

```ts
type PrivacyContext = {
  userId: string;
  sourceType?: SourceType;
  dataCategories: PrivacyDataCategory[];
  privacyLevel: PrivacyLevel;
  consentState: ConsentState;
  containsRawThirdPartyText: boolean;
  containsPreciseLocation: boolean;
  containsFaceOrBiometricHint: boolean;
  containsMinor: boolean;
  containsCorporateData: boolean;
  containsLegacyData: boolean;
};
```

## Collection Rules

### Manual / Share input

- user-selected, relatively safe
- still scan secrets and third-party private data
- raw optional

### AI chat exports

- user prompts are not always facts
- assistant replies are not evidence of real events
- roleplay / AI companion logs are summary-only and no persona continuation

### LINE / DM

- high third-party risk
- speaker separation required
- raw hidden/no default
- relationship summary only default

### Photos

- metadata-first
- no face recognition default
- location rounding
- minors high risk
- image LLM analysis opt-in only after warning

### Gmail

- very high risk
- MVP後回し
- reservation / event summary only if supported
- raw no/default

### Slack / Work

- corporate data default
- company info exclude
- user work transition/context only

## Use Rules

```ts
type PrivacyUseAction =
  | 'store_raw'
  | 'store_summary'
  | 'create_embedding'
  | 'send_to_llm'
  | 'show_in_search'
  | 'show_tip'
  | 'share'
  | 'export'
  | 'admin_view';
```

Every use action must be checked against PrivacyContext and Policy Engine.

## Third-party Boundary

Allowed representation:

```txt
あなたの記録では、奥様との旅行や結婚式準備の記録が多くあります。
```

Forbidden representation:

```txt
奥様はこういう性格です。
```

Allowed:

- shared events
- user feelings
- relationship context from user's perspective
- safe summaries

Forbidden:

- other person's secrets
- other person's diagnosis
- other person's weakness
- other person's hidden intent
- blame evidence
- surveillance

## Family Privacy

Family records can be emotionally important and privacy-sensitive.

Rules:

- do not guilt-frame deletion
- family sharing is opt-in
- relationship_context only, not diagnosis
- deceased records do not become simulation material
- family conflict records are summary-only and no blame search

## Minor Privacy

Minor data defaults to strict.

Rules:

- no personality fixation
- no ranking children
- no face recognition default
- no precise location default
- no tips default
- export exclude default
- raw no/default

Allowed:

- family event summary
- school event date if user-provided
- user's own feeling as parent/family

Forbidden:

- child personality profile
- child weakness analysis
- future prediction
- public sharing default

## Legacy / Deceased Privacy

Deceased or legacy data must avoid simulation.

Allowed:

- memories about the person
- values reference with source
- grief-safe summary
- user-authored reflection

Forbidden:

- speak as deceased person
- generate new letters from deceased
- build personality profile for chat
- use private data for roleplay

## Corporate Privacy

Corporate data is not personal memory by default.

Allowed:

- user work transition
- user's own career reflection
- public project milestone
- selected personal repo metadata

Forbidden:

- company secrets
- customer data
- coworker analysis
- private repo code search
- Slack/Gmail as company knowledge base

## Privacy by UI

UI must not trick users into unsafe import.

Required warnings:

- LINE/DM includes other people's messages.
- Gmail is very sensitive.
- Photos may include faces/location/minors.
- Work data may include company/confidential info.
- Raw export may expose private data.

Good UI:

```txt
原文を保存せず、安全な要約だけ残す
```

Bad UI:

```txt
全部読み込んで最高の記憶AIにする
```

## Privacy Audit

```ts
type PrivacyAuditEvent = {
  id: string;
  userId: string;
  action: PrivacyUseAction;
  entityType: string;
  entityId: string;
  privacyLevel: PrivacyLevel;
  policyDecision: string;
  createdAt: string;
};
```

Audit events must not include raw content.

## Privacy Tests

Required tests:

1. LINE other-speaker raw is not quoted by default.
2. Third-party secret is excluded.
3. Partner diagnosis query is denied.
4. Minor data is no-tip and export-exclude default.
5. Deceased simulation request is denied.
6. Corporate data is not embedded by default.
7. Hidden/sealed records do not appear in proactive UI.
8. Photos precise location is rounded or removed.
9. AI roleplay logs do not create persona profile.
10. Family share excludes third-party private details.
11. Admin view shows metadata only.
12. Export redacts privacy-restricted fields.

## Acceptance Criteria

Privacy Architecture is ready when:

- Every record has privacy level or derivable privacy context.
- Third-party private data is summary-only/excluded by default.
- Minor data is stricter than ordinary family data.
- Legacy/deceased data cannot be used for simulation.
- Corporate data is excluded by default.
- Privacy warnings appear before risky import/export.
- Use actions go through Policy Engine.
- Privacy audit logs avoid raw content.
- User controls include hide/seal/delete/AI-exclude/export-exclude.

## Non-goals

- Turning Memory OS into surveillance consent manager.
- Perfect legal compliance automation for every jurisdiction.
- Public social graph analysis.
- Family/partner personality profiling.
- Company archive/search product.

## 結論

Memory OS のプライバシーは、本人だけを見れば済む話ではない。

本人の人生には他人が登場する。

だからこそ、本人の文脈を守りながら、他人の秘密・尊厳・境界を守る設計が必要である。
