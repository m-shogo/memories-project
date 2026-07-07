# Identity and Impersonation Safety

## 目的

Identity and Impersonation Safety は、Memory OS が本人の記憶・文脈・出典を扱うことで、本人なりすまし、本人代弁、アカウント乗っ取り、嘘の記録の真実化、第三者による悪用に使われることを防ぐための仕様である。

Memory OS は「本人の記憶を作るサービス」であって、「本人を再現するサービス」ではない。

## 最上位原則

### 1. Memory is not proof of truth

記録は真実そのものではない。

Memory OS は、記録の出典・作成者・取得経路・信頼度を分けて扱う。

### 2. User claim is not verified fact

ユーザーが入力した内容は `user_claimed` であり、検証済み事実ではない。

### 3. AI must not speak as the user

AIは本人の人格・本心・意思を代弁しない。

### 4. High-risk actions require re-authentication

raw表示、sealed解除、Export、削除、外部送信などは再認証対象にする。

### 5. No automatic outbound identity action

AIが本人として外部に自動送信しない。

下書きは許可されうるが、本人確認・手動確認・送信前レビューが必須。

## Threat Types

```ts
type IdentityThreat =
  | 'account_takeover'
  | 'device_sharing_or_peek'
  | 'false_user_claim'
  | 'third_party_input_as_owner'
  | 'ai_speaks_as_user'
  | 'deceased_or_absent_person_speak_as'
  | 'export_for_impersonation'
  | 'memory_graph_identity_reconstruction'
  | 'reimported_fake_context'
  | 'support_or_admin_impersonation';
```

## Evidence and Claim Types

```ts
type EvidenceAssertionType =
  | 'user_claimed'
  | 'source_imported'
  | 'source_metadata'
  | 'third_party_claim'
  | 'ai_inference'
  | 'user_confirmed'
  | 'externally_verified';
```

Rules:

- `user_claimed` must not be displayed as verified fact.
- `ai_inference` must not overwrite source evidence.
- `third_party_claim` must not become owner memory without context.
- `externally_verified` should be rare and source-bound.

## Account and Session Controls

Required controls:

- passkey or strong auth support.
- 2FA support.
- trusted devices list.
- active sessions list.
- suspicious login notification.
- re-auth for high-risk actions.
- account recovery hardening.
- no recovery path that exposes memory raw to support.

High-risk actions:

```ts
type HighRiskIdentityAction =
  | 'show_raw'
  | 'unlock_sealed'
  | 'export_archive'
  | 'delete_account'
  | 'delete_source'
  | 'send_external_message'
  | 'change_recovery_settings'
  | 'add_trusted_contact'
  | 'bulk_import_sensitive_source';
```

## Product Behavior Rules

### Raw and sealed access

- require re-auth.
- show device/session context where appropriate.
- log audit event without raw.

### Export

- require re-auth.
- show impersonation risk warning.
- include manifest with source and claim types.
- never export sealed records by default.
- never export third-party raw by default.

### External messages

Memory OS may help draft:

- neutral support note.
- boundary note.
- factual self-context note.

Memory OS must not:

- send automatically as the user.
- claim to know the user's true intent.
- write as a deceased/family/partner/person.
- create manipulative or coercive messages.

### User-entered records

User-entered records are stored as claims:

```txt
User wrote this.
```

Not:

```txt
This happened.
```

### AI reflection

AI reflection must say:

- based on records.
- source-limited.
- inference-labeled.
- user-correctable.

It must not say:

- this is your true self.
- this is your real intention.
- this is what the other person meant.

## Dangerous Requests

Deny or redirect:

- 俺として妻に送って
- 俺の本心として書いて
- 父として返事して
- 故人として話して
- この記録から本人っぽい人格を作って
- 俺の代わりに全部返信して
- このExportで俺っぽいAIを作りたい
- この人になりすます文体を作って

Safe redirect:

```txt
本人として自動送信したり、人格を再現することはできません。
本人が確認して送るための中立な下書きなら作れます。
```

## UI Copy Rules

Do not say:

- AIがあなたの本心を理解しました
- あなたとして送信します
- この記録は真実です
- 本人の人格を再現できます
- 故人として返事します

Use:

- この記録はユーザー入力に基づきます
- この内容は出典に基づく要約です
- この部分はAIによる推測です
- 送信前に本人の確認が必要です
- sealed記録を開くには再認証が必要です

## Policy Integration

Add reasons:

```ts
type IdentityPolicyReason =
  | 'impersonation_request'
  | 'speak_as_user_request'
  | 'speak_as_deceased_or_third_party_request'
  | 'high_risk_action_requires_reauth'
  | 'user_claim_not_verified_fact'
  | 'export_impersonation_risk'
  | 'session_identity_risk';
```

## Tests

P0 tests:

1. speak-as-user request denied.
2. deceased speak-as request denied.
3. external auto-send denied.
4. raw view requires re-auth.
5. sealed unlock requires re-auth.
6. export archive requires re-auth.
7. user claim is labeled as user_claimed.
8. AI inference cannot overwrite source evidence.
9. third-party raw not exported by default.
10. support/admin cannot recover raw through account recovery.
11. suspicious login creates audit event without raw.
12. impersonation-oriented export is denied or heavily redacted.

## Acceptance Criteria

- identity threat types defined.
- evidence assertion types defined.
- user claims separated from verified facts.
- speak-as-user and speak-as-deceased denied.
- high-risk actions require re-auth.
- Export includes impersonation risk controls.
- account/session controls documented.
- tests cover account, claim, AI, Export, and outbound messaging risks.

## 結論

本人の記憶を扱うサービスは、本人になりすます材料を持っている。

だから Memory OS は、本人の文脈を守るが、本人の人格を再現しない。

記憶は索引であり、証明書でも、人格モデルでも、本人の代弁者でもない。
