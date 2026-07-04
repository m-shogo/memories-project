# Memory Query Language

## 目的

Memory Query Language (MQL) は、ユーザーの自然文質問を、記憶検索・安全フィルタ・時間範囲・人物関係・ソース制御へ変換するための内部検索仕様である。

ユーザーは自然に聞く。

- 妻ってどんな人？
- 去年の俺ならどう思う？
- 卒業式の後って何してた？
- 父と旅行した記録ある？
- ゲーム開発で悩んでた時期を見たい

内部では、これを明示的な検索条件に変換する。

## 最上位原則

**MQLは人生を評価しない。探し方を指定するだけ。**

## Query Object

```ts
type MemoryQuery = {
  queryText: string;
  intent: MemoryQueryIntent;
  subjects: QuerySubject[];
  timeRange?: TimeRangeQuery;
  sources?: SourceFilter;
  includeKinds?: MemoryKind[];
  excludeRiskClasses?: RiskClass[];
  safetyMode: SafetyMode;
  evidenceRequirement: EvidenceRequirement;
  sort: QuerySort;
  limit: number;
};
```

## Intent

```ts
type MemoryQueryIntent =
  | 'find_records'
  | 'summarize_period'
  | 'relationship_context'
  | 'past_self_perspective'
  | 'compare_periods'
  | 'source_lookup'
  | 'timeline_view'
  | 'meaning_reflection'
  | 'export_selection'
  | 'unknown';
```

## Subjects

```ts
type QuerySubject =
  | { type: 'self' }
  | { type: 'person'; personRefId?: string; nameHint: string }
  | { type: 'topic'; topicId?: string; nameHint: string }
  | { type: 'place'; nameHint: string }
  | { type: 'event'; nameHint: string }
  | { type: 'source'; sourceType: SourceType }
  | { type: 'time'; phrase: string };
```

## SafetyMode

```ts
type SafetyMode =
  | 'normal'
  | 'hide_sensitive'
  | 'summary_only'
  | 'owner_only'
  | 'red_team_strict';
```

デフォルトは `hide_sensitive`。

## EvidenceRequirement

```ts
type EvidenceRequirement =
  | 'any'
  | 'user_statement_preferred'
  | 'multi_source_preferred'
  | 'high_confidence_only'
  | 'no_ai_inference_only';
```

## QuerySort

```ts
type QuerySort =
  | 'relevance'
  | 'time_asc'
  | 'time_desc'
  | 'source_order'
  | 'user_pinned_first';
```

重要:

- `importance` sort は作らない
- AIが人生の重要度を順位付けしない
- 必要なら `user_pinned_first` を使う

## Natural Language Examples

### 「妻ってどんな人？」

```json
{
  "intent": "relationship_context",
  "subjects": [{ "type": "person", "nameHint": "妻" }],
  "includeKinds": ["relationship_context", "event", "experience", "thought"],
  "safetyMode": "summary_only",
  "evidenceRequirement": "user_statement_preferred",
  "sort": "relevance",
  "limit": 50
}
```

応答ルール:

- 妻本人の性格を断定しない
- ユーザーから見た関係性として答える
- LINE原文は出さない

### 「去年の俺ならどう思う？」

```json
{
  "intent": "past_self_perspective",
  "subjects": [{ "type": "self" }],
  "timeRange": { "type": "relative_year", "value": -1 },
  "safetyMode": "hide_sensitive",
  "evidenceRequirement": "user_statement_preferred",
  "sort": "relevance",
  "limit": 100
}
```

応答ルール:

- 過去の自分を演じない
- 危険発言は再現しない
- 当時の記録からの推測として答える

### 「卒業式の後」

```json
{
  "intent": "find_records",
  "subjects": [{ "type": "event", "nameHint": "卒業式" }],
  "includeKinds": ["fact", "event", "experience"],
  "safetyMode": "normal",
  "sort": "time_asc",
  "limit": 100
}
```

応答ルール:

- 大きなイベントだけでなく、焼肉、写真、帰り道、雑談なども拾う

### 「父ならなんて言う？」

```json
{
  "intent": "relationship_context",
  "subjects": [{ "type": "person", "nameHint": "父" }],
  "includeKinds": ["relationship_context", "thought", "decision", "experience"],
  "safetyMode": "summary_only",
  "evidenceRequirement": "multi_source_preferred",
  "sort": "relevance",
  "limit": 80
}
```

応答ルール:

- 父本人を再現しない
- 残された記録から見える価値観を参照する
- 「可能性があります」と明示

## Query Planning

自然文からMQLを作る手順。

```ts
parseNaturalQuery()
  -> detectIntent()
  -> resolveSubjects()
  -> resolveTimeRange()
  -> applyDefaultSafetyMode()
  -> applySourcePolicy()
  -> runSearch()
  -> buildEvidenceBundle()
  -> generateAnswer()
```

## Default Filters

常に除外。

- secrets
- credentials
- corporate confidential raw data
- third-party secrets
- child high-risk raw data
- hidden/deleted memories

デフォルト非表示。

- self-harm historical raw
- medical/mental raw
- grief raw
- romantic/sexual raw
- LINE/DM raw

## Search Sources

検索は複数エンジンを組み合わせる。

- lexical full text
- embedding semantic search
- date/time search
- source search
- person graph search
- topic graph search

## MQL is Internal

MQLはユーザーに直接見せない。

ただし、説明可能性として、どの範囲を検索したかは表示できる。

例:

> 2026年のChatGPT会話、LINE要約、旅行記録から探しました。医療・高感度記録は除外しています。

## Non-goals

- SQLのようなユーザー向け検索構文
- 人生重要度ランキング
- 人格診断
- 監視検索
- 他人分析

## 結論

MQLは、記憶体をただのEmbedding検索にしないための内部仕様である。

人間の自然な質問を、安全で説明可能な検索へ変換する。
