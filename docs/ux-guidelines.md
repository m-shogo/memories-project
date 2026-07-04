# UX Guidelines

## 目的

UX Guidelines は、Memory OS の思想をユーザー体験で壊さないための設計原則である。

Memory OS は、ChatGPT / Claude の代替でも、Character.AIでも、人生診断サービスでもない。

ユーザーが自分の人生の文脈を失わないための索引である。

そのためUXは、保存・検索・振り返り・削除・Exportを気持ちよくしつつ、AIが人生を評価しているように見せてはいけない。

## 最上位原則

### 1. Calm memory, not addictive chat

Memory OS は会話依存を作らない。

ユーザーが毎日長時間話すことより、必要な時に戻れる安心を重視する。

### 2. Index, not judge

UIは記憶の価値をランク付けしない。

検索性・出典・時期・安全状態を見せる。

### 3. Small records matter

ラーメン、焼肉、帰り道、写真、短いメモを軽く扱わない。

「小さい記録」「大したことない記録」と表示しない。

### 4. Big events are not forced

卒業式、結婚式、誕生日、死別などを、AIが勝手に人生の中心として押し付けない。

### 5. User control is visible

隠す、封印、削除、原文削除、AI除外、Tip除外、Export除外を分かりやすく置く。

## Product Surface

```ts
type ProductSurface =
  | 'onboarding'
  | 'capture'
  | 'import_preview'
  | 'memory_detail'
  | 'search_results'
  | 'timeline'
  | 'tip'
  | 'reflection'
  | 'settings'
  | 'export'
  | 'deletion'
  | 'error_state';
```

Each surface must state or imply:

- what is stored
- what is not stored
- source/date if available
- user control
- safety boundary

## Tone Rules

### Use

- 記録
- 記憶
- 出典
- この時期
- 関連
- 振り返る
- 後から探す
- 安全な要約
- 原文を保存しない

### Avoid

- 診断
- 評価
- スコア
- ランク
- 本質
- 一番大切
- あなたはこういう人
- 相手はこういう人
- AIが選んだ重要な記憶
- 人生の答え

## Onboarding

Onboarding should clarify:

```txt
これはAIチャットの代わりではありません。
あなたの人生の文脈を、後から探せる形で残すためのMemory OSです。
```

Must explain:

- AIは人生を評価しない
- 保存時に分析しすぎない
- 出典・日付・検索性を大事にする
- 原文を保存しない選択ができる
- 他人の秘密は記憶化しない
- 削除・非表示・封印ができる

Do not promise:

- 完全にあなたを理解する
- あなたの人生を診断する
- 大切な人を再現する
- AIが全部覚えてくれるから安心

## Capture UX

Capture is the most important habit surface.

Good capture UX:

- one-tap share
- short memo allowed
- photo metadata-only option
- date/source auto capture
- category optional
- importance selection not required
- analysis off by default

Bad capture UX:

- every record requires long form
- importance score required
- emotion analysis forced
- relationship diagnosis suggested
- all imports pushed as full analysis

### Capture Fields

Required:

- text or source
- capturedAt/importedAt
- source type

Optional:

- occurredAt
- place
- people hints
- tags
- note
- visibility

Forbidden required fields:

- importance
- emotion score
- life category
- personality relevance

## Import Preview UX

Before import:

Show:

- source type
- file count
- record estimate
- date range
- sensitive findings count
- excluded by default
- cost estimate
- raw storage setting
- LLM/embedding setting

Do not show:

- secret values
- raw third-party messages
- private coworker/customer data

Recommended copy:

```txt
まず中身を棚卸しします。全文解析やEmbeddingは、あなたが選んだ範囲だけ実行します。
```

For LINE/DM:

```txt
このデータには、あなた以外の人の発言が含まれます。相手の秘密や原文は既定では保存せず、あなたとの関係性や出来事の安全な要約を優先します。
```

For Gmail/Slack:

```txt
このデータは非常に高感度です。MVPでは全文取り込みせず、必要な範囲の棚卸しまたは安全なイベント要約に限定します。
```

## Memory Detail UX

Memory detail should show:

- title/summary
- occurredAt or period
- source refs
- evidence/confidence
- privacy/safety state
- actions: hide / seal / delete / raw delete / correct / exclude from AI / exclude from tips / export this

Do not show:

- life importance rank
- personality diagnosis
- other person's inferred intent
- AI certainty without evidence

### Confidence Copy

Good:

```txt
この記録は、あなたのメモとカレンダー情報に基づいています。
```

Bad:

```txt
これはあなたの本質を表しています。
```

## Search UX

Search placeholder examples:

- 旅行の記録を探す
- 2026年10月の出来事
- 焼肉の思い出
- この出典から探す
- あの時のメモ

Search result explanations:

- 検索語と一致しました
- 同じ時期の記録です
- 関連する出典があります
- あなたがタグ付けしました
- 安全のため要約のみ表示しています

Forbidden:

- AIが重要と判断しました
- あなたに最も影響した人です
- 人生で一番大切な記録です

## Timeline UX

Timeline should be calm and non-ranking.

Good sections:

- 2026年の記録
- 10月の記録
- 旅行に関する記録
- 食事に関する記録
- 仕事の転機に関する記録

Avoid:

- 人生ハイライト自動ランキング
- 最高の年 / 最悪の年
- 成功/失敗スコア
- 重要人物順

Timeline should allow small records to sit next to large events without hierarchy.

## Tip UX

Tip is dangerous because it resurfaces memories without request.

Default Tip candidates:

- low-risk hobbies
- safe preferences
- seasonal happy records with opt-in
- user-pinned memories
- routine reminders
- safe gratitude records

Never proactive by default:

- grief/death
- self-harm/crisis
- medical/mental
- romantic/sexual
- third-party private
- minor sensitive
- hidden/sealed
- shame/regret-heavy records

Tip copy should be gentle:

```txt
前にこんな記録がありました。
```

Avoid:

```txt
これはあなたにとって重要です。
```

## Reflection UX

Reflection is user-requested only.

Allowed prompts:

- この時期を振り返る
- 旅行の記録をまとめる
- 最近の興味を出典つきで見る
- この経験から、当時の自分が大事にしていたことを整理する

Forbidden prompts:

- あなたの人格診断
- 妻の本音を分析
- 父として話して
- 故人からメッセージ
- 人生で一番大切なものを決める

Reflection must separate:

- fact
- user statement
- AI inference
- later interpretation
- confidence

## Deletion UX

Deletion UI must be respectful and non-guilt-inducing.

Good:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

Bad:

```txt
本当にこの大切な思い出を消しますか？
```

Deletion options:

- 表示しない
- 封印する
- 原文だけ削除する
- 記憶を削除する
- この出典の取り込みを削除する
- AI解析対象から外す
- Tipに出さない

## Export UX

Export should make boundaries visible.

Before export show:

- export mode
- included data
- excluded data
- raw included or not
- third-party handling
- hidden/sealed handling
- deleted tombstone handling
- expiration

Copy:

```txt
あなたの記憶を持ち出せます。相手の秘密、会社情報、パスワードらしき情報は除外または要約されます。
```

Do not say:

```txt
全データを完全に持ち出せます。
```

## Error UX

Errors should be safe and useful.

Secret detected:

```txt
秘密情報らしき文字列を検出したため、この部分は保存・解析しません。値は表示しません。
```

Unknown source:

```txt
出典を確信できないため、全文解析は行いません。ファイル数や期間の棚卸しだけ表示します。
```

Cost limit:

```txt
この処理は大きすぎるため、まず範囲を絞ってください。
```

Policy denied:

```txt
この使い方は、相手の秘密や監視につながる可能性があるため実行できません。あなた自身の記録として安全に振り返る形なら整理できます。
```

## Empty States

Good empty states:

```txt
まだ記録はありません。短いメモや共有から始められます。
```

```txt
この条件では見つかりませんでした。期間や出典を変えて探せます。
```

Avoid:

```txt
重要な記憶がありません。
```

```txt
あなたの人生データが不足しています。
```

## Visual Guidelines

Memory OS should feel:

- calm
- durable
- private
- searchable
- non-judgmental
- user-controlled

Avoid visual patterns that imply:

- gamified life score
- social ranking
- dating/AI companion intimacy
- surveillance dashboard
- productivity KPI dashboard

## Accessibility

- deletion controls must not be hidden behind tiny menus only
- warnings must be readable
- redaction states must not rely only on color
- privacy states need text labels
- export warnings need confirmation summary
- mobile share flow must be short

## UX Review Checklist

Before shipping any surface:

1. Does it imply AI judges life importance?
2. Does it push full import too strongly?
3. Does it make deletion feel wrong?
4. Does it expose third-party raw text?
5. Does it suggest personality diagnosis?
6. Does it encourage surveillance or blame?
7. Does it make raw saving the default?
8. Does it hide source/evidence?
9. Does it make cost invisible?
10. Does it respect hidden/sealed/deleted?
11. Does it avoid deceased/family simulation?
12. Does it keep small records welcome?

## Acceptance Criteria

UX Guidelines are ready when:

- Import preview exists before analysis.
- Capture does not require importance score.
- Search result explanations avoid life value language.
- Tip is opt-in/restricted for sensitive categories.
- Deletion UI is non-guilt-inducing.
- Export UI shows exclusions and raw status.
- Risky sources show specific warnings.
- User controls are visible on memory detail.
- Empty states do not shame the user.
- Reflection separates fact/inference/source.

## Non-goals

- Maximizing engagement at any cost.
- Making AI feel like a person.
- Turning memories into scores.
- Making users save everything.
- Hiding safety boundaries to improve conversion.

## 結論

Memory OS のUXは、綺麗で便利なだけでは足りない。

画面の言葉ひとつで、記憶の索引が、人格診断・監視・故人再現・人生ランキングに見えてしまう。

だからUXは、ユーザーが安心して小さな記録を残し、必要な時に探し、消したい時に消せることを中心にする。
