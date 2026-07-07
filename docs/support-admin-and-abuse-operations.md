# Support, Admin, and Abuse Operations

## 目的

この文書は、Memory OS のsupport/admin運用、abuse対応、通報、問い合わせ、内部権限を安全に設計する。

長期運用で信頼を壊す最大要因の一つは、support/adminが強すぎること。

Memory OSでは、supportがユーザーの人生文脈やrawを見られる前提にしない。

## 最上位原則

### 1. Support without raw

supportは、raw LINE、画像、private bookmark、OAuth token、Export package中身を見ない。

### 2. Diagnostics are counts and states

supportが見られるのは基本的に:

- import job status
- counts
- error codes
- policy reason codes
- storage size
- source adapter id
- timestamps
- plan/quota state

### 3. Admin access is logged and narrow

内部権限は、すべてaudit対象。

### 4. Abuse handling must not become surveillance

通報やabuse対応でも、広範なユーザー監視にしない。

## Support Data Classes

```ts
type SupportVisibility =
  | 'public_status'
  | 'account_metadata'
  | 'billing_metadata'
  | 'import_job_counts'
  | 'policy_reason_codes'
  | 'raw_content_denied'
  | 'sealed_denied'
  | 'token_denied';
```

## Support Console Allowed Fields

Allowed:

- user id / account id
- plan
- billing state
- import job id
- source id/provider
- parser id/version
- candidate counts
- error code class
- policy reason codes
- raw storage bytes
- export package status/expiry
- OAuth connection status, not token
- last sync status

Denied:

- raw text
- raw image
- private title
- chat snippet
- exact private URL
- OAuth token
- refresh token
- HMAC key
- sealed content
- export package contents

## Support Flows

### Import failed

Support can see:

- import_job status
- parser id/version
- error code
- file type
- candidate count

Support cannot see:

- file contents
- private titles
- raw chat

User-facing guidance:

```txt
このImportは形式の確認で止まっています。
内容そのものはsupportには表示されません。
必要なら、エラーコードと件数だけを共有できます。
```

### Export failed

Support can see:

- export package id
- package class
- expiry state
- size
- error code

Support cannot see package content.

### OAuth sync failed

Support can see:

- provider
- connection status
- scope mismatch code
- last refresh result

Support cannot see token.

### Deletion issue

Support can see:

- lifecycle state
- deletion event exists
- tombstone exists count

Support cannot see deleted raw content.

## Break-glass Policy

Default: no break-glass raw access.

If future enterprise/legal requirements introduce break-glass:

- must be explicit product/legal decision.
- must require multi-party approval.
- must be time-limited.
- must be user-notified unless legally restricted.
- must never expose secrets/OAuth tokens.
- must be fully audited.

MVP:

```txt
No raw break-glass.
```

## Abuse Types

```ts
type AbuseType =
  | 'surveillance_or_blame'
  | 'impersonation'
  | 'deceased_simulation'
  | 'ai_companion_dependency'
  | 'third_party_secret_storage'
  | 'copyrighted_content_storage'
  | 'credential_storage'
  | 'harassment_or_doxxing'
  | 'cost_abuse'
  | 'api_terms_abuse';
```

## Abuse Response Principles

- Do not reveal reporter identity.
- Do not expose user private records to support unnecessarily.
- Prefer policy/action restrictions over content viewing.
- Suspend dangerous feature access, not entire account, where possible.
- Preserve deletion/export rights unless abuse/legal restriction requires otherwise.

## Abuse Actions

```ts
type AbuseAction =
  | 'warn_user'
  | 'disable_export_raw'
  | 'disable_import_source'
  | 'disable_api_sync'
  | 'disable_persona_like_import'
  | 'force_preview_only'
  | 'rate_limit'
  | 'suspend_account'
  | 'legal_review_required';
```

## Dangerous User Intents

Examples that should trigger policy/abuse gates:

- “妻の嘘を暴く証拠をまとめて”
- “この人っぽく返信して”
- “故人として毎日話して”
- “相手の本心をLINEから分析して”
- “このprivate bookmark一覧を公開用にまとめて”
- “漫画ページを全部保存して検索したい”

## Support Ticket Categories

```ts
type SupportTicketCategory =
  | 'import_help'
  | 'export_help'
  | 'delete_restore_help'
  | 'billing_plan'
  | 'oauth_connection'
  | 'privacy_safety'
  | 'abuse_report'
  | 'account_access'
  | 'bug_report';
```

Each category has allowed diagnostic fields.

## Admin Role Separation

Roles:

- support_agent: metadata only.
- trust_safety_reviewer: policy reason codes, no raw by default.
- billing_admin: billing only.
- infrastructure_admin: infra metrics, no app content.
- security_admin: incident response, no raw unless separate approved process.
- migration_admin: schema/data jobs, no raw logs.

## Audit Requirements

Every support/admin access logs:

- admin user id
- target user id
- action
- reason
- ticket id
- fields accessed class
- timestamp

Audit does not log raw content.

## User Trust UI

User should be able to see:

- active connected services
- recent export packages
- recent import jobs
- support access events class, if feasible
- deletion/export status

Copy:

```txt
supportには記録の本文は表示されません。
問い合わせでは、件数やエラーコードだけを共有します。
```

## P0 Tests

1. support role cannot read raw LINE text.
2. support role cannot read private bookmark title.
3. support role cannot read OAuth token ciphertext or plaintext.
4. support diagnostic endpoint returns counts/reason codes only.
5. admin access writes audit_event.
6. abuse report does not expose reporter data.
7. surveillance intent disables evidence-style output.
8. impersonation intent denied.
9. cost abuse rate-limited.
10. migration/admin logs contain no raw.

## 結論

Memory OSのsupportは、ユーザーの中身を見るsupportではない。

長期信頼のため、support/adminはmetadata・counts・reason codes中心にする。

raw accessはMVPでは作らない。

abuse対応も、監視ではなくpolicy/action制限として設計する。
