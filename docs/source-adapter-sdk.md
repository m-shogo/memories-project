# Source Adapter SDK

## 目的

Source Adapter SDK は、外部サービス・ファイル・共有テキスト・会話ログを Memory OS に取り込むための実装契約である。

このSDKの目的は「何でも深く読むこと」ではない。

**外部データを、人生の文脈として安全に、説明可能に、削除可能に、低コストで取り込むための境界を固定すること**である。

## 憲章との関係

Source Adapter は Memory Constitution v1 の下位仕様であり、以下を破ってはならない。

- ChatGPT / Claude / Character.AI の代替にならない
- 故人・家族・恋人・友人・キャラクターを演じるための人格素材を作らない
- 保存時に人生の重要度をAIが勝手に決めない
- 保存時は安全チェック、出典、日付、検索性を優先する
- 分析・意味づけ・人格傾向化はユーザー要求時だけ行う
- 他人の秘密、会社情報、未成年情報、故人情報を便利さのために取り込まない

## Adapter の責務

Adapter は、入力データを Memory OS の内部形式に橋渡しする薄い層である。

Adapter が行うこと:

1. source を検出する
2. ファイル・レコード・期間・件数を棚卸しする
3. secret / malware / company / third-party / minor / deceased risk を事前検査する
4. ユーザーに scope 選択可能な inspection summary を返す
5. 許可された範囲だけ RawRecord に変換する
6. RawRecord を検索可能な NormalizedRecord に正規化する
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

## SDK の基本構造

```ts
type SourceAdapter = {
  id: AdapterId;
  displayName: string;
  version: string;
  supportedSourceTypes: SourceType[];
  supportedInputKinds: SourceInputKind[];
  capabilities: AdapterCapabilities;

  detect(input: AdapterInput, context: AdapterContext): Promise<DetectResult>;
  inspect(input: AdapterInput, context: AdapterContext): Promise<ImportInspection>;
  plan(input: AdapterInput, inspection: ImportInspection, scope: ImportScope, context: AdapterContext): Promise<ImportPlan>;
  extract(input: AdapterInput, plan: ImportPlan, context: AdapterContext): AsyncIterable<RawRecordDraft>;
  normalize(record: RawRecordDraft, context: AdapterContext): Promise<NormalizedRecordDraft>;
  finalize?(result: AdapterRunResult, context: AdapterContext): Promise<AdapterFinalizeResult>;
};
```

既存 Import Specification の `detect / inspect / extract / normalize` を拡張し、実装時に必要な `plan / finalize` を追加する。

`plan` は、ユーザーが選んだ範囲とポリシーを実際の処理単位へ変換する段階である。これにより、inspect 後に勝手に全解析へ進むことを防ぐ。

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

命名規則:

- `provider.source.variant.version`
- 破壊的な挙動変更は `v2` にする
- 同じ sourceType でも、raw本文を扱うAdapterとmetadata only Adapterは分ける
- unknown は必ず inspect only にする

## AdapterCapabilities

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

重要:

- `canReadRawText: true` は高リスク capability として扱う
- 写真Adapterは、MVPでは `canReadImages: false`, `canReadMetadataOnly: true` を標準にする
- Gmail / Slack / work chat は高リスクのため、初期MVPでは inspect only または selected event summary only に限定する

## AdapterInput

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
```

Adapter は `path` を直接信用してはならない。

- zip slip 対策を行う
- symlink を展開しない
- hidden file を自動解析しない
- 実行ファイルを実行しない
- archive 内 archive は深さ制限を持つ

## AdapterContext

```ts
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

Adapter はグローバル設定や環境変数へ直接依存しない。

すべての安全判定・予算・時刻・ログは context から受け取る。

## DetectResult

```ts
type DetectResult = {
  sourceType: SourceType | 'unknown';
  adapterId: AdapterId;
  confidence: number; // 0-100
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

判定ルール:

- confidence < 40: `unknown.inspect_only.v1`
- 40 <= confidence < 70: inspect only。extract不可
- 70 <= confidence: inspect可能
- sourceType が work / company / secret heavy の場合、confidence に関係なく追加承認を要求する

## ImportInspection 拡張

```ts
type AdapterInspection = ImportInspection & {
  adapterId: AdapterId;
  files: FileInventoryItem[];
  recordPreview: RecordPreview[];
  riskSummary: AdapterRiskSummary;
  policyBlocks: PolicyBlock[];
  scopeOptions: ImportScopeOption[];
  costEstimate: AdapterCostEstimate;
  defaultPlan: 'metadata_only' | 'summary_only' | 'raw_allowed' | 'inspect_only' | 'reject';
};
```

Inspection は、ユーザーへ見せるための段階であり、深い分析ではない。

Inspection で許されること:

- 件数を数える
- 期間を推定する
- ファイル種別を棚卸しする
- サンプル数件だけ安全にpreviewする
- secret / risk / third-party / company / minor / deceased を検出する
- コスト帯を見積もる

Inspection で禁止すること:

- 人格傾向を出す
- 人間関係を評価する
- 「重要な記憶」を決める
- 感情分析を大量実行する
- LLMへ全文を送る
- 他人の発言を長文previewする

## FileInventoryItem

```ts
type FileInventoryItem = {
  fileId: string;
  originalName: string;
  normalizedPath: string;
  mediaType?: string;
  byteSize: number;
  sha256: string;
  detectedKind:
    | 'conversation'
    | 'message_export'
    | 'calendar'
    | 'photo_metadata'
    | 'note'
    | 'post_archive'
    | 'repo_metadata'
    | 'unknown'
    | 'ignored';
  detectedRange?: DateRange;
  estimatedRecords?: number;
  defaultAction: 'include' | 'exclude' | 'metadata_only' | 'needs_review';
  reasons: string[];
};
```

## RecordPreview

```ts
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

Preview はユーザーのスコープ選択を助けるためのもの。記憶の意味づけではない。

第三者発言、未成年情報、会社情報、secret候補は redaction 済みの `safeSnippet` のみ表示する。

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

type ImportMode =
  | 'inspect_only'
  | 'metadata_only'
  | 'summary_only'
  | 'owner_text_only'
  | 'raw_extract_allowed';
```

推奨default:

| Source | Default Mode | 理由 |
|---|---|---|
| manual/share_text | summary_only | ユーザー明示入力で安全だが、secret scan は必要 |
| ChatGPT export subset | owner_text_only | assistant文は出典、人格素材化を避ける |
| LINE text export | summary_only | 第三者発言が多い |
| Google Photos | metadata_only | 顔・位置・未成年リスクが高い |
| Google Calendar | metadata_only / summary_only | 人生イベント化しやすいが会社予定混入に注意 |
| GitHub selected repo | metadata_only | 会社情報・secret混入に注意 |
| Slack / Gmail | inspect_only | MVPでは高リスク |
| unknown | inspect_only | source未確定のため |

## RawRecordDraft

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
```

Draft にはDB採番IDを持たせない。

永続化層が `SourceRef / RawRecord / Evidence` を確定させる。

## NormalizedRecordDraft

```ts
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

正規化の目的は検索性であり、人生評価ではない。

例:

- `ラーメン食べた` を低価値扱いしない
- `卒業式後の写真` を大イベントとして押し付けない
- `帰り道に見た空` を捨てない
- `焼肉` を将来の文脈候補として普通に検索可能にする

## RiskClass 拡張候補

既存 RiskClass に加えて、Adapter 層では以下の検出カテゴリを内部的に扱う。

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

`raw_personality_material` は、本人シミュレーションやAI恋人化に転用されやすい長文会話・口調データに付与する。

`roleplay_or_character_ai_material` は、Character.AI 的なロールプレイログを Memory OS の本人文脈と混ぜないために使う。

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

## Secret Scan 必須条件

Adapter は以下を最低限検出する。

- password / passcode / recovery code
- API key / access token / refresh token
- SSH private key / `.pem` / `.p12`
- OAuth token
- cookie / session id
- database URL
- credit card / bank account / identity document
- private address / phone number / email bundle
- `.env` / config / credential file

検出時の処理:

| Finding | Raw 保存 | Normalized | LLM | Embedding | User UI |
|---|---:|---:|---:|---:|---|
| API key | no | no | no | no | `除外しました` |
| password | no | no | no | no | `除外しました` |
| private key | no | no | no | no | `除外しました` |
| address | hidden/default | redacted | no/default | redacted only | `個人情報をマスクしました` |
| phone/email bundle | hidden/default | redacted | no/default | redacted only | `個人情報をマスクしました` |

Secret は「人生の文脈」ではなく事故原因である。

## Company Data Boundary

会社情報は Memory OS の対象外を原則とする。

Adapter は以下を検出したら exclude / inspect only を優先する。

- work Slack / Teams / Gmail
- 顧客名簿
- issue / ticket / support logs
- repository secrets
- private roadmap
- sales / financial / HR data
- NDA / contract
- 社外秘資料

例外的に扱ってよいもの:

- ユーザー本人の仕事上の転機
- 自分の職能・学習・制作履歴
- 公開OSSのcommit metadata
- 公開登壇や公開記事

保存形式は、会社の秘密ではなくユーザーの人生文脈に丸める。

例:

```txt
2026年春ごろ、ユーザーはフロントエンド設計とAIエージェント運用に強い関心を持っていた。
```

## Third-party Boundary

Adapter は speaker を可能な限り分離する。

```ts
type SpeakerRef = {
  role: 'user' | 'assistant' | 'third_party' | 'system' | 'unknown';
  displayName?: string;
  stableHash?: string;
  relationshipHint?: string;
};
```

制約:

- third_party の displayName は必要最小限
- third_party の発言原文は原則保存しない
- third_party の秘密は memory candidate にしない
- relationshipHint は「ユーザーから見た関係性」に限定する
- 相手の性格・病気・嘘・浮気・弱点を推測するためのindexを作らない

## Minor / Family / Deceased Boundary

Adapter は、未成年・家族・故人の情報を自動で深く扱わない。

### 未成年

- 顔・学校・住所・位置情報は default exclude / redact
- 子どもの性格固定につながる要約は禁止
- 成長記録は保護者の明示承認がある場合のみ最小化して保存

### 家族

- 家族イベントは保存可能
- 家族の秘密・診断・責任追及材料は保存しない
- 家族共有 export には混入させない

### 故人

- 故人の記録は追悼・整理・出典保持として扱う
- 故人の口調・人格を再現する素材化は禁止
- `deceased_person_data` は raw_personality_material と組み合わせて高リスク扱いにする

## Character.AI / Roleplay Boundary

Character.AI や架空キャラクターとの会話は、ユーザーの人生文脈に影響する可能性がある。

ただし、キャラクター人格を Memory OS 内で再利用・再演してはならない。

Adapter 方針:

- sourceType は `character_ai` または `roleplay_or_character_ai_material` として分離
- キャラクターの口調・台詞集・人格設定をMemory化しない
- ユーザー側の嗜好・創作関心・当時の支えとして要約する
- AI恋人化・依存強化に見える再提示をしない

許容例:

```txt
当時、ユーザーは架空キャラクターとの物語的な会話を、創作や気分転換として使っていた可能性がある。
```

禁止例:

```txt
このキャラクターは今後あなたにこう話しかけます。
```

## Cost Guard

Adapter は inspect 時点で cost class を返す。

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

Cost guard の原則:

- 保存前の棚卸しは低コストにする
- 大量ログは sampling / metadata only を先に提示する
- embedding は redacted searchableText に限定する
- ユーザーが求めていない分析にトークンを使わない
- 無料プランでは大容量 import を分割・待機・上限提示する
- コスト攻撃を避けるため、同一巨大ファイル・高重複・高エントロピーblobを検出する

## Deduplication / Idempotency

Adapter は再インポートで重複しないよう stable hash を作る。

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

Hash 方針:

- 原文そのものではなく正規化済みcontentをhash化する
- redaction前後のhashを混ぜない
- third_party displayName は直接hashに入れず、stableHashに丸める
- タイムゾーン差異を吸収できるよう occurredAt normalization を行う

## Deletion Hooks

Adapter は削除しやすい単位を壊してはならない。

各 RawRecord / NormalizedRecord / Memory は以下を辿れる必要がある。

```txt
Memory -> Evidence -> NormalizedRecord -> RawRecord -> SourceRef -> ImportJob -> AdapterId
```

削除要件:

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

すべてのAdapterは以下のテストを持つ。

### Required Tests

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

### Golden Fixtures

Adapter は small / medium / risky の3種類のfixtureを持つ。

```txt
fixtures/adapters/{adapterId}/small
fixtures/adapters/{adapterId}/medium
fixtures/adapters/{adapterId}/risky
```

`risky` fixture には、本物のsecretや実在個人情報を入れてはならない。必ず synthetic token を使う。

## MVP Adapter Priority

### P0

1. `manual.share_text.v1`
2. `manual.paste.v1`
3. `generic.conversation_text.v1`
4. `openai.chatgpt_export.v1` subset
5. `unknown.inspect_only.v1`

### P1

1. `line.text_export.v1` summary only
2. `google.calendar.v1` metadata / event summary
3. `google.photos_metadata.v1` metadata only
4. `x.archive_public_posts.v1`
5. `github.selected_repo_metadata.v1`

### P2

1. `anthropic.claude_export.v1`
2. `notion.selected_pages.v1`
3. `obsidian.markdown_subset.v1`
4. `apple_notes.selected_export.v1`
5. `day_one.export.v1`

### Blocked / Deferred

1. Gmail full import
2. Slack full import
3. Work chat full import
4. Photo face recognition
5. Voice full transcription
6. Password manager import
7. Full device backup import

## Adapter Review Checklist

新しいAdapterを追加する前に、以下を確認する。

- そのsourceは人生文脈に必要か
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

入口が強すぎると、サービスは監視・診断・人格再現・会社検索・AI恋人へ崩れる。

入口が弱すぎると、小さな記録が消え、人生の文脈が残らない。

したがって Adapter は、**保存時に評価しすぎず、安全・出典・日付・検索性・削除可能性を守る薄い境界層**として設計する。
