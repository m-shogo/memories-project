# RFC-0008: UX Guidelines

## Status

`accepted_with_limits`

## Summary

UX Guidelines は、Memory OS の思想を画面・文言・導線で壊さないための仕様である。

このRFCは `docs/ux-guidelines.md` を採用仕様として扱う。

Memory OS は、AIチャットでも、人生診断でも、キャラクター会話でもない。

ユーザーが自分の人生文脈を失わないための索引である。

## Motivation

設計が安全でも、UIが以下のように見えるとサービスの性質が変質する。

- AIが人生の重要度を決める
- 家族や恋人を診断する
- 故人が話しているように見える
- 小さな記録が価値なしに見える
- 削除が悪いことに見える
- 全履歴importが推奨に見える
- Tipがつらい記憶を勝手に出す

UXは思想の実装である。

## Non-goals

- engagement最大化
- AIを人間っぽく見せる
- 人生スコア化
- 思い出ランキング
- 恋人/家族/故人の人格演出
- 削除の罪悪感化
- 安全境界を隠すこと

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. always-on chat導線を作らない。 |
| Character.AI化しないか | Yes. persona UIを禁止。 |
| 本人・家族・故人を演じないか | Yes. speak-as copy禁止。 |
| 人格診断にならないか | Yes. diagnosis words禁止。 |
| 人生ランキングにならないか | Yes. score/rank copy禁止。 |
| 保存時に分析しすぎないか | Yes. captureでanalysisを強制しない。 |
| 小さな記録を捨てないか | Yes. tiny memo歓迎。 |
| 大きなイベントを押し付けないか | Yes. highlight強制しない。 |
| 出典・日付・検索性を守るか | Yes. source/dateをUIで表示。 |
| 削除・非表示・Exportを尊重するか | Yes. controls visible。 |

## User Value

- 安心して小さな記録を残せる。
- AIに評価されている感じがしない。
- 危険な取り込み前に分かる。
- 消したい時に消せる。
- 出典と日付を見て納得できる。

## Data Model Impact

UX must expose these states:

- sourceRef
- occurredAt/importedAt
- confidence basis
- rawStored
- privacyLevel
- lifecycle
- visibility
- policyDecision mode
- export redaction

No new schema required beyond v1.1.

## Policy Impact

UX must display policy outcomes safely.

| Policy mode | UX behavior |
|---|---|
| allow | normal action |
| allow_with_warning | warning + continue |
| summary_only | explain raw unavailable |
| masked_only | explain masking |
| hide_by_default | not shown unless explicit |
| deny | safe refusal + alternative |
| require_user_approval | scope/confirmation UI |

## Privacy Impact

Risky imports require warnings:

- LINE/DM: other people's messages
- Gmail: very sensitive
- Photos: faces/location/minors
- Slack/work: company/customer/coworker data
- Export: third-party/secret/corporate exclusions

## Security Impact

UX must never display secret values.

Error messages must be safe:

- show count/kind
- do not show raw secret
- do not show raw third-party private content

## Third-party Impact

UI must describe relationship context, not other person diagnosis.

Allowed:

```txt
奥様との旅行や結婚式準備の記録
```

Forbidden:

```txt
奥様の性格分析
```

## Minor / Family Impact

- no child personality UI
- no family ranking
- no guilt deletion copy
- family share not MVP

## Legacy / Deceased Impact

Forbidden:

- 故人からのメッセージ
- 父として話す
- あの人ならこう言う

Allowed:

- 故人に関する記録
- 当時の思い出
- 出典に基づく価値観の整理

## Corporate Data Impact

UI must not imply company search.

Forbidden:

- 社内情報を検索
- 同僚の弱点
- 顧客情報を整理

Allowed:

- 自分の仕事の転機
- 自分が関わった公開プロジェクトの記録

## Cost Impact

UX must show estimate before medium+ jobs.

Required:

- count estimate
- scope selection
- full analysis disabled default
- blocked explanation

## UX Impact

This RFC defines UX impact.

Required surfaces:

- onboarding
- capture
- import preview
- memory detail
- search results
- timeline
- deletion
- export
- error states

## Explainability Impact

UI must answer:

- なぜ保存されたか
- どの出典か
- なぜ表示できないか
- なぜ要約だけか
- なぜExportから除外されたか
- 何がAI推測か

## Deletion / Export Impact

Deletion copy must be guilt-free.

Bad:

```txt
本当にこの大切な思い出を消しますか？
```

Good:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

Export copy must not promise full raw export.

## Failure Modes

- onboarding says AI understands your life.
- capture requires importance.
- search says AI judged important.
- deletion guilt copy.
- export says all data included.
- Tip resurfaces grief/crisis.
- empty state says important memories missing.
- family UI implies diagnosis.

## Abuse Cases

1. UI encourages full LINE import.
2. UX shows wife personality analysis.
3. Deleted grief record guilt-tripped.
4. Export button implies raw safe package.
5. Search result explains life importance.
6. Child memory appears as personality profile.
7. Deceased record appears as message from deceased.
8. Slack import marketed as company search.
9. Tip shows self-harm memory proactively.
10. Empty state pressures saving everything.

## Alternatives Considered

### Friendly AI persona UI

却下。AI companion/Character.AI化しやすい。

### Gamified memory score

却下。人生ランキング化する。

### Frictionless full import CTA

却下。privacy/cost/safetyを壊す。

## Acceptance Criteria

- Capture does not require importance score.
- Import preview before analysis.
- Search explanations avoid life value language.
- Tip excludes sensitive categories default.
- Deletion UI non-guilt-inducing.
- Export UI shows exclusions/raw status.
- Risky source warnings exist.
- User controls visible on memory detail.
- Empty states do not shame user.
- UX copy scan passes.

## Rollout Plan

1. forbidden phrase scan
2. onboarding boundary copy
3. capture without importance
4. import preview warnings
5. deletion/export safe copy
6. search explanation copy
7. Tip copy only after strict policy

## Open Questions

- exact product tagline.
- how much philosophy to show in onboarding.
- mobile share flow microcopy.

## Decision

`accepted_with_limits`

制限:

- no ranking/diagnosis/persona copy.
- no full import pressure.
- no guilt deletion copy.
