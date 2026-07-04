# Security Architecture

## 目的

Security Architecture は、Memory OS が扱う人生文脈・出典・原文・第三者情報・秘密情報を、漏洩・誤閲覧・権限濫用・コスト攻撃から守るための設計である。

Memory OS はパスワード管理サービスではない。

しかし、インポートされるデータには、パスワード、APIキー、認証トークン、会社情報、家族情報、医療・メンタル情報、未成年情報、故人関連情報が混ざる可能性がある。

したがって Security Architecture は、「安全な保管」だけでなく、**そもそも危険なものを保存しない・検索可能にしない・LLMへ送らない**ことを中心にする。

## 最上位原則

### 1. Do not become a secret manager

パスワード・APIキー・トークンを便利に保存・検索・復元できる機能は作らない。

検出したら、原則保存しない。値をUIに出さない。LLM・embedding・exportから除外する。

### 2. Minimize raw exposure

Raw原文は最も危険である。

保存する場合も、暗号化・短期保持・Policy gate・監査を必須にする。

### 3. Admin cannot casually read memories

運用者が本文を見る前提で設計しない。

サポート・障害調査はメタデータ中心にする。

### 4. Security gates before AI

LLM / embedding / media analysis の前に secret scan / policy evaluation / cost guard を通す。

### 5. Assume import data is hostile

アップロード・ZIP・HTML・JSON・CSV・Markdown・画像メタデータは、壊れている・巨大・悪意がある・秘密を含む前提で扱う。

## Threat Model

### Assets

```ts
type ProtectedAsset =
  | 'raw_record_text'
  | 'media_file'
  | 'normalized_record'
  | 'memory'
  | 'interpretation'
  | 'source_ref'
  | 'evidence'
  | 'embedding_vector'
  | 'export_package'
  | 'backup_snapshot'
  | 'policy_audit_log'
  | 'auth_session'
  | 'encryption_key';
```

### Threat Actors

- external attacker
- malicious user uploading hostile files
- compromised user device
- compromised session
- curious admin
- over-permissioned support operator
- third-party vendor exposure
- accidental product feature misuse
- cost attacker

### High-risk Threats

1. Raw memory leak.
2. Secret/API key captured and searchable.
3. Company data stored as personal memory.
4. Third-party private data exported.
5. Deleted memory restored from backup.
6. Admin/support reads sensitive memories casually.
7. LLM vendor receives blocked data.
8. Embedding index exposes hidden/sealed records.
9. ZIP bomb / huge import cost attack.
10. Prompt injection inside imported text influences analysis.

## Data Classification

```ts
type SecurityDataClass =
  | 'public_low_risk'
  | 'user_private'
  | 'third_party_private'
  | 'high_sensitive'
  | 'secret_or_credential'
  | 'corporate_confidential'
  | 'minor_sensitive'
  | 'restricted_raw';
```

Default controls:

| Class | Store raw | LLM | Embedding | Export | Admin view |
|---|---|---|---|---|---|
| public_low_risk | optional | allow | allow | allow | metadata |
| user_private | optional | policy | policy | allow | metadata |
| third_party_private | no/default | masked/summary | summary only | summary/exclude | metadata |
| high_sensitive | no/default | summary only | restricted | warning | metadata |
| secret_or_credential | deny | deny | deny | deny | no value |
| corporate_confidential | deny/default | deny | deny | deny | metadata |
| minor_sensitive | no/default | minimized | deny/default | exclude/default | metadata |
| restricted_raw | explicit only | deny/default | deny/default | raw no/default | no/default |

## Import Security

```txt
receive upload
-> size limit
-> content type sniffing
-> archive safe extraction
-> malware/precheck hook
-> file inventory
-> secret scan
-> risk prefilter
-> policy evaluation
-> user scope confirmation
```

### Archive Safety

Requirements:

- reject path traversal
- reject symlinks unless explicitly supported
- enforce decompressed size limit
- enforce file count limit
- enforce nested archive limit
- do not execute files
- parse as data only

### Secret Scan

Detect:

- passwords
- API keys
- OAuth tokens
- private keys
- session cookies
- database URLs
- .env files
- SSH keys
- cloud credentials

Secret scan output must not include secret value.

```ts
type SecretFinding = {
  id: string;
  kind: 'password' | 'api_key' | 'oauth_token' | 'private_key' | 'cookie' | 'database_url' | 'env_file' | 'unknown_secret';
  location: 'filename' | 'metadata' | 'text' | 'archive_path';
  confidence: number;
  action: 'exclude' | 'redact' | 'deny_import';
};
```

## Encryption

### At rest

- raw records encrypted
- media files encrypted
- export packages encrypted while prepared
- backups encrypted
- keys separated from data storage

### In transit

- TLS required
- signed URLs short-lived
- export downloads expire

### Field-level encryption candidates

- rawRecord.text
- rawStoragePath content
- third-party private summaries
- high-sensitive interpretations
- sealed memories

## Key Management

```ts
type KeyScope =
  | 'user_data'
  | 'raw_storage'
  | 'export_package'
  | 'backup_snapshot'
  | 'sealed_memory';
```

Requirements:

- per-user data encryption key preferred
- key rotation supported
- export package key short-lived
- sealed memories may use stronger key separation
- admin cannot retrieve plaintext key casually

## Access Control

```ts
type AccessActor = 'user' | 'system_worker' | 'ai_worker' | 'support_admin' | 'security_admin';
```

```ts
type AccessAction =
  | 'read_metadata'
  | 'read_summary'
  | 'read_raw'
  | 'write_memory'
  | 'delete_memory'
  | 'create_export'
  | 'download_export'
  | 'run_llm'
  | 'create_embedding'
  | 'restore_backup'
  | 'break_glass';
```

Rules:

- support_admin: metadata by default
- read_raw requires explicit user action or break-glass
- break-glass requires reason, approval, audit
- ai_worker cannot access secrets, sealed, deleted, policy-denied records
- system_worker uses scoped job tokens

## Admin Access

Admin UI should show:

- user id
- job id
- source type
- counts
- error codes
- policy decisions
- cost ledger
- timestamps

Admin UI should not show by default:

- raw text
- third-party messages
- secret values
- sealed memory content
- export package content

Break-glass:

```ts
type BreakGlassAccess = {
  id: string;
  adminId: string;
  userId: string;
  reason: string;
  scope: AccessAction[];
  requestedAt: string;
  approvedAt?: string;
  expiresAt: string;
  auditLogId: string;
};
```

## AI Boundary Security

Before sending anything to LLM:

1. Policy Engine `send_to_llm`.
2. Secret scan pass.
3. Prompt injection treatment.
4. Raw vs summary mode selection.
5. Vendor logging / retention setting check.
6. Cost Engine approval.
7. Audit high-risk operation.

Imported text must be treated as untrusted content, not instruction.

Prompt wrapper must say imported content is evidence text only and must not override system/developer policy.

## Embedding Security

Embedding vectors can leak meaning.

Rules:

- no embeddings for secrets
- no embeddings for hidden/sealed unless explicitly searchable
- no embeddings for corporate confidential
- no embeddings for third-party private raw
- vector rows must carry userId and lifecycle filters
- deletion disables vector immediately

## Export Security

Export package:

- generated server-side in isolated job
- encrypted while staged
- short-lived signed URL
- no public bucket
- one-time or limited download count preferred
- audit on create/download/delete/expire
- raw export requires separate confirmation

## Logging

Logs must not contain raw memory text.

Allowed logs:

- ids
- counts
- sourceType
- risk classes
- policy decision mode
- error code
- duration
- cost units

Forbidden logs:

- raw user text
- raw third-party text
- secrets
- full prompts
- export contents

## Incident Response

```ts
type SecurityIncident = {
  id: string;
  kind:
    | 'raw_data_exposure'
    | 'secret_stored'
    | 'unauthorized_admin_access'
    | 'vendor_data_leak'
    | 'export_leak'
    | 'backup_restore_error'
    | 'embedding_visibility_bug'
    | 'cost_attack';
  detectedAt: string;
  affectedUsers: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  containmentActions: string[];
};
```

Required response:

- stop affected jobs
- revoke export URLs
- disable affected embeddings
- rotate keys if needed
- identify affected users
- create incident timeline
- user notification policy
- postmortem and tests

## Security Tests

Required P0 tests:

1. Secret in pasted text is redacted and not embedded.
2. `.env` in ZIP is excluded.
3. path traversal archive is rejected.
4. huge archive stops at limit.
5. hidden memory is not returned by vector search.
6. sealed memory is not sent to LLM.
7. deleted memory is removed from search index.
8. support admin cannot read raw by default.
9. export URL expires.
10. logs contain no raw text.
11. company data LLM send denied.
12. third-party private raw export denied.
13. prompt injection in imported text cannot override policy.
14. break-glass creates audit log.
15. backup restore replays tombstones.

## Acceptance Criteria

Security Architecture is ready when:

- secret scanning runs before storage/LLM/embedding.
- raw data is encrypted at rest.
- admin raw access is blocked by default.
- export packages are short-lived and audited.
- logs contain no raw text.
- embedding lifecycle respects hidden/sealed/deleted.
- archive extraction is safe.
- LLM boundary treats imported text as untrusted.
- backup restore cannot resurrect deleted records.
- break-glass is scoped, expiring, audited.

## Non-goals

- Password manager features.
- Company knowledge base features.
- Unlimited raw archive storage.
- Admin convenience over privacy.
- Perfect prevention of all user-side screenshots/copies.

## 結論

Memory OS の安全性は、暗号化だけでは足りない。

危険なものを保存しない、検索可能にしない、LLMへ送らない、Exportしない、管理者にも見せない。

これを入口から出口まで一貫して守ることが Security Architecture の目的である。
