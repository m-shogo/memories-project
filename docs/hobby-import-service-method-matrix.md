# Hobby Import Service Method Matrix

## 目的

この文書は、趣味系Importについて、サービスごとに最適な取り込み方法を整理する。

前提:

- 全部APIではない。
- 全部スクレイピングでもない。
- 各サービスごとに、公式API、公式Export、CSV、RSS、Takeout、メール、URL保存、手入力、非対応を分ける。
- Memory OSは、無理にログイン情報を預からない。
- Memory OSは、趣味から人格・価値・本質を断定しない。

## Method Types

```ts
type ImportMethod =
  | 'api_oauth'
  | 'api_key_public'
  | 'official_export_file'
  | 'takeout_archive'
  | 'csv_file'
  | 'rss_feed'
  | 'opml_file'
  | 'html_bookmark_file'
  | 'receipt_or_email_forward'
  | 'url_clip'
  | 'manual_entry'
  | 'catalog_enrichment_only'
  | 'not_supported_no_scraping';
```

## Service Policy

```ts
type ServiceImportDecision = {
  service: string;
  domain: string;
  preferredMethod: ImportMethod[];
  fallbackMethod: ImportMethod[];
  doNotUse: ImportMethod[];
  importable: string[];
  avoidImporting: string[];
  privacyDefault: 'owner_only' | 'owner_sensitive' | 'restricted';
  mvpPriority: 'mvp' | 'next' | 'later' | 'avoid';
};
```

## Music

### Spotify

Preferred:

- `api_oauth`
- optional later: `official_export_file` if user provides Spotify account data export

Importable:

- saved tracks
- saved albums
- playlists
- followed artists
- recently played
- currently playing
- top tracks / top artists
- podcast shows / episodes if user allows

Avoid:

- using music taste for personality inference
- writing back to playlists in MVP
- storing full recommendation vectors as raw identity profile

Decision:

- MVP API connector candidate.
- Use minimal scopes.
- Read-only by default.
- Do not require Spotify Premium assumption until endpoint-specific verification.

### Last.fm

Preferred:

- `api_key_public`
- `api_oauth` only if write/scrobble features are ever needed

Importable:

- recent tracks
- loved tracks
- top artists
- top albums
- top tracks
- weekly charts

Avoid:

- commercial/research use without checking Last.fm conditions
- treating scrobbles as complete listening history

Decision:

- MVP API connector candidate.
- Good bridge for Apple Music / Spotify / local player listening history when user already scrobbles.

### ListenBrainz

Preferred:

- `api_key_public`
- user token if private user data is needed

Importable:

- listens
- imported Last.fm listens
- listening history

Decision:

- Next candidate.
- Good open-scrobble ecosystem.

### MusicBrainz

Preferred:

- `api_key_public`
- `catalog_enrichment_only`

Importable:

- artist metadata
- release metadata
- recording metadata
- IDs for matching

Avoid:

- treating MusicBrainz as user activity source

Decision:

- MVP catalog enrichment.
- Use for name normalization and external IDs.

### Apple Music

Preferred:

- `api_oauth` via Apple Music API / MusicKit after implementation review
- fallback: `official_export_file` from Apple privacy/data export if available to user
- fallback: Last.fm scrobble if user uses it
- fallback: manual playlist/library import

Importable:

- library items if authorized
- playlists if authorized
- catalog metadata
- playback/current state depending on platform capability

Avoid:

- promising complete listening history before endpoint verification
- scraping Apple Music account pages

Decision:

- Next candidate, not MVP-first.
- Important for Japanese/iPhone users, but requires careful Apple Developer/MusicKit review.

### Amazon Music

Preferred:

- `manual_entry`
- `receipt_or_email_forward` for purchased music only
- fallback: Last.fm scrobble if user has configured it
- fallback: Amazon account data export if user can obtain relevant files

Importable:

- purchased music references
- manually saved playlists/albums
- listening memory claims

Avoid:

- login scraping
- claiming full personal listening API support

Decision:

- Later / file-first.
- Do not build as API connector until official personal history API is confirmed.

## Movie / TV

### Letterboxd

Preferred:

- `csv_file`
- `rss_feed`

Importable:

- watched films
- diary entries
- ratings
- reviews
- tags
- watchlist
- lists

Avoid:

- using API as default path
- applying for API for LLM/private/personal/recommendation use

Decision:

- MVP file/RSS connector.
- CSV import is safer than API dependency.

### TMDb

Preferred:

- `api_key_public`
- `catalog_enrichment_only`

Importable:

- movie metadata
- tv metadata
- cast/crew
- poster/backdrop
- release dates
- external IDs

Avoid:

- treating TMDb as personal watch history

Decision:

- MVP catalog enrichment.
- Use for Letterboxd / Filmarks / manual entries.

### Trakt

Preferred:

- `api_oauth`

Importable:

- watched history
- watchlist
- ratings
- progress
- collections

Avoid:

- assuming all Japanese users use it

Decision:

- Next candidate.
- Strong for movie/TV power users.

### Simkl

Preferred:

- `api_oauth`

Importable:

- anime/movie/tv tracking
- watch history
- lists

Decision:

- Next/later candidate.

### Filmarks

Preferred:

- `manual_entry`
- `url_clip`
- user-provided export if Filmarks provides one in the future

Importable:

- watched movie title
- rating if user manually provides
- review/memo if user manually provides
- watch date if user manually provides
- profile/list URL as source reference

Avoid:

- login scraping
- public profile scraping as default
- importing others' reviews as user memory

Decision:

- Manual/file-first.
- Use TMDb for catalog enrichment.

### Netflix

Preferred:

- `official_export_file` if user downloads viewing activity
- `manual_entry`

Importable:

- viewing activity title/date from user-provided file

Avoid:

- account scraping
- inferring sensitive traits from viewing history

Decision:

- File-first later candidate.
- Viewing history is owner_sensitive.

### Prime Video / Disney+ / Hulu / U-NEXT / TVer / ABEMA

Preferred:

- `manual_entry`
- `official_export_file` only if user can obtain one
- `receipt_or_email_forward` for purchase/rental receipts

Importable:

- title
- watched/started/completed claim
- purchase/rental date
- user memo

Avoid:

- login scraping
- browser automation
- importing family profile viewing history by default

Decision:

- Later/manual.

## Anime / Manga

### AniList

Preferred:

- `api_oauth`

Importable:

- anime list
- manga list
- status: watching / reading / completed / paused / dropped / planning
- score
- progress
- favourites

Avoid:

- using score for personality/value judgment
- importing private lists without clear preview

Decision:

- MVP API connector.

### MyAnimeList

Preferred:

- `api_oauth` after OAuth/rate-limit review
- fallback: user-provided list export if available
- fallback: manual entry

Importable:

- anime list
- manga list
- status
- score
- progress

Avoid:

- relying on unofficial scraping

Decision:

- Next candidate.

### Kitsu

Preferred:

- `api_oauth` / public API after review

Importable:

- library entries
- anime/manga status
- progress

Decision:

- Later/next.

### MangaDex

Preferred:

- `url_clip`
- `manual_entry`
- optional metadata lookup only after rights review

Importable:

- title reference
- URL reference
- user memo

Avoid:

- raw chapter content
- scanlation content import
- reading history scraping

Decision:

- Avoid as MVP connector.
- MangaDex may contain unofficial translations, so treat carefully.

### MANGA Plus / Shonen Jump+ / BookWalker / ebookjapan / コミックシーモア / ピッコマ / LINEマンガ

Preferred:

- `manual_entry`
- `receipt_or_email_forward` for purchases
- `url_clip`
- `official_export_file` only if user can obtain one

Importable:

- title
- volume/chapter claim
- purchase date
- user memo
- currently reading state

Avoid:

- login scraping
- app automation
- importing manga pages or text
- family/shared account assumptions

Decision:

- Manual/file-first.
- Use external catalog enrichment where legal and available.

## Books / Libraries

### Google Books

Preferred:

- `api_oauth` for personal bookshelves where appropriate
- `api_key_public` for catalog search
- `catalog_enrichment_only`

Importable:

- book metadata
- viewability/eBook availability
- personal bookshelves if authorized

Decision:

- MVP catalog + possible personal bookshelf connector.

### Open Library

Preferred:

- `api_key_public`
- `catalog_enrichment_only`
- public reading log only if user explicitly selects it

Importable:

- book search
- covers
- work/edition metadata
- public reading log
- public lists

Avoid:

- high-volume backend dependency
- HTML scraping

Decision:

- MVP catalog enrichment.
- Respect rate limits and cache.

### NDL Search

Preferred:

- `api_key_public` / public API according to NDL conditions
- `catalog_enrichment_only`

Importable:

- Japanese bibliographic metadata
- identifiers
- publication data

Avoid:

- continuous/commercial use without application/condition review
- bulk harvesting for app backend without process

Decision:

- MVP Japanese book metadata enrichment.

### Calil

Preferred:

- `api_key_public`
- `catalog_enrichment_only`

Importable:

- library holdings
- availability status
- nearby libraries

Avoid:

- treating Calil as loan history

Decision:

- MVP library availability enrichment.
- User's actual loan history remains manual/file-first.

### Goodreads

Preferred:

- `csv_file`
- `manual_entry`

Importable:

- bookshelves
- ratings
- read dates
- reviews if user provides CSV

Avoid:

- old API dependency
- scraping profile pages

Decision:

- File-first.

### StoryGraph

Preferred:

- `csv_file`
- `manual_entry`

Importable:

- reading history
- ratings
- owned/wishlist/reading states if export supports them

Decision:

- File-first next.

### 読書メーター / ブクログ

Preferred:

- `manual_entry`
- `url_clip`
- `csv_file` only if user can export

Importable:

- title
- read date
- status
- user memo/review if user provides it

Avoid:

- login scraping
- public profile scraping by default

Decision:

- Manual/file-first.

### Library loan history / 図書館履歴

Preferred:

- `manual_entry`
- user-provided receipt/photo metadata with manual correction
- user-provided CSV only if library provides it

Importable:

- borrowed book title
- borrow date / return date if user provides
- library name if user wants

Avoid:

- library account scraping
- family/child card import by default
- automatic precise location retention

Decision:

- Restricted/manual-only.
- Loan history is highly sensitive.

## Cooking / Recipes

### Cookpad

Preferred:

- `url_clip`
- `manual_entry`
- user-provided export if Cookpad provides one in the future

Importable:

- recipe title
- source URL
- cooked date
- user photo
- user memo
- family reaction memo
- want-to-try / cooked / repeat state

Avoid:

- copying full recipe text
- unauthorized recipe scraping
- login scraping saved recipes

Decision:

- Manual/url-first.
- Strong Memory OS value without full API.

### Rakuten Recipe

Preferred:

- `api_key_public` after Rakuten Web Service review
- `url_clip`
- `manual_entry`

Importable:

- recipe metadata
- title / URL
- category/ranking if allowed

Avoid:

- copying full recipe content beyond license

Decision:

- Next candidate.

### Edamam / Spoonacular

Preferred:

- `api_key_public` / paid API
- `catalog_enrichment_only`

Importable:

- recipe metadata
- nutrition/allergen metadata if licensed

Avoid:

- making overseas recipe API central for Japanese MVP
- storing full recipe content beyond terms

Decision:

- Later.

## Games

### Steam

Preferred:

- `api_key_public` / user-authenticated Steam Web API flow as appropriate

Importable:

- owned games when visible
- recently played games
- playtime
- badges / Steam level if user allows

Avoid:

- using playtime as life value/discipline score
- assuming private profile data is available

Decision:

- MVP API connector.

### IGDB

Preferred:

- `api_key_public`
- `catalog_enrichment_only`

Importable:

- game metadata
- cover
- release date
- platform
- genre

Decision:

- Catalog enrichment for manual/Steam imports.

### Nintendo / PlayStation / Xbox

Preferred:

- `manual_entry`
- annual wrap-up exports/screenshots with user correction
- purchase receipt import if available

Importable:

- played title
- play period
- user memo
- purchase/owned claim

Avoid:

- login scraping console accounts

Decision:

- Manual/file-first.

## Web / Articles / Bookmarks

### Browser bookmarks

Preferred:

- `html_bookmark_file`
- browser JSON export if available

Importable:

- title
- URL
- folder path
- added date if included

Avoid:

- instant AI summarization of every URL
- importing work/private bookmarks into AI context by default

Decision:

- MVP file import.

### Pocket / Instapaper / Raindrop.io

Preferred:

- `api_oauth` if available and approved
- `official_export_file`
- `csv_file`

Importable:

- saved URL
- title
- tags
- archived/read status
- saved date

Avoid:

- full article body by default

Decision:

- Next candidate.

## Video / YouTube / Podcast

### Google Takeout / YouTube

Preferred:

- `takeout_archive`

Importable:

- YouTube watch history
- YouTube search history only if explicitly selected
- liked videos
- playlists
- subscriptions
- YouTube Music data if included

Avoid:

- API-only assumption for full watch history
- AI analysis on by default
- importing search history without separate warning

Decision:

- MVP file import, but sensitive default.

### YouTube Data API

Preferred:

- `api_oauth` for playlists/subscriptions/liked videos as applicable
- `catalog_enrichment_only`

Importable:

- playlists
- subscriptions
- video metadata

Avoid:

- treating API as full watch-history source

Decision:

- Next candidate after Takeout parser.

### Podcast Apps

Preferred:

- `opml_file`
- `manual_entry`
- app export if available

Importable:

- subscribed podcasts
- episode URLs
- user memo

Avoid:

- claiming complete listening history unless app export provides it

Decision:

- OPML-first.

### Netflix and other video services

Preferred:

- `official_export_file` if user downloads viewing activity
- `manual_entry`

Importable:

- title
- watch date
- profile context only if user confirms

Avoid:

- scraping
- family profile import by default

Decision:

- File/manual-first.

## Priority by Build Order

### Build first: generic import infrastructure

1. Import Preview
2. Source Adapter interface
3. File parser framework
4. Catalog enrichment framework
5. HobbyActivity schema
6. Manual entry and URL clipper
7. Privacy/safety classifier before AI use

### Build second: high-value safe imports

1. Browser bookmarks
2. Letterboxd CSV/RSS
3. AniList API
4. Last.fm API
5. Spotify API
6. Google Takeout YouTube parser
7. Google Books / Open Library / NDL / Calil enrichment
8. Steam API

### Build later

1. Apple Music
2. MyAnimeList
3. Trakt / Simkl
4. Pocket / Raindrop / Instapaper
5. Readwise
6. StoryGraph / Goodreads CSV
7. Cookpad URL clipper enhancements
8. Filmarks manual helper

## UI Copy

Use:

- このサービスは公式APIで接続できます。
- このサービスは公式Exportファイルから取り込めます。
- このサービスは公開APIが確認できないため、URL保存または手入力で対応します。
- 作品情報だけを補完します。あなたの感想や評価は勝手に作りません。
- 趣味から性格や人生価値を判断しません。
- この履歴はセンシティブな内容を含む可能性があります。AI分析は既定でオフです。

Do not use:

- このサービスの履歴を自動で全部吸い上げます。
- あなたの本当の趣味を分析します。
- この作品群からあなたの本質が分かります。
- ログインすれば全部取れます。
- スクレイピングで対応します。

## 結論

趣味Importはサービスごとに最適解が違う。

APIが強いサービスはAPI、Exportが強いサービスはファイル、APIもExportも弱いサービスはURL保存・手入力に寄せる。

Memory OSの強さは「全部自動で吸うこと」ではなく、「安全に、出典つきで、趣味の文脈を残せること」である。
