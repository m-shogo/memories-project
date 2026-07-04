# Explainability

## 目的

Explainability は、記憶体が答えた内容について、何を根拠にしたのか、何を除外したのか、どこまでが推測なのかをユーザーへ説明するための設計である。

AI記憶体では、自然な回答ほど危険になる。

自然に見える回答が、実はAIの推測だけだった場合、ユーザーはそれを人生の事実として受け取ってしまう。

## 最上位原則

**答えには、根拠と限界を持たせる。**

## Explanation Object

```ts
type Explanation = {
  answerId: string;
  query: string;
  usedSources: UsedSource[];
  usedEvidenceIds: string[];
  excludedSources: ExcludedSource[];
  inferenceLevel: InferenceLevel;
  confidence: TrustScore;
  safetyTransformations: SafetyTransformation[];
};
```

## UsedSource

```ts
type UsedSource = {
  sourceType: SourceType;
  sourceName?: string;
  count: number;
  dateRange?: DateRange;
  riskFiltered: boolean;
};
```

例:

- ChatGPT会話 12件
- LINE要約 8件
- Google Photos metadata 4件
- Calendar event 2件

## ExcludedSource

```ts
type ExcludedSource = {
  sourceType: SourceType;
  reason:
    | 'hidden_by_user'
    | 'deleted'
    | 'high_sensitive'
    | 'third_party_private'
    | 'secret_detected'
    | 'corporate_confidential'
    | 'not_in_scope'
    | 'low_confidence';
};
```

## Inference Level

```ts
type InferenceLevel =
  | 'record_only'
  | 'summary_of_records'
  | 'light_inference'
  | 'strong_inference'
  | 'speculative'
  | 'refused';
```

## UI Examples

### 通常回答

> この回答は、2026年7月のChatGPT会話12件と、旅行関連メモ4件を元にしています。

### 関係性回答

> この回答は、あなたの記録に残っている奥様との旅行・結婚式準備・日常会話の要約を元にしています。LINE原文は表示していません。

### 父なら？

> これはお父さん本人の言葉ではありません。残された記録から見える考え方を、推測として整理しています。

### 高感度除外

> 医療・家族・他人の秘密に関する記録は、この回答から除外しています。

## Safety Transformations

```ts
type SafetyTransformation = {
  type:
    | 'raw_hidden'
    | 'quote_removed'
    | 'secret_masked'
    | 'third_party_minimized'
    | 'self_harm_reframed'
    | 'deceased_impersonation_prevented'
    | 'corporate_data_excluded';
  description: string;
};
```

## When to Show Explanation

常に全部見せると重い。

UIでは段階的にする。

1. 短い根拠表示
2. 「根拠を見る」ボタン
3. 詳細表示
4. 原文表示はポリシー次第

## Required Explanations

以下では必ず説明を出す。

- 親・故人に関する回答
- 昔の自分なら？
- 関係性回答
- 高感度記憶を除外した回答
- AI推測が含まれる回答
- エクスポート
- 家族共有
- 削除完了

## Prohibited Explanations

説明に高感度原文を含めない。

悪い:

> 「死ね」という原文を安全のため除外しました。

良い:

> 強い自己否定表現を含む原文は除外しました。

## Confidence Display

数値を直接出すと誤解がある。

表示は段階でよい。

- 根拠強め
- いくつかの記録に基づく
- 推測を含む
- 根拠弱め

内部ではTrustScoreを保持する。

## Export Explanation

エクスポート時は、各Memoryに以下を含める。

- source refs
- confidence
- inference level
- safety notes
- quote policy
- not for impersonation metadata

## Non-goals

- AIの内部思考を出すこと
- 長い監査ログをユーザーに押し付けること
- 高感度原文を根拠として見せること

## 結論

Explainability は、AIを信用させるためではない。

AIを過信させないためにある。

記憶体は、自然な回答の裏に、根拠・除外・不確実性を持つ必要がある。
