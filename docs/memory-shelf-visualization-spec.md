# Memory Shelf Visualization Spec

## 目的

この文書は、媒体/DBごとの可視化を定義し、ユーザーがImportしたくなる・週1で戻りたくなる・開発者が作っていて手応えを見えるようにするための仕様である。

Memory OSの良い依存性は、抽象的な未来価値ではなく、棚・地図・箱・年表・進行表として見える必要がある。

## Core Metaphor

```txt
Memory OS = 自分の文脈の部屋
Medium DB = 部屋の中の棚・地図・箱
Import = 棚を作る/埋める行為
Weekly action = 棚を1つ見る/1つ増やす/1つ整える行為
```

## Top-level Home: Memory Room

Home should not start as a boring dashboard.

It should show a room-like collection of shelves.

```txt
あなたの棚

映画棚          126件
漫画/アニメ棚    42件
音楽棚          230件
ラジオ棚         18件
食の地図         31件
写真箱           12件
会話メモ箱        4件
旅行箱            2件
```

Empty shelves are visible but inviting.

```txt
音楽棚はまだ空です。
Apple Music / Spotify / Last.fm / URLから作れます。
```

## Shelf States

```ts
type ShelfState =
  | 'empty'
  | 'preview_available'
  | 'first_imported'
  | 'growing'
  | 'rich'
  | 'needs_review'
  | 'quiet_archived';
```

### empty

Show:

- what this shelf becomes
- how to import
- example preview

### preview_available

Show:

- Import preview ready
- candidate count
- save not required

### first_imported

Show celebration, but not addictive pressure.

```txt
映画棚ができました。
126件の作品を確認できます。
```

### growing

Show:

- latest additions
- year/month coverage
- gaps
- next import suggestion

### rich

Show deeper views:

- timeline
- clusters
- cross-source links
- revisit prompts

### needs_review

Show:

- low confidence
- duplicate candidates
- previously deleted candidates

### quiet_archived

Show:

- low activity but preserved
- no guilt

## Visualization Types

```ts
type ShelfVisualizationType =
  | 'shelf_grid'
  | 'timeline'
  | 'progress_tracker'
  | 'map_view'
  | 'calendar_heatmap_light'
  | 'cross_source_links'
  | 'weekly_box'
  | 'year_capsule'
  | 'collection_stack';
```

## Domain Shelves

### Movie Shelf

Sources:

- Netflix
- Prime Video
- Disney+
- U-NEXT
- Filmarks
- Letterboxd
- manual movie
- cinema ticket/email

Views:

- watched timeline
- want-to-watch list
- rating/review if user provided
- cinema visits
- cross-source duplicates

Import motivation:

```txt
Netflixを入れると、見た映画の年表ができます。
Filmarksを足すと、見たい映画や評価も同じ棚に並びます。
```

Weekly hook:

```txt
去年の今ごろ見ていた映画を1本開く。
```

### Streaming Shelf

Sources:

- Netflix
- Prime Video
- Disney+
- U-NEXT
- YouTube Takeout

Views:

- watched timeline
- series progress
- platform breakdown
- shared profile warning

Import motivation:

```txt
視聴履歴を入れると、どの時期に何を見ていたかが棚になります。
```

### Manga / Anime Progress Shelf

Sources:

- manual progress
- AniList
- manga/anime paste
- purchase email
- streaming progress

Views:

- progress tracker
- reading/watching/completed
- paused/dropped
- next volume/episode
- years active

Import motivation:

```txt
「12巻まで」のように貼るだけで、進行表ができます。
```

Weekly hook:

```txt
1作品だけ進行を更新する。
```

This shelf has high practical value.

### Music Shelf

Sources:

- Apple Music
- Spotify
- Last.fm
- playlist URLs
- manual music notes

Views:

- recent listening timeline
- playlists
- artist/album stacks
- period music
- cross-source track links

Import motivation:

```txt
音楽棚を作ると、この時期によく聴いていた曲を後から見返せます。
```

Safe discovery:

```txt
2026年7月によく記録されていた曲です。
```

Avoid:

```txt
あなたの本当の性格はこの音楽に出ています。
```

### Audio / Radio Shelf

Sources:

- GERA
- Podcast
- radio apps
- OPML/RSS
- episode URLs

Views:

- subscribed shows
- listened episodes
- want-to-listen
- show timeline

Import motivation:

```txt
番組名やURLを貼ると、ラジオ/Podcast棚ができます。
```

Weekly hook:

```txt
今週聴きたい回を1つ入れる。
```

### Food Map

Sources:

- 食べログ
- restaurant URLs
- reservation email
- manual restaurant
- food photo metadata

Views:

- map by area
- want-to-go
- visited
- genre clusters
- travel food map

Import motivation:

```txt
食べログURLを貼ると、行きたい店の地図ができます。
```

Weekly hook:

```txt
行きたい店を1つ追加する。
```

Safety:

- precise visit date/location owner_sensitive
- companion inference denied

### Photo Box

Sources:

- image metadata
- safe thumbnails
- camera roll export later

Views:

- month boxes
- travel/photo group by date
- no face identity inference
- EXIF stripped badge

Import motivation:

```txt
写真そのものではなく、まず安全なメタデータから箱を作れます。
```

### Conversation Memo Box

Sources:

- LINE selected snippets
- chat snippets
- safe summaries

Views:

- safe summaries
- date range
- source labels
- raw hidden

Import motivation:

```txt
会話の原文を残さず、安全な要約だけ記録できます。
```

No weekly dependency hooks from private conversations.

### Travel Box

Sources:

- calendar
- restaurant map
- photos metadata
- manual notes
- tickets/emails

Views:

- trip timeline
- map
- places
- food
- photos metadata

Import motivation:

```txt
旅行の前後の記録を、地図と時系列でまとめられます。
```

## Cross-shelf Links

Good excitement comes from shelves connecting.

Examples:

- Netflix and Filmarks both mention same movie.
- Restaurant and photo metadata share same trip period.
- Music heavily appears during a travel month.
- Manga progress and anime watch progress share title.
- Calendar event and restaurant reservation align.

Safe copy:

```txt
同じ作品が複数の棚にあります。
```

```txt
この旅行時期に、写真箱と食の地図が増えています。
```

Avoid:

```txt
この時期のあなたの本心は...
```

## Importable Empty State Cards

Every shelf should have empty-state cards.

```ts
interface EmptyShelfCard {
  shelfId: string;
  title: string;
  whatAppearsAfterImport: string[];
  supportedImports: string[];
  exampleInput: string;
  privacyNote: string;
}
```

Example:

```txt
漫画棚

貼るだけで作れます:
ワンピース 108巻まで
ブルーロック 31巻まで

できるもの:
- 進行表
- 読書中/完了
- 次に読む候補
```

## Visual Reward Copy

Allowed:

```txt
棚ができました。
```

```txt
地図に3件追加されました。
```

```txt
この時期の記録が少し見えるようになりました。
```

```txt
1件だけ直すと、この棚がきれいになります。
```

Avoid:

```txt
あなたの記憶が完全になりました。
```

```txt
この棚が空なのはもったいないです。
```

```txt
今日も埋めないと忘れてしまいます。
```

## MVP Visualization Requirement

MVP must include at least:

1. Home shelf grid.
2. Empty shelf cards.
3. Import preview to shelf preview.
4. Post-import shelf created state.
5. One timeline view.
6. One progress tracker.
7. One map/list view.
8. Weekly one-action card.

Recommended MVP shelves:

```txt
Movie/Streaming Shelf
Manga/Anime Progress Shelf
Food Map
Audio/Radio Shelf
Conversation Memo Box
```

## Developer Motivation Rule

Every parser/adapter should unlock or improve a visible shelf.

Do not build invisible plumbing for too long without a shelf reward.

Ticket acceptance should include:

```txt
What shelf does this unlock?
What visible state changes after fixture import?
What weekly action does it enable?
```

## P0 Tests

1. Empty shelf card exists for each MVP shelf.
2. Import preview shows which shelf will be created.
3. Post-import state shows shelf count/coverage.
4. Sensitive shelves do not show raw private details by default.
5. Weekly card does not use guilt/streak copy.
6. Every MVP parser maps to a shelf visualization.
7. Cross-source links do not infer personality or hidden intent.
8. User can hide a shelf without penalty copy.
9. Export readiness is visible but not fear-based.
10. No shelf says AI understands user better than people.

## 結論

DBごとの可視化は、Memory OSの良い依存性を見える化する中心である。

ユーザーはAIに戻るのではなく、自分の棚・地図・箱・年表に戻る。

開発者はparserやadapterを作るたびに、見える棚が増える。

これがワクワク感と継続モチベーションの土台になる。
