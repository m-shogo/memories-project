# Cost Engine

## 目的

Cost Engine は、Memory OS の import / embedding / LLM / storage / export のコストを、ユーザー体験・安全・事業継続の観点から制御するための設計である。

このサービスは「人生の文脈を持ち続ける」ためのものだが、無制限に全履歴を解析すると、赤字・遅延・誤保存・プライバシー事故・コスト攻撃が起きる。

Cost Engine は、ケチるためだけの仕組みではない。

**勝手に大量解析しない、保存時に分析しすぎない、ユーザーに見えない課金事故を起こさないための安全機構**である。

## 最上位原則

### 1. Cost is consent

大量処理には、ユーザーの明示的な理解と同意が必要である。

### 2. Inspect is cheap, analyze is expensive

棚卸し・件数・期間・サイズ確認は軽く行う。

LLM解析・embedding・画像解析・全文抽出は重い処理として扱う。

### 3. Default to small scope

MVPでは、全履歴一括解析ではなく、共有入力・手動貼り付け・選択範囲から始める。

### 4. Safety overrides paid capacity

有料ユーザーでも、危険データを無制限にLLMへ送ってよいわけではない。

Policy Engine の deny / summary_only / masked_only は Cost Engine より優先される。

## Cost Domains

```ts
type CostDomain =
  | 'import_inspection'
  | 'raw_extraction'
  | 'normalization'
  | 'embedding'
  | 'llm_summary'
  | 'llm_analysis'
  | 'image_or_media_analysis'
  | 'search_retrieval'
  | 'export_generation'
  | 'storage'
  | 'backup';
```

## Cost Class

```ts
type CostClass =
  | 'free_or_tiny'
  | 'low'
  | 'medium'
  | 'high'
  | 'requires_credit'
  | 'blocked';
```

| Class | Meaning | Default UX |
|---|---|---|
| free_or_tiny | 共有テキスト、小さなメモ | 即時処理可 |
| low | 小さな会話、数十件 | 簡易見積もり表示 |
| medium | 数百〜数千件 | 範囲選択 + 確認 |
| high | 全履歴・大容量 | 強い確認 + 後続処理 |
| requires_credit | 無料枠では危険 | 課金/上限設定が必要 |
| blocked | 安全/思想上不可 | 実行しない |

## Cost Context

```ts
type CostContext = {
  userId: string;
  plan: UserPlan;
  action: CostedAction;
  sourceType?: SourceType;
  inputKind?: SourceInputKind;
  riskClasses: RiskClass[];
  policyDecision?: PolicyDecision;
  requestedAt: string;
};
```

```ts
type CostedAction =
  | 'inspect_import'
  | 'extract_records'
  | 'normalize_records'
  | 'create_embeddings'
  | 'summarize_records'
  | 'analyze_memories'
  | 'generate_tip'
  | 'search'
  | 'export'
  | 'backup';
```

## Cost Estimate

```ts
type CostEstimate = {
  id: string;
  userId: string;
  action: CostedAction;
  costClass: CostClass;
  estimatedInputBytes: number;
  estimatedRecords: number;
  estimatedTextTokens?: number;
  estimatedOutputTokens?: number;
  estimatedEmbeddingWrites?: number;
  estimatedStorageBytes?: number;
  estimatedMediaItems?: number;
  estimatedYen?: number;
  confidence: ConfidenceScore;
  hardStops: CostHardStop[];
  warnings: CostWarning[];
  requiresUserConfirmation: boolean;
  expiresAt: string;
};
```

```ts
type CostHardStop =
  | 'policy_denied'
  | 'unknown_source_full_analysis'
  | 'secret_detected'
  | 'corporate_data_raw_analysis'
  | 'third_party_private_raw_llm'
  | 'minor_sensitive_raw_llm'
  | 'plan_limit_exceeded'
  | 'daily_budget_exceeded'
  | 'monthly_budget_exceeded'
  | 'unsupported_media_analysis';
```

## Budget Model

```ts
type UserCostBudget = {
  userId: string;
  plan: UserPlan;
  daily: BudgetWindow;
  monthly: BudgetWindow;
  lifetimeImport?: BudgetWindow;
  userConfiguredMaxYen?: number;
  hardStopOnOverage: boolean;
};
```

```ts
type BudgetWindow = {
  limitUnits: number;
  usedUnits: number;
  resetAt: string;
};
```

Cost units should abstract vendor pricing.

```ts
type CostUnitKind =
  | 'input_token'
  | 'output_token'
  | 'embedding_write'
  | 'storage_mb_day'
  | 'media_analysis'
  | 'export_mb'
  | 'job_runtime_second';
```

## Plan Defaults

MVP can start with simple plan gates.

| Plan | Import | Embedding | LLM analysis | Export | Notes |
|---|---|---|---|---|---|
| free | share/manual small only | tiny selected only | user-requested only | markdown/small JSON | no full history |
| plus | selected archive subsets | selected safe text | scoped summaries | larger export | credit estimate |
| pro | larger batch | safe batch | async scoped | full safe archive | still policy gated |

No plan can bypass:

- secrets deny
- company raw deny
- surveillance intent deny
- deceased impersonation deny
- third-party private raw LLM deny

## Operation Limits

```ts
type OperationLimit = {
  action: CostedAction;
  maxInputBytes: number;
  maxRecords: number;
  maxTokens: number;
  maxEmbeddingWrites: number;
  maxRuntimeMs: number;
  overflowMode: 'stop' | 'partial' | 'ask_user' | 'queue';
};
```

Default overflow:

- inspect_import: partial
- extract_records: partial
- create_embeddings: ask_user
- summarize_records: ask_user
- analyze_memories: ask_user
- export: queue or ask_user

## Source Risk Cost Defaults

| Source | Default cost stance | Reason |
|---|---|---|
| manual_paste | low | user-selected small scope |
| share_text | free_or_tiny | explicit share |
| ChatGPT selected export | medium | can be large and mixed truth |
| full ChatGPT history | requires_credit | high volume + privacy |
| LINE | high | third-party + long logs |
| Gmail | blocked/default | very high privacy |
| Slack / Discord work | blocked/default | corporate data |
| Google Photos metadata | medium | many items, location risk |
| image content analysis | blocked/default | privacy + cost |
| GitHub metadata | medium | company/secrets risk |

## LLM Cost Rules

LLM calls are allowed only after Policy Engine approval.

```ts
function canRunLlmCostedJob(ctx: CostContext, estimate: CostEstimate): CostDecision {
  deny if ctx.policyDecision?.allow === false;
  deny if estimate.hardStops.length > 0;
  require confirmation if estimate.costClass in ['medium', 'high', 'requires_credit'];
  deny if monthly budget exceeded;
  allow if low risk and within budget;
}
```

Forbidden defaults:

- full raw DM summarization
- Gmail full summarization
- Slack / company full summarization
- self-harm raw tip generation
- grief/deceased impersonation generation
- AI companion roleplay continuation

## Embedding Cost Rules

Embedding is cheap per item but dangerous at scale because it makes data searchable.

Embedding allowed:

- low-risk user text
- safe normalized summaries
- metadata-only event descriptions
- user-approved selected subsets

Embedding denied:

- secrets
- raw credentials
- company confidential
- third-party secrets
- raw self-harm/crisis text
- raw minor sensitive records
- hidden/sealed memories unless explicitly searchable

## Storage Cost Rules

Raw storage can become expensive and risky.

Default raw storage:

| Data | Default |
|---|---|
| user manual note | optional |
| low-risk share text | optional |
| ChatGPT subset | metadata + safe text |
| LINE / DM | hidden summary, raw no/default |
| Gmail | raw no/default |
| Slack/company | raw no/default |
| photos | metadata only |

Raw retention must be explicit and visible.

## User-visible Cost UI

Before medium or higher jobs:

```txt
この取り込みは約3,200件の記録を確認します。まず棚卸しだけ行い、全文解析やEmbeddingは選択した範囲だけ実行します。
```

Before requires_credit:

```txt
この処理は大きなコストがかかる可能性があります。無料枠では全件解析せず、期間や出典を絞ってください。
```

Blocked:

```txt
このデータは安全上、全文解析できません。出典・期間・件数の棚卸しと、安全な要約候補の作成に限定します。
```

## Cost Attack Scenarios

### Attack: Huge archive upload

Mitigation:

- inspect only first
- file count / size limits
- no auto embedding
- user scope required

### Attack: Paste secrets then search later

Mitigation:

- secret scan before storage
- search / embedding deny
- redacted inspection

### Attack: Free plan full history processing

Mitigation:

- plan limit
- partial preview
- credit requirement

### Attack: Repeated re-import to bypass limits

Mitigation:

- contentHash dedupe
- importJob cost ledger
- tombstone check

### Attack: Use export as cheap raw dump

Mitigation:

- export policy gate
- raw deny defaults
- redaction log

## Cost Ledger

```ts
type CostLedgerEntry = {
  id: string;
  userId: string;
  importJobId?: string;
  action: CostedAction;
  estimateId?: string;
  actual: ActualCost;
  createdAt: string;
  sourceType?: SourceType;
  riskClasses: RiskClass[];
};
```

```ts
type ActualCost = {
  inputTokens?: number;
  outputTokens?: number;
  embeddingWrites?: number;
  storageBytesAdded?: number;
  mediaItemsProcessed?: number;
  runtimeMs?: number;
  vendorCostYen?: number;
};
```

Ledger must not include raw text.

## Acceptance Criteria

Cost Engine is ready when:

- Every import job has a cost estimate before extraction.
- Every LLM / embedding job checks budget and Policy Engine.
- Medium+ jobs require user confirmation.
- Full history import is never automatic.
- Unknown source full analysis is blocked.
- Cost ledger records actual usage without raw text.
- Plan limits cannot bypass safety policy.
- Large inputs stop as partial, not silent failure.
- UI shows understandable warnings.

## Non-goals

- Perfect vendor pricing prediction.
- User-hostile paywalling.
- Hiding cost from users.
- Letting paid users bypass privacy/safety.

## 結論

Cost Engine は、Memory OS を半永久的に続けるための現実的な防波堤である。

安くするためだけではなく、勝手に読みすぎない、保存時に分析しすぎない、危険データを検索可能にしない、という思想を実装で守る。
