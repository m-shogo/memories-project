# Founder Visible Motivation Loop

## 目的

この文書は、Memory OS を作る側が、AIで何でも楽に作れそうな時代に、それでも真面目に作り続けられるようにするための設計である。

これは慰めではない。

問題は、悪意ある依存アプリが稼げるかどうかではない。

根本問題は、良い依存性が未来価値すぎて、作っている本人に今日の報酬が見えにくいこと。

## 問題定義

AIで多くのものが作れそうになる。

- 悪い依存アプリも作れそう
- 良いMemory OSも作れそう
- ゲームも作れそう
- 画像も作れそう
- 設計も実装も進められそう

この「やれば出来そう」は希望であると同時に、重さを奪う。

さらに、悪い依存性は見えやすい。

```txt
優しいAI
否定しない会話
恋人/結婚/独占関係
長時間滞在
すぐ戻ってくる
課金導線が見える
```

一方、Memory OSの良い依存性は見えにくい。

```txt
5年後に効く
AI乗り換えで効く
記録が積み上がって効く
失った時に価値が分かる
```

これでは作成者の脳に報酬が来るのが遅い。

## Core Insight

```txt
良い依存性も、作る側に今日見える報酬へ変換する必要がある。
```

## Founder-visible Loop

```txt
fixtureを作る
→ parserが動く
→ previewが出る
→ shelfが生まれる
→ map/timeline/progressが埋まる
→ weekly actionが増える
→ 作った意味が画面で見える
```

このloopがない実装は、長期でモチベーションを削る。

## Ticket Acceptance Rule

すべての実装ticketは、以下に答える。

```txt
1. このticketで、どの棚/箱/地図/年表が見えるようになるか？
2. fixtureを入れた時、画面のどこが変わるか？
3. ユーザーがImportしたくなる理由は何か？
4. 週1で戻る理由は増えるか？
5. 毎日でも触れるmicro actionは増えるか？
```

答えられないticketは、必要でも「見えない作業」として扱い、短く切る。

## Invisible Work Budget

安全設計、DB、RLS、Policy、Migrationは必要。

ただし、見えない作業だけを長く続けると、作成者が折れる。

Rule:

```txt
2〜3個のinvisible foundation作業ごとに、1個visible reward作業を挟む。
```

Examples:

```txt
SecurityGate
ParserRegistry
Detector
→ title-list shelf preview
```

```txt
RLS tests
Migration slice
Policy tests
→ Netflix fixture to Movie/Streaming Shelf
```

```txt
Dedupe/Tombstone
Preview policy
Audit
→ duplicate badge / previously deleted candidate visible
```

## Work Types

```ts
type WorkVisibility =
  | 'invisible_foundation'
  | 'semi_visible_preview'
  | 'visible_shelf_reward'
  | 'weekly_ritual_reward'
  | 'developer_demo_reward';
```

### invisible_foundation

Examples:

- RLS
- migration
- key management
- audit
- policy internals

Must be paired with visible proof.

### semi_visible_preview

Examples:

- Import Preview cards
- warnings
- confidence badges
- selected/skipped states

### visible_shelf_reward

Examples:

- Movie Shelf created
- Food Map added
- Manga Progress visible
- Audio Shelf filled

### weekly_ritual_reward

Examples:

- Weekly Box card
- one-action prompt
- last-year-this-week view

### developer_demo_reward

Examples:

- fixture gallery
- local demo seed
- snapshot screenshots
- before/after import story

## Demo-first Development

Every medium should have a demo story.

Example:

```txt
Demo: Netflix CSV
1. empty Movie Shelf
2. upload fixture
3. Preview shows 4 candidates
4. Save disabled in preview-only mode
5. Shelf preview shows watched timeline
6. duplicate badge appears
7. weekly action appears: 去年の今ごろ見た映画を見る
```

This makes the future visible.

## The Right Hardness

AIで楽に作れる時代に、難しさは外から来ない。

自分で選ぶ。

Memory OSが選ぶ難しさ:

- 悪い依存で稼がない
- でも戻りたくなるものを作る
- 安全にしすぎて退屈にしない
- Importした瞬間に自分の世界を見せる
- 出られるのに残りたくなる設計にする
- 長期で壊れないDBにする
- support/admin raw accessを作らない
- persona化しない

This is not moral decoration.

This is the craft challenge.

## Founder Motivation Milestones

### Milestone 1: First visible shelf

```txt
title-list fixture → Shelf Preview appears
```

### Milestone 2: First personal-feeling shelf

```txt
manga-progress fixture → progress tracker appears
```

### Milestone 3: First map

```txt
restaurant URL fixture → Food Map list/area view appears
```

### Milestone 4: First cross-source link

```txt
Netflix + Filmarks same title → connected record appears
```

### Milestone 5: First weekly ritual

```txt
Weekly Box shows one action based on imported shelf
```

### Milestone 6: First safe sensitive box

```txt
LINE snippet → safe Conversation Memo Box without raw
```

### Milestone 7: First export readiness badge

```txt
standard records show export-ready state
```

## Anti-patterns

Avoid:

- months of invisible architecture only.
- safety docs with no demo payoff.
- monetization talk before visible excitement.
- AI companion features because they are easier to feel.
- dashboard with only counts.
- generic import list with no shelf transformation.

## P0 Tests

1. Every MVP parser maps to a visible shelf reward.
2. Every sprint contains at least one visible reward ticket.
3. Fixture import changes a user-visible shelf/preview state.
4. Invisible foundation tickets declare their paired visible proof.
5. Weekly ritual is unlocked by at least one shelf.
6. Local demo can show before/after import in under 2 minutes.
7. No ticket uses emotional dependency as reward.
8. No dashboard shows only raw counts without domain meaning.
9. Developer demo fixtures use synthetic data only.
10. Roadmap labels invisible vs visible work.

## 結論

Memory OSの開発モチベーション問題は、思想や倫理の問題だけではない。

良い依存性が未来価値すぎることが問題である。

だから、作るたびに画面が変わり、自分の棚・地図・年表が育つようにする。

作成者本人が先を見える設計にする。
