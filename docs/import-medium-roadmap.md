# Import Medium Roadmap

## 目的

この文書は、Memory OS のImportを「サービス単位」だけでなく、「媒体カテゴリ単位」で整理し、どの媒体をどの順番で、どの方式で、安全に取り込むかを固定する。

ユーザー優先Sランクは維持する。

ただし、実装ではサービスごとに完全別実装せず、媒体ごとのParser/Normalizer/Privacy defaultを共有し、Source Adapterで意味を補正する。

## 最重要方針

```txt
Medium-first capabilities
+ Service-specific adapters
+ Import Preview
+ Policy Evaluation
+ Safe Commit
```

媒体カテゴリで共通化する。

サービス別に意味を調整する。

例:

- Netflix / Prime / Disney+ / U-NEXT は Streaming Watch Activity 系。
- Spotify / Apple Music / Last.fm は Music Listening Activity 系。
- GERA / Podcast / Radio は Audio Episode Activity 系。
- Filmarks / Letterboxd / TMDb は Movie Activity / Catalog 系。
- AniList / MAL / Manga manual は Anime/Manga Progress 系。
- LINE / DM / chat screenshot は Message/Conversation Context 系。
- 食べログ / 予約メール / restaurant URL は Place/Food Activity 系。

## Medium Categories

```ts
type ImportMedium =
  | 'manual_note'
  | 'title_list'
  | 'url_clip'
  | 'web_bookmark'
  | 'streaming_watch_activity'
  | 'music_listening_activity'
  | 'audio_episode_activity'
  | 'movie_activity'
  | 'anime_manga_progress'
  | 'book_reading_activity'
  | 'library_activity'
  | 'restaurant_food_activity'
  | 'recipe_cooking_activity'
  | 'game_activity'
  | 'social_post_activity'
  | 'message_conversation_context'
  | 'email_receipt_context'
  | 'calendar_event_context'
  | 'image_media_context'
  | 'persona_like_context'
  | 'export_archive_context';
```

## Priority Layers

### Layer 0: Foundation

Must exist before any medium-specific commit.

- SecurityGate
- SourceSelector
- Parser Registry
- Content Detector
- Import Preview
- Policy Evaluation
- Dedupe/Tombstone checks
- Audit without raw

### Layer 1: Universal High-Value Mediums

These unlock many S-rank services quickly.

1. `title_list`
2. `url_clip`
3. `manual_note`
4. `streaming_watch_activity` via paste/CSV
5. `anime_manga_progress` via paste/manual
6. `restaurant_food_activity` via URL/list/email
7. `audio_episode_activity` via URL/list/OPML/RSS
8. `web_bookmark`

### Layer 2: Sensitive High-Value Mediums

Implement only after Preview + Policy + Tombstone are working.

1. `message_conversation_context`
2. `social_post_activity`
3. `image_media_context`
4. `export_archive_context`
5. `persona_like_context`

### Layer 3: API-backed Mediums

Implement after token/OAuth gates.

1. `music_listening_activity` Spotify/Last.fm
2. `anime_manga_progress` AniList
3. `game_activity` Steam
4. `movie_activity` TMDb enrichment
5. `book_reading_activity` catalog enrichment

## Medium → Services Mapping

### streaming_watch_activity

Services:

- Netflix
- Amazon Prime Video
- Disney+
- U-NEXT
- YouTube/YouTube Takeout video history

Methods:

- Netflix CSV
- viewing history copy-paste
- watchlist copy-paste
- current watching manual
- URL clip
- email receipt for purchase/rental

Privacy:

- owner_sensitive default
- shared profile warning
- AI analysis off
- Export excluded by default

### music_listening_activity

Services:

- Spotify
- Apple Music
- Last.fm
- YouTube Music/Takeout
- podcast/music app paste

Methods:

- API
- playlist/library paste
- URL clip
- data export
- Last.fm fallback
- manual current listening

Privacy:

- public playlist owner_only
- recent/current/private listening owner_sensitive
- AI taste/personality diagnosis disabled

### audio_episode_activity

Services:

- Podcast apps
- GERA
- radiko/radio apps
- YouTube audio shows

Methods:

- OPML
- RSS
- episode URL
- episode list paste
- manual listened/want_to_listen

Privacy:

- owner_only default
- sensitive show/folder owner_sensitive
- no personality inference

### movie_activity

Services:

- Filmarks
- Letterboxd
- Netflix/Prime/Disney+/U-NEXT
- TMDb enrichment
- cinema ticket/reservation email

Methods:

- list paste
- CSV/RSS where available
- URL clip
- manual watched/want_to_watch
- ticket/email receipt
- catalog enrichment

Privacy:

- owner_only for title/status
- owner_sensitive for review/private rating/shared profile

### anime_manga_progress

Services:

- AniList
- MyAnimeList/Kitsu later
- manga apps manual/list paste
- purchase emails
- streaming watchlist paste

Methods:

- API
- progress list paste
- manual current progress
- purchase email
- URL clip

Privacy:

- owner_only default
- private folders owner_sensitive
- no app scraping
- no manga page raw import

### book_reading_activity / library_activity

Services:

- Goodreads CSV
- StoryGraph CSV
- Booklog/読書メーター paste/manual
- Google Books/Open Library/NDL/Calil enrichment
- library loan manual/file

Methods:

- CSV
- list paste
- ISBN list
- manual reading progress
- catalog enrichment

Privacy:

- reading list owner_only/owner_sensitive user choice
- library loan history restricted/manual
- public catalog not treated as user history

### restaurant_food_activity

Services:

- 食べログ
- Google Maps saved places later
- reservation emails
- cooking/meal manual notes

Methods:

- URL clip
- saved list paste
- reservation email
- manual visited/want_to_go
- food photo metadata

Privacy:

- restaurant title owner_only
- precise visit date/location/companions owner_sensitive
- no location/relationship pattern inference

### recipe_cooking_activity

Services:

- Cookpad
- recipe sites
- personal cooking notes
- food photos

Methods:

- URL clip
- manual cooked memory
- recipe title/list paste
- photo metadata

Privacy:

- owner_only for recipe title
- family reaction/health/diet owner_sensitive
- full recipe body not stored by default

### game_activity

Services:

- Steam
- Nintendo/PlayStation/Xbox emails/manual
- game lists

Methods:

- API where safe
- library list paste
- recently played paste/API
- purchase email
- manual current playing

Privacy:

- owner_only default
- playtime owner_sensitive option
- no life discipline score

### social_post_activity

Services:

- X archive
- social URL clips
- copied posts

Methods:

- archive ZIP
- URL clip
- copied post/thread paste

Privacy:

- own posts owner_only
- likes/bookmarks owner_sensitive
- DMs excluded/restricted summary-only
- no surveillance

### message_conversation_context

Services:

- LINE
- DM screenshots
- selected chat copy
- email snippets

Methods:

- text export
- selected copy-paste
- summary-only manual memory
- screenshot metadata/summary only

Privacy:

- restricted default
- raw off
- AI analysis off
- Export excluded
- no evidence package

### image_media_context

Services:

- photo upload
- screenshots
- thumbnails
- cover images
- receipts/documents

Methods:

- image upload metadata
- safe thumbnail when allowed
- EXIF stripped
- OCR off by default

Privacy:

- owner_sensitive/restricted default
- minor/face/chat/doc/work images restricted
- standard export excluded by default

### persona_like_context

Services:

- Character cards
- roleplay logs
- AI companion logs
- prompts/system prompts
- writing style samples

Methods:

- file import preview
- copy-paste metadata
- manual creative notes

Privacy:

- simulationAllowed=false
- Export excluded by default
- real person/deceased/partner/family persona denied/restricted

## Implementation Backlog by Medium

### Backlog M0: Universal Medium Foundation

- `SecurityGate`
- `ImportMediumDetector`
- `SourceSelector`
- `ParserRegistry`
- `PreviewCandidateBuilder`
- `PrivacyDefaultClassifier`
- `PolicyPreflight`

### Backlog M1: Paste/URL Common Parsers

- `line-based-title-list-parser`
- `url-list-parser`
- `table-like-history-parser`
- `progress-list-parser`
- `restaurant-list-parser`
- `episode-list-parser`

### Backlog M2: Service-specific first adapters

- `NetflixViewingActivityAdapter`
- `FilmarksPasteAdapter`
- `TabelogUrlListAdapter`
- `GeraEpisodeAdapter`
- `PodcastOpmlAdapter`
- `MangaAnimeProgressAdapter`
- `BrowserBookmarkAdapter`

### Backlog M3: Sensitive adapters

- `LineTextExportAdapter`
- `XArchiveAdapter`
- `ImageMediaAdapter`
- `PersonaLikeAdapter`
- `MemoryOsExportReimportAdapter`

### Backlog M4: API adapters

- `SpotifyAdapter`
- `LastFmAdapter`
- `AniListAdapter`
- `SteamAdapter`
- `TmdbCatalogAdapter`
- `BookCatalogAdapter`

## Acceptance Criteria

- Every medium has at least one non-API import path.
- Every S-rank service maps to a medium and adapter.
- Every medium has privacy defaults.
- Sensitive mediums are preview-only until policy gates pass.
- API mediums wait for token/OAuth security gates.
- Media/persona mediums never bypass Export/Re-import policy.

## 結論

Memory OSのImportは、サービス別の寄せ集めではなく、媒体ごとの能力を積み上げる。

まず媒体別の共通ParserとPreviewを作り、サービスAdapterで意味を補正する。

これにより、APIがないサービスでも、ユーザーが今使っている画面から安全にImportできる。
