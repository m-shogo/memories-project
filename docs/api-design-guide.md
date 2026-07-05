# API Design Guide

## 目的

API Design Guide は、Memory OS のAPIを一貫性・安全性・互換性・運用性のある形にするためのルールである。

ここでいうAPIはREST/GraphQLの好み以前に、外部境界としての設計を指す。

## 最上位原則

### 1. Policy-aware API

危険な操作はAPI層でPolicy/ AuthZ / Costを必ず通す。

### 2. Explicit over magic

import, export, delete, LLM, embedding は暗黙に実行しない。

### 3. Idempotent where retryable

再試行される操作はidempotency keyを持つ。

### 4. Safe errors

エラーにraw textやsecretを含めない。

### 5. Versioned boundaries

Public APIはversionを持つ。

## Resource Naming

Recommended MVP REST-like resources:

```txt
/memories
/source-refs
/import-jobs
/export-jobs
/policy-decisions
/deletion-tombstones
/search
```

Use nouns for resources and commands for workflows when necessary.

Examples:

```txt
POST /import-jobs/inspect
POST /import-jobs/{id}/plan
POST /import-jobs/{id}/extract
POST /memories/{id}/hide
POST /memories/{id}/seal
POST /memories/{id}/delete
POST /memories/{id}/delete-raw
POST /export-jobs
```

## API Versioning

MVP internal can be unversioned, but public boundary should use:

```txt
/api/v1/...
```

or header:

```txt
Memory-OS-Version: 1
```

## Request Metadata

Every mutation should accept/request:

```ts
type RequestMetadata = {
  requestId: string;
  idempotencyKey?: string;
  actor: ActorType;
  requestedAt: string;
};
```

## Idempotency

Required for:

- create memory
- create import job
- extract import job
- delete memory
- delete raw
- create export job
- expire/revoke export job

Idempotency result:

- same key + same payload => same result
- same key + different payload => conflict

## Error Shape

```ts
type ApiError = {
  code: string;
  message: string;
  safeUserMessage: string;
  requestId: string;
  details?: Record<string, unknown>;
};
```

Forbidden in errors:

- raw memory text
- secret value
- raw third-party message
- full prompt
- full filename if sensitive

## Stable Error Codes

Examples:

```txt
POLICY_DENIED
AUTHZ_DENIED
REAUTH_REQUIRED
SOURCE_UNKNOWN_INSPECT_ONLY
COST_CONFIRMATION_REQUIRED
SECRET_DETECTED
CORPORATE_DATA_BLOCKED
THIRD_PARTY_RAW_BLOCKED
MINOR_DATA_BLOCKED
MEMORY_SEALED
MEMORY_PENDING_DELETION
EXPORT_EXPIRED
IDEMPOTENCY_CONFLICT
```

## Pagination

Use cursor pagination for large lists.

```ts
type Page<T> = {
  items: T[];
  nextCursor?: string;
};
```

Avoid offset pagination for large memory/import lists.

## Long-running Jobs

Import/export can be jobs.

```ts
type JobStatus = 'requested' | 'running' | 'completed' | 'partial' | 'blocked' | 'failed' | 'expired';
```

Client polls:

```txt
GET /import-jobs/{id}
GET /export-jobs/{id}
```

## Safe API Flows

### Create Memory

```txt
POST /memories
-> AuthZ owner
-> Policy create_memory
-> SourceRef required
-> create Memory/Evidence
```

### Import

```txt
POST /import-jobs/inspect
POST /import-jobs/{id}/plan
POST /import-jobs/{id}/extract
```

No extract before inspect.

### Export

```txt
POST /export-jobs
-> AuthZ
-> Policy per entity
-> redaction
-> package
-> short-lived URL
```

### Delete

```txt
POST /memories/{id}/delete
-> pending_deletion immediately
-> tombstone
-> async propagation
```

## Response Safety

Memory detail response should include:

- summary/body safe
- SourceRef summary
- occurredAt/importedAt
- lifecycle
- visibility
- policy notices

Should not include:

- raw by default
- third-party raw
- secret values
- hidden/sealed content without explicit unlock

## API Review Checklist

1. Does it check AuthZ?
2. Does it check Policy?
3. Does it need Cost estimate?
4. Does it need idempotency?
5. Can it return raw accidentally?
6. Does it respect lifecycle?
7. Does it need audit log?
8. Does it need versioning?
9. Does error leak content?
10. Does it enable a never-build use case?

## Acceptance Criteria

- stable error codes defined
- no extract-before-inspect API
- delete is idempotent
- export is job-based and expires
- errors are safe
- pagination strategy exists
- API review checklist exists

## 結論

API設計は、UIやDBより先に安全境界を作る場所である。

Memory OSでは、便利な一発APIより、Policy・削除・Export・Costを明示したAPIを優先する。
