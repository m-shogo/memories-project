# Trust and Provenance

## 目的

Trust and Provenance は、記憶の根拠・出典・確信度・推測度を管理するための設計である。

AI記憶体で最も危険なのは、AIの推測が本人の事実として扱われること。

このサービスでは、すべての記憶に「どこから来たか」「どれくらい確からしいか」「誰の発言か」を持たせる。

## 最上位原則

**記憶は出典なしに事実にならない。**

## Provenance Levels

```ts
type ProvenanceLevel =
  | 'user_direct'
  | 'user_repeated'
  | 'cross_source_confirmed'
  | 'metadata_confirmed'
  | 'third_party_statement'
  | 'assistant_generated'
  | 'ai_summary'
  | 'ai_inference'
  | 'unknown';
```

## 信頼度の目安

| Source | Trust | Notes |
|---|---:|---|
| ユーザー本人が明示的に言った | 90-100 | ただし時期限定 |
| 本人が複数回繰り返した | 95-100 | 長期傾向として扱いやすい |
| 複数ソースで一致 | 90-100 | 強い根拠 |
| カレンダー/写真メタデータ | 60-90 | 出来事の根拠には強いが意味は弱い |
| 他人の発言 | 30-70 | 本人の事実としては弱い |
| AI要約 | 40-80 | 元データ参照必須 |
| AI推測 | 10-60 | 推測として表示 |
| 写真だけからの関係推測 | 10-40 | 原則断定禁止 |
| ロールプレイログ | 20-60 | 現実の本人嗜好と分離 |

## TrustScore

```ts
type TrustScore = {
  value: number; // 0-100
  provenanceLevel: ProvenanceLevel;
  evidenceCount: number;
  sourceTypes: SourceType[];
  firstSeenAt?: string;
  lastSeenAt?: string;
  uncertainty: 'low' | 'medium' | 'high';
  explanation: string;
};
```

## Speaker Provenance

会話データでは、誰の発言かを必ず区別する。

```ts
type SpeakerProvenance =
  | 'user'
  | 'assistant'
  | 'third_party'
  | 'ai_character'
  | 'fictional_character'
  | 'system'
  | 'unknown';
```

### 重要ルール

- user発言は本人の記録になり得る
- assistant発言はAI応答であり、本人の考えではない
- third_party発言は他人の情報であり、本人の事実ではない
- ai_character発言は創作/ロールプレイであり、現実の関係ではない

## Evidence Bundle

AIが回答する時は、裏でEvidence Bundleを作る。

```ts
type EvidenceBundle = {
  query: string;
  records: Evidence[];
  includedMemories: string[];
  excludedBecauseSensitive: string[];
  inferenceLevel: 'record_only' | 'summary' | 'weak_inference' | 'strong_inference';
  confidence: TrustScore;
};
```

## 回答表現ルール

### Trust 90以上

使える表現:

- 記録では
- 複数の記録で確認できます
- この時期によく出ています

避ける表現:

- 永遠にそうです
- 本質です

### Trust 60-89

使える表現:

- 記録から見ると
- 可能性が高いです
- そう考えていた場面がいくつかあります

### Trust 30-59

使える表現:

- 可能性があります
- 断定はできません
- 限られた記録では

### Trust 0-29

使える表現:

- 根拠は弱いです
- 記録だけでは判断できません
- 推測としても慎重に扱うべきです

## Inference Taxonomy

```ts
type InferenceType =
  | 'direct_fact'
  | 'time_bounded_summary'
  | 'relationship_context'
  | 'preference_pattern'
  | 'value_pattern'
  | 'later_reflection'
  | 'weak_speculation'
  | 'forbidden_inference';
```

## Forbidden Inferences

以下は推測禁止。

- 医療診断
- 心理診断
- 性的指向やジェンダーの推測
- 宗教・政治思想の断定
- 他人の性格診断
- 浮気推測
- 犯罪性推測
- 子どもの将来適性
- 故人の現在の意思
- AIキャラの現実感情

## Source Conflict

記録が矛盾する場合。

悪い:

> あなたは矛盾しています。

良い:

> 2026年の記録ではAを重視していましたが、2028年の記録ではBへ変化しています。これは矛盾というより、時期や状況の変化として扱うのが自然です。

## Trust Decay and Update

記憶の確信度は固定ではない。

上がる条件:

- ユーザー確認
- 複数ソース一致
- 繰り返し登場
- 日付付き証拠

下がる条件:

- ユーザー修正
- 反対記録
- ソースがAI推測だけ
- ロールプレイ由来
- 文脈不足

## Display Requirements

高い確信度がない場合、UIで断定しない。

表示例:

- 本人発言に基づく
- AI要約に基づく
- 推測
- 根拠弱め
- 複数ソースあり

## Export Requirements

エクスポートには、各Memoryのprovenanceとtrustを含める。

これにより、別AIへ渡しても推測が事実化しにくい。

## 結論

Trust and Provenance は、記憶体が人を勝手に定義しないための基盤である。

AIの答えが自然に見えるほど、根拠と不確実性を内部で厳密に持つ必要がある。
