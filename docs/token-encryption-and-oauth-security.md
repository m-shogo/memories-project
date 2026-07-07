# Token Encryption and OAuth Security Spec

## 目的

この文書は、Memory OS が Spotify、Apple Music、AniList、Last.fm、Google、X、Steam などのAPI connectorを実装する前に、OAuth token / API key / service credentials / HMAC key / export keyを安全に扱うための仕様である。

Import API connectorは便利だが、tokenが漏れるとユーザーの外部アカウントへの継続アクセス権が漏れる。

したがって、API connectorは Import Preview / Policy Evaluation / token encryption plan が存在するまで実装しない。

## 対象

```ts
type SecretMaterialKind =
  | 'oauth_access_token'
  | 'oauth_refresh_token'
  | 'api_key'
  | 'developer_token'
  | 'webhook_secret'
  | 'dedupe_hmac_key'
  | 'tombstone_hmac_key'
  | 'raw_object_encryption_key'
  | 'export_package_key';
```

## 最上位原則

### 1. Token material is never stored in plaintext

DBにtoken平文を保存しない。

### 2. Key material is not stored in the application database

暗号鍵/HMAC鍵の実体はDBに置かない。

DBに置くのはkey_referenceだけ。

### 3. Least privilege scopes

OAuth scopeは必要最小限。

MVPはread-onlyを基本にする。

### 4. Token access is audited without token contents

tokenを使ったsync/API callはauditするが、token値・API response rawはlogに出さない。

### 5. Revocation is a product feature

ユーザーはいつでもconnectorを解除できる。

解除後:

- future sync停止
- token削除/crypto-erasure
- existing imported recordsはユーザー選択で残す/削除/封印できる

## Key Reference Model

```sql
create table key_reference (
  id uuid primary key,
  purpose text not null,
  key_version text not null,
  kms_key_id text not null,
  status text not null,
  created_at timestamptz not null default now(),
  retired_at timestamptz
);
```

Rules:

- `kms_key_id` is a reference, not key material.
- `status` examples: active, decrypt_only, retired, revoked.
- One key may be purpose-specific or tenant/user scoped depending cost/security.

## Credential Tables

### oauth_connection

```sql
create table oauth_connection (
  id uuid primary key,
  user_id uuid not null references app_user(id),
  source_account_ref_id uuid references source_account_ref(id),
  provider text not null,
  provider_account_hash bytea,
  display_label text,
  status text not null default 'active',
  granted_scopes text[] not null default '{}',
  requested_scopes text[] not null default '{}',
  token_encryption_key_ref uuid not null references key_reference(id),
  token_ciphertext bytea not null,
  token_nonce bytea not null,
  token_tag bytea,
  refresh_token_ciphertext bytea,
  refresh_token_nonce bytea,
  refresh_token_tag bytea,
  expires_at timestamptz,
  last_used_at timestamptz,
  last_refresh_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index idx_oauth_connection_user_provider
  on oauth_connection (user_id, provider, status);
```

### api_credential_reference

For service keys / developer tokens that are app-level.

```sql
create table api_credential_reference (
  id uuid primary key,
  provider text not null,
  credential_kind text not null,
  key_reference_id uuid not null references key_reference(id),
  ciphertext bytea not null,
  nonce bytea not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  retired_at timestamptz
);
```

## Encryption Requirements

Minimum:

- AEAD encryption such as AES-GCM or XChaCha20-Poly1305.
- authenticated associated data includes user_id, provider, connection_id, key_version.
- random nonce per encryption.
- key material from KMS or equivalent secure secret manager.
- no decrypted token in logs or errors.

Associated data example:

```txt
MemoryOS/oauth_connection/{user_id}/{provider}/{connection_id}/{key_version}
```

## Token Lifecycle

```ts
type OAuthConnectionStatus =
  | 'active'
  | 'expired'
  | 'revoked_by_user'
  | 'revoked_by_provider'
  | 'error_requires_reconnect'
  | 'deleted';
```

### Connect

1. user selects provider.
2. app creates OAuth state with CSRF protection.
3. provider redirects back.
4. app exchanges code server-side.
5. token encrypted immediately.
6. source_account_ref created/linked.
7. Import Preview can start.

### Use

1. background job loads oauth_connection metadata.
2. decrypt token in memory only.
3. call provider API.
4. discard token from memory.
5. audit counts/status only.

### Refresh

1. decrypt refresh token.
2. request new access token.
3. encrypt replacement.
4. update last_refresh_at.
5. on failure mark error_requires_reconnect.

### Revoke

1. call provider revocation endpoint if supported.
2. mark revoked_by_user.
3. delete/crypto-erase token ciphertext.
4. stop scheduled sync.
5. audit no raw.

## OAuth Security

Required:

- Authorization Code + PKCE for public/mobile clients.
- server-side code exchange where possible.
- state parameter for CSRF.
- redirect URI exact allowlist.
- no token in URL fragments stored in logs.
- no broad scopes by default.
- refresh token rotation if provider supports.
- suspicious reauth requires user confirmation.

Do not:

- store provider password.
- ask user for service password.
- use login scraping.
- request write scopes for MVP.
- share one user's token with another import job.

## Scope Policy

### Spotify

Allowed MVP scopes:

- user-read-recently-played
- user-library-read
- playlist-read-private
- playlist-read-collaborative
- user-top-read
- user-read-currently-playing

Avoid MVP:

- playlist-modify-private
- playlist-modify-public
- user-modify-playback-state

### AniList

Use read access to lists/progress where possible.

Avoid write/update list scopes in MVP.

### Google / YouTube

Prefer Takeout first.

If API connector later:

- minimal read scopes
- avoid broad Drive/Gmail unless separate high-risk connector design exists

### Apple Music

MusicKit/API research required before production.

Do not promise complete listening history.

### X

Prefer archive/URL/paste first.

API connector requires separate cost/terms/security review.

## Source Account Binding

Every OAuth connection should link to `source_account_ref`.

This prevents:

- mixing main/sub accounts
- confusing shared profiles
- dedupe across wrong account
- wrong revocation target

`provider_account_hash` must be HMAC or otherwise privacy-preserving.

## Scheduled Sync Safety

Scheduled sync must be:

- incremental
- idempotent
- rate-limited
- policy-aware
- stopped after revocation
- stopped after repeated provider errors
- source_account_ref scoped

Do not run full-history import every time.

## Token Access Audit

Audit allowed:

- provider
- connection id
- job id
- status
- item count
- error code class
- latency

Audit forbidden:

- token
- refresh token
- raw response body
- private titles
- private URLs

## Error Handling

### Expired token

```txt
接続の再確認が必要です。
このサービスの記録は、再接続するまで更新されません。
```

### Provider revoked

```txt
このサービスとの接続が解除されています。
既に取り込んだ記録は、削除するまで残ります。
```

### Scope insufficient

```txt
この範囲の取り込みには追加の許可が必要です。
必要な範囲だけを確認してから接続できます。
```

Do not show raw provider errors if they contain tokens or private data.

## Key Rotation

### Token encryption key rotation

1. create new key_reference active.
2. mark old key decrypt_only.
3. decrypt each token in memory.
4. re-encrypt with new key.
5. verify count.
6. retire old key after validation window.

### HMAC key rotation

Harder than encryption because old hashes cannot be reversed.

Approach:

- keep old key for match/decrypt-equivalent HMAC verification.
- generate new keys when source records are reprocessed.
- store key_version.
- support multiple active verification versions.
- never log source values during re-HMAC.

## Account Deletion

On account deletion:

- revoke provider tokens where possible.
- delete token ciphertext.
- delete source_account_ref or anonymize according to deletion mode.
- handle tombstones according to account deletion policy.
- ensure background jobs cannot run after deletion.

## Tests

P0 tests:

1. token is never stored plaintext.
2. token decrypt requires key_reference.
3. app logs contain no token.
4. OAuth state mismatch fails.
5. redirect URI mismatch fails.
6. revoked connection cannot sync.
7. expired token marks reconnect required.
8. refresh token rotation updates encrypted value.
9. user revocation stops scheduled jobs.
10. wrong user cannot use another user's token.
11. provider_account_hash does not store clear account id.
12. scope escalation requires user confirmation.
13. API connector cannot run before Import Preview path exists.
14. token rotation can re-encrypt without raw log.
15. account deletion deletes/crypto-erases token material.

## Production Readiness Gate

Do not implement API connector until:

- key_reference exists.
- oauth_connection table exists.
- encryption/decryption helper exists.
- audit without raw exists.
- Import Preview exists.
- Policy Evaluation exists.
- source_account_ref exists.
- revocation flow exists.
- token rotation plan exists.

## 結論

API connectorはImport体験を強くするが、tokenが漏れればMemory OSへの信頼は終わる。

そのため、OAuth/API connectorは、暗号化・scope最小化・source_account_ref・revocation・audit・rotation・policy-before-syncが揃うまで実装しない。
