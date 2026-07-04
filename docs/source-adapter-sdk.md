# Source Adapter SDK

## 目的

Source Adapter SDK は、外部サービス・ファイル・共有入力を Memory OS に取り込むための実装境界である。

このSDKの目的は、外部データを賢く解釈することではない。

**安全に受け取り、出典を失わず、日付と検索性を整え、ユーザー本人の記憶として扱える最小単位へ変換すること**である。

Memory OS は ChatGPT / Claude の代替ではない。Adapter は会話AIを作らない。人格を再現しない。人生の重要度を勝手に決めない。

## 最上位原則

### 1. Adapter は分析器ではなく変換器

Adapter が行うこと:

- 入力形式の検出
- コンテナの安全検査
- ファイル棚卸し
- 秘密情報・会社情報・第三者情報の事前検知
- ユーザーに見せる import preview の生成
- RawRecord / NormalizedRecord / SourceRef の生成
- 日付・出典・検索テキストの整形
- Policy Engine に渡すための risk hints 付与

Adapter が行わないこと:

- 「この記憶は重要」と決める
- 「あなたはこういう人」と分析する
- 相手の性格・本心・嘘を推測する
- 故人・家族・恋人・架空キャラとして返答する
- 会社情報検索を便利にする
- パスワード・秘密情報を記憶化する

### 2. Save First は Value Judge ではない

Import Specification の Save First, Judge Later は、「人生価値を保存時に判定しない」という意味である。

保存時に行ってよい判断:

- セキュリティリスク
- 法務・会社情報リスク
- 第三者プライバシーリスク
- 未成年・家族・故人リスク
- LLM送信可否
- raw保存可否
- embedding可否
- export / share 可否の初期値

保存時に行ってはいけない判断:

- 人生にとって重要かどうか
- 思い出として上位か下位か
- 人格傾向・診断・ランク
- 家族や恋人の良し悪し
- 仕事能力や人間関係の勝敗

### 3. Inspect Before Analyze

Adapter は、ファイルやアーカイブを受け取っても即座にLLMへ送らない。

必ず以下の順に進める。

```txt
receive
-> container precheck
-> source detect
-> inventory
-> secret scan
-> risk prefilter
-> cost estimate
-> user scope selection
-> extraction
-> normalization
-> source ref creation
-> policy evaluation
-> indexing
-> optional user review
```

### 4. Unknown は inspect only

sourceType が unknown、または detect confidence が低い場合、Adapter は深い抽出をしない。

許可:

- ファイル数
- サイズ
- 拡張子
- 推定期間
- 危険ファイル種別
- 秘密情報らしき断片の存在フラグ

禁止:

- 全文LLM解析
- 全文embedding
- raw全文保存の既定ON
- 自動Memory化

## SDK Package Structure

```txt
packages/source-adapter-sdk/
  src/
    types.ts
    adapter.ts
    detection.ts
    inspection.ts
    extraction.ts
    normalization.ts
    safety.ts
    cost.ts
    provenance.ts
    approval-gates.ts
    sync-state.ts
    test-harness.ts
  adapters/
    manual/
    chatgpt/
    line/
    calendar/
    photos-metadata/
    github-metadata/
  fixtures/
    safe/
    risky/
    malformed/
```

MVPでは monorepo 化していない場合でも、同等の境界を `src/source-adapters/` に置いてよい。

重要なのはディレクトリ名ではなく、**Adapter が Policy / Schema / Cost / Provenance に従う実装境界を持つこと**である。

## Adapter Manifest

各 Adapter は、実行コードとは別に Manifest を持つ。

Manifest は UI・Policy Engine・Cost Engine・Test Harness が、Adapter を実行する前に安全境界を理解するための契約である。

```ts
type AdapterManifest = {
  id: SourceAdapterId;
  sourceType: SourceType;
  displayName: string;
  version: string;
  schemaVersion: string;
  minPolicyVersion: string;
  supportedInputKinds: SourceInputKind[];
  supportedRecordTypes: RawRecordType[];
  defaultRiskLevel: 'low' | 'medium' | 'high' | 'very_high';
  capabilities: AdapterCapabilities;
  defaultPermissions: AdapterPermissions;
  defaultScope: ImportScope;
  requiredUserApprovals: AdapterApprovalKind[];
  forbiddenActions: PolicyAction[];
  piiClassesExpected: RiskClass[];
  costProfile: AdapterCostProfile;
  deletionSupport: AdapterDeletionSupport;
};
```

```ts
type AdapterApprovalKind =
  | 'store_raw'
  | 'create_embedding'
  | 'send_to_llm'
  | 'include_third_party_text'
  | 'include_corporate_context'
  | 'include_minor_data'
  | 'include_legacy_or_deceased_context'
  | 'process_large_archive'
  | 'export_with_warnings';
```

Manifest rules:

- Manifest の default は安全側に倒す。
- 実行時 permissions は Manifest より緩くしてはいけない。ただし、ユーザー承認と PolicyDecision が揃った場合だけ scope を拡張できる。
- Adapter は Manifest に書いていない inputKind / recordType を処理してはいけない。
- Manifest 変更は breaking / non-breaking を明示する。
- Test Harness は Manifest から必須fixtureを自動生成できる必要がある。

## Core Interfaces

### SourceAdapter

```ts
type SourceAdapter = {
  readonly manifest: AdapterManifest;
  readonly id: SourceAdapterId;
  readonly sourceType: SourceType;
  readonly version: string;
  readonly capabilities: AdapterCapabilities;

  detect(input: AdapterInput): Promise<DetectResult>;
  inspect(input: AdapterInput, ctx: AdapterContext): Promise<ImportInspection>;
  estimateCost(input: AdapterInput, inspection: ImportInspection, ctx: AdapterContext): Promise<CostEstimate>;
  plan(input: AdapterInput, inspection: ImportInspection, scope: ImportScope, ctx: AdapterContext): Promise<ExtractionPlan>;
  extract(input: AdapterInput, plan: ExtractionPlan, ctx: AdapterContext): AsyncIterable<RawRecordEnvelope>;
  normalize(record: RawRecordEnvelope, ctx: AdapterContext): Promise<NormalizedRecordEnvelope>;
  finalize?(job: ImportJob, ctx: AdapterContext): Promise<AdapterFinalizeResult>;
};
```

### AdapterContext

```ts
type AdapterContext = {
  userId: string;
  importJobId: string;
  policyVersion: string;
  schemaVersion: string;
  adapterRuntime: 'server' | 'client' | 'local_cli' | 'worker';
  now: string;
  locale?: string;
  userTimezone?: string;
  limits: AdapterLimits;
  permissions: AdapterPermissions;
  approvalState: AdapterApprovalState;
  syncState?: AdapterSyncState;
  logger: AdapterLogger;
};
```

### AdapterLimits

```ts
type AdapterLimits = {
  maxInputBytes: number;
  maxFiles: number;
  maxRecords: number;
  maxRecordBytes: number;
  maxExtractedTextBytes: number;
  maxEmbeddingRecords: number;
  maxLlmBytes: number;
  wallClockMs: number;
};
```

Adapter は limits を超えたら失敗ではなく、原則 `partial` として止める。

大量データを受け取った時に、コスト攻撃・誤課金・全履歴解析を避けるためである。

### AdapterPermissions

```ts
type AdapterPermissions = {
  canStoreRaw: boolean;
  canStoreSummary: boolean;
  canCreateEmbedding: boolean;
  canSendToLlm: boolean;
  canExtractThirdPartyText: boolean;
  canExtractCorporateData: boolean;
  canProcessMinorData: boolean;
};
```

permissions は UI だけでなく Adapter 実行時にも強制する。

## Input Model

```ts
type AdapterInput =
  | ShareTextInput
  | ShareUrlInput
  | ManualPasteInput
  | UploadedFileInput
  | UploadedArchiveInput
  | ApiImportInput
  | LocalExportInput;
```

```ts
type AdapterInputBase = {
  inputId: string;
  inputKind: SourceInputKind;
  receivedAt: string;
  declaredSourceType?: SourceType;
  userProvidedLabel?: string;
  userProvidedNote?: string;
  sizeBytes?: number;
  contentHash?: string;
};
```

Adapter は userProvidedLabel を記憶本文と混ぜてはいけない。

ラベルは出典・整理用であり、事実の証拠ではない。

## Detection

### DetectResult

```ts
type DetectResult = {
  sourceType: SourceType | 'unknown';
  confidence: number; // 0-100
  matchedSignals: DetectSignal[];
  matchedFiles: string[];
  warnings: AdapterWarning[];
  safeToInspect: boolean;
};
```

### DetectSignal

```ts
type DetectSignal = {
  kind: 'filename' | 'mime' | 'json_shape' | 'csv_header' | 'html_marker' | 'text_pattern' | 'archive_structure' | 'metadata';
  value: string;
  confidenceDelta: number;
};
```

### Detection Thresholds

| Confidence | Mode | Allowed |
|---:|---|---|
| 90-100 | strong | inspect + scoped extract |
| 70-89 | probable | inspect + user confirmation before extract |
| 40-69 | weak | inventory only + manual mapping |
| 0-39 | unknown | inspect only |

## Inspection

Inspection はユーザーが「何を渡したのか」を理解するための画面を作る。

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
  deceasedOrLegacyPreview: LegacyPreview;
  excludedByDefault: ExclusionPreview[];
  recommendedScopes: ImportScopeSuggestion[];
  estimatedCostClass: CostClass;
  warnings: AdapterWarning[];
};
```

### Inspection Must Not Leak Secrets

Inspection UI に秘密情報の値を表示してはいけない。

悪い例:

```txt
API key found: sk-xxxx...
```

良い例:

```txt
APIキーらしき文字列を2件検出しました。値は表示せず、保存・解析から除外します。
```

## Scope Selection

Adapter はユーザーに解析範囲を選ばせる。

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

Default scope:

- rawStoragePreference: `metadata_only`
- llmPreference: `safe_summary_only`
- embeddingPreference: `metadata_only`
- thirdPartyMode: `relationship_summary_only`
- corporateMode: `exclude`

## Approval Gates

ユーザーが scope を広げたとしても、Adapter は即実行してはいけない。

Scope request、Manifest、PolicyDecision、CostEstimate、ApprovalState が揃った時だけ危険操作を許可する。

```ts
type AdapterApprovalState = {
  approvals: AdapterApproval[];
  denied: AdapterApprovalKind[];
};
```

```ts
type AdapterApproval = {
  kind: AdapterApprovalKind;
  approvedAt: string;
  approvedBy: 'user';
  scopeFingerprint: string;
  expiresAt?: string;
};
```

Approval rules:

- `send_to_llm` approval は `store_raw` approval を意味しない。
- `create_embedding` approval は `send_to_llm` approval を意味しない。
- `include_third_party_text` は raw保存・embedding・LLM送信の各 approval と別で必要。
- `include_corporate_context` は初期状態では deny。MVPでは personal_work_context_only に限定する。
- scopeFingerprint が変わったら approval は再取得する。
- Approval UI は「便利になります」ではなく「何が保存/除外/送信されるか」を表示する。

## Extraction

### RawRecordEnvelope

```ts
type RawRecordEnvelope = {
  raw: RawRecord;
  source: SourceRefDraft;
  extraction: ExtractionMetadata;
  safetyHints: SafetyHint[];
  costHints: CostHint[];
  provenance: ProvenanceDraft;
};
```

### ExtractionMetadata

```ts
type ExtractionMetadata = {
  adapterId: string;
  adapterVersion: string;
  inputId: string;
  filePath?: string;
  byteRange?: { start: number; end: number };
  recordIndex?: number;
  parserName: string;
  parserVersion: string;
  extractedAt: string;
  extractionMode: 'full' | 'metadata_only' | 'summary_seed' | 'masked';
};
```

### Extraction Rules

- 1 record must be independently deletable.
- 1 record must carry sourceRefId or SourceRefDraft.
- Large conversations must be chunked by date / topic / message window.
- Chunking must not create fake events.
- Missing dates must remain missing; Adapter must not invent occurredAt.
- Speaker inference must be marked as inference.
- Attachments are excluded by default unless adapter explicitly supports safe metadata.

## Normalization

Normalization は検索可能性のための整形であり、人格分析ではない。

```ts
type NormalizedRecordEnvelope = {
  normalized: NormalizedRecord;
  evidenceDrafts: EvidenceDraft[];
  policyInputs: PolicyInputDraft[];
  quality: NormalizationQuality;
};
```

```ts
type NormalizationQuality = {
  textExtracted: boolean;
  dateResolved: boolean;
  speakerResolved: boolean;
  sourceLinked: boolean;
  language?: string;
  confidence: ConfidenceScore;
  warnings: AdapterWarning[];
};
```

Allowed normalization:

- 改行・引用符・絵文字の軽微な整形
- 日付形式の標準化
- URL・電話番号・メールの masking
- 自分発言 / 相手発言の分離
- 検索用 keyword hints の抽出
- 場所名の丸め

Forbidden normalization:

- 感情の断定
- 人格診断
- 相手の本心推測
- 出来事の美化
- 複数記録を混ぜた事実生成
- 危険な原文を displayText に残すこと

## SourceRef Draft

```ts
type SourceRefDraft = {
  sourceType: SourceType;
  sourceName?: string;
  importJobId: string;
  externalId?: string;
  externalUrl?: string;
  capturedAt?: string;
  importedAt: string;
  rawStored: boolean;
  rawStoragePath?: string;
  rawRetentionPolicy: RawRetentionPolicy;
  riskClass: RiskClass[];
  adapterId: string;
  adapterVersion: string;
};
```

SourceRef は Memory OS の信頼性の根である。

Adapter は SourceRef を省略してはいけない。

## Idempotency and Deduplication

Adapter は、同じ入力を複数回取り込んでも記憶を増殖させてはいけない。

```ts
type AdapterIdempotencyKey = {
  userId: string;
  sourceType: SourceType;
  adapterId: string;
  externalId?: string;
  contentHash?: string;
  occurredAt?: string;
  speakerStableId?: string;
};
```

Dedup priority:

1. `sourceType + externalId`
2. `sourceType + externalId + occurredAt` when externalId is conversation-level only
3. `contentHash + occurredAt + speakerStableId`
4. `contentHash` only for exact duplicate files

Rules:

- contentHash は masking 前の秘密値を直接ハッシュしてはいけない。必要なら secret-safe canonical hash を使う。
- AI要約の hash を RawRecord dedupe に使ってはいけない。
- Dedup は「重要度が低いから捨てる」ではなく「同じ記録の二重登録を避ける」ためだけに使う。
- 衝突時は古い record を上書きせず、SourceRef を追加するか conflict として保持する。
- 既存Memoryと似ているだけでは dedupe しない。

## Incremental Sync

API import や継続接続型 Adapter は、差分同期をサポートできる。

ただし、Memory OS は監視ツールではない。Incremental Sync はユーザー本人が選んだ source scope の更新取り込みであり、他人や会社の監視ではない。

```ts
type AdapterSyncState = {
  userId: string;
  adapterId: string;
  sourceType: SourceType;
  sourceAccountId?: string;
  cursor?: string;
  lastImportedAt?: string;
  lastExternalUpdatedAt?: string;
  scopeFingerprint: string;
  permissionFingerprint: string;
  status: 'active' | 'paused' | 'needs_reauth' | 'scope_changed' | 'disabled';
};
```

Incremental sync rules:

- Sync は user-selected scope の外に出てはいけない。
- permissionFingerprint が変わったら停止して再承認を要求する。
- scopeFingerprint が変わったら差分を続行せず、inspection からやり直す。
- 会社・DM・家族・未成年・故人関連の source は自動同期を default off にする。
- 同期失敗時に raw error body を保存してはいけない。
- 削除済み tombstone に一致する record は復活させない。
- 「毎日自動で相手の発言を取り込む」体験は監視化しやすいため、MVPでは禁止する。

## Safety Hints

Adapter は最終判断をしないが、Policy Engine に渡すヒントを必ず作る。

```ts
type SafetyHint = {
  riskClass: RiskClass;
  confidence: number;
  location?: 'filename' | 'metadata' | 'text' | 'speaker' | 'attachment' | 'unknown';
  actionSuggestion:
    | 'allow'
    | 'mask'
    | 'summary_only'
    | 'exclude'
    | 'require_user_approval'
    | 'deny';
  explanation: string;
};
```

Required risk checks:

- secret_or_credential
- corporate_confidential
- third_party_private
- minor_sensitive
- medical_or_mental
- self_harm_or_crisis
- grief_or_death
- romantic_or_sexual
- surveillance_or_blame_intent
- impersonation_or_roleplay_intent

## Cost Guardrails

Adapter は Cost Engine に入力する見積もりを作る。

```ts
type CostEstimate = {
  costClass: CostClass;
  inputBytes: number;
  estimatedRecords: number;
  estimatedTextBytes: number;
  estimatedEmbeddingRecords: number;
  estimatedLlmBytes: number;
  hardStopReasons: string[];
  userWarnings: string[];
};
```

```ts
type CostClass = 'free_or_tiny' | 'low' | 'medium' | 'high' | 'requires_credit' | 'blocked';
```

```ts
type AdapterCostProfile = {
  pricingUnit: 'record' | 'byte' | 'file' | 'conversation' | 'event' | 'metadata_only';
  defaultCostClass: CostClass;
  llmCostRisk: 'none' | 'low' | 'medium' | 'high' | 'blocked';
  embeddingCostRisk: 'none' | 'low' | 'medium' | 'high' | 'blocked';
  archiveExplosionRisk: boolean;
};
```

Rules:

- ZIP / Takeout / 全履歴は `requires_credit` 以上にしてよい。
- unknown source の全解析は `blocked`。
- LINE / Gmail / Slack / Discord の全文LLM解析は `blocked` default。
- Embedding は safe normalized text のみ。
- Cost estimate は実行前に UI に出す。
- ユーザーが無料枠でも、勝手に大量処理しない。
- Cost estimate と実処理量が大きく乖離した場合は partial stop する。

## Adapter Capability Matrix

```ts
type AdapterCapabilities = {
  supportsDetect: boolean;
  supportsInspect: boolean;
  supportsExtract: boolean;
  supportsNormalize: boolean;
  supportsIncrementalImport: boolean;
  supportsDeletionByExternalId: boolean;
  supportsRawStorage: boolean;
  supportsMetadataOnly: boolean;
  supportsClientSideProcessing: boolean;
  supportedInputKinds: SourceInputKind[];
  supportedRecordTypes: RawRecordType[];
  defaultRiskLevel: 'low' | 'medium' | 'high' | 'very_high';
};
```

MVP defaults:

| Adapter | Risk | Raw | LLM | Embedding | Notes |
|---|---|---|---|---|---|
| manual_paste | medium | ask | safe_summary_only | safe_text_only | User-selected |
| share_text | medium | ask | safe_summary_only | safe_text_only | Small scope |
| chatgpt_export_subset | medium | metadata/default | masked/safe | selected only | Not full history by default |
| line_text | high | hidden/default | masked summary | summary only | Third-party default |
| google_calendar | medium | metadata | safe | metadata + title | Event context only |
| photos_metadata | high | metadata only | no image LLM default | metadata only | No face recognition |
| github_metadata | high | metadata only | no code default | metadata only | Personal work context only |
| gmail_takeout | very_high | no/default | blocked/default | blocked/default | Post-MVP |
| slack_export | very_high | no/default | blocked/default | blocked/default | Company data risk |

## Adapter-specific Boundaries

### ChatGPT / Claude / Gemini Exports

Allowed:

- conversation title
- user messages
- assistant messages as context
- timestamps
- user-selected subset
- safe summary seeds

Default excluded:

- attachments
- hidden system metadata
- secrets pasted into prompts
- third-party private data inside conversations
- roleplay / AI companion logs from automatic Memory creation

Special rule:

AI chat logs are not automatically treated as truth. They are evidence of what the user discussed or explored, not evidence that the discussed event happened.

### LINE / DM

Allowed:

- relationship summary
- shared event summary
- user's own feeling or action
- date range

Default excluded:

- other person's raw messages
- other person's secrets
- medical / money / sexual / family trouble details
- blame evidence search

Special rule:

Adapter must preserve speaker separation. If speaker cannot be resolved, output must be high-risk and summary-only.

### Photos

MVP should prefer metadata only.

Allowed:

- date
- coarse location
- album name if safe
- user-provided caption
- event grouping

Forbidden by default:

- face recognition
- child profiling
- location precision without consent
- other person identity inference
- image LLM analysis at import time

### GitHub

GitHub can be personal context but also company risk.

Allowed:

- selected personal repo metadata
- commit dates
- commit messages after secret scan
- project phase summary
- user's own development timeline

Forbidden by default:

- private company code content
- credentials
- issue comments about coworkers as personality evidence
- customer / client information
- repo-wide code search as company search tool

## Runtime Job State

Adapter 実行は ImportJob の状態機械として扱う。

```ts
type AdapterJobState =
  | 'created'
  | 'detected'
  | 'inspected'
  | 'awaiting_scope'
  | 'awaiting_approval'
  | 'planned'
  | 'extracting'
  | 'normalizing'
  | 'policy_evaluating'
  | 'indexing'
  | 'completed'
  | 'partial_completed'
  | 'failed'
  | 'cancelled';
```

State rules:

- `awaiting_scope` から `extracting` へ直接遷移してはいけない。
- `awaiting_approval` のまま background job を開始してはいけない。
- `failed` error は safeUserMessage と内部原因を分離する。
- `partial_completed` は成功扱いではなく、UIで「どこまで取り込んだか」を出す。
- Cancel は best-effort ではなく、以後の RawRecord / NormalizedRecord / Memory 作成を止める。

## Error Handling

```ts
type AdapterError = {
  code:
    | 'UNSUPPORTED_INPUT'
    | 'LOW_CONFIDENCE_SOURCE'
    | 'LIMIT_EXCEEDED'
    | 'MALFORMED_FILE'
    | 'SECRET_DETECTED'
    | 'POLICY_DENIED'
    | 'USER_SCOPE_REQUIRED'
    | 'USER_APPROVAL_REQUIRED'
    | 'COST_APPROVAL_REQUIRED'
    | 'SYNC_SCOPE_CHANGED'
    | 'DELETED_TOMBSTONE_MATCH'
    | 'PARTIAL_EXTRACTION'
    | 'INTERNAL_ADAPTER_ERROR';
  message: string;
  safeUserMessage: string;
  retryable: boolean;
};
```

Errors must not expose raw secrets, private text, or file contents.

## Deletion and Re-import

Adapter output must support deletion.

Requirements:

- Every RawRecord has contentHash.
- Every SourceRef has importJobId.
- externalId is stored when available.
- Deleting an import job can delete all linked RawRecord / NormalizedRecord / Memory candidates.
- Re-import must dedupe by sourceType + externalId or contentHash.
- If user deleted a record, re-import must not silently restore it.

```ts
type ImportTombstone = {
  userId: string;
  sourceType: SourceType;
  externalId?: string;
  contentHash?: string;
  deletedAt: string;
  deletionScope: 'raw_only' | 'normalized' | 'memory' | 'entire_import';
};
```

```ts
type AdapterDeletionSupport = {
  canDeleteByImportJobId: boolean;
  canDeleteByExternalId: boolean;
  canDeleteByContentHash: boolean;
  canPropagateSourceDeletion: boolean;
  tombstoneRequired: boolean;
};
```

Deletion rules:

- `entire_import` deletion は SourceRef / RawRecord / NormalizedRecord / Memory candidate / embeddings を対象にする。
- Memory に昇格済みのものは、ユーザーに「記憶本文も消すか、出典だけ外すか」を選ばせる。
- external service 側で消えたデータを、Memory OS が勝手に消すかは source ごとに決める。MVPでは自動削除しない。
- Re-import は tombstone を尊重する。
- Backup / Export は tombstone も含める。別環境で復元した時に削除済み記録が復活しないようにする。

## Security Requirements

Adapter は untrusted input parser である。

必須:

- Archive extraction は zip slip / path traversal を拒否する。
- MIME type は拡張子だけで信じない。
- HTML / Markdown は script / remote resource を無効化して扱う。
- CSV / spreadsheet は formula injection を sanitize する。
- Image / media metadata は precise location を default masked にする。
- Logs に raw text / secret / third-party private text を出さない。
- Parser crash は job failure に閉じ込め、他ユーザーの import に影響させない。
- Adapter runtime は最小権限にする。

禁止:

- Adapter が任意URLを内部ネットワークへ fetch すること。
- Adapter が外部サービスへ raw data を送ること。
- Adapter がユーザー承認なしにLLM providerへ本文を送ること。
- Adapter が secret scan 前に全文embeddingすること。

## Privacy Requirements

Adapter は「保存できるもの」を増やすより、「保存しない初期値」を明確にする。

Privacy defaults:

- third-party raw text: exclude or summary-only
- minor data: high-risk, no tip, no sharing default
- deceased / legacy data: warning + no impersonation
- corporate data: exclude default
- precise location: masked default
- face / identity inference: disabled default
- medical / mental / crisis: no proactive tip

Adapter は本人の記憶の入口であり、他人の秘密の保管庫ではない。

## Test Harness

Every Adapter must pass shared tests.

### Required Test Categories

1. Detect known safe fixture.
2. Refuse or inspect-only unknown fixture.
3. Secret is detected and not displayed.
4. Third-party private text is summary-only or excluded.
5. Company data is excluded by default.
6. Minor data is high-risk and no-tip.
7. Missing date is not invented.
8. Speaker ambiguity is not treated as fact.
9. Large input stops at limits with partial result.
10. Deleted tombstone is not resurrected on re-import.
11. Adapter output contains SourceRef.
12. Adapter output can be exported without raw secrets.
13. LLM eligibility is denied for blocked data.
14. Embedding eligibility is denied for unsafe raw.
15. Error messages do not leak sensitive content.
16. Manifest default permissions are not weaker than Policy defaults.
17. Approval gates are required for raw / LLM / embedding expansion.
18. Incremental sync stops when scopeFingerprint changes.
19. Idempotency prevents duplicate records without merging merely similar memories.
20. CSV / HTML / archive security fixtures are sanitized.

### Fixture Layout

```txt
fixtures/<adapter>/
  safe/
  risky-secret/
  risky-third-party/
  risky-corporate/
  risky-minor/
  risky-legacy/
  risky-roleplay/
  risky-surveillance/
  malformed/
  huge/
  unknown/
  security-archive-traversal/
  security-html-script/
  security-csv-formula/
```

## MVP Implementation Order

1. `manual_paste` adapter
2. `share_text` adapter
3. `chatgpt_export_subset` adapter
4. `line_text` adapter in summary-only mode
5. `google_calendar` adapter
6. `photos_metadata` adapter
7. `github_metadata` adapter

Do not start with Gmail / Slack / Discord full imports. They are useful but can easily break the product philosophy and safety boundary.

## Acceptance Criteria

Source Adapter SDK is ready when:

- Adapter interface compiles as TypeScript types.
- Adapter Manifest can be loaded before Adapter execution.
- One safe fixture can produce SourceRef + RawRecord + NormalizedRecord.
- One risky fixture is blocked before LLM / embedding.
- Import preview can show counts, date range, cost class, and exclusions.
- Policy Engine receives risk hints for every extracted record.
- User can select scope before extraction.
- Approval gates block raw / LLM / embedding expansion without explicit approval.
- Deletion tombstone prevents silent resurrection.
- Incremental sync respects scopeFingerprint and permissionFingerprint.
- No Adapter can bypass raw / LLM / embedding permissions.
- Tests include at least the 20 shared categories above.

## Non-goals

- Build a universal scraper.
- Parse every export format perfectly.
- Turn all chat logs into memories.
- Analyze personality at import time.
- Preserve every raw message forever.
- Make work search, password search, or surveillance easier.

## 結論

Source Adapter SDK は Memory OS の入口である。

入口でやるべきことは、人生を評価することではない。

安全に受け取り、危険を止め、出典と日付を守り、後から本人が探せる形にすること。

その先の意味づけは、ユーザーが求めた時にだけ、Policy Engine と Evidence に基づいて慎重に行う。
