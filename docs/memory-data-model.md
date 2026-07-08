# Memory Data Model

> **Status: concept doc (superseded for implementation)**
>
> この文書は初期概念モデルとして残すが、実装契約ではない。
> 実装は `docs/db-table-design-v1.md` / `docs/migration-001-foundation-contract.md` / `docs/fable-review-and-db-hardening-addendum.md` に従う。
>
> 特に以下はこの文書の記述を使わないこと:
>
> - `privacyLevel: normal | sensitive | very_sensitive` → 物理enumは `owner_only | owner_sensitive | restricted`(mapping: normal→owner_only, sensitive→owner_sensitive, very_sensitive→restricted)。
> - `importance: low | medium | high (| core)` → DBカラムにしない。AI由来の優先度は `candidate_review_priority` としてレビュー列の並び替え専用。life score・人生の重要度判定への使用は禁止。
> - `MemoryCandidate`(AI自動抽出) → 保存時の自動解析は行わない。保存時はsafety check / source / date / provenance / searchability / user controlのみ。深い解析はユーザーが求めた時だけ。
> - `RawRecord.text`(DB内raw全文) → raw本文はDB text columnに置かず、object storage + `raw_object_ref` で扱う。
> - dedupe / tombstone / policy / RLS / export eligibilityはこのモデルに存在しないため、この文書だけを根拠に実装しない。

## 目的

このサービスはログ全文を集めるのではなく、人生の文脈として使える情報へ変換する。

そのため、データモデルは「元データ」ではなく「記憶」を中心にする。

## 基本単位

### Source

どこから来た情報か。

```ts
type SourceType =
  | 'manual'
  | 'share_text'
  | 'share_url'
  | 'chatgpt_export'
  | 'claude_export'
  | 'x_archive'
  | 'google_photos'
  | 'github'
  | 'notion'
  | 'google_drive'
  | 'calendar'
  | 'gmail';
```

### SourceRef

元データへの参照。

元データを必ず保存する必要はない。

```ts
type SourceRef = {
  id: string;
  sourceType: SourceType;
  externalId?: string;
  externalUrl?: string;
  title?: string;
  capturedAt?: string;
  importedAt: string;
  rawStored: boolean;
  rawStoragePath?: string;
};
```

### RawRecord

入力元を読み取り単位へ分解したもの。

例:

- ChatGPTの1会話
- Xの1投稿
- Googleフォトの1写真
- GitHubの1コミット
- Calendarの1予定

```ts
type RawRecord = {
  id: string;
  sourceRefId: string;
  recordType: 'conversation' | 'post' | 'photo' | 'commit' | 'event' | 'document' | 'note';
  occurredAt?: string;
  title?: string;
  text?: string;
  metadata?: Record<string, unknown>;
  contentHash?: string;
};
```

### MemoryCandidate

AIが抽出した保存候補。

ユーザー承認前。

```ts
type MemoryCandidate = {
  id: string;
  rawRecordIds: string[];
  title: string;
  summary: string;
  occurredAt?: string;
  confidence: number;
  importance: 'low' | 'medium' | 'high';
  categoryIds: string[];
  personIds: string[];
  topicIds: string[];
  placeIds: string[];
  emotionTags: string[];
  valueTags: string[];
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'auto_saved';
};
```

### Memory

確定保存された記憶。

```ts
type Memory = {
  id: string;
  title: string;
  summary: string;
  body?: string;
  occurredAt?: string;
  periodStart?: string;
  periodEnd?: string;
  sourceRefIds: string[];
  rawRecordIds?: string[];
  categoryIds: string[];
  personIds: string[];
  topicIds: string[];
  placeIds: string[];
  emotionTags: string[];
  valueTags: string[];
  importance: 'low' | 'medium' | 'high' | 'core';
  privacyLevel: 'normal' | 'sensitive' | 'very_sensitive';
  createdAt: string;
  updatedAt: string;
};
```

## 引き出し

記憶は引き出しに入る。

### Person

```ts
type Person = {
  id: string;
  displayName: string;
  relation?: string;
  aliases: string[];
  notes?: string;
  privacyLevel: 'normal' | 'sensitive' | 'very_sensitive';
};
```

### Topic

```ts
type Topic = {
  id: string;
  name: string;
  parentTopicId?: string;
  aliases: string[];
};
```

例:

- ゲーム
  - Unity
  - Godot
  - Steam
  - ドット絵
- 投資
  - 特殊状況
  - AI
  - 半導体
  - 宇宙

### Place

```ts
type Place = {
  id: string;
  name: string;
  type?: 'country' | 'city' | 'spot' | 'home' | 'work' | 'venue';
  aliases: string[];
};
```

### Value / Belief

単なる出来事ではなく、長期的な考え方。

```ts
type ValueBelief = {
  id: string;
  statement: string;
  evidenceMemoryIds: string[];
  firstSeenAt?: string;
  lastSeenAt?: string;
  confidence: number;
};
```

例:

- 家族を大事にしたい
- 新しい技術は触ってから判断する
- 思い出を残すことに価値を感じる
- 面倒なことは続かないので自動化したい

## Embedding

全文を毎回LLMに渡さない。

記憶、人物、トピック、価値観ごとにEmbeddingを持つ。

```ts
type EmbeddingIndex = {
  id: string;
  ownerType: 'memory' | 'person' | 'topic' | 'value_belief' | 'raw_record';
  ownerId: string;
  embeddingModel: string;
  contentHash: string;
  createdAt: string;
};
```

実際のベクトルはDBのvector型や外部vector storeで管理する。

## Tip

ホーム画面で出す発見。

コストを抑えるため、事前生成・キャッシュを基本にする。

```ts
type Tip = {
  id: string;
  title: string;
  body: string;
  tipType: 'on_this_day' | 'change_detected' | 'forgotten_memory' | 'person' | 'topic' | 'value_shift';
  relatedMemoryIds: string[];
  generatedAt: string;
  expiresAt?: string;
};
```

例:

- 去年の今日は、ゲームを完成させたいと言っていました。
- 最近、旅行の話題が増えています。
- 2026年のあなたは、思い出を残すことを強く意識していました。

## Query Flow

ユーザー質問:

> 去年の俺ならどう思う？

処理:

1. 質問から検索意図を抽出
2. 時期条件を抽出
3. 関連するMemory / Value / PersonをEmbedding検索
4. 必要な記憶だけLLMへ渡す
5. 回答生成
6. 回答には「推測」であることを明示

## 重要な制約

- 全文を毎回読ませない
- すべてのRawRecordを永続保存しない
- 高感度データはprivacyLevelを持つ
- ユーザーが削除した記憶は検索対象から外す
- エクスポート可能な形式を維持する
