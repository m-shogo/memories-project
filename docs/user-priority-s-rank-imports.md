# User Priority S Rank Imports

## 目的

この文書は、Memory OS の趣味・生活文脈Importにおいて、実装しやすさよりもユーザー本人のやる気が出るサービスを Sランクとして優先するための方針である。

前提:

- ユーザーが実際に使っているサービスから始める。
- 自分がやっているもの・見ているもの・聴いているものから入る方が継続意欲が出る。
- APIが無理なサービスでも、CSV、公式Export、履歴画面コピー、URL貼り付け、手入力を正式なImport方法にする。
- 便利さよりも、まず「自分の人生文脈が入る感覚」を優先する。

## Priority Override

過去の実装しやすさ基準より、このSランクを優先する。

```ts
type ImportPrioritySource =
  | 'user_motivation_first'
  | 'technical_feasibility'
  | 'safety_requirement'
  | 'cost_constraint';
```

Sランクでは `user_motivation_first` を最優先する。

ただし、以下は禁止:

- login scraping
- unauthorized scraping
- raw content copying beyond rights/terms
- personal chat history API misuse
- AI personality analysis from hobby data
- importing other people's private data by default

## S Rank Sources

### Music

#### Apple Music

Priority: S

Preferred methods:

- Apple Music API / MusicKit after review
- Apple privacy/data export if available
- Last.fm scrobble fallback
- playlist/library screenshot or copied list paste
- manual current listening / favorite album entry

Why S:

- iPhoneユーザー文脈として強い。
- その時期に聴いていた曲は人生文脈になる。

MVP route:

1. manual paste/list import
2. Last.fm fallback
3. Apple Music connector research
4. MusicKit connector later

#### Spotify

Priority: S

Preferred methods:

- Spotify OAuth API
- playlist URL import
- copied playlist/album/track list paste
- manual current listening entry

Importable:

- saved tracks
- playlists
- recently played
- currently playing
- top artists / tracks

MVP route:

1. Spotify API connector
2. playlist URL paste
3. copied list parser

#### Radio / GERA / Podcasts

Priority: S

Preferred methods:

- OPML file for podcast subscriptions
- RSS feed URL
- episode URL clip
- copied episode/show list paste
- manual listening entry
- app screenshot/manual correction if needed

GERA route:

- APIが確認できるまでAPI前提にしない。
- 番組URL/エピソードURL/履歴画面コピーを正式ルートにする。
- 聴いた日、番組名、エピソード名、メモを保存できれば十分価値がある。

Podcast route:

- OPML first.
- RSS URL first.
- listening historyは手入力/アプリExportがあれば対応。

## Video / Movie / Streaming

#### Netflix

Priority: S

Preferred methods:

- official Viewing Activity CSV
- Netflix personal data request if needed
- viewing activity screen copy/paste
- manual current watching entry

Importable:

- watched title
- watched date
- profile context if user confirms
- currently watching manual state

MVP route:

1. Netflix Viewing Activity CSV parser
2. copy/paste table parser
3. manual currently watching

Safety:

- profile共有に注意。
- family/shared account viewing history is sensitive.
- AI analysis off default.

#### Amazon Prime Video

Priority: S

Preferred methods:

- official data export if user can obtain it
- viewing/history screen copy/paste
- purchase/rental email forward
- manual current watching entry

Importable:

- watched title claim
- purchased/rented title
- date if available
- current watching state

MVP route:

1. copy/paste history parser
2. receipt/email parser
3. manual entry

Avoid:

- account scraping
- browser automation

#### Disney+

Priority: S

Preferred methods:

- official data export if user can obtain it
- watchlist/current watching screen copy/paste
- manual current watching entry

Importable:

- watched/current title claim
- watchlist
- current series/episode if user provides

MVP route:

1. copy/paste watchlist/current screen parser
2. manual entry
3. data export parser if format is available

Avoid:

- account scraping

#### U-NEXT

Priority: S

Preferred methods:

- viewing history screen copy/paste
- purchase/rental email forward
- manual current watching entry
- official export if user can obtain it

Importable:

- watched/current title claim
- purchased/rented title
- date if available

MVP route:

1. copy/paste parser
2. receipt/email parser
3. manual entry

Avoid:

- account scraping

#### Filmarks

Priority: S

Preferred methods:

- URL clip
- watched list copy/paste
- review/rating copy/paste if user explicitly selects
- manual movie entry
- official export if ever available

Importable:

- watched title
- rating
- watched date
- user review/memo
- watchlist

MVP route:

1. copy/paste watched list parser
2. URL clip + TMDb enrichment
3. manual entry

Avoid:

- login scraping
- public profile scraping by default

#### Movies outside listed services

Priority: S

Preferred methods:

- manual movie entry
- title list paste
- Letterboxd CSV/RSS if user uses it
- TMDb enrichment
- cinema ticket email/photo/manual entry

Importable:

- watched movie
- theater visit
- date
- who with, only if user provides
- user memo

## Social / Communication

#### Twitter / X

Priority: S

Preferred methods:

- official X archive ZIP/data export
- URL clip for important posts
- copied post/thread paste
- manual memory entry

Importable:

- own posts
- bookmarks/likes if included in archive and user selects
- saved URLs
- important threads
- profile timeline snippets if user provides

MVP route:

1. X archive parser
2. copied post/thread parser
3. URL clip

Safety:

- likes/bookmarks may be highly sensitive.
- other people replies/DMs are third-party content.
- default to owner_sensitive for likes/bookmarks.
- no surveillance use.

Avoid:

- API-first assumption
- scraping
- importing DMs by default

#### LINE

Priority: S

Preferred methods:

- per-chat exported text file if user provides it
- manual copy/paste from chat
- screenshots with manual correction only if needed
- keep only safe summary by default

Importable:

- user-side memory of events
- chat snippets user explicitly selects
- date/source/person labels

MVP route:

1. LINE text export parser
2. copy/paste chat parser
3. manual memory creation from selected snippet

Safety:

- LINE personal chat is third-party-sensitive.
- raw default off.
- relationship chat summary-only default.
- no spouse/partner intent analysis.
- no evidence package generation.

Avoid:

- pretending LINE Messaging API can read personal chat history.
- bulk raw import by default.
- other person's private raw by default.

## Food / Places

#### 食べログ

Priority: S

Preferred methods:

- restaurant URL clip
- visited/favorite list copy/paste
- reservation email forward if user has it
- manual visited restaurant entry
- receipt/photo/date manual correction

Importable:

- restaurant name
- URL
- visited date if user provides
- rating/memo if user provides
- area/genre
- who with, only if user provides and privacy allows

MVP route:

1. 食べログURL clipper
2. copied list parser
3. reservation/receipt email parser
4. manual restaurant memory

Safety:

- location and companions are sensitive.
- do not infer relationship patterns.
- no stalking/location timeline by default.

Avoid:

- scraping account lists
- importing private dining companions by default

## Manga / Anime

#### Manga outside listed services

Priority: S

Preferred methods:

- manual title/current volume entry
- copied reading list paste
- purchase email forward
- URL clip
- AniList/MAL connector if user uses them

Importable:

- title
- current volume/chapter
- reading/completed/paused state
- purchased date
- user memo

MVP route:

1. manual current reading
2. copied list parser
3. purchase email parser
4. AniList connector

Avoid:

- manga app login scraping
- page/text content import
- scanlation content import

#### Anime outside listed services

Priority: S

Preferred methods:

- manual current watching
- copied watch list paste
- AniList connector
- MyAnimeList connector later
- streaming service current screen copy/paste

Importable:

- title
- episode/progress
- watching/completed/paused state
- user memo

MVP route:

1. manual current watching
2. copied list parser
3. AniList connector

Avoid:

- streaming account scraping

## S Rank Implementation Order

### Phase S0: Manual / paste foundation

This comes before many APIs.

Build:

1. Universal paste import box
2. Source selector
3. HobbyActivity schema
4. Import preview
5. private/sensitive detector
6. title/url/date parser
7. manual current-state entry
8. folder/source-level privacy defaults

Supported paste types:

- title list
- watch history table
- chat snippet
- restaurant list
- podcast episode list
- manga/anime progress list
- music playlist list
- URL list

### Phase S1: High motivation parsers

Build:

1. Netflix Viewing Activity CSV parser
2. LINE text/copy parser
3. X archive parser
4. Filmarks copy/paste + URL clipper
5. 食べログ URL/list parser
6. Podcast OPML/RSS parser
7. GERA episode URL/list parser
8. manga/anime manual progress parser

### Phase S2: High motivation APIs

Build:

1. Spotify API
2. AniList API
3. Last.fm API
4. Apple Music/MusicKit research spike
5. TMDb enrichment
6. Google Books/Open Library/NDL/Calil enrichment as needed

### Phase S3: Streaming/manual bridges

Build:

1. Amazon Prime Video copy/paste parser
2. Disney+ copy/paste parser
3. U-NEXT copy/paste parser
4. streaming service current watching screen parser
5. purchase/rental email parser

## UX Principles

Use:

- まず使っているサービスから始めます。
- APIがないサービスでも、履歴画面のコピーやURL貼り付けで記録できます。
- このサービスは自動連携ではなく、コピー/貼り付けから始めます。
- 作品情報だけ補完します。あなたの感想は勝手に作りません。
- この履歴はプライベート性が高いため、AI分析は既定でオフです。

Do not use:

- APIがないので対応できません。
- ログインすれば全部吸い上げます。
- あなたの趣味傾向を診断します。
- 視聴履歴からあなたの本質を分析します。

## Acceptance Criteria

- User-priority S Rank overrides generic technical priority.
- Manual/paste import is treated as first-class, not fallback shame.
- Each S Rank service has an allowed method even when API is unavailable.
- Scraping remains forbidden.
- LINE raw and private hobby records are protected by default.
- Streaming services can be supported by copy/paste/manual/file import without account scraping.
- Motivation-first onboarding can show these services first.

## 結論

Memory OSの最初のImportは、実装しやすいサービスからではなく、ユーザー本人が実際に使っているサービスから始める。

APIがなくてもよい。

履歴画面コピー、一覧コピー、URL貼り付け、手入力を正式な入口にすれば、Apple Music、X、Netflix、Prime Video、Disney+、U-NEXT、LINE、食べログ、Radio、GERA、Spotify、Podcast、Filmarks、漫画、映画、ラジオ、アニメをSランクとして扱える。

最初に作るべきものは、個別APIではなく、Universal paste/manual import foundationである。
