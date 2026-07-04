# Schema v1.1 Proposal

## 目的

Schema v1.1 Proposal は、既存 `docs/memory-schema-v1.md` を壊さず、MVP実装に必要な型・フィールドを additive に追加するための提案である。

この提案は `docs/data-model-delta.md` を具体化する。

## 方針

### 1. Additive first

既存型を破壊しない。v1.1では新規entityとoptional fieldを中心に追加する。

### 2. Safety / Privacy / Lifecycle を実装可能にする

Policy, Export, Search, Delete, Cost, Adapter の境界がコードで表現できるようにする。

### 3. No life ranking fields

重要度・人生価値・人格スコアに見えるフィールドを追加しない。

禁止:

- importanceScore
- lifeScore
- personalityScore
- personRank
- topMemory
- bestMemory
- deceasedPersona

## New Core Types

### AdapterMetadata

```ts
type AdapterMetadata = {
  adapterId: string;
  adapterVersion: string;
  parserName?: string;
  parserVersion?: string;
  extractionMode: 'full' | 'metadata_only' | 'summary_seed' | 'masked' | 'inspect_only';
};
```

Used by:

- SourceRef
- ImportJob
- RawRecord.metadata
- NormalizedRecord.metadata

### ImportScope

```ts
type ImportScope = {
  includeDateRange?: DateRange;
  includeConversationIds?: string[];
  includeFileIds?: string[];
  includeKinds?: RawRecordType[];
  excludeKinds?: RawRecordType[];
  rawStoragePreference: 'none' | 'metadata_only' | 'safe_raw' | 'ask_each_time';
  llmPreference: 'never' | 'safe_summary_only' | 'masked_only' | 'allow_low_risk';
  embeddingPreference: 'never' | 'metadata_only' | 'safe_text_only';
  thirdPartyMode: 'exclude' | 'relationship_summary_only' | 'ask_each_time';
  corporateMode: 'exclude' | 'personal_work_context_only';
};
```

### MemoryLifecycleState

```ts
type MemoryLifecycleState =
  | 'active'
  | 'hidden'
  | 'sealed'
  | 'archived'
  | 'pending_deletion'
  | 'deleted'
  | 'tombstoned';
```

### SurfaceVisibility

```ts
type SurfaceVisibility = {
  search: 'visible' | 'hidden' | 'sealed';
  tips: 'eligible' | 'excluded' | 'requires_opt_in';
  ai: 'eligible' | 'excluded' | 'summary_only' | 'masked_only';
  export: 'eligible' | 'excluded' | 'summary_only';
  share: 'owner_only' | 'limited' | 'excluded';
};
```

### PrivacyContext

```ts
type PrivacyContext = {
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

```ts
type PrivacyLevel =
  | 'public'
  | 'owner_only'
  | 'owner_sensitive'
  | 'third_party_limited'
  | 'restricted'
  | 'sealed';
```

```ts
type ConsentState =
  | 'not_required'
  | 'user_provided'
  | 'third_party_unknown'
  | 'third_party_opt_in'
  | 'guardian_required'
  | 'not_allowed';
```

## New Entities

### PolicyDecisionRecord

```ts
type PolicyDecisionRecord = {
  id: string;
  userId: string;
  action: PolicyAction;
  target: PolicyTarget;
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
  policyVersion: string;
  decidedAt: string;
};
```

Rule: must not include raw text.

### DeletionTombstone

```ts
type DeletionTombstone = {
  id: string;
  userId: string;
  entityType: 'raw_record' | 'normalized_record' | 'memory' | 'source_ref' | 'import_job' | 'source';
  entityId?: string;
  sourceType?: SourceType;
  externalId?: string;
  contentHash?: string;
  importJobId?: string;
  deletedAt: string;
  deletionScope: DeletionScope;
  reason?: 'user_request' | 'policy_violation' | 'retention_expired' | 'account_deletion';
  retainUntil?: string;
};
```

```ts
type DeletionScope =
  | 'memory_only'
  | 'interpretations_only'
  | 'raw_only'
  | 'normalized_only'
  | 'source_import_job'
  | 'entire_source'
  | 'account_all';
```

### CostEstimateRecord

```ts
type CostEstimateRecord = {
  id: string;
  userId: string;
  action: CostedAction;
  sourceType?: SourceType;
  costClass: CostClass;
  estimatedInputBytes: number;
  estimatedRecords: number;
  estimatedTextTokens?: number;
  estimatedEmbeddingWrites?: number;
  hardStops: CostHardStop[];
  requiresUserConfirmation: boolean;
  createdAt: string;
  expiresAt: string;
};
```

```ts
type CostClass = 'free_or_tiny' | 'low' | 'medium' | 'high' | 'requires_credit' | 'blocked';
```

### CostLedgerEntry

```ts
type CostLedgerEntry = {
  id: string;
  userId: string;
  importJobId?: string;
  action: CostedAction;
  estimateId?: string;
  actual: ActualCost;
  sourceType?: SourceType;
  riskClasses: RiskClass[];
  createdAt: string;
};
```

Rule: must not include raw text.

### ExportJob

```ts
type ExportJob = {
  id: string;
  userId: string;
  exportMode: ExportMode;
  status: 'requested' | 'running' | 'completed' | 'failed' | 'expired' | 'deleted';
  filters: ExportFilters;
  manifestPath?: string;
  packagePath?: string;
  createdAt: string;
  expiresAt?: string;
  downloadedAt?: string;
  deletedAt?: string;
};
```

### EmbeddingRecord

```ts
type EmbeddingRecord = {
  id: string;
  userId: string;
  targetType: 'normalized_record' | 'memory' | 'evidence';
  targetId: string;
  model: string;
  vectorRef: string;
  lifecycle: 'active' | 'disabled_by_visibility' | 'pending_delete' | 'deleted';
  createdAt: string;
  deletedAt?: string;
};
```

## Optional Field Additions

### SourceRef additions

```ts
type SourceRefV1_1Additions = {
  adapter?: AdapterMetadata;
  privacy?: PrivacyContext;
};
```

### ImportJob additions

```ts
type ImportJobV1_1Additions = {
  adapter?: AdapterMetadata;
  costEstimateId?: string;
  policyDecisionIds?: string[];
};
```

### RawRecord additions

```ts
type RawRecordV1_1Additions = {
  privacy?: PrivacyContext;
  lifecycle?: MemoryLifecycleState;
  policyDecisionIds?: string[];
};
```

### NormalizedRecord additions

```ts
type NormalizedRecordV1_1Additions = {
  privacy?: PrivacyContext;
  lifecycle?: MemoryLifecycleState;
  policyDecisionIds?: string[];
};
```

### Memory additions

```ts
type MemoryV1_1Additions = {
  surfaceVisibility?: SurfaceVisibility;
  privacy?: PrivacyContext;
  policyDecisionIds?: string[];
};
```

## MVP Database Tables

Minimum tables:

- users
- source_refs
- import_jobs
- raw_records
- normalized_records
- memories
- evidence
- memory_interpretations
- policy_decision_records
- deletion_tombstones
- cost_estimate_records
- cost_ledger_entries
- export_jobs
- embedding_records

## Index Requirements

### Search indexes

- userId + lifecycle
- userId + occurredAt
- userId + sourceType
- userId + memoryKind
- userId + visibility/search

### Deletion indexes

- userId + contentHash
- userId + externalId
- userId + importJobId
- userId + sourceType

### Policy indexes

- userId + action
- userId + target id
- policyVersion

### Cost indexes

- userId + createdAt
- userId + action
- importJobId

## Migration Plan

### Step 1: Add tables

Add new tables without touching existing rows.

### Step 2: Backfill defaults

Existing memories:

- lifecycle: active unless deletedAt exists
- surfaceVisibility.search: visible
- tips: eligible only if low-risk
- ai: eligible/summary_only based on safety
- export: eligible unless high-risk
- share: owner_only

### Step 3: Enforce new writes

New records must include:

- SourceRef
- lifecycle
- privacy or derivable privacy
- policy decision for high-risk actions

### Step 4: Add tests

Run P0 test suites before enabling adapters/export/search.

## Compatibility

v1 readers can ignore v1.1 optional fields.

v1.1 writers must not assume old records have privacy/surfaceVisibility.

## Acceptance Criteria

- All additions are additive.
- No forbidden ranking/personality fields.
- Tombstones can prevent re-import resurrection.
- Policy decisions auditable without raw.
- Cost ledger tracks usage without raw.
- Export jobs can create manifest/redactions.
- Embedding lifecycle can block hidden/sealed/deleted.
- Adapter metadata supports parser versioning.

## 結論

Schema v1.1 は、Memory OS の思想をコードで守るための最小追加である。

AI機能を増やす前に、SourceRef・Policy・Deletion・Export・Cost・Privacy・Lifecycleをデータモデルに固定する。
