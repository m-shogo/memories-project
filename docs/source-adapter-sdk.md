# Source Adapter SDK

## 目的

Source Adapter SDK は、外部サービス・ファイル・共有テキスト・会話ログを Memory OS に取り込むための実装契約である。

目的は「何でも深く読むこと」ではない。外部データを、人生の文脈として安全に、説明可能に、削除可能に、低コストで取り込むための入口境界を固定することである。

## 上位原則

Adapter は Memory Constitution v1 / Import Specification / Third Party Data Policy / Memory Schema v1 の下位仕様である。

守ること:

- ChatGPT / Claude / Character.AI の代替にならない
- 故人・家族・恋人・友人・キャラクターを演じるための人格素材を作らない
- 保存時に人生の重要度をAIが勝手に決めない
- 保存時は安全チェック、出典、日付、検索性を優先する
- 分析・意味づけ・人格傾向化はユーザー要求時だけ行う
- 他人の秘密、会社情報、未成年情報、故人情報を便利さのために取り込まない
- 小さな記録を捨てないが、大きなイベントとして押し付けない

## Adapter の責務

Adapter が行うこと:

1. source を検出する
2. ファイル・レコード・期間・件数を棚卸しする
3. secret / company / third-party / minor / deceased / roleplay risk を事前検査する
4. ユーザーに scope 選択可能な inspection summary を返す
5. 許可された範囲だけ RawRecord draft に変換する
6. 検索可能な NormalizedRecord draft に正規化する
7. SourceRef / Evidence に必要な出典情報を保持する
8. 削除・再インポート・差分同期に必要な contentHash を作る

Adapter が行ってはいけないこと:

1. 人生の重要度を順位付けする
2. 人格診断・相性診断・親子診断・恋人診断を生成する
3. 故人や家族の本人シミュレーション用 profile を作る
4. 相手の秘密をユーザーの記憶価値として保存する
5. 会社情報検索、顧客情報検索、同僚分析に使える形で保存する
6. 保存前にLLMへ全文を送る
7. unknown source を深く解析する
8. コスト見積もりなしに embedding / LLM 処理へ進む

## SDK Contract

```ts
type SourceAdapter = {
  id: AdapterId;
  displayName: string;
  version: string;
  supportedSourceTypes: SourceType[];
  supportedInputKinds: SourceInputKind[];
  capabilities: AdapterCapabilities;

  detect(input: AdapterInput, context: AdapterContext): Promise<DetectResult>;
  inspect(input: AdapterInput, context: AdapterContext): Promise<AdapterInspection>;
  plan(input: AdapterInput, inspection: AdapterInspection, scope: ImportScope, context: AdapterContext): Promise<ImportPlan>;
  extract(input: AdapterInput, plan: ImportPlan, context: AdapterContext): AsyncIterable<RawRecordDraft>;
  normalize(record: RawRecordDraft, context: AdapterContext): Promise<NormalizedRecordDraft>;
  finalize?(result: AdapterRunResult, context: AdapterContext): Promise<AdapterFinalizeResult>;
};
```

既存 Import Specification の `detect / inspect / extract / normalize` に、ユーザー選択後の処理計画である `plan` を追加する。`plan` がないAdapterは、inspect後に勝手に全解析へ進みやすいため禁止する。

## AdapterId

```ts
type AdapterId =
  | 'manual.share_text.v1'
  | 'manual.paste.v1'
  | 'generic.conversation_text.v1'
  | 'openai.chatgpt_export.v1'
  | 'anthropic.claude_export.v1'
  | 'google.calendar.v1'
  | 'google.photos_metadata.v1'
  | 'line.text_export.v1'
  | 'x.archive_public_posts.v1'
  | 'github.selected_repo_metadata.v1'
  | 'notion.selected_pages.v1'
  | 'unknown.inspect_only.v1';
```

命名は `provider.source.variant.version`。同じ sourceType でも、raw本文を扱うAdapterとmetadata only Adapterは分ける。unknown は必ず inspect only にする。

## Capabilities

```ts
type AdapterCapabilities = {
  canReadRawText: boolean;
  canReadAttachments: boolean;
  canReadImages: boolean;
  canReadMetadataOnly: boolean;
  canDetectSpeakers: boolean;
  canDetectTimeRange: boolean;
  canGenerateStableExternalIds: boolean;
  canIncrementalSync: boolean;
  supportsDryRun: boolean;
  supportsUserScopedExtraction: boolean;
  requiresNetwork: boolean;
  maxRecommendedInputBytes: number;
};
```

`canReadRawText: true` は高リスク capability として扱う。写真AdapterはMVPでは `canReadImages: false`, `canReadMetadataOnly: true` を標準にする。Gmail / Slack / work chat は初期MVPでは inspect only または selected event summary only に限定する。

## Input / Context

```ts
type AdapterInput = {
  importJobId: string;
  userId: string;
  inputKind: SourceInputKind;
  files?: AdapterFileRef[];
  text?: string;
  url?: string;
  metadata?: Record<string, unknown>;
  receivedAt: string;
};

type AdapterFileRef = {
  id: string;
  path: string;
  originalName: string;
  mediaType?: string;
  byteSize: number;
  sha256: string;
  containerPath?: string;
};

type AdapterContext = {
  now: string;
  userLocale?: string;
  defaultTimezone?: string;
  policy: PolicySnapshot;
  costBudget: CostBudget;
  secrets: SecretScanService;
  risk: RiskClassifier;
  hashing: HashService;
  logger: AdapterLogger;
};
```

Adapter は `path` を信用しない。zip slip、symlink、実行ファイル、archive内archive、hidden file、大容量ファイル、高エントロピーblobを安全検査する。

## Detection

```ts
type DetectResult = {
  sourceType: SourceType | 'unknown';
  adapterId: AdapterId;
  confidence: number;
  matchedFiles: string[];
  matchedSignals: DetectSignal[];
  warnings: AdapterWarning[];
  nextAction: 'inspect_allowed' | 'inspect_only' | 'reject';
};

type DetectSignal = {
  kind: 'filename' | 'schema' | 'header' | 'metadata' | 'text_pattern' | 'user_declared';
  value: string;
  confidenceImpact: number;
};
```

判定:

- confidence < 40: `unknown.inspect_only.v1`
- 40 <= confidence < 70: inspect only、extract不可
- 70 <= confidence: inspect可能
- work / company / secret heavy source は confidence に関係なく追加承認

## Inspection

```ts
type AdapterInspection = ImportInspection & {
  adapterId: AdapterId;
  files: FileInventoryItem[];
  recordPreview: RecordPreview[];
  riskSummary: AdapterRiskSummary;
  policyBlocks: PolicyBlock[];
  scopeOptions: ImportScopeOption[];
  costEstimate: AdapterCostEstimate;
  defaultPlan: 'metadata_only' | 'summary_only' | 'owner_text_only' | 'raw_allowed' | 'inspect_only' | 'reject';
};
```

Inspection で許すこと:

- 件数・期間・ファイル種別の棚卸し
- サンプル数件の安全preview
- secret / company / third-party / minor / deceased / roleplay risk の検出
- コスト帯の見積もり

Inspection で禁止すること:

- 人格傾向を出す
- 人間関係を評価する
- 重要な記憶を決める
- 感情分析を大量実行する
- LLMへ全文を送る
- 他人の発言を長文previewする

## Preview / Inventory

```ts
type FileInventoryItem = {
  fileId: string;
  originalName: string;
  normalizedPath: string;
  mediaType?: string;
  byteSize: number;
  sha256: string;
  detectedKind: 'conversation' | 'message_export' | 'calendar' | 'photo_metadata' | 'note' | 'post_archive' | 'repo_metadata' | 'unknown' | 'ignored';
  detectedRange?: DateRange;
  estimatedRecords?: number;
  defaultAction: 'include' | 'exclude' | 'metadata_only' | 'needs_review';
  reasons: string[];
};

type RecordPreview = {
  previewId: string;
  sourceFileId?: string;
  occurredAt?: string;
  speakerRole?: 'user' | 'assistant' | 'third_party' | 'system' | 'unknown';
  safeSnippet: string;
  redactions: Redaction[];
  riskFlags: RiskClass[];
};
```

Preview はユーザーのスコープ選択を助けるためのもので、記憶の意味づけではない。第三者発言、未成年情報、会社情報、secret候補は redaction 済みの `safeSnippet` のみ表示する。

## ImportPlan

```ts
type ImportPlan = {
  id: string;
  importJobId: string;
  adapterId: AdapterId;
  sourceType: SourceType | 'unknown';
  mode: ImportMode;
  scope: ImportScope;
  policySnapshotId: string;
  expectedRecords: number;
  expectedRawStorageBytes: number;
  estimatedCost: AdapterCostEstimate;
  llmUse: LlmUsePolicy;
  embeddingUse: EmbeddingUsePolicy;
  rawRetentionPolicy: RawRetentionPolicy;
  exclusionRules: ImportExclusionRule[];
  createdAt: string;
};

type ImportMode = 'inspect_only' | 'metadata_only' | 'summary_only' | 'owner_text_only' | 'raw_extract_allowed';
```

Default mode:

| Source | Default | 理由 |
|---|---|---|
| manual/share_text | summary_only | ユーザー明示入力だがsecret scan必須 |
| ChatGPT export subset | owner_text_only | assistant文を人格素材化しない |
| LINE text export | summary_only | 第三者発言が多い |
| Google Photos | metadata_only | 顔・位置・未成年リスクが高い |
| Google Calendar | metadata_only / summary_only | 会社予定混入に注意 |
| GitHub selected repo | metadata_only | 会社情報・secret混入に注意 |
| Slack / Gmail | inspect_only | MVPでは高リスク |
| unknown | inspect_only | source未確定 |

## Record Drafts

```ts
type RawRecordDraft = {
  userId: string;
  sourceRefDraft: SourceRefDraft;
  importJobId: string;
  externalId?: string;
  recordType: RawRecordType;
  occurredAt?: string;
  speaker?: SpeakerRef;
  text?: string;
  metadata?: Record<string, unknown>;
  contentHash: string;
  riskFlags: RiskClass[];
  rawStoragePolicy: RawStoragePolicy;
  redactions: Redaction[];
};

type NormalizedRecordDraft = {
  userId: string;
  rawContentHash: string;
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
  normalizationNotes: string[];
};
```

正規化の目的は検索性であり、人生評価ではない。ラーメン、焼肉、帰り道、卒業式後の写真、何気ない会話を低価値扱いしない。一方で、大きなイベントを勝手に人生の中心へ押し上げない。

## Adapter Risk Classes

```ts
type AdapterRiskClass =
  | 'secret_or_credential'
  | 'company_confidential'
  | 'third_party_private'
  | 'minor_data'
  | 'deceased_person_data'
  | 'medical_or_mental_health'
  | 'financial_private'
  | 'sexual_or_romantic_private'
  | 'location_sensitive'
  | 'surveillance_or_evidence_seeking'
  | 'harassment_or_blame_material'
  | 'self_harm_or_violence'
  | 'identity_document'
  | 'raw_personality_material'
  | 'roleplay_or_character_ai_material'
  | 'copyright_heavy_content'
  | 'unknown_high_entropy_blob';
```

`raw_personality_material` は、本人シミュレーションやAI恋人化に転用されやすい長文会話・口調データに付与する。`roleplay_or_character_ai_material` は、架空キャラ会話を本人文脈と混ぜないために使う。

## LLM / Embedding Eligibility

```ts
type LlmUsePolicy = {
  allowed: boolean;
  mode: 'none' | 'redacted_summary_only' | 'selected_records_only' | 'full_text_allowed';
  reason: string;
};

type EmbeddingUsePolicy = {
  allowed: boolean;
  textSource: 'none' | 'searchableText' | 'displayText' | 'redactedSummary';
  reason: string;
};
```

原則:

- secret候補: LLM不可、embedding不可
- 会社情報: LLM不可、embedding不可
- 他人の秘密: LLM不可、embedding不可
- LINE/DM相手発言: 原則 redacted summary only
- 写真: metadata only。顔認識embeddingは禁止
- Character.AIログ: 本人文脈と混ぜない。roleplay archive として隔離または除外

## Secret / Company / Third-party Boundary

Secret は人生の文脈ではなく事故原因として扱う。password、API key、token、SSH key、cookie、DB URL、identity document、`.env` は保存・LLM・embeddingすべて不可を原則にする。

会社情報は Memory OS の対象外を原則とする。work Slack、Teams、Gmail、顧客情報、private roadmap、契約、NDA、社外秘、repository secret は exclude / inspect only を優先する。例外は、ユーザー本人の仕事上の転機、公開OSSのcommit metadata、公開登壇、公開記事などに限定する。

第三者データは、相手そのものではなくユーザーから見た関係性・出来事・影響だけを扱う。相手の秘密、病気、金銭、恋愛、家庭、性、メンタル、嘘、浮気、弱点を推測するindexを作らない。

```ts
type SpeakerRef = {
  role: 'user' | 'assistant' | 'third_party' | 'system' | 'unknown';
  displayName?: string;
  stableHash?: string;
  relationshipHint?: string;
};
```

`relationshipHint` は「ユーザーから見た関係性」に限定する。

## Minor / Family / Deceased Boundary

未成年:

- 顔・学校・住所・位置情報は default exclude / redact
- 子どもの性格固定につながる要約は禁止
- 成長記録は明示承認がある場合のみ最小化して保存

家族:

- 家族イベントは保存可能
- 家族の秘密・診断・責任追及材料は保存しない
- 家族共有 export には混入させない

故人:

- 故人の記録は追悼・整理・出典保持として扱う
- 故人の口調・人格を再現する素材化は禁止
- `deceased_person_data` と `raw_personality_material` の組み合わせは高リスク扱い

## Roleplay / Character.AI Boundary

架空キャラクターとの会話は、ユーザーの創作・嗜好・支えとして扱える場合がある。ただし、キャラクター人格を再利用・再演してはならない。

方針:

- sourceType は `character_ai` または `roleplay_or_character_ai_material` として分離
- キャラクターの口調・台詞集・人格設定をMemory化しない
- ユーザー側の嗜好・創作関心・当時の支えとして要約する
- AI恋人化・依存強化に見える再提示をしない

許容:

```txt
当時、ユーザーは架空キャラクターとの物語的な会話を、創作や気分転換として使っていた可能性がある。
```

禁止:

```txt
このキャラクターは今後あなたにこう話しかけます。
```

## Cost Guard

```ts
type AdapterCostEstimate = {
  class: 'free_or_tiny' | 'low' | 'medium' | 'high' | 'requires_credit' | 'blocked';
  estimatedInputBytes: number;
  estimatedRecords: number;
  estimatedTokens?: number;
  estimatedEmbeddingUnits?: number;
  requiresUserConfirmation: boolean;
  reasons: string[];
};
```

原則:

- 保存前の棚卸しは低コストにする
- 大量ログは sampling / metadata only を先に提示する
- embedding は redacted searchableText に限定する
- ユーザーが求めていない分析にトークンを使わない
- 無料プランでは大容量 import を分割・待機・上限提示する
- 同一巨大ファイル・高重複・高エントロピーblobを検出する

## Deduplication / Idempotency

```ts
type StableRecordKey = {
  sourceType: SourceType | 'unknown';
  adapterId: AdapterId;
  externalId?: string;
  occurredAt?: string;
  normalizedSpeakerHash?: string;
  contentHash: string;
};
```

原文そのものではなく正規化済みcontentをhash化する。third_party displayName は直接hashに入れず、stableHashに丸める。タイムゾーン差異を吸収できるよう occurredAt normalization を行う。

## Deletion Hooks

Adapter は次を辿れる形を壊してはならない。

```txt
Memory -> Evidence -> NormalizedRecord -> RawRecord -> SourceRef -> ImportJob -> AdapterId
```

削除単位:

- source単位削除
- importJob単位削除
- file単位削除
- conversation単位削除
- person/speaker hint単位の非表示
- rawのみ削除してsummary/searchableTextだけ残す
- embedding削除
- export除外

Adapter は、削除後に再生成できない interpretation を勝手に混ぜない。

## Adapter Test Contract

全Adapterに必須:

1. detect confidence test
2. unknown source inspect-only test
3. secret exclusion test
4. third-party redaction test
5. company data exclusion test
6. minor data minimization test
7. deceased simulation prevention test
8. roleplay separation test
9. cost estimate test
10. duplicate import idempotency test
11. deletion traceability test
12. malformed archive safety test
13. timezone normalization test
14. raw retention policy test
15. LLM / embedding eligibility test

fixture は `fixtures/adapters/{adapterId}/small|medium|risky` に置く。risky fixture に本物のsecretや実在個人情報を入れてはならない。

## MVP Priority

P0:

1. `manual.share_text.v1`
2. `manual.paste.v1`
3. `generic.conversation_text.v1`
4. `openai.chatgpt_export.v1` subset
5. `unknown.inspect_only.v1`

P1:

1. `line.text_export.v1` summary only
2. `google.calendar.v1` metadata / event summary
3. `google.photos_metadata.v1` metadata only
4. `x.archive_public_posts.v1`
5. `github.selected_repo_metadata.v1`

P2:

1. `anthropic.claude_export.v1`
2. `notion.selected_pages.v1`
3. `obsidian.markdown_subset.v1`
4. `apple_notes.selected_export.v1`
5. `day_one.export.v1`

Deferred:

1. Gmail full import
2. Slack full import
3. Work chat full import
4. Photo face recognition
5. Voice full transcription
6. Password manager import
7. Full device backup import

## Adapter Review Checklist

新しいAdapterを追加する前に確認する。

- 人生文脈に必要か
- ChatGPT代替・Character.AI化に寄っていないか
- 本人シミュレーション素材を作っていないか
- 他人の秘密を保存価値にしていないか
- 会社情報検索になっていないか
- 未成年・故人・家族データを最小化しているか
- 保存時に分析しすぎていないか
- SourceRef / Evidence / contentHash が残るか
- ユーザーが後から削除・非表示・export除外できるか
- 無料ユーザーでも破綻しない cost guard があるか
- unknown / malformed / huge / duplicate input に耐えるか

## 結論

Source Adapter SDK は、Memory OS の入口である。

入口が強すぎると、サービスは監視・診断・人格再現・会社検索・AI恋人へ崩れる。入口が弱すぎると、小さな記録が消え、人生の文脈が残らない。

したがって Adapter は、保存時に評価しすぎず、安全・出典・日付・検索性・削除可能性を守る薄い境界層として設計する。
