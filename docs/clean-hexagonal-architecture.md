# Clean / Hexagonal Architecture for Memory OS

## 目的

このドキュメントは、Clean Architecture / Hexagonal Architecture を Memory OS にどう適用するかを説明する。

目的は、Memory OS の本質的なルールを、DB・UI・LLM・検索エンジン・外部APIから独立させることである。

Memory OS で一番大切なのは、PostgreSQLでもReactでもOpenAIでもない。

一番大切なのは、**AIは人生を評価しない、出典を守る、削除を尊重する、他人の秘密を記憶化しない**というドメインルールである。

## 一言で言うと

```txt
中心にビジネスルールを置き、外側にDB・UI・LLM・外部サービスを置く設計。
```

DBを変えても、LLMを変えても、UIを変えても、PolicyやMemoryのルールは変わらないようにする。

## なぜ必要か

悪い設計では、こうなる。

```txt
API handler
  -> DB query
  -> LLM call
  -> policyっぽいif文
  -> search update
  -> response
```

これだと以下が起きる。

- Policyが画面ごとにバラバラになる。
- Exportだけ安全チェックが抜ける。
- LLMベンダー変更でドメインロジックが壊れる。
- DB schemaがそのままビジネスルールになる。
- テストしづらい。

良い設計では、こうする。

```txt
UI/API
  -> UseCase
    -> Domain Service
      -> PolicyEvaluator
      -> Repository Interface
      -> Adapter Interface
  -> Infrastructure implementation
```

## Layer Model

```txt
Domain Layer
Application Layer
Ports Layer
Infrastructure Layer
Presentation Layer
```

## Domain Layer

Memory OS の中心。

ここに置くもの:

- Memory
- SourceRef
- Evidence
- PolicyDecision
- DeletionTombstone
- PrivacyContext
- CostEstimate
- Domain errors
- Pure domain rules

ここに置かないもの:

- SQL
- HTTP request
- React components
- OpenAI SDK
- S3 SDK
- Elasticsearch client
- Date.now直呼び

## Application Layer

ユースケースを置く。

Examples:

```ts
CreateMemoryUseCase
InspectImportUseCase
DeleteMemoryUseCase
SearchMemoriesUseCase
CreateExportUseCase
EstimateImportCostUseCase
```

UseCaseの責務:

- 入力を受ける
- domain serviceを呼ぶ
- repository portを使う
- transaction boundaryを決める
- output DTOを返す

UseCaseがやってはいけないこと:

- raw secretをログに出す
- Policyを迂回する
- DB実装詳細を書く
- LLMへ直接送る

## Ports Layer

中心から外部へ出るためのinterface。

Examples:

```ts
type MemoryRepository = {
  save(memory: Memory): Promise<void>;
  findById(userId: string, memoryId: string): Promise<Memory | null>;
};

type PolicyDecisionRepository = {
  save(decision: PolicyDecisionRecord): Promise<void>;
};

type ObjectStoragePort = {
  putEncrypted(path: string, bytes: Uint8Array): Promise<void>;
  delete(path: string): Promise<void>;
};

type LlmPort = {
  summarizeSafe(input: SafeLlmInput): Promise<SafeLlmOutput>;
};
```

重要:

- DomainはPortを知ってもよいが、実装を知らない。
- InfrastructureはPortを実装する。

## Infrastructure Layer

外側の具体実装。

Examples:

- PostgreSQLMemoryRepository
- SQLiteMemoryRepository
- S3ObjectStorage
- LocalFileObjectStorage
- OpenAIAdapter
- AnthropicAdapter
- PgVectorIndex
- OpenSearchIndex

ここは差し替え可能にする。

## Presentation Layer

ユーザー/APIとの接点。

Examples:

- REST API
- Next.js route
- React UI
- CLI
- mobile share extension

Presentation は直接DBやLLMに触らない。

## Hexagonal Ports for Memory OS

### Inbound Ports

外からアプリへ入る操作。

```ts
type CaptureMemoryCommand = { ... };
type InspectImportCommand = { ... };
type DeleteMemoryCommand = { ... };
type SearchMemoryQuery = { ... };
type ExportMemoryCommand = { ... };
```

### Outbound Ports

アプリから外部へ出る依存。

```ts
MemoryRepository
SourceRefRepository
PolicyDecisionRepository
ObjectStoragePort
SearchIndexPort
VectorIndexPort
LlmPort
ClockPort
IdGeneratorPort
LoggerPort
AuditLogPort
```

## Dependency Rule

依存方向:

```txt
Presentation -> Application -> Domain
Infrastructure -> Application/Domain ports
```

Domain must not import:

- React
- Express/Next Request
- Prisma client
- OpenAI SDK
- AWS SDK
- GitHub SDK

## Example: Create Memory Flow

```txt
API receives request
-> CreateMemoryUseCase
-> PolicyEvaluator.evaluate(create_memory)
-> SourceRef required
-> Memory entity created
-> Evidence linked
-> repository.save
-> searchIndex.indexSafeText if policy allows
```

LLM is not required.

## Example: LLM Summary Flow

```txt
User requests summary
-> SummarizeMemoryUseCase
-> load Memory/Evidence
-> PolicyEvaluator.evaluate(send_to_llm)
-> Redactor masks input
-> LlmPort.summarizeSafe
-> save Interpretation as inference
```

LLM output never overwrites Memory fact.

## Example: Delete Flow

```txt
DeleteMemoryUseCase
-> set pending_deletion
-> repository.save lifecycle
-> searchIndex.disable
-> vectorIndex.disable
-> objectStorage.delete raw if raw-only/full
-> tombstoneRepository.save
-> auditLog.write no raw
```

## Testing Benefit

Clean Architecture lets us test Policy without DB/LLM.

```ts
it('denies secret embedding', () => {
  const decision = evaluatePolicy({ action: 'create_embedding', riskClasses: ['secret_or_credential'] });
  expect(decision.mode).toBe('deny');
});
```

This is fast and safe.

## Anti-patterns

### DB-first domain

Bad:

```ts
if (memory.importanceScore > 0.8) showTopMemory(memory)
```

Why bad:

- importanceScore should not exist.
- DB field created product behavior.

### LLM-first domain

Bad:

```ts
const analysis = await openai.chat(rawUserArchive)
```

Why bad:

- Policy/secret/cost bypass.

### UI-controlled safety

Bad:

```ts
if (checkboxChecked) exportRaw()
```

Why bad:

- UI checkbox cannot override policy.

## Recommended Folder Structure

```txt
src/
  domain/
    memory/
      Memory.ts
      Evidence.ts
      SourceRef.ts
    policy/
      PolicyDecision.ts
      PolicyEvaluator.ts
    deletion/
      DeletionTombstone.ts
      Lifecycle.ts
    cost/
      CostEstimate.ts
  application/
    useCases/
      CreateMemoryUseCase.ts
      InspectImportUseCase.ts
      DeleteMemoryUseCase.ts
      SearchMemoriesUseCase.ts
      CreateExportUseCase.ts
  ports/
    MemoryRepository.ts
    SearchIndexPort.ts
    ObjectStoragePort.ts
    LlmPort.ts
    AuditLogPort.ts
  infrastructure/
    db/
    storage/
    adapters/
    llm/
    search/
  presentation/
    api/
    ui/
```

## MVP Simplification

最初から完璧なClean Architectureにしすぎない。

MVPで守る最低ライン:

- PolicyEvaluator is pure.
- UseCases call Policy before dangerous actions.
- LLM is behind LlmPort.
- Storage is behind ports.
- Domain types do not import framework/vendor SDK.
- Tests can run without DB/LLM.

## Acceptance Criteria

- Policy tests run without DB/LLM.
- Domain layer has no OpenAI/AWS/React/Prisma imports.
- UseCases are the only place coordinating multiple repositories.
- Infrastructure implementations can be swapped.
- No Presentation code directly sends memory content to LLM.
- No Export code bypasses PolicyEvaluator.

## 結論

Clean / Hexagonal Architecture は、Memory OSを長く壊さないための骨格である。

DBやLLMやUIが変わっても、Memory OSの思想が変わらないように、中心にドメインルールを置く。
