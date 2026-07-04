# Import Specification

## 目的

Import Specification は、外部サービスから受け取ったデータを、安全に、低コストで、人生の文脈として検索可能にするための仕様である。

このサービスの強みは「何でも読める」ことではない。

**何でも受け取れるが、危険なものを見分け、人生として扱える形に整えること**である。

## 基本方針

### Share First

MVPでは、ZIP一括インポートよりシェア入力を優先する。

理由:

- スマホで自然
- ユーザーが明示的に選んで渡す
- 範囲が小さく安全
- コストが読みやすい
- 初回ハードルが低い

### Inspect Before Analyze

アップロードされたファイルやアーカイブは、すぐにAI解析しない。

必ず先に棚卸しする。

- サービス種別
- ファイル数
- サイズ
- 期間
- データ種類
- 高感度カテゴリ
- 除外予定
- 解析候補

### Save First, Judge Later

保存時に人生の価値をAIが決めない。

ただし、安全のための除外は行う。

- パスワード
- APIキー
- トークン
- 会社機密
- 他人の秘密
- 高リスク原文

## Import Stages

```ts
type ImportStage =
  | 'received'
  | 'virus_or_malware_precheck'
  | 'safe_container_inspection'
  | 'source_detection'
  | 'file_inventory'
  | 'secret_scan'
  | 'risk_prefilter'
  | 'user_scope_selection'
  | 'raw_record_extraction'
  | 'normalization'
  | 'embedding_precheck'
  | 'embedding'
  | 'memory_indexing'
  | 'user_review'
  | 'completed'
  | 'failed'
  | 'cancelled';
```

## Universal Input Types

```ts
type SourceInputKind =
  | 'share_text'
  | 'share_url'
  | 'manual_paste'
  | 'uploaded_file'
  | 'uploaded_archive'
  | 'api_import'
  | 'local_export'
  | 'photo_metadata'
  | 'calendar_file'
  | 'conversation_log';
```

## Common Pipeline

```ts
receiveInput()
  -> inspectContainer()
  -> detectSource()
  -> scanSecrets()
  -> classifyRisk()
  -> showInspectionUI()
  -> userSelectsScope()
  -> extractRawRecords()
  -> normalizeRecords()
  -> createSourceRefs()
  -> createEmbeddingsIfAllowed()
  -> indexForSearch()
  -> optionalMemoryCandidateReview()
```

## Source Detection

Adapterは、入力データがどのサービス由来かを検出する。

```ts
type DetectResult = {
  sourceType: SourceType | 'unknown';
  confidence: number;
  matchedFiles: string[];
  warnings: string[];
};
```

検出confidenceが低い場合、深い解析をしない。

unknownはinspect only。

## SourceType

```ts
type SourceType =
  | 'chatgpt'
  | 'claude'
  | 'gemini'
  | 'poe'
  | 'character_ai'
  | 'x_archive'
  | 'line_export'
  | 'discord_export'
  | 'slack_export'
  | 'gmail_takeout'
  | 'google_photos_takeout'
  | 'apple_photos_export'
  | 'google_calendar'
  | 'apple_calendar'
  | 'github'
  | 'notion'
  | 'obsidian'
  | 'day_one'
  | 'journey'
  | 'bear_notes'
  | 'apple_notes'
  | 'manual'
  | 'unknown';
```

## Adapter Contract

```ts
type ImportAdapter = {
  sourceType: SourceType;
  detect(input: ImportInput): Promise<DetectResult>;
  inspect(input: ImportInput): Promise<ImportInspection>;
  extract(input: ImportInput, scope: ImportScope): AsyncIterable<RawRecord>;
  normalize(record: RawRecord): Promise<NormalizedRecord>;
};
```

## ImportInspection

```ts
type ImportInspection = {
  sourceType: SourceType | 'unknown';
  detectedRange?: {
    start?: string;
    end?: string;
  };
  counts: {
    conversations?: number;
    messages?: number;
    posts?: number;
    photos?: number;
    videos?: number;
    files?: number;
    calendarEvents?: number;
    commits?: number;
    notes?: number;
  };
  sensitiveFindings: SensitiveFinding[];
  excludedByDefault: ExclusionPreview[];
  recommendedScopes: ImportScopeSuggestion[];
  estimatedCostClass: 'free_or_tiny' | 'low' | 'medium' | 'high' | 'requires_credit';
};
```

## SourceごとのMVP優先度

### P0: MVP必須

- share_text
- manual_paste
- shared_url
- ChatGPT exported conversation subset
- generic conversation text

### P1: 早期対応

- X archive public posts
- LINE text export / pasted chat
- Google Calendar
- GitHub selected repo metadata
- Google Photos metadata only

### P2: 後続

- Claude export
- Gemini export / Takeout if available
- Poe shared logs
- Character.AI shared/copied logs
- Notion selected page
- Obsidian markdown vault subset

### P3: 慎重対応

- Gmail
- Slack
- Discord
- Apple Photos
- Apple Notes
- Day One / Journey
- AI companion logs

## Sourceごとの基本方針

### ChatGPT / Claude / Gemini

扱うもの:

- 会話タイトル
- 本人入力
- AI応答
- 日付
- 会話単位

注意:

- 添付ファイルは初期除外
- 全履歴Embeddingしない
- 最近・選択・検索対象から開始

### LINE

扱うもの:

- 自分と相手の会話
- 日付
- 会話の塊

注意:

- 相手発言は第三者情報
- 原文保存は非推奨
- safe summary優先
- スタンプは基本メタデータ
- 画像/動画は初期除外

### X Archive

扱うもの:

- 自分の公開投稿
- 投稿日時
- 返信/引用の文脈

注意:

- DMは初期除外
- 住所録や広告推定情報は除外
- 他人への攻撃は原文拡散しない

### Google Photos / Apple Photos

扱うもの:

- メタデータ
- アルバム
- 日付
- 大まかな場所
- イベント単位

注意:

- 画像本体保存しない
- 顔認識しない
- 代表画像解析のみ
- 子ども写真は高感度

### GitHub

扱うもの:

- repo metadata
- commit message
- PR/Issue title/body
- release notes

注意:

- private repoは選択式
- secrets除外
- code全文は基本対象外
- 会社repoは慎重

### Gmail / Slack / Discord

扱うもの:

- 初期MVPでは原則非推奨
- ユーザー本人の人生イベントや仕事観のみ

注意:

- 第三者情報が非常に多い
- 会社情報混入
- 原文保存しない

## RawRecord

```ts
type RawRecord = {
  id: string;
  sourceType: SourceType;
  sourceRefId: string;
  recordType:
    | 'message'
    | 'conversation'
    | 'post'
    | 'photo_metadata'
    | 'calendar_event'
    | 'commit'
    | 'issue'
    | 'note'
    | 'document'
    | 'unknown';
  occurredAt?: string;
  speaker?: 'user' | 'assistant' | 'third_party' | 'system' | 'unknown';
  text?: string;
  metadata?: Record<string, unknown>;
  contentHash: string;
  rawRiskFlags: RawRiskFlag[];
};
```

## NormalizedRecord

```ts
type NormalizedRecord = {
  id: string;
  sourceType: SourceType;
  sourceRefId: string;
  occurredAt?: string;
  canonicalText?: string;
  searchableText?: string;
  displayText?: string;
  speakerRole?: string;
  peopleHints: string[];
  timeHints: string[];
  placeHints: string[];
  topicHints: string[];
  safetyFlags: SafetyFlag[];
  llmEligibility: 'allowed' | 'masked' | 'summary_only' | 'forbidden';
  embeddingEligibility: 'allowed' | 'masked' | 'forbidden';
};
```

## Security Requirements

- safe zip extraction
- zip bomb protection
- file count limit
- total size limit
- per-file size limit
- path traversal protection
- symlink rejection
- MIME validation
- extension allowlist
- secret scan before embedding
- prompt injection guard
- text sanitization
- no raw sensitive logs
- user_id scoping

## Cost Requirements

- no full archive LLM pass
- chunk only after scope selection
- embedding only after secret scan
- media metadata first
- image representative sampling
- dedupe by hash
- rate limit by account and source
- background queue for heavy imports

## UX Requirements

### Upload後すぐに出す画面

> このデータから見つかったもの
>
> - 会話: 1,240件
> - 画像: 300枚（今回は画像本体を読みません）
> - 高感度の可能性: LINE / 医療 / 他人の情報
> - 除外予定: パスワード候補、添付ファイル、第三者の秘密

### Scope Selection

- 最近100件だけ
- 自分の発言だけ
- 公開投稿だけ
- DM除外
- 画像本体除外
- 医療/恋愛/家族を除外
- 原文保存しない

## Output

インポートの成果は、最初から「分析結果」ではない。

MVPでは以下を作る。

- SourceRef
- RawRecord metadata
- NormalizedRecord
- Embedding if allowed
- Search index
- Optional MemoryCandidate

## Non-goals

- 全文倉庫
- 会社検索
- パスワード保管
- 自動人格分析
- 故人再現
- 画像全量解析
- Gmail全量解析

## 結論

Importは、このサービスの入口であり最大の危険点である。

最初から、何でも解析する入口ではなく、何を受け取り、何を除外し、何を検索可能にするかを制御する入口として設計する。
