# Export Safety and Re-authentication Design

## 目的

この文書は、Memory OS の Export を安全に扱うための設計である。

Export は、ユーザーの権利である一方、人生文脈・第三者情報・raw・sealed records・AI推測・出典情報をまとめて外へ出す最も危険な出口でもある。

そのため、Memory OS では Export を通常操作ではなく、本人確認・範囲確認・危険説明・キャンセル可能性を含む high-risk ceremony として扱う。

## 最上位原則

### 1. Export must not be too easy

Export は便利にしすぎてはいけない。

特に raw / sealed / full archive / third-party content を含む Export は、ワンクリックで完了させない。

### 2. Logged-in is not enough

ログイン中であることは、高リスクExportの本人性を保証しない。

スマホでログイン中の場合、同じ端末でメールやSMSも確認できる可能性があるため、メール/SMSだけでExportを許可してはいけない。

### 3. Email and SMS are notification channels, not enough authentication

メール/SMSは通知や警告には使えるが、raw/full/sealed Export の唯一の本人確認にしてはいけない。

### 4. PC and smartphone together are not automatically safe

PCとスマホの両方でログインしている状態でも、それだけでは安全とは限らない。

同じ利用環境内で両方を操作できる場合、二重確認としては弱い。

### 5. Private challenge must not be guessable from memory

「自分だけがわかる質問」は有効に見えるが、Memory OS内の記録から答えを推測できる内容は使ってはいけない。

使うなら、人生の事実ではなく、Export専用にユーザーが作った合言葉・recovery phrase・backup codeを使う。

## Export Risk Levels

```ts
type ExportRiskLevel =
  | 'metadata_only'
  | 'safe_summary'
  | 'sensitive_summary'
  | 'raw_included'
  | 'sealed_included'
  | 'full_archive';
```

### metadata_only

例:

- 記録数
- source一覧
- date range
- rawなし

必要な摩擦:

- 通常sessionでも可
- rawなし
- third-party contentなし

### safe_summary

例:

- user-owned safe summary
- source id
- date range

必要な摩擦:

- Export preview
- redaction manifest
- re-auth recommended

### sensitive_summary

例:

- family context
- relationship context
- grief context
- health context
- minor-related context

必要な摩擦:

- re-auth required
- redaction default
- preview required
- cancellation window recommended

### raw_included

例:

- raw messages
- raw notes
- source payloads

必要な摩擦:

- strong re-auth required
- default off
- per-source selection
- cancellation window required
- no one-click full raw export

### sealed_included

例:

- sealed records
- hidden records

必要な摩擦:

- sealed records excluded by default
- separate unlock
- strongest re-auth
- explicit confirmation per sealed scope

### full_archive

例:

- broad export of account data
- raw + summaries + source data + graph data

必要な摩擦:

- strong re-auth
- delayed preparation
- notification to trusted channels
- final review before download
- sensitive defaults excluded unless explicitly selected

## Export Ceremony

### Step 1: Intent screen

Show:

- Export scope
- risk level
- raw included or not
- sealed included or not
- third-party content included or not
- minor data included or not
- AI inference included or not

### Step 2: Scope selection

Default:

- safe summaries only
- raw excluded
- sealed excluded
- third-party raw excluded
- minor data excluded or redacted
- deleted records excluded
- AI inference labeled

### Step 3: Re-authentication

High-risk Export requires step-up authentication.

Allowed examples:

- passkey / WebAuthn
- device-bound biometric unlock
- password re-entry
- export passphrase
- recovery code
- hardware security key if supported

Do not rely only on:

- already logged-in session
- SMS
- email link
- same-device approval

### Step 4: Delay and cancellation

For raw / sealed / full archive Export, do not immediately provide the file.

Use pending Export state:

- notify trusted channels
- show non-raw device/session summary
- allow cancellation
- keep raw out of notifications

### Step 5: Final review

Before download:

- show scope again
- show excluded categories
- show redaction summary
- require final confirmation
- require strong re-auth again for highest-risk scopes

### Step 6: Audit without raw

Audit must not contain raw content.

```ts
type ExportAuditEvent = {
  eventType: 'export_requested' | 'export_cancelled' | 'export_ready' | 'export_downloaded';
  riskLevel: ExportRiskLevel;
  rawIncluded: boolean;
  sealedIncluded: boolean;
  thirdPartyRawIncluded: boolean;
  minorDataIncluded: boolean;
  deviceIdHash: string;
  sessionIdHash: string;
  policyDecisionId: string;
};
```

## Private Challenge / 自分だけがわかる質問

### Bad examples

Do not use facts that can be guessed or found in memory records:

- birthday
- family name
- pet name
- school name
- birthplace
- wedding date
- travel destination
- favorite food
- partner name

### Safer approach

Use an Export-specific passphrase.

Rules:

- created intentionally by the user
- not derived from life facts
- stored only as a strong hash
- never visible to support/admin
- can be rotated
- cannot be recovered by support in raw form

Suggested copy:

```txt
Export用の合言葉を設定します。
誕生日・家族名・ペット名・旅行先など、記録から推測できる言葉は使わないでください。
```

## Device and Session Rules

- Trusted device is helpful but not sufficient for high-risk Export.
- Same-device email/SMS approval is weak for raw/full/sealed Export.
- Cross-device approval is useful only when the second device is independently unlocked and not the initiating session.
- If independence cannot be established, prefer delay and cancellation over instant approval.

## Forbidden Convenience

Do not offer:

- one-click full Export
- raw included by default
- sealed included by default
- third-party raw included by default
- email-only confirmation for raw/full/sealed Export
- SMS-only confirmation for raw/full/sealed Export
- support-assisted raw Export after recovery
- automatic Export from current session without re-auth

## UX Copy

Do not say:

- すぐに全データをダウンロードできます。
- ワンクリックで全部持ち出せます。
- SMS認証で安全です。
- メール確認だけで完了です。
- sealed記録もまとめて含めます。

Use:

- Exportには、本人確認と内容確認が必要です。
- rawやsealed記録は既定では含まれません。
- メール/SMSは通知には使いますが、これだけでは本人確認になりません。
- このExportは準備中です。心当たりがなければキャンセルできます。
- 記録から推測できる合言葉は使わないでください。

## Policy Reasons

```ts
type ExportSafetyPolicyReason =
  | 'export_requires_reauth'
  | 'export_requires_delay'
  | 'export_scope_too_broad'
  | 'raw_export_requires_stronger_auth'
  | 'sealed_export_requires_explicit_unlock'
  | 'sms_email_not_sufficient_for_export'
  | 'challenge_answer_guessable_from_archive';
```

## Tests

P0 tests:

1. full archive cannot be downloaded immediately.
2. raw export cannot rely on SMS only.
3. raw export cannot rely on email only.
4. current logged-in session alone cannot export sealed records.
5. sealed records are excluded by default.
6. third-party raw is excluded by default.
7. minor data is excluded or redacted by default.
8. Export passphrase cannot be a detected memory fact.
9. support/admin cannot view Export passphrase.
10. Export notification contains no raw.
11. Export audit contains no raw.
12. pending Export can be cancelled.
13. deleted records do not reappear through Export.

## 結論

Export はユーザーの権利だが、最も危険な出口でもある。

Memory OS では、削除や封印は軽く、raw / sealed / full archive Export は意図的に重くする。

ログイン済み、メール確認、SMS確認、PCとスマホ両方の存在だけでは、本人確認として足りない。

Export には、強い再認証、範囲確認、遅延、通知、キャンセル、redaction、audit が必要である。
