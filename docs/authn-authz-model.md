# AuthN / AuthZ Model for Memory OS

## 目的

このドキュメントは、Memory OS の認証（AuthN）と認可（AuthZ）の考え方を定義する。

Memory OS は、個人の人生文脈・第三者情報・未成年情報・故人情報・会社情報・raw記録・Exportを扱う。

そのため、ただログインできればよいのではなく、**誰が、どの記憶に、何の目的で、どの操作をできるか**を明確にする必要がある。

## AuthN と AuthZ の違い

### AuthN: Authentication

```txt
あなたは誰ですか？
```

例:

- メールログイン
- OAuth
- passkey
- session
- 2FA

### AuthZ: Authorization

```txt
あなたはそれをしてよいですか？
```

例:

- このMemoryを読めるか
- rawをExportできるか
- sealedを解除できるか
- adminがmetadataを見られるか

## 最上位原則

### 1. Owner first

記憶の基本ownerはユーザー本人である。

### 2. Sharing is not default

共有はMVP外。将来も opt-in。

### 3. Admin is not owner

管理者はユーザーの記憶の所有者ではない。

### 4. Raw requires stronger authorization

raw本文・rawファイル・sealed memory・export packageは通常のreadより強い権限が必要。

### 5. Policy still applies

AuthZで許可されても、Policyがdenyなら実行できない。

Example:

```txt
User owns the data
but export of third-party raw is denied.
```

## Actors

```ts
type ActorType =
  | 'owner_user'
  | 'system_worker'
  | 'ai_worker'
  | 'support_admin'
  | 'security_admin'
  | 'family_member_future'
  | 'external_importer'
  | 'anonymous';
```

## Resources

```ts
type ResourceType =
  | 'memory'
  | 'raw_record'
  | 'normalized_record'
  | 'source_ref'
  | 'import_job'
  | 'evidence'
  | 'interpretation'
  | 'export_job'
  | 'backup_snapshot'
  | 'policy_decision'
  | 'audit_log'
  | 'admin_case';
```

## Actions

```ts
type AuthzAction =
  | 'read_metadata'
  | 'read_summary'
  | 'read_raw'
  | 'create'
  | 'update'
  | 'hide'
  | 'seal'
  | 'delete'
  | 'delete_raw'
  | 'export'
  | 'share'
  | 'send_to_llm'
  | 'create_embedding'
  | 'admin_read_metadata'
  | 'admin_break_glass_read_raw'
  | 'restore_backup';
```

## AuthZ Decision

```ts
type AuthzDecision = {
  allow: boolean;
  mode: 'allow' | 'deny' | 'require_reauth' | 'require_break_glass' | 'require_owner_confirmation';
  reasons: string[];
  expiresAt?: string;
};
```

AuthZ decision is not PolicyDecision.

Both are required for sensitive actions.

```txt
AuthZ: can this actor do this?
Policy: should this action be allowed for this data/context?
```

## MVP Permission Matrix

| Actor | read summary | read raw | delete | export | admin metadata | break-glass |
|---|---|---|---|---|---|---|
| owner_user | yes | policy+reauth if sensitive | yes | policy | no | no |
| system_worker | scoped | scoped | scoped | scoped | no | no |
| ai_worker | policy only | no/default | no | no | no | no |
| support_admin | no content | no | no | no | yes | no/default |
| security_admin | metadata | require break-glass | no/default | no | yes | yes |
| anonymous | no | no | no | no | no | no |

## Re-authentication

Require re-auth for:

- raw export
- account deletion
- large export
- sealed unlock
- backup download
- changing security settings

MVP may simulate reauth as explicit confirmation if auth system is not implemented yet.

## Break-glass

Break-glass is emergency access by security admin.

```ts
type BreakGlassAccess = {
  id: string;
  adminId: string;
  userId: string;
  reason: string;
  resourceScope: ResourceType[];
  actionScope: AuthzAction[];
  requestedAt: string;
  approvedAt?: string;
  expiresAt: string;
  auditLogId: string;
};
```

Rules:

- never default.
- requires reason.
- time-limited.
- audited.
- preferably approval by another admin.
- user notification policy applies.

## Session Model

```ts
type SessionContext = {
  userId?: string;
  actorType: ActorType;
  sessionId: string;
  authenticatedAt?: string;
  lastReauthAt?: string;
  authStrength: 'anonymous' | 'password' | 'oauth' | 'passkey' | 'mfa';
};
```

## Resource Ownership

```ts
type Ownership = {
  ownerUserId: string;
  createdByActor: ActorType;
  sourceUserId?: string;
};
```

Every Memory, RawRecord, SourceRef, ExportJob must have ownerUserId.

## Future Sharing Model

Sharing is post-MVP.

If added, use scoped grants.

```ts
type ResourceGrant = {
  id: string;
  ownerUserId: string;
  granteeId: string;
  resourceType: ResourceType;
  resourceId: string;
  actions: AuthzAction[];
  expiresAt?: string;
  createdAt: string;
};
```

Default restrictions:

- no raw share default
- no minor share default
- no third-party private share
- no sealed share
- no export by grantee default

## AuthZ + Policy Flow

```txt
request
-> authenticate actor
-> authorize actor/action/resource
-> evaluate policy for data/action/context
-> execute if both allow
-> audit if sensitive
```

AuthZ alone is not enough.

Policy alone is not enough.

## Examples

### Owner searches low-risk memory

```txt
AuthZ: allow read_summary
Policy: allow show_in_search
Result: show
```

### Owner exports third-party raw

```txt
AuthZ: owner can request export
Policy: deny third-party raw export
Result: deny
```

### Support admin investigates failed import

```txt
AuthZ: allow admin_read_metadata
Policy: admin_access metadata_only
Result: counts/errors only, no raw
```

### AI worker summarizes sealed memory

```txt
AuthZ: scoped worker maybe
Policy: deny sealed_by_user send_to_llm
Result: deny
```

## Failure Modes

- AuthZ allows owner to bypass Policy.
- support admin can read raw by default.
- share grant includes raw records accidentally.
- sealed memory unlocked without reauth.
- export package downloadable by stale session.
- ai_worker gets broad read permission.

## Tests

Required tests:

1. anonymous cannot read memory.
2. owner can read own low-risk summary.
3. owner cannot export third-party raw due to Policy.
4. support_admin cannot read raw.
5. security_admin raw requires break-glass.
6. sealed unlock requires reauth.
7. ai_worker cannot read raw default.
8. grantee cannot export shared memory default.
9. authz allow + policy deny results deny.
10. authz deny + policy allow results deny.

## MVP Scope

MVP AuthN/AuthZ can be simple:

- single owner user
- session required
- owner-only resources
- support/admin modeled but not fully implemented
- share disabled
- reauth simulated or basic

But code should not assume:

- all users can read all resources
- owner can bypass policy
- admin is owner

## Acceptance Criteria

- every resource has ownerUserId.
- every sensitive use case checks AuthZ then Policy.
- admin raw access impossible by default.
- share is disabled unless explicit future grant model.
- tests cover AuthZ + Policy interaction.
- no broad ai_worker access.

## 結論

AuthN/AuthZ は、Memory OS を安全に大きくするための土台である。

MVPでは共有機能を作らなくても、owner・admin・system・ai_workerの境界を先に決めておくことで、将来の事故を防げる。
