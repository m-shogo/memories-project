# Memory Graph

## 目的

Memory Graph は、記憶を単なる一覧やEmbedding検索ではなく、人物・関係・出来事・場所・ソース・時間・話題でつなぐための設計である。

人間の記憶は、単独のログではなく関係の網として思い出される。

例:

- 妻 -> ハワイ -> プロポーズ -> Wolfgang -> 写真 -> 結婚式
- 父 -> 仕事観 -> 挑戦 -> 失敗した時の言葉
- 卒業式 -> 写真 -> 焼肉 -> 帰り道 -> 友人

## 最上位原則

**Graphは人を評価するためではなく、記憶を見つけるために使う。**

## Node Types

```ts
type GraphNodeType =
  | 'memory'
  | 'person'
  | 'relationship'
  | 'event'
  | 'place'
  | 'topic'
  | 'source'
  | 'media'
  | 'time_period'
  | 'life_phase'
  | 'value_hint'
  | 'artifact';
```

## Edge Types

```ts
type GraphEdgeType =
  | 'mentions'
  | 'involves'
  | 'occurred_at'
  | 'occurred_during'
  | 'located_at'
  | 'from_source'
  | 'same_period_as'
  | 'related_to'
  | 'user_confirmed_relation'
  | 'ai_suggested_relation'
  | 'derived_from'
  | 'contrasts_with'
  | 'later_reflection_of';
```

## Graph Node

```ts
type MemoryGraphNode = {
  id: string;
  userId: string;
  type: GraphNodeType;
  label: string;
  ownerEntityId: string;
  privacy: PrivacyLevel;
  riskClasses: RiskClass[];
  confidence: ConfidenceScore;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string;
};
```

## Graph Edge

```ts
type MemoryGraphEdge = {
  id: string;
  userId: string;
  fromNodeId: string;
  toNodeId: string;
  type: GraphEdgeType;
  evidenceIds: string[];
  confidence: ConfidenceScore;
  createdBy: 'user' | 'system' | 'ai';
  safety: MemorySafety;
  createdAt: string;
  deletedAt?: string;
};
```

## Person Graph

人物ノードは他人の人格評価ではない。

Person nodeが持つのは、名前・別名・ユーザーとの関係性の参照だけ。

禁止:

- 性格診断
- 弱点推測
- 監視
- 浮気推測

許容:

- 一緒にいた出来事
- ユーザーが感じたこと
- ユーザーとの関係性の記録

## Relationship Graph

RelationshipはPersonより重要。

例:

- 妻との関係
- 父から受けた影響
- 友人との卒業式後の記憶

Relationship nodeは、ユーザー視点で作る。

## Event Graph

Eventは大きい/小さいで価値付けしない。

例:

- 結婚式
- 卒業式
- 焼肉
- ラーメン
- 帰り道
- 外に出た日

すべてEventになり得る。

## Value Hint

Value nodeではなく `value_hint` と呼ぶ。

理由:

- AIが価値観を断定しないため
- 価値観は後から変わるため
- 推測であることを明示するため

例:

- 思い出を残したい
- 家族を大事にしたい
- 安全性を重視していた

## Graph Confidence

Edgeには信頼度を持つ。

高い:

- ユーザーが明示的に確認
- 複数ソースで一致
- 日付付き記録

低い:

- AI推測
- 写真だけ
- ロールプレイ由来
- 他人発言のみ

## Search with Graph

MQLからGraph検索へ変換する。

例: `妻ってどんな人？`

1. person node 妻 を探す
2. relationship node を探す
3. connected events を探す
4. high risk edgeを除外
5. evidence bundleを作る
6. relationship contextとして回答

例: `卒業式のあと`

1. event node 卒業式を探す
2. same_period_as / occurred_after を探す
3. 焼肉・写真・帰り道など小さいeventも拾う

## Graph Safety

Graphは危険にもなる。

危険例:

- 元恋人の行動追跡
- 妻の性格分析
- 子どもの行動パターン分析
- 同僚の弱点分析

対策:

- third-party risk edgesは検索制限
- person graphはowner perspectiveのみ
- surveillance intentを拒否
- high sensitive edgesはhidden default

## Graph Deletion

Memory削除時は関連edgeも削除または無効化する。

- nodeが孤立したらarchive
- evidenceが消えたedgeはconfidenceを下げる
- user-deleted relationship edgeは復活させない

## UI

MVPではGraph可視化を作りすぎない。

最初は内部検索用。

将来:

- 人物カード
- 出来事カード
- ソース別カード
- タイムライン
- 関連記憶

## Non-goals

- SNSの人間関係グラフ
- 監視ダッシュボード
- 性格診断グラフ
- 人生重要度ランキング

## 結論

Memory Graphは、記憶を評価する仕組みではない。

過去の何気ない出来事が、後から別の記憶とつながるための索引である。
