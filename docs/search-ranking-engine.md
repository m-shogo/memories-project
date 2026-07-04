# Search & Ranking Engine

## 目的

Search & Ranking Engine は、Memory OS の記憶を安全に検索・発見・再提示するための設計である。

このエンジンは、人生の重要度を決めるものではない。

**検索順位は、ユーザーの現在のクエリに対する関連度・安全性・出典品質・時間文脈の組み合わせであり、人生価値ランキングではない。**

ラーメン、焼肉、帰り道、卒業式後の写真、何気ないメモも、検索時の文脈によって大切になる。

## 最上位原則

### 1. Ranking is relevance, not worth

順位は「今の検索にどれだけ合うか」であり、「人生でどれだけ大切か」ではない。

禁止表現:

- 一番大切な記憶
- あなたの人生TOP10
- 重要人物ランキング
- 最高/最低の年
- 価値が低い記憶

許可表現:

- この検索に近い記録
- 関連する記憶
- 同じ時期の記録
- 同じ出典から見つかった記録
- 根拠が強い記録

### 2. Safety filters before scoring

検索スコアを計算する前に Policy Engine を通す。

hidden / sealed / deleted / third-party private / minor / corporate / crisis は、検索対象・表示内容・引用可否が変わる。

### 3. Source and evidence visible

検索結果は、なぜ表示されたかを説明できる必要がある。

### 4. No surveillance search

検索は本人の人生文脈を探すためのもの。

他人の嘘・弱点・居場所・秘密・不倫・責任追及を探す検索は deny または redirect する。

## Search Pipeline

```txt
receive query
-> classify intent
-> policy precheck
-> build retrieval plan
-> retrieve candidates
-> apply visibility / lifecycle filters
-> apply safety filters
-> score candidates
-> diversify results
-> prepare safe snippets
-> explain ranking reasons
-> return results
-> audit high-risk queries
```

## Query Intent

```ts
type SearchIntent =
  | 'find_memory'
  | 'timeline_lookup'
  | 'source_lookup'
  | 'relationship_context'
  | 'preference_lookup'
  | 'decision_lookup'
  | 'recovery_pattern_lookup'
  | 'export_scope_selection'
  | 'debug_provenance'
  | 'surveillance_or_blame'
  | 'impersonation_request'
  | 'diagnosis_request'
  | 'unknown';
```

Forbidden or restricted intents:

| Intent | Decision |
|---|---|
| surveillance_or_blame | deny/redirect |
| impersonation_request | deny |
| diagnosis_request | deny safe alternative |
| source_lookup for secrets | deny |
| corporate search | deny or metadata-only personal context |

## Search Request

```ts
type MemorySearchRequest = {
  userId: string;
  query: string;
  intent?: SearchIntent;
  filters?: SearchFilters;
  limit: number;
  cursor?: string;
  includeSnippets: boolean;
  includeExplanations: boolean;
  requester: 'user' | 'system' | 'ai';
};
```

```ts
type SearchFilters = {
  dateRange?: DateRange;
  sourceTypes?: SourceType[];
  memoryKinds?: MemoryKind[];
  people?: string[];
  places?: string[];
  topics?: string[];
  visibility?: MemoryVisibility[];
  includeHidden?: boolean;
  includeSealed?: boolean;
  includeDeleted?: false;
  riskClasses?: RiskClass[];
};
```

Defaults:

- includeHidden: false
- includeSealed: false
- includeDeleted: false always
- includeSnippets: true for low risk only
- includeExplanations: true

## Retrieval Sources

```ts
type RetrievalSource =
  | 'keyword_index'
  | 'embedding_index'
  | 'time_index'
  | 'source_ref_index'
  | 'people_relationship_index'
  | 'tag_index'
  | 'manual_pin_index';
```

No single retrieval source dominates.

Embedding is useful but must not become the only memory.

## Candidate

```ts
type SearchCandidate = {
  memoryId: string;
  sourceRefIds: string[];
  evidenceIds: string[];
  retrievalSources: RetrievalSource[];
  rawScores: RawSearchScores;
  safety: MemorySafety;
  visibility: MemoryVisibility;
  lifecycle: MemoryLifecycleState;
};
```

```ts
type RawSearchScores = {
  keyword?: number;
  semantic?: number;
  time?: number;
  sourceTrust?: number;
  evidenceStrength?: number;
  userPinned?: number;
  recency?: number;
};
```

## Ranking Score

```ts
type RankingScore = {
  finalScore: number;
  components: {
    queryRelevance: number;
    timeFit: number;
    sourceTrust: number;
    evidenceStrength: number;
    userControlBoost: number;
    safetyPenalty: number;
    diversityPenalty: number;
  };
  explanation: RankingExplanation;
};
```

Important:

- finalScore is not shown as life importance.
- safetyPenalty must not be shown as shame or value judgment.
- sourceTrust means evidence quality, not person trustworthiness.

## Scoring Rules

### Query relevance

Combines keyword + semantic match.

### Time fit

Boosts memories close to requested date or life phase.

If no date in query, do not over-boost recent memories. Old memories can be relevant.

### Source trust

Higher when SourceRef and Evidence are clear.

Does not mean a person is trustworthy.

### Evidence strength

User direct statements, calendar metadata, confirmed records are stronger than AI inference.

### User control boost

User-pinned, user-tagged, user-corrected memories may rank higher.

### Safety penalty

High-risk records may be hidden, summary-only, snippetless, or excluded.

### Diversity penalty

Avoid showing 20 near-duplicate records from one import.

## Safety Filtering

Before ranking:

- deleted: exclude
- sealed: exclude unless explicit unlock
- hidden: exclude unless explicit include
- secret_or_credential: exclude
- corporate_confidential: exclude default
- third_party_private: summary-only or exclude
- minor_sensitive: exclude default
- self_harm_or_crisis: no snippets, safe summary only
- grief_or_death: warning or safe summary
- romantic_or_sexual: no proactive surfacing

## Snippet Rules

```ts
type SearchSnippet = {
  text: string;
  snippetMode: 'quote' | 'safe_summary' | 'metadata_only' | 'redacted' | 'none';
  redactions: ExportRedaction[];
};
```

Raw quote allowed only when:

- policy allows show_raw_quote
- not third-party private
- not secret
- not self-harm/crisis raw
- not corporate confidential
- not minor sensitive

## Explainability

Every result should be able to answer:

```txt
なぜ出た？
```

Allowed explanations:

- 検索語と一致しました
- 同じ時期の記録です
- この出典に関連しています
- あなたが以前タグ付けしました
- カレンダー情報と一致しました
- 安全のため要約のみ表示しています

Forbidden explanations:

- これは人生で重要だからです
- この人はあなたに一番影響があります
- あなたの本質を表しています
- AIが大切だと判断しました

## Tip / Discovery Ranking

Tip は検索より厳しい。

Proactive discovery must not surface:

- grief/death unless opt-in
- self-harm/crisis
- medical/mental
- romantic/sexual
- third-party private
- minor sensitive
- hidden/sealed
- shame/regret-heavy records without user request

Tip ranking can use:

- low-risk preferences
- happy routine memories
- user-pinned memories
- seasonal memories with opt-in
- safe hobby records
- safe life milestones

## Relationship Search

Allowed:

```txt
妻との旅行の記録を見たい
父との思い出を探したい
友人と行った焼肉の記録
```

Restricted:

```txt
妻が嘘をついた証拠
父が悪い理由
友人の弱点
同僚の能力不足
```

Allowed response shape:

- ユーザー本人から見た関係性
- 共有イベント
- 本人の感情
- 出典と時期

Forbidden:

- 相手の人格評価
- 相手の本心推測
- 監視・証拠化

## Search Result

```ts
type MemorySearchResult = {
  memoryId: string;
  title?: string;
  summary?: string;
  occurredAt?: string;
  period?: DateRange;
  memoryKind: MemoryKind;
  snippet?: SearchSnippet;
  sourceRefs: SourceRefSummary[];
  explanations: RankingExplanation[];
  safetyNotice?: string;
  actions: SearchResultAction[];
};
```

```ts
type SearchResultAction =
  | 'open'
  | 'show_source'
  | 'hide'
  | 'seal'
  | 'delete'
  | 'correct'
  | 'exclude_from_ai'
  | 'exclude_from_tips'
  | 'export_this';
```

Every result should give user control.

## Evaluation Metrics

Do not optimize only for click-through.

Good metrics:

- user found intended memory
- result was safe
- source was understandable
- user corrected less over time
- hidden/sealed respected
- no third-party leak
- no unwanted resurfacing
- cost per search stable

Bad metrics if used alone:

- time spent scrolling
- emotional reaction intensity
- number of memories opened
- return frequency from grief/stress triggers

## Acceptance Criteria

Search & Ranking Engine is ready when:

- Ranking code has no field named importanceScore for result order.
- Policy filters run before scoring.
- Hidden/sealed/deleted states are respected.
- Search explanations never claim life importance.
- Snippets obey show_raw_quote policy.
- Surveillance/blame queries are denied or redirected.
- Third-party private results are summary-only or excluded.
- Tip ranking has stricter policy than search.
- User can hide/seal/delete/correct from results.
- Search tests include safe, hidden, third-party, corporate, minor, grief, self-harm, surveillance cases.

## Non-goals

- Ranking people by importance.
- Scoring life events by value.
- Turning search into therapy diagnosis.
- Enabling evidence search against others.
- Maximizing engagement at safety cost.

## 結論

Search & Ranking Engine は、記憶の価値を決めるAIではない。

それは、本人が必要な時に、自分の人生文脈へ安全に戻るための索引である。

順位は関連度であって、人生の順位ではない。
