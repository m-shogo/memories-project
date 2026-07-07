# Weekly Ritual and Daily Micro Action Spec

## 目的

この文書は、Memory OS が週1でも戻りたくなる、毎日でも軽く触れることができる体験を定義する。

これは慰め機能ではない。

ユーザーにとっても、開発者にとっても、良い依存性とワクワク感を今日見える形にするためのproduct loopである。

## Core Principle

```txt
週1で意味がある。
毎日でも少し育つ。
来なくても壊れない。
```

Bad dependencyではない。

- 連続ログインを煽らない。
- AIが寂しがらない。
- 記録しない罪悪感を作らない。
- 深夜に引き止めない。

Good attachmentとして、以下を作る。

- 棚が増える
- 地図が埋まる
- 進行表が整う
- 週の箱が閉じる
- 去年の今ごろが見える
- 次に入れるものが分かる

## Weekly Ritual: 週の箱

週に1回、Memory OSが開かれる理由を作る。

### Weekly Box

```txt
今週の箱

増えた記録: 12件
新しくできた棚: 1つ
見返せる時期: 2024年7月
確認が必要: 2件
次に入れると広がる棚: 食の地図
```

### Weekly Box Actions

User chooses one:

- 今週見たものを1つ入れる
- 今週聴いたものを1つ入れる
- 今週行きたい店を1つ入れる
- 1件だけ重複を確認する
- 1件だけタイトルを直す
- 去年の今ごろを1つ見る
- 空の棚を1つ開く
- Export readinessを確認する

### Weekly Completion

Completion copy:

```txt
今週の箱を閉じました。
また見返したくなった時に開けます。
```

Avoid:

```txt
連続記録達成！明日も来てください。
```

```txt
来ないと箱が寂しがります。
```

## Daily Micro Actions

Daily actions are optional and tiny.

```ts
type DailyMicroAction =
  | 'add_one_title'
  | 'add_one_url'
  | 'update_one_progress'
  | 'review_one_duplicate'
  | 'open_one_shelf'
  | 'save_one_restaurant'
  | 'mark_one_want_to_watch'
  | 'mark_one_want_to_read'
  | 'close_one_preview'
  | 'check_one_export_ready_item';
```

Design:

- one tap or one small input.
- no infinite feed.
- no AI chat loop.
- no emotional escalation.

Copy:

```txt
今日1つだけ入れる
```

```txt
1件だけ整える
```

```txt
最近の棚を見る
```

## Ritual Types

### 1. Add Ritual

Small import.

Examples:

- 今日見た映画を1つ
- 今読んでる漫画を1つ
- 行きたい店を1つ
- 聴いた番組を1つ

### 2. Review Ritual

Look back without adding.

Examples:

- 去年の今ごろ
- 今月増えた棚
- 昔の食の地図
- 2024年の映画棚

### 3. Clean Ritual

Make shelf cleaner.

Examples:

- duplicate候補1件確認
- title修正1件
- low confidence 1件確認
- hidden/sealed整理

### 4. Prepare Ritual

Future-facing.

Examples:

- 旅行前の行きたい店追加
- 見たい映画追加
- 読みたい漫画追加
- Export readiness確認

## Weekly Prompt Examples

Allowed:

```txt
今週は、1つだけ棚を増やせます。
```

```txt
去年の今ごろの映画棚を見られます。
```

```txt
食の地図に、行きたい店を1つ足せます。
```

```txt
確認が必要な候補が2件あります。あとででも大丈夫です。
```

Denied:

```txt
今週まだ記録していません。
```

```txt
記録しないと忘れてしまいます。
```

```txt
あなたを待っています。
```

```txt
連続記録が途切れます。
```

## Weekly Digest

A weekly digest can be generated if user opts in.

Content:

- counts
- shelves changed
- preview ready
- export package expiring
- user-requested reminders

No:

- emotional dependency copy
- sensitive proactive reflection
- private relationship analysis

Example:

```txt
今週のMemory Room

映画棚: 3件追加
食の地図: 1件追加
漫画棚: 1作品の進行を更新できます
確認が必要: 2件

1つだけ整えることもできます。
```

## Import-triggered Rituals

After import:

```txt
映画棚ができました。
次はFilmarksを足すと、見たい映画も並べられます。
```

```txt
漫画棚ができました。
次は1作品だけ進行を更新できます。
```

```txt
食の地図に3件追加されました。
次は旅行先の店だけまとめられます。
```

## Developer Motivation Hooks

Every weekly/daily feature should show a visible artifact.

Ticket questions:

```txt
What weekly action does this enable?
What daily micro action does this enable?
What shelf changes visually?
What user-visible reward appears after completion?
```

Examples:

- `URL List Parser` enables daily add_one_url.
- `Manga Progress Parser` enables update_one_progress.
- `Restaurant Adapter` enables save_one_restaurant and Food Map growth.
- `Dedupe Preview` enables review_one_duplicate.
- `Export Manifest` enables check_one_export_ready_item.

## Metrics

Good metrics:

- weekly_box_open_rate
- weekly_one_action_completion_rate
- daily_micro_action_completion_rate
- import_to_shelf_created_rate
- empty_shelf_to_first_import_rate
- duplicate_review_completion_rate
- user_correction_completion_rate
- return_to_shelf_rate

Bad metrics:

- total AI chat messages
- romantic escalation rate
- distress return rate
- late-night dependency sessions
- streak rescue rate

## MVP Requirements

MVP must include:

1. Weekly Box UI placeholder.
2. At least 3 weekly actions.
3. At least 5 daily micro actions.
4. No streak system.
5. No guilt notification.
6. Post-import shelf reward.
7. Empty shelf import prompt.

Recommended first weekly actions:

```txt
1. 1つImportする
2. 1件だけ進行を更新する
3. 去年の今ごろを1つ見る
```

Recommended first daily actions:

```txt
1. タイトルを1つ入れる
2. URLを1つ入れる
3. 漫画の巻数を1つ更新する
4. 行きたい店を1つ入れる
5. 重複候補を1つ確認する
```

## 結論

Memory OSの継続理由は、AI人格との関係ではなく、ユーザー自身の棚・箱・地図が育つことにある。

週1で1つだけでも意味がある。

毎日でも小さく触れる。

来なくても壊れない。

この設計が、良い依存性を見えるプロダクト体験に変える。
