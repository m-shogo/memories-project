# Next Chat Concrete MVP Scope Addendum

## 目的

この文書は、Memory OS MVPへ具体的に何を入れるかを次チャットへ引き継ぐ。

## Canonical Docs

- `docs/concrete-mvp-product-scope.md`
- `docs/concrete-mvp-ticket-backlog.md`
- `docs/adopted-patterns-implementation-plan.md`
- `docs/adopted-product-patterns-registry.md`

## MVP Promise

```txt
タイトル、URL、進行、簡単な履歴を入れる
→ 保存前にPreviewできる
→ 自分の棚・地図・進行表として見える
→ 後から検索、更新、Exportできる
```

## MVP Navigation

```txt
ホーム
発見
振り返り
日常
```

## Home

Include:

- 今週の箱 0〜1枚
- 漫画・アニメ棚
- 映画・視聴棚
- 食の地図
- あとで見る棚
- 未整理Inbox

Do not include:

- life score
- streak
- daily completion
- mood/personality analysis
- graph-first home

## Daily

Include:

- Quick Add input
- manga/anime +1 progress
- restaurant quick add
- Inbox cleanup one item

Accepted input:

```txt
SPY×FAMILY 12巻まで
葬送のフリーレン 8話まで
PERFECT DAYS 見た
食べログURL
店名 行きたい
```

## Import Preview

Always required before save.

Include:

- detected format
- destination shelf
- source
- confidence
- warning
- candidate select/unselect
- title/progress/status correction
- duplicate candidate

No direct import-to-save.

## Shelves

### Manga / Anime

- 進行中
- 見たい
- 完了
- 保留
- volume/episode/chapter
- +1 / direct edit

### Movie / Streaming

- 見た
- 見たい
- お気に入り
- manual text first
- Netflix CSV fixture second

### Food

- area grouped list first
- 行きたい / 行った
- favorite
- source URL
- map SDK later

### Later list

- cross-medium temporary want-later collection

## Discovery

MVP:

- recent additions
- confirmed exact relations
- relation reason

Later:

- Memory Constellation graph

## Reflection

MVP:

- month selector
- factual shelf counts
- updates/additions

P1:

- safe last year
- seasonal/year capsule

## Search

MVP:

- title
- restaurant name
- user note
- source label

Filters:

- shelf
- source
- status
- period
- area

No embedding required.

## Export

MVP:

- JSON
- progress/food CSV
- manifest
- shelf/period/status selection
- eligible/excluded count

## MVP Import Forms

M0:

- title-list
- URL-list
- manga/anime progress text
- restaurant URL/name

M1:

- Netflix viewing CSV fixture
- generic table CSV

Deferred:

- Filmarks
- LINE
- Spotify/Apple Music
- image metadata
- browser bookmarks

## Weekly / Monthly

Weekly:

- one progress update
- one Inbox item
- one shelf change
- one exact relation

Monthly:

- factual Month Capsule

No push notification in initial MVP except operational notification.

## Build Order

```txt
foundation
→ app shell
→ Quick Add / Detector / Preview / Commit
→ Home Shelf Grid
→ Manga/Anime end-to-end
→ Food end-to-end
→ Inbox/Search
→ Weekly/Month
→ Movie/Netflix fixture
→ Discovery relations
→ Export
```

## Definition of Done

1. paste/title/URL/progress accepted.
2. Preview always shown.
3. manga/anime works end-to-end.
4. food works end-to-end.
5. movie/manual and Netflix fixture work.
6. unknown data goes to Inbox.
7. search works.
8. Weekly Box shows at most one safe action.
9. Month Capsule shows facts only.
10. Export works.
11. no streak, life score, personality inference.
12. synthetic fixture demo under 2 minutes.

## Current Phase Note

設計上の具体スコープは固定した。

実装開始時は `docs/concrete-mvp-ticket-backlog.md` の `MVP-0001` から進め、各作業を小さくcommit/pushする。
