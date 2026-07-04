# Data Model Delta

## 目的

Data Model Delta は、既存 `docs/memory-schema-v1.md` に対して、Source Adapter SDK / Export Specification / Cost Engine / Search Ranking / Deletion Backup / Security / Privacy / UX を実装するために必要な型・フィールド差分を整理する。

このファイルは即座に schema v1 を破壊的変更するためのものではない。

実装前に、どの entity に何が不足しているかを明確にし、migration可能な形で schema v1.1 / v2 へ進めるための設計メモである。

## Delta Principles

### 1. Raw / Normalized / Memory / Interpretation を混ぜない

Rawは元データ。Normalizedは検索整形。Memoryは記憶単位。Interpretationは後からの意味づけ。

この分離を壊さない。

### 2. Safety and privacy are first-class

safety/privacy/export/AI eligibility は後付けタグではなく、主要entityの一級フィールドとして扱う。

### 3. Deletion is modeled, not just removed

削除・非表示・封印・tombstone・raw-only delete を区別する。

### 4. Cost and policy are auditable without raw

CostLedger / PolicyDecision / AuditLog は raw text を持たない。

### 5. SourceRef is required for trust

Memory OS で「どこから来たか」を失うことは、AIが勝手に作った記憶に近づく。

## Existing Strong Foundation

`memory-schema-v1.md` はすでに以下を持つ。

- User
- SourceRef
- ImportJob
- RawRecord
- NormalizedRecord
- Memory
- MemoryKind
- MemoryInterpretation
- Evidence
- ConfidenceScore
- PersonRef

良い点:

- RawとMemoryを分けている。
- MemoryとInterpretationを分けている。
- Evidenceがある。
- SourceRefがある。
- Safetyが主要fieldとしてある。

## Missing / Needs Expansion

### 1. Adapter Metadata

Source Adapter SDK 実装には adapter情報が必要。

```ts
type AdapterId = string;

type AdapterMetadata = {
  adapterId: AdapterId;
  adapterVersion: string;
  parserName?: string;
  parserVersion?: string;
  extractionMode: 'full' | 'metadata_only' | 'summary_seed' | 'masked' | 'inspect_only';
};
```

Add to:

- SourceRef
- ImportJob
- RawRecord metadata
- NormalizedRecord metadata

Reason:

- parser変更時の再処理可否
- fixture再現性
- bug調査
- migration

### 2. Import Inspection

既存 ImportJob に inspectionSummary はあるが、inspectionの標準型を拡張する。

```ts
type ImportInspection = {
  sourceType: SourceType | 'unknown';
  adapterId: string;
  adapterVersion: string;
  detectedRange?: DateRange;
  inventory: FileInventorySummary;
  counts: ImportCounts;
  sensitiveFindings: SensitiveFinding[];
  thirdPartyPreview: ThirdPartyPreview;
  corporatePreview: CorporatePreview;
  minorPreview: MinorPreview;
  legacyPreview: LegacyPreview;
  excludedByDefault: ExclusionPreview[];
  recommendedScopes: ImportScopeSuggestion[];
  estimatedCostClass: CostClass;
  warnings: AdapterWarning[];
};
```

### 3. Import Scope

Adapter planには user-selected scope が必要。

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

Add to:

- ImportJob.userScope

### 4. Visibility Expansion

既存 Memory has visibility but lifecycle semantics need stronger states.

```ts
type MemoryVisibility = {
  search: 'visible' | 'hidden' | 'sealed';
  tips: 'eligible' | 'excluded' | 'requires_opt_in';
  ai: 'eligible' | 'excluded' | 'summary_only' | 'masked_only';
  export: 'eligible' | 'excluded' | 'summary_only';
  share: 'owner_only' | 'limited' | 'excluded';
};
```

Reason:

- hidden と sealed を一つのbooleanで扱わない。
- Tip/AI/Export/Share の可否が別。

### 5. Lifecycle Expansion

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

Add to:

- Memory.lifecycle
- RawRecord lifecycle or deletedAt + tombstone
- NormalizedRecord lifecycle
- EmbeddingLifecycle

### 6. Deletion Tombstone

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

Reason:

- re-import resurrection防止。
- backup restoreで削除をreplay。

### 7. Policy Decision Persistence

Policy Engine decisions should be persisted for audit and explainability.

```ts
type PolicyDecisionRecord = {
  id: string;
  userId: string;
  action: PolicyAction;
  target: PolicyTarget;
  mode: PolicyDecision['mode'];
  reasons: PolicyReason[];
  requiredActions: PolicyRequiredAction[];
  policyVersion: string;
  decidedAt: string;
};
```

Must not include raw content.

### 8. Cost Estimate and Ledger

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

No raw text.

### 9. Export Entities

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

```ts
type ExportRedaction = {
  fieldPath: string;
  reason: RedactionReason;
  replacement: '[REDACTED]' | '[SUMMARY_ONLY]' | '[EXCLUDED]' | '[HIDDEN_BY_USER]';
  policyDecisionId?: string;
};
```

### 10. Privacy Context

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

Add to:

- RawRecord metadata or safety
- NormalizedRecord
- Memory.safety
- Evidence.privacy

### 11. Embedding Lifecycle

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

Reason:

- hidden/sealed/deleted を vector search から確実に除外。

### 12. Search Explanation

```ts
type SearchResultExplanation = {
  resultId: string;
  reasons: Array<
    | 'keyword_match'
    | 'semantic_match'
    | 'same_time_period'
    | 'source_match'
    | 'user_tagged'
    | 'evidence_match'
    | 'safe_summary_only'
  >;
  safeText: string;
};
```

Forbidden:

- `life_importance`
- `person_importance`
- `personality_match`

## Field Naming Bans

Avoid these field names in schema and code:

- importanceScore
- lifeScore
- personalityScore
- personRank
- topMemory
- bestMemory
- worstMemory
- wifePersonality
- parentProfile
- deceasedPersona
- evidenceAgainstPerson

Allowed alternatives:

- queryRelevance
- sourceTrust
- evidenceStrength
- timeFit
- userPinned
- safetyPenalty
- visibility
- lifecycle

## Migration Notes

### v1.1 additive migration

Safe additions:

- adapter metadata
- policy decision record
- cost estimate/ledger
- tombstone table
- export job table
- embedding lifecycle table
- privacy context fields

### v2 potential migration

Potential breaking refinements:

- split MemorySafety into Safety + Privacy + Eligibility
- split MemoryVisibility into per-surface controls
- formalize RelationshipContext separate from PersonRef
- normalize ImportInspection as its own entity

## MVP Required Schema Deltas

For MVP, prioritize:

1. DeletionTombstone
2. PolicyDecisionRecord
3. AdapterMetadata
4. ImportScope
5. CostEstimateRecord
6. ExportJob
7. EmbeddingLifecycle stub
8. MemoryVisibility per-surface fields

Do not block MVP on:

- complex relationship graph
- full privacy consent engine
- advanced vector storage abstraction
- cross-service migration completeness

## Acceptance Criteria

Data Model Delta is ready when:

- MVP additions are additive.
- No forbidden ranking/personality fields are introduced.
- Tombstone can prevent re-import resurrection.
- Policy decisions can be audited without raw.
- Cost ledger can track usage without raw.
- Export job can generate manifest/redactions.
- Embedding lifecycle can block hidden/sealed/deleted.
- Adapter metadata can support parser versioning.

## 結論

Memory Schema v1 の思想は良い。

次に必要なのは、入口・出口・削除・コスト・検索・privacyを実装で守るための補助entityである。

この差分は、Memory OS が「人生の索引」であり続けるための実装ガードになる。
