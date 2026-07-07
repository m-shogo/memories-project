# Import Ritual Reward Calendar

## 目的

この文書は、Memory OSに週1・月1・季節ごとに戻りたくなる理由を作るための、Import ritual / reward calendar を定義する。

通知で引き戻すのではない。

戻ると、自分の棚・地図・箱・年表が少し見える、少し増える、少し整う。

これを特典として設計する。

## Core Principle

```txt
戻る理由は、AI人格ではなく、自分の世界にある。
```

```txt
特典は、限定煽りではなく、自分の蓄積を見やすくすること。
```

## Reward Types

```ts
type RitualReward =
  | 'weekly_box_summary'
  | 'last_year_this_week'
  | 'one_shelf_unlock'
  | 'one_empty_slot_suggestion'
  | 'one_duplicate_cleanup'
  | 'one_progress_update'
  | 'month_capsule_preview'
  | 'seasonal_box_preview'
  | 'cross_source_spark'
  | 'export_readiness_badge'
  | 'travel_or_event_pack'
  | 'collection_completion_hint';
```

## Weekly Rewards

### 1. Weekly Box Summary

```txt
今週のMemory Room

映画棚: 3件追加
食の地図: 1件追加
漫画棚: 1作品更新できます
確認が必要: 2件
```

User action:

- 1つだけ見る
- 1つだけ追加
- 1つだけ直す

### 2. Last Year This Week

```txt
去年の今ごろの棚を1つ開けます。
```

Variants:

- 去年の今ごろ見ていた作品
- 去年の今ごろ聴いていた曲
- 去年の今ごろ保存していた店
- 去年の今ごろ読んでいた漫画

Rules:

- user opt-in or visible card.
- no sensitive LINE/DM.
- no emotional diagnosis.

### 3. One Empty Slot Suggestion

```txt
漫画棚に進行未更新の作品があります。
1作品だけ更新できます。
```

```txt
食の地図に、行きたい店を1つ追加できます。
```

No guilt.

### 4. One Duplicate Cleanup

```txt
同じ作品かもしれない候補が1件あります。
後で確認できます。
```

### 5. One Shelf Unlock

```txt
URLを1つ貼ると、食の地図を始められます。
```

## Monthly Rewards

### 1. Month Capsule Preview

```txt
2026年7月の箱

映画棚: 5件
漫画棚: 2作品更新
食の地図: 4件
音楽棚: 12件
```

Rules:

- fact/count-based.
- no life score.
- no mood diagnosis.

### 2. Shelf Growth Snapshot

```txt
今月育った棚

食の地図 +8
漫画棚 +3
映画棚 +2
```

### 3. Import Gap Hint

```txt
音楽棚はまだ空です。
プレイリストURLから始められます。
```

### 4. Export Readiness Check

```txt
今月の記録は標準Exportに含められます。
プライベート候補は既定で除外されます。
```

This makes trust visible.

## Seasonal Rewards

### 1. Seasonal Box

```txt
2026年夏の箱
```

Contains:

- trips
- food map
- photo metadata
- music
- watched/read/listened records

### 2. Travel Pack

Triggered by user action or calendar/travel import.

```txt
旅行箱を作れます。
店・写真メタデータ・予定をまとめられます。
```

### 3. Year Capsule

```txt
2026年の棚まとめ
```

Careful:

- no life ranking.
- no “best year” judgment.
- no emotional diagnosis.

## Import-triggered Rewards

### First Import Reward

```txt
映画棚ができました。
```

### Second Source Reward

```txt
NetflixとFilmarksが同じ映画棚につながりました。
```

### Cross-source Reward

```txt
同じ作品が複数の棚にあります。
```

### Progress Reward

```txt
漫画棚に進行表ができました。
```

### Map Reward

```txt
食の地図に3件追加されました。
```

## Reward Safety Rules

Allowed:

- counts
- source links
- shelf created
- timeline unlocked
- map/list added
- progress updated
- export readiness

Denied:

- guilt
- streak pressure
- AI loneliness
- private relationship analysis
- personality diagnosis
- life score
- sensitive surprise reveal

## Notification Strategy

Default:

- in-app cards first.
- opt-in digest second.
- push/email only for user-chosen reminders, export expiry, backup status, import preview ready.

Weekly digest allowed only if user opts in.

Digest content:

- shelf changes
- preview ready
- one safe action
- export/backup status

No:

- emotional hooks
- sensitive content details
- relationship/personality analysis

## Reward Calendar Example

### Week 1

- Empty Shelf Card
- First Import Reward
- Weekly Box appears

### Week 2

- One Progress Update
- Last Year This Week card

### Week 3

- Cross-source Spark
- Duplicate Cleanup

### Week 4

- Month Capsule Preview
- Export Readiness Badge

### Month 2

- Seasonal Box if relevant
- Next Source Suggestion
- Shelf Growth Snapshot

## Segment-specific Rewards

### Hobby-heavy

- progress update
- shelf unlock
- year capsule
- cross-source spark

### Food/travel

- map region added
- travel pack
- monthly food map

### Busy adult

- weekly one action
- export readiness
- podcast/radio shelf

### Family/couple

- travel/life event box
- photo metadata box
- safe sharing card

### Senior

- photo/travel box
- large simple weekly card
- backup/export reassurance

### AI-heavy

- context pack readiness
- versioned export
- source coverage

## Implementation Requirements

- ritual rewards must be generated from safe shelf metadata.
- sensitive sources opt out by default.
- user can disable weekly/monthly cards.
- no reward depends on daily streak.
- no reward creates relationship state.
- no reward uses private raw content.

## P0 Tests

1. weekly box contains no raw private text.
2. monthly capsule uses counts/facts, no life score.
3. last year this week excludes sensitive conversation data by default.
4. no streak/guilt copy in reward calendar.
5. export readiness badge is not fear-based.
6. user can disable digest cards.
7. each reward maps to shelf metadata.
8. cross-source spark does not infer hidden meaning.
9. seasonal box does not auto-include restricted media.
10. reward generation works on synthetic fixtures.

## 結論

週1・月1で戻る理由は、AIに会うためではなく、自分の棚・地図・箱・年表が少し見えるために作る。

特典は、不安を煽るものではなく、自分の蓄積を見やすくするもの。

これが良い依存性を、長期ではなく今日の体験へ変換する。
