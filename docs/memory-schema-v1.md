# Memory Schema v1

## 目的

Memory Schema v1 は、AI記憶体サービスが扱うデータの基礎構造を定義する。

このサービスは、AIモデルが変わっても、外部サービスが変わっても、ユーザーの人生文脈を持ち出せる必要がある。

そのため、スキーマは特定LLMや特定DBに依存しない。

## 設計方針

### 1. RawとMemoryを分ける

RawRecordは元データに近い。

Memoryはユーザーが後から見つけるための単位。

### 2. MemoryとInterpretationを分ける

記憶そのものと、AIやユーザーによる解釈は別。

同じ出来事でも、後から意味が変わる。

### 3. PersonとRelationshipを分ける

人物そのものを評価しない。

ユーザーから見た関係性を扱う。

### 4. Evidenceを必ず持つ

AIが勝手に作った記憶を事実にしない。

### 5. Safetyを第一級フィールドにする

安全・プライバシー・共有可否は後付けメタデータではなく、中心的なフィールド。

## Core Entities

```ts
type User = {
  id: string;
  createdAt: string;
};
```

```ts
type SourceRef = {
  id: string;
  userId: string;
  sourceType: SourceType;
  sourceName?: string;
  importJobId?: string;
  externalId?: string;
  externalUrl?: string;
  capturedAt?: string;
  importedAt: string;
  rawStored: boolean;
  rawStoragePath?: string;
  rawRetentionPolicy: RawRetentionPolicy;
  riskClass: RiskClass[];
};
```

```ts
type ImportJob = {
  id: string;
  userId: string;
  sourceType: SourceType | 'unknown';
  status: ImportStatus;
  startedAt: string;
  completedAt?: string;
  inputKind: SourceInputKind;
  fileInventoryHash?: string;
  detectedRange?: DateRange;
  inspectionSummary?: ImportInspection;
  userScope?: ImportScope;
  error?: string;
};
```

```ts
type RawRecord = {
  id: string;
  userId: string;
  sourceRefId: string;
  importJobId?: string;
  recordType: RawRecordType;
  occurredAt?: string;
  speaker?: SpeakerRef;
  text?: string;
  metadata?: Record<string, unknown>;
  contentHash: string;
  riskFlags: RiskClass[];
  rawStoragePolicy: RawStoragePolicy;
  deletedAt?: string;
};
```

```ts
type NormalizedRecord = {
  id: string;
  userId: string;
  rawRecordId: string;
  occurredAt?: string;
  canonicalText?: string;
  searchableText?: string;
  displayText?: string;
  peopleHints: string[];
  topicHints: string[];
  placeHints: string[];
  timeHints: string[];
  safetyFlags: RiskClass[];
  llmEligibility: LlmEligibility;
  embeddingEligibility: EmbeddingEligibility;
  deletedAt?: string;
};
```

## Memory

```ts
type Memory = {
  id: string;
  userId: string;
  title?: string;
  body?: string;
  summary?: string;
  memoryKind: MemoryKind;
  occurredAt?: string;
  period?: DateRange;
  sourceRefIds: string[];
  rawRecordIds: string[];
  evidenceIds: string[];
  safety: MemorySafety;
  visibility: MemoryVisibility;
  lifecycle: MemoryLifecycleState;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string;
};
```

```ts
type MemoryKind =
  | 'fact'
  | 'event'
  | 'experience'
  | 'relationship_context'
  | 'preference'
  | 'routine'
  | 'thought'
  | 'question'
  | 'decision'
  | 'life_phase'
  | 'future_intention'
  | 'unknown';
```

重要:

- MemoryKindは価値の上下ではない
- factが低価値、life_phaseが高価値という意味ではない
- 何気ないfactが後から重要になることがある

## Interpretation

```ts
type MemoryInterpretation = {
  id: string;
  userId: string;
  memoryId: string;
  interpretationType:
    | 'user_note'
    | 'ai_summary'
    | 'ai_inference'
    | 'later_reflection'
    | 'relationship_reading'
    | 'value_reading';
  text: string;
  createdAt: string;
  createdBy: 'user' | 'ai';
  evidenceIds: string[];
  confidence: ConfidenceScore;
  validForPeriod?: DateRange;
  deletedAt?: string;
};
```

これにより、同じ出来事に対して後から意味が変わることを扱える。

例:

- 2026年: ただの焼肉
- 2036年: 卒業式後にみんなで行った大切な思い出

## Evidence

```ts
type Evidence = {
  id: string;
  userId: string;
  sourceRefId: string;
  rawRecordId?: string;
  normalizedRecordId?: string;
  quote?: string;
  quotePolicy: QuotePolicy;
  occurredAt?: string;
  evidenceType:
    | 'user_statement'
    | 'assistant_statement'
    | 'third_party_statement'
    | 'photo_metadata'
    | 'calendar_event'
    | 'commit_metadata'
    | 'ai_inference'
    | 'user_confirmation';
  confidence: ConfidenceScore;
  privacy: PrivacyLevel;
};
```

## Confidence

```ts
type ConfidenceScore = {
  value: number; // 0-100
  basis:
    | 'user_direct_statement'
    | 'multiple_user_statements'
    | 'cross_source_match'
    | 'calendar_or_metadata'
    | 'photo_metadata'
    | 'third_party_statement'
    | 'ai_summary'
    | 'ai_inference'
    | 'user_confirmed';
  explanation: string;
};
```

## Person and Relationship

```ts
type PersonRef = {
  id: string;
  userId: string;
  displayName: string;
  aliases: string[];
  personType:
    | 'self'
    | 'family'
    | 'partner'
    | 'friend'
    | 'coworker'
    | 'public_person'
    | 'fictional_character'
    | 'ai_character'
    | 'unknown';
  privacy: PrivacyLevel;
  createdAt: string;
  updatedAt: string;
};
```

```ts
type RelationshipContext = {
  id: string;
  userId: string;
  personRefId: string;
  relationshipLabel?: string;
  userPerspectiveSummary?: string;
  evidenceIds: string[];
  confidence: ConfidenceScore;
  safety: MemorySafety;
  createdAt: string;
  updatedAt: string;
};
```

重要:

- PersonRefは他人を診断しない
- RelationshipContextはユーザーから見た関係性
- 「妻はこういう人」ではなく「妻との記録にはこういう関係性が見える」

## Topic

```ts
type Topic = {
  id: string;
  userId: string;
  name: string;
  aliases: string[];
  parentTopicId?: string;
  topicType:
    | 'hobby'
    | 'work'
    | 'family'
    | 'place'
    | 'media'
    | 'life_event'
    | 'value'
    | 'unknown';
  createdAt: string;
};
```

## MediaRef

```ts
type MediaRef = {
  id: string;
  userId: string;
  sourceRefId: string;
  mediaType: 'image' | 'video' | 'audio' | 'document';
  originalStored: boolean;
  storagePath?: string;
  metadataOnly: boolean;
  capturedAt?: string;
  approximateLocation?: string;
  preciseLocationStored: boolean;
  faceAnalysisPerformed: boolean;
  childOrMinorRisk: boolean;
  safety: MemorySafety;
};
```

## EmbeddingIndex

```ts
type EmbeddingIndex = {
  id: string;
  userId: string;
  ownerType:
    | 'normalized_record'
    | 'memory'
    | 'interpretation'
    | 'relationship_context'
    | 'topic';
  ownerId: string;
  embeddingModel: string;
  contentHash: string;
  embeddingEligibility: EmbeddingEligibility;
  createdAt: string;
  deletedAt?: string;
};
```

## Safety

```ts
type MemorySafety = {
  riskClasses: RiskClass[];
  policy: MemoryPolicy;
  containsThirdParty: boolean;
  containsMinor: boolean;
  containsMedicalOrMental: boolean;
  containsSecret: boolean;
  containsCorporateConfidential: boolean;
  quotePolicy: QuotePolicy;
  tipPolicy: TipPolicy;
  sharePolicy: SharePolicy;
  exportPolicy: ExportPolicy;
};
```

```ts
type MemoryVisibility =
  | 'normal'
  | 'hidden_by_default'
  | 'archived'
  | 'locked'
  | 'deleted';
```

```ts
type QuotePolicy =
  | 'allow_quote'
  | 'short_quote_only'
  | 'summary_only'
  | 'hide_by_default'
  | 'forbidden';
```

## Deletion

```ts
type DeletionRequest = {
  id: string;
  userId: string;
  targetType:
    | 'memory'
    | 'source_ref'
    | 'import_job'
    | 'person_ref'
    | 'topic'
    | 'period'
    | 'all_user_data';
  targetId?: string;
  requestedAt: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  cascadeTargets: string[];
  completedAt?: string;
};
```

削除対象:

- RawRecord
- NormalizedRecord
- Memory
- Interpretation
- Evidence
- Embedding
- Tip
- Summary cache
- Export cache
- Person/Topic inference

## Audit

```ts
type AuditEvent = {
  id: string;
  userId: string;
  eventType:
    | 'import_inspected'
    | 'secret_detected'
    | 'memory_created'
    | 'memory_hidden'
    | 'memory_deleted'
    | 'llm_called'
    | 'embedding_created'
    | 'export_created'
    | 'policy_blocked';
  occurredAt: string;
  metadata: Record<string, unknown>;
  containsRawText: false;
};
```

監査ログに本文は入れない。

## Memory Object Export

エクスポート可能な形式。

```ts
type ExportedMemory = {
  schemaVersion: 'memory-schema-v1';
  exportedAt: string;
  memories: Memory[];
  interpretations: MemoryInterpretation[];
  evidence: Evidence[];
  people: PersonRef[];
  relationships: RelationshipContext[];
  topics: Topic[];
  safetyNotes: string[];
};
```

## Non-goals

- 人格の完全再現
- 他人の診断
- 会社検索
- パスワード保管
- 画像本体の大量保存
- 医療記録管理

## 結論

Memory Schema v1 は、人生の価値をAIが決めるための構造ではない。

未来のユーザーが過去の自分を見つけられるように、記録・出典・解釈・安全性を分けて保存するための構造である。
