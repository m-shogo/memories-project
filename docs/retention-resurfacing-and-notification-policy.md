# Retention, Resurfacing, and Notification Policy

## 目的

この文書は、Memory OSが長く使われるために、毎日利用、週次/月次の振り返り、通知、再表示、離脱後の復帰をどう設計するかを定義する。

目標は毎日開かせることではない。

```txt
必要な時にすぐ使える
週1で少し整えられる
月1で特別な見返りがある
長く空いても戻れる
```

## 最重要判断

### 毎日利用をNorth Starにしない

Memory OSはSNS、ニュース、AI chatのように毎日新しい刺激が自然発生するサービスではない。

毎日利用を強制すると、以下へ寄りやすい。

- streak
- 入力ノルマ
- mood score
- “今日も記録”
- 数量目標
- 薄い通知

Dailyはoptional utilityとする。

### Weekly / Monthly / Event-drivenを中心にする

- Daily: quick capture / progress update
- Weekly: one action / shelf changes
- Monthly: Month Capsule
- Yearly/seasonal: Year Capsule / event box
- Event-driven: travel, wedding, AI migration, new hobby

---

# 1. Daily Experience

## 目的

毎日開かせるのではなく、毎日でも使えるようにする。

## Daily Core

- one-tap add
- share extension
- progress update
- save one URL
- add one restaurant
- mark watched/read/listened
- recent Inbox

## Daily Home Card

ホーム上部には、全部ではなく1枚だけ出す。

候補:

- 漫画を1作品だけ更新
- 最近保存したURLを1件整理
- 行きたい店を1つ追加
- Import Preview ready
- month capsule ready

Rule:

```txt
1 screen / 1 suggested action
```

## 不採用

- 今日の記録率
- 今日の人生progress
- 20件中何件
- daily streak
- 未入力日の赤表示

---

# 2. Weekly Experience

## Weekly Box

週次は「先週何をしていたか」より、「先週から続いているもの」「棚で変化したもの」を中心にする。

### 出す

- 今週増えた棚
- 先週保存した未処理URL
- 進行更新できる作品
- duplicate候補1件
- cross-source connection
- new shelf preview

### 原則出さない

- 1週間前の行動一覧
- private conversation recap
- mood recap
- “今週記録していません”

## なぜ「1週間前なにしてた」を中心にしないか

- 近すぎて驚きが弱い
- まだ覚えている
- 記録が少ない週に価値が出ない
- 毎週同じ形式で飽きる
- privateな出来事を出しやすい

代わりに:

```txt
先週保存した続きを見る
```

```txt
今週棚に増えたものを見る
```

```txt
1件だけ整える
```

## Weekly Card Rotation

同じcard typeを連続表示しない。

```ts
type WeeklyCardType =
  | 'shelf_growth'
  | 'unfinished_item'
  | 'saved_for_later'
  | 'duplicate_review'
  | 'cross_source_link'
  | 'new_shelf'
  | 'last_year_this_week'
  | 'export_readiness';
```

Rules:

- max 1〜3 cards
- same type cooldown: 3〜4 weeks
- sensitive source excluded
- no empty/weak card
- cardがなければ表示しない

---

# 3. Monthly Experience

## Month Capsule

月1はMemory OSの主要rewardにする。

```txt
2026年7月の箱ができました
```

Contents:

- shelf changes
- records by safe domain
- timeline
- map additions
- progress updates
- cross-source connections
- user corrections

## 表示例

```txt
7月の箱

映画棚 5件
漫画棚 2作品更新
食の地図 4件
音楽棚 12件
新しくつながった記録 2件
```

## 特典

物理的/架空通貨rewardではなく、見え方をrewardにする。

- Month timeline
- Month shelf cover
- Month map
- selected safe collage
- Export-ready summary

## Notification

Month Capsule notificationはopt-inを推奨。

初期onboardingで選択:

```txt
月に1回、月の箱ができた時だけ知らせる
```

Defaultの候補:

- privacy-first MVP: OFF
- consumer MVP: explicit opt-in during onboarding

勝手にONにしない。

---

# 4. Last Year This Week / On This Day

## 判断

採用する。

ただし、毎週pushする中心機能にはしない。

## 表示場所

- 振り返りtab
- Month Capsule内
- Homeの今日の1枚
- user opt-in notification

## Safe Sources

Default allow:

- movie
- manga/anime
- music
- food/place without precise sensitive context
- travel box user-approved
- public/low-risk notes

Default exclude:

- LINE/DM
- health/mental health
- grief/loss
- deceased data
- partner/family private raw
- minor data
- hidden/sealed/restricted
- user-excluded people/dates/periods

## User Controls

- この棚を振り返りに使わない
- この期間を表示しない
- この人物/イベントを表示しない
- 今は見せない
- 通知しない
- resurfacingから削除

## Copy

Allowed:

```txt
去年の今ごろ、映画棚にこの作品がありました。
```

Avoid:

```txt
大切な思い出を忘れていませんか？
```

---

# 5. Notifications

## Tier 1: Operational

必要性が高い。

- Import Preview ready
- Export package expires
- backup completed/failed
- OAuth reconnect required
- security/account event
- user-set reminder

## Tier 2: Product Value

opt-in。

- Month Capsule ready
- safe Last Year This Week
- new cross-source connection
- shared/event box update

## Tier 3: Engagement-only

不採用。

- 最近開いていません
- 今週まだ記録していません
- 棚が寂しがっています
- streakが切れます
- 1週間前を振り返りませんか、だけの通知
- AIが待っています

## Notification Budget

```txt
Operational: event-driven
Product value: maximum 1 per week, preferably monthly
Engagement-only: 0
```

Users can set:

- all off
- operational only
- monthly only
- selected shelves/events only

---

# 6. Re-engagement after Inactivity

## Multiple Lives Model

利用は一つの連続habitではなく、複数の利用期を持つ。

Examples:

- new hobby
- travel planning
- wedding/event
- year-end review
- AI migration
- finding old information

## Return Screen

Bad:

```txt
87日記録していません。
```

Good:

```txt
また必要なところから始められます。
```

Options:

- 新しい棚を作る
- 前の棚を1つ見る
- Importする
- 進行を1件更新
- 何も埋めずに検索する

## No Backfill Requirement

- 空白期間を埋めなくてよい
- overdue inboxを全処理しなくてよい
- old notificationを連続表示しない
- new purposeを選べる

---

# 7. Persona-specific Cadence

| Persona | Daily | Weekly | Monthly | Notifications |
|---|---|---|---|---|
| Collector | optional add | shelf growth | capsule | monthly/cross-source opt-in |
| Progress Tracker | strong | unfinished items | stats optional | user-set only |
| Lightweight Capturer | share action | Inbox 1件 | optional | preview ready |
| Nostalgia Reflector | weak | app card | strong | monthly opt-in |
| Family/Event | event period | event box | capsule | event user-set |
| Re-finder | none | none | none | operational only |
| AI Power | none | maintenance | context readiness | expiry/error |
| Returning | none | none | optional | default off |
| Sensitive | none | none | user-requested | security only |
| Social Taste | activity-based | list updates | year/month share | shared list only |

---

# 8. Feature Decisions

| Feature | Decision | Reason |
|---|---|---|
| Daily streak | Reject | pressure, objective substitution |
| Daily completion rate | Reject | life becomes quota |
| 1 week ago push | Reject as default | too recent, weak, repetitive |
| Last week unfinished items | Adopt | actionable continuation |
| Weekly Box | Adopt | shelf change + one action |
| Month Capsule | Strong adopt | meaningful interval, reward |
| Last Year This Week | Adopt carefully | nostalgia and surprise |
| On This Day sensitive | Reject default | emotional risk |
| New cross-source link | Adopt in-app | visible Memory OS value |
| Recently inactive notification | Reject | guilt/engagement-only |
| User-set reminders | Adopt | user intent |
| Operational notifications | Adopt | clear utility |
| Monthly notification | Opt-in | infrequent and valuable |

---

# 9. Implementation Requirements

- notification service must know policy/lifecycle/privacy state
- hidden/sealed/restricted records cannot enter resurfacing
- resurfacing candidate must include reason/explainability
- user exclusion must be durable
- notification text must not include private raw data
- same weekly card type requires cooldown
- no card is better than weak card
- month capsule can be empty without shame copy
- lapsed user state must not show missed-day count

## Resurfacing Candidate

```ts
interface ResurfacingCandidate {
  candidateId: string;
  shelfId: string;
  recordIds: string[];
  reason:
    | 'last_year_same_period'
    | 'month_capsule'
    | 'unfinished_item'
    | 'saved_for_later'
    | 'cross_source_link'
    | 'shelf_growth';
  sensitivity: 'low' | 'owner_sensitive' | 'restricted';
  notificationEligible: boolean;
  inAppEligible: boolean;
  excludedByUser: boolean;
  explanation: string;
}
```

## P0 Tests

1. hidden/sealed/restricted data never enters default resurfacing.
2. LINE/DM excluded from Last Year This Week by default.
3. inactive user receives no guilt notification.
4. weekly card is omitted when weak/empty.
5. same weekly card type respects cooldown.
6. monthly capsule notification requires opt-in.
7. user exclusion persists across import/re-import.
8. notification contains no raw private title/text.
9. user can disable all product-value notifications.
10. return screen never shows missed-day or lost-streak state.

## 結論

Memory OSは、毎日開かせる必要はない。

長く使われるために必要なのは、

```txt
すぐ入れられる
週1で少し整えられる
月1で自分の箱が見える
安全に昔へ戻れる
何カ月空いても再開できる
```

というcadenceである。
