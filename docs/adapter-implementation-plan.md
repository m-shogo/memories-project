# Adapter Implementation Plan

## 目的

Adapter Implementation Plan は、Source Adapter SDK を MVP 実装へ落とすための具体計画である。

Source Adapter は Memory OS の入口であり、ここが崩れると、秘密情報・第三者情報・会社情報・未成年情報・故人情報・コスト攻撃がすべて中へ入ってしまう。

したがって Adapter は便利な parser ではなく、**安全な取り込み境界**として実装する。

## 実装原則

### 1. Inspect before analyze

すべての Adapter は、抽出・正規化・LLM・Embedding の前に inspect を返す。

### 2. Plan before extract

inspect後、ユーザーscopeとcost/policy確認なしに extract しない。

### 3. SourceRef required

Adapter output は必ず SourceRefDraft を持つ。

### 4. No source-specific bypass

どのAdapterもPolicy/Cost/Deletionを迂回しない。

### 5. Unknown is inspect-only

unknown source は全文解析しない。

## MVP Adapter Order

### A0: Adapter Core

Build first:

- SourceAdapter interface
- AdapterInput
- DetectResult
- ImportInspection
- CostEstimate
- ExtractionPlan
- RawRecordEnvelope
- NormalizedRecordEnvelope
- AdapterError

Acceptance:

- TypeScript compile.
- no adapter can omit detect/inspect/plan/extract/normalize.
- plan requires ImportScope.

### A1: manual.paste.v1

Use case:

- user manually pastes a small memory or note.

Capabilities:

- detect: declared/manual fallback
- inspect: text size, rough date hints, secret scan
- estimateCost: free_or_tiny/low
- plan: raw preference, LLM preference, embedding preference
- extract: one RawRecordEnvelope
- normalize: searchableText + SourceRef + Evidence seed

Risks:

- pasted secret/API key
- pasted third-party private info
- pasted company data

Default:

- raw optional
- LLM not required
- embedding safe_text_only only

### A2: manual.share_text.v1

Use case:

- mobile/share sheet small text.

Similar to manual.paste but:

- userProvidedLabel may be source label only
- shared URL/text should not be treated as fact without user basis

Acceptance:

- tiny input works with no LLM.
- user label not mixed into canonical fact.

### A3: generic.conversation_text.v1

Use case:

- pasted conversation snippets.

Capabilities:

- detect speaker markers weakly
- inspect speaker ambiguity
- extract message windows
- normalize user/other speaker separation if possible

Default:

- thirdPartyMode: relationship_summary_only
- raw other-speaker no/default
- LLM masked/summary only

Hard requirements:

- if speaker ambiguous, mark high risk.
- do not quote other speaker raw by default.

### A4: openai.chatgpt_export_subset.v1

Use case:

- user-selected ChatGPT export subset, not full history.

Capabilities:

- detect JSON shape/metadata
- inspect conversations count/date range
- exclude attachments default
- distinguish user messages and assistant messages

Important:

- AI assistant responses are not evidence that real events happened.
- user prompt is evidence of what user discussed, not always fact.
- roleplay/persona logs no automatic Memory creation.

Default:

- selected conversations only
- no full history default
- safe summary seed only

## Post-MVP Adapters

### line.text_export.v1

- summary-only default
- speaker separation required
- third-party raw no/default
- blame/surveillance query deny

### google.calendar.v1

- metadata/event context
- good for occurredAt confidence
- avoid company/calendar confidential details if work calendar

### photos.metadata.v1

- metadata only
- no face recognition
- location rounding
- minor high risk

### github.metadata.v1

- selected personal repos only
- metadata/commit dates/project timeline
- no private company code
- secret scan commit messages

## Deferred / Blocked Adapters

Do not implement in MVP:

- Gmail full takeout
- Slack full export
- Discord full export
- Apple Photos full library
- image content analysis
- face recognition
- raw media analysis

## Adapter Core Types

```ts
type SourceAdapter = {
  readonly id: string;
  readonly sourceType: SourceType;
  readonly version: string;
  readonly capabilities: AdapterCapabilities;

  detect(input: AdapterInput): Promise<DetectResult>;
  inspect(input: AdapterInput, ctx: AdapterContext): Promise<ImportInspection>;
  estimateCost(input: AdapterInput, inspection: ImportInspection, ctx: AdapterContext): Promise<CostEstimate>;
  plan(input: AdapterInput, inspection: ImportInspection, scope: ImportScope, ctx: AdapterContext): Promise<ExtractionPlan>;
  extract(input: AdapterInput, plan: ExtractionPlan, ctx: AdapterContext): AsyncIterable<RawRecordEnvelope>;
  normalize(record: RawRecordEnvelope, ctx: AdapterContext): Promise<NormalizedRecordEnvelope>;
};
```

## Implementation Modules

```txt
src/adapters/
  core/
    types.ts
    registry.ts
    errors.ts
    safety.ts
    cost.ts
    testHarness.ts
  manualPaste/
    adapter.ts
    fixtures/
    adapter.test.ts
  shareText/
    adapter.ts
    fixtures/
    adapter.test.ts
  genericConversationText/
    adapter.ts
    fixtures/
    adapter.test.ts
  chatgptExportSubset/
    adapter.ts
    fixtures/
    adapter.test.ts
```

## Adapter Registry

```ts
type AdapterRegistry = {
  register(adapter: SourceAdapter): void;
  detect(input: AdapterInput): Promise<DetectResult[]>;
  get(adapterId: string): SourceAdapter | undefined;
};
```

Rules:

- registry returns ranked detect results.
- low confidence sources cannot auto-extract.
- unknown adapter always exists and is inspect-only.

## Secret Scan Integration

Every adapter inspect must call secret scan before displaying preview.

SecretFinding must not include raw value.

```ts
type SecretFinding = {
  kind: 'password' | 'api_key' | 'oauth_token' | 'private_key' | 'cookie' | 'database_url' | 'env_file' | 'unknown_secret';
  location: 'filename' | 'metadata' | 'text' | 'archive_path';
  confidence: number;
  action: 'exclude' | 'redact' | 'deny_import';
};
```

## Adapter Test Harness

Shared harness should test:

1. detect safe fixture
2. inspect without LLM
3. secret redacted
4. third-party private summary/exclude
5. corporate excluded
6. minor high-risk
7. missing date not invented
8. speaker ambiguity high-risk
9. huge input partial
10. tombstone skip
11. SourceRef present
12. LLM eligibility denied when blocked
13. embedding denied for unsafe raw
14. error safe message
15. no raw in logs

## Acceptance Criteria by Adapter

Each MVP Adapter must provide:

- adapter id/version
- capabilities
- safe fixtures
- risky fixtures
- detect tests
- inspect tests
- extract tests
- normalize tests
- policy integration tests
- cost estimate tests
- deletion/tombstone tests if re-import relevant

## Failure Modes

- adapter stores raw before scan
- adapter sends content to LLM during inspect
- adapter creates Memory without SourceRef
- adapter invents occurredAt
- adapter treats assistant reply as fact
- adapter quotes third-party raw
- adapter ignores tombstone
- adapter processes full history by default

## MVP Done for Adapter Layer

Adapter layer is MVP-ready when:

- manual.paste.v1 passes shared harness
- manual.share_text.v1 passes shared harness
- generic.conversation_text.v1 passes high-risk speaker tests
- unknown inspect-only works
- openai.chatgpt_export_subset.v1 is at least design-ready or feature-flagged off
- no adapter can bypass policy/cost/deletion

## 結論

Source Adapter はMemory OSの入口である。

入口では賢く分析するより、安全に止めることが重要である。

MVPは manual/share/generic conversation から始め、危険な大規模importは後に回す。
