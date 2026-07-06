# Digital Wellbeing for Memory OS

## 目的

Digital Wellbeing は、ユーザーを長時間使わせ続けるのではなく、ユーザーの生活・注意・感情・自律性を守るための設計である。

Memory OS は、ユーザーの人生文脈を扱うため、依存・不安・罪悪感・過去への固着を生みやすい危険がある。

このドキュメントは、Memory OS を「安心して離れられる記憶の索引」として設計するためのルールを定義する。

## Digital Wellbeing を一言で言うと

```txt
ユーザーの時間と心を奪わない設計。
```

## Memory OS Wellbeing Principles

```ts
type DigitalWellbeingPrinciple =
  | 'calm_presence'
  | 'no_engagement_maximization'
  | 'no_shame_or_guilt'
  | 'no_fomo'
  | 'healthy_distance_from_past'
  | 'notification_restraint'
  | 'session_completion'
  | 'sensitive_memory_restraint';
```

## 1. Calm Presence

### 原則

Memory OS は、必要な時に静かに使える道具である。

### UI direction

- calm empty state
- no aggressive animation
- no daily pressure
- no streaks
- no “come back” manipulation

Good:

```txt
残したいことがあれば記録できます。
```

Bad:

```txt
今日も記録して連続日数を伸ばしましょう！
```

## 2. No Engagement Maximization

### 原則

滞在時間・開封回数・AI会話数を主要成功指標にしない。

### Bad metrics

- time spent
- messages sent to AI
- daily active streak
- emotional reaction intensity
- number of tips opened

### Better metrics

- user found intended memory
- deletion worked
- export succeeded
- source coverage
- policy denied risky actions
- user left after completing task

## 3. No Shame or Guilt

### 原則

記録しないこと、削除すること、見返さないことを責めない。

Bad:

```txt
最近記録していません。
```

```txt
本当にこの大切な思い出を消しますか？
```

Good:

```txt
新しい記録を追加できます。
```

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

## 4. No FOMO

### 原則

「今やらないと失う」と煽らない。

Bad:

```txt
忘れる前に保存してください。
```

Good:

```txt
残したいことがあれば、短いメモとして保存できます。
```

## 5. Healthy Distance from Past

### 原則

過去を見返すことを強制しない。

Memory OS は、過去に閉じ込めるサービスではない。

Forbidden proactive surfacing:

- grief/death
- self-harm/crisis
- shame/regret-heavy records
- romantic/sexual records
- family conflict
- minor sensitive records

Allowed if user requests:

- search
- explicit reflection
- safe archive

## 6. Notification Restraint

### 原則

通知は最小限。

Allowed notifications:

- export ready
- security incident
- backup completed if opted-in
- user-requested reminder

Avoid:

- daily memory prompts
- streak reminders
- emotional resurfacing
- “you have memories waiting”

## 7. Session Completion

### 原則

ユーザーが目的を終えたら、自然に離れられる。

Good endings:

```txt
Exportが完了しました。
```

```txt
この記録を削除しました。
```

Bad endings:

```txt
続けて他の思い出も見ますか？
```

```txt
もっと深く分析しましょう。
```

## 8. Sensitive Memory Restraint

### 原則

敏感な記憶は、ユーザーが求めた時だけ出す。

Default off:

- grief tips
- crisis tips
- relationship conflict tips
- medical/mental tips
- child/minor tips
- sealed/hidden reminders

## Wellbeing UX Rules

### Empty State

Good:

```txt
まだ記録はありません。短いメモや共有から始められます。
```

Bad:

```txt
重要な記憶がありません。
```

### Search No Results

Good:

```txt
この条件では見つかりませんでした。期間や出典を変えて探せます。
```

Bad:

```txt
あなたの人生データが不足しています。
```

### Reflection

Good:

```txt
この期間の記録を、出典つきで整理します。
```

Bad:

```txt
あなたの人生の意味を分析します。
```

## Product Metrics Policy

Forbidden primary metrics:

- maximize time spent
- maximize memories opened
- maximize emotional tips
- maximize AI conversations
- maximize daily streaks

Preferred metrics:

- task completion
- safe export completion
- successful search
- deletion completion
- raw reduction
- policy safety catch rate
- user-controlled settings usage

## Wellbeing Tests

1. No streak UI.
2. No guilt deletion copy.
3. No FOMO capture copy.
4. No proactive grief/crisis tips.
5. No engagement-maximizing success metric in MVP docs.
6. Session completion copy does not push more use.
7. Empty state does not shame.
8. Sensitive memory reminders default off.
9. Notification list is restricted.
10. Search no-results copy does not imply life insufficiency.

## Wellbeing Review Checklist

Before shipping UX:

1. Does this pressure the user to record more?
2. Does this make deletion feel wrong?
3. Does this create fear of forgetting?
4. Does this reward daily usage?
5. Does this resurface sensitive memory without request?
6. Does this push AI analysis when search is enough?
7. Does this let the user leave after task completion?
8. Is this metric compatible with wellbeing?

## Acceptance Criteria

- engagement maximization rejected.
- notification restraint defined.
- no shame/guilt/FOMO copy rules defined.
- sensitive resurfacing default off.
- metrics policy defined.
- wellbeing tests listed.

## 結論

Digital Wellbeing は、Memory OS を「毎日使わせるアプリ」ではなく、「必要な時に戻れる安心の道具」にするための設計である。

Memory OS の成功は、ユーザーを長く滞在させることではない。

ユーザーが必要な文脈を見つけ、安心して閉じられることである。
