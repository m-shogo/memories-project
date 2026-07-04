# Time Engine

## 目的

Time Engine は、日付だけではなく、人生フェーズ・季節・イベント前後・相対時期で記憶を扱うための設計である。

人間は必ずしも `2026-07-05` のように記憶しない。

- 卒業式のあと
- 結婚式準備の頃
- 付き合い始めた頃
- コロナの頃
- 転職前
- 父が亡くなる前
- 高校の時
- あのゲームを作っていた時期

このような時間表現を扱える必要がある。

## 最上位原則

**時間は日付だけではない。人生の文脈である。**

## Time Types

```ts
type MemoryTime =
  | ExactDateTime
  | DateRange
  | ApproximateTime
  | RelativeTime
  | LifePhase
  | EventRelativeTime
  | SourceTime;
```

## ExactDateTime

明確な日時。

例:

- 2026-10-24 14:10
- カレンダー予定
- Git commit timestamp

## DateRange

範囲。

例:

- 2026年7月
- 2026年夏
- 2025〜2026年

## ApproximateTime

曖昧な時期。

例:

- 高校の頃
- 20代前半
- 結婚前
- 付き合いたて

## RelativeTime

現在や基準日からの相対。

例:

- 去年
- 3年前
- 最近
- あの頃

## EventRelativeTime

イベントに対する前後。

例:

- 卒業式の後
- プロポーズ前
- 結婚式準備中
- 転職直後
- 父が亡くなる前

## LifePhase

人生フェーズ。

```ts
type LifePhase = {
  id: string;
  userId: string;
  label: string;
  start?: string;
  end?: string;
  confidence: ConfidenceScore;
  sourceRefIds: string[];
  userDefined: boolean;
};
```

例:

- 小学生
- 中学生
- 高校
- 大学
- 社会人初期
- 同棲していた頃
- 結婚準備
- 新婚
- 子育て
- 介護
- 転職活動
- ゲーム開発期

## SourceTime

ソース上の時刻。

例:

- LINE message timestamp
- X post timestamp
- photo takenAt
- import createdAt
- file modifiedAt

注意:

- file modifiedAt は出来事日時とは限らない
- import date は記憶発生日ではない

## Time Confidence

```ts
type TimeConfidence = {
  value: number;
  basis:
    | 'explicit_timestamp'
    | 'calendar_event'
    | 'photo_exif'
    | 'message_timestamp'
    | 'user_statement'
    | 'inferred_from_context'
    | 'approximate';
};
```

## Time Query Examples

### 「卒業式の後」

処理:

1. 卒業式eventを探す
2. event dateを取得
3. 当日〜数日後を検索
4. 関連graph edgesを見る
5. 焼肉、写真、帰り道なども拾う

### 「去年の俺」

処理:

1. 現在日付から前年範囲を作る
2. user statementsを優先
3. AI推測は弱める
4. 高感度原文は除外

### 「結婚式準備の頃」

処理:

1. 結婚式eventを探す
2. 準備期間を推定
3. カレンダー、ChatGPT、LINE、写真メタデータを横断
4. ユーザー定義があれば優先

## User-defined Phases

AIが勝手に人生フェーズを固定しない。

ユーザーが後から修正できる。

例:

- 「この時期はゲーム開発期だった」
- 「この半年は結婚式準備」
- 「この頃は仕事で悩んでいた」

## Time Safety

時間検索は危険にもなる。

危険例:

- 元恋人の行動追跡
- 子どもの通学パターン
- 家族の病院予定
- 会社情報の時系列

対策:

- third-party high-risk time queriesを制限
- precise location + time は高感度
- 子ども関連は時刻・場所を丸める

## Time and Meaning

意味は時間で変わる。

同じ出来事に対して、複数の解釈を持てる。

例:

- 当時: ただの焼肉
- 後年: 卒業式後の大切な思い出

このため、Time Engine は `later_reflection` を扱う。

## Implementation

```ts
type TimeIndexEntry = {
  id: string;
  userId: string;
  ownerType: 'memory' | 'raw_record' | 'event' | 'media' | 'life_phase';
  ownerId: string;
  exactAt?: string;
  rangeStart?: string;
  rangeEnd?: string;
  approximateLabel?: string;
  confidence: TimeConfidence;
};
```

## Non-goals

- 完璧な年表を自動生成する
- 人生フェーズをAIが勝手に確定する
- 行動監視
- 位置履歴トラッキング

## 結論

Time Engine は、人生の記憶を日付だけでなく文脈として扱うために必要である。

人はカレンダーではなく、「あの頃」で思い出す。

このサービスは、その「あの頃」を探せるようにする。
