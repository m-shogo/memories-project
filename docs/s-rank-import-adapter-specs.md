# S Rank Import Adapter Specs

## 目的

この文書は、SランクImportを実装する直前に、各Adapterが何を受け取り、何を返し、どのprivacy defaultを持つかを定義する。

前提:

- Import Coreは共通。
- Service Adapterはサービス固有の意味づけを担当する。
- Parserは形式を読む。
- Adapterは意味へ変換する。
- Import Previewを必ず通す。

## Common Adapter Interface

```ts
interface SourceAdapter {
  sourceId: string;
  displayName: string;
  priority: 'S' | 'A' | 'B' | 'later';
  supportedInputKinds: ImportInputKind[];
  supportedMethods: ImportMethod[];
  parserIds: string[];
  detect(input: ImportIntake): SourceDetectionResult;
  normalize(raw: RawImportRecord): CanonicalImportRecord;
  privacyDefault(record: CanonicalImportRecord): PrivacyDecision;
  previewMode(record: CanonicalImportRecord): ImportPreviewMode;
  enrichmentPlan(record: CanonicalImportRecord): EnrichmentRequest[];
}
```

## Common Canonical Domains

```ts
type CanonicalDomain =
  | 'music'
  | 'movie'
  | 'tv'
  | 'anime'
  | 'manga'
  | 'message'
  | 'social'
  | 'restaurant'
  | 'radio'
  | 'podcast'
  | 'web_bookmark'
  | 'book'
  | 'game'
  | 'other';
```

## Adapter: NetflixViewingActivityAdapter

sourceId: `netflix.viewing_activity`

Supported methods:

- CSV upload
- copied history paste
- manual current watching

Parsers:

- `netflix-viewing-activity-csv-parser`
- `table-like-history-paste-parser`
- `manual-current-watching-parser`

Normalize:

```ts
{
  domain: 'movie' | 'tv',
  title,
  occurredAt: watchedDate,
  status: 'watched',
  evidenceType: 'file_imported' | 'paste_imported' | 'manual_claim',
  sourceRef
}
```

Privacy:

- owner_sensitive default
- AI analysis off
- Export excluded by default unless user opts in

Warnings:

- profile may be shared
- family viewing history may be mixed

## Adapter: PrimeVideoAdapter

sourceId: `prime_video.manual_or_paste`

Supported methods:

- copied history/list paste
- URL clip
- purchase/rental email
- manual current watching

Parsers:

- `streaming-title-list-paste-parser`
- `url-list-parser`
- `receipt-email-parser`
- `manual-current-watching-parser`

Normalize:

- domain movie/tv
- status watched/watching/want_to_watch/purchased/rented
- occurredAt from email/date if present

Privacy:

- owner_sensitive default
- profile/shared warning

Avoid:

- account scraping

## Adapter: DisneyPlusAdapter

sourceId: `disney_plus.manual_or_paste`

Supported methods:

- watchlist paste
- continue watching paste
- manual current watching
- data export if user provides

Normalize:

- domain movie/tv
- status watching/want_to_watch/watched
- progress optional

Privacy:

- owner_sensitive default

## Adapter: UNextAdapter

sourceId: `unext.manual_or_paste`

Supported methods:

- watch history paste
- mylist paste
- purchase/rental email
- manual current watching

Normalize:

- movie/tv/anime depending user-selected domain or enrichment
- status watched/watching/purchased/rented

Privacy:

- owner_sensitive default

## Adapter: SpotifyAdapter

sourceId: `spotify.api_or_clip`

Supported methods:

- OAuth API
- URL clip
- playlist/list paste
- manual listening

Parsers:

- `spotify-api-payload-parser`
- `spotify-url-parser`
- `music-list-paste-parser`
- `manual-current-listening-parser`

Normalize:

```ts
{
  domain: 'music' | 'podcast',
  title: trackOrEpisodeTitle,
  occurredAt: playedAt,
  status: 'listened' | 'saved' | 'currently_playing',
  progress: undefined,
  externalIds: { spotifyId },
  sourceRef
}
```

Privacy:

- public playlist: owner_only
- recently played/currently playing/private playlist: owner_sensitive option
- AI taste/personality analysis disabled

## Adapter: AppleMusicAdapter

sourceId: `apple_music.hybrid`

Supported methods:

- MusicKit/API after research
- Apple data export
- playlist/library paste
- Last.fm fallback reference
- manual listening

Parsers:

- `apple-music-api-payload-parser`
- `apple-data-export-parser`
- `music-list-paste-parser`
- `manual-current-listening-parser`

Normalize:

- domain music
- title/artist/album
- status saved/listened/currently_listening/manual_claim

Privacy:

- owner_sensitive for listening history
- owner_only for selected library/playlist if user chooses

Notes:

- do not promise complete listening history.
- adapter may start as paste/manual only.

## Adapter: XArchiveAdapter

sourceId: `x.archive_or_clip`

Supported methods:

- official archive ZIP
- post/thread URL clip
- copied post/thread paste

Parsers:

- `x-archive-parser`
- `x-url-parser`
- `social-post-paste-parser`

Normalize:

- domain social
- status posted/bookmarked/liked/saved/reference depending source
- occurredAt if present
- url if present

Privacy:

- own posts: owner_only
- likes/bookmarks: owner_sensitive
- DMs: excluded by default; if supported later, restricted summary-only

Safety:

- no surveillance
- no third-party profiling
- no harassment package

## Adapter: LineTextExportAdapter

sourceId: `line.text_or_paste`

Supported methods:

- per-chat text export
- selected chat copy-paste
- manual memory note

Parsers:

- `line-text-export-parser`
- `chat-snippet-paste-parser`
- `manual-memory-note-parser`

Normalize:

- domain message
- occurredAt from timestamp
- title generated from date/source, not content
- status memory_reference
- rawStored=false default

Privacy:

- restricted default for relationship/family chats
- owner_sensitive for low-risk self notes
- AI analysis off
- Export excluded by default

Safety:

- summary-only default
- no intent analysis
- no evidence package
- no spouse/partner truth verdict

## Adapter: TabelogAdapter

sourceId: `tabelog.url_or_paste`

Supported methods:

- restaurant URL clip
- visited/saved list paste
- reservation email
- manual restaurant entry

Parsers:

- `tabelog-url-parser`
- `restaurant-list-paste-parser`
- `reservation-email-parser`
- `manual-restaurant-parser`

Normalize:

- domain restaurant
- title restaurant name
- url
- occurredAt visit/reservation date if present
- status visited/want_to_go/reserved

Privacy:

- restaurant title owner_only
- visit date/location/companions owner_sensitive
- companions not stored unless user explicitly provides

Safety:

- no relationship/location pattern inference

## Adapter: FilmarksAdapter

sourceId: `filmarks.paste_or_clip`

Supported methods:

- watched list paste
- watchlist paste
- work URL clip
- manual movie entry

Parsers:

- `filmarks-list-paste-parser`
- `filmarks-url-parser`
- `manual-movie-parser`

Normalize:

- domain movie
- title
- status watched/want_to_watch
- rating optional
- review memo optional

Enrichment:

- TMDb by title/year when confidence is enough

Privacy:

- owner_only default
- review/memo may be owner_sensitive user option

Safety:

- no taste/personality diagnosis

## Adapter: GeraAdapter

sourceId: `gera.url_or_paste`

Supported methods:

- episode URL clip
- show/episode list paste
- manual radio/podcast entry

Parsers:

- `gera-url-parser`
- `radio-episode-list-paste-parser`
- `manual-listening-parser`

Normalize:

- domain radio/podcast
- title episode title
- show title as creator/source metadata
- status listened/want_to_listen
- occurredAt published/listened date if present

Privacy:

- owner_only default
- private listening contexts owner_sensitive if user marks

## Adapter: PodcastAdapter

sourceId: `podcast.opml_rss_or_paste`

Supported methods:

- OPML upload
- RSS URL clip
- episode URL clip
- episode list paste
- manual listening entry

Parsers:

- `opml-parser`
- `rss-feed-parser`
- `podcast-episode-url-parser`
- `radio-episode-list-paste-parser`

Normalize:

- domain podcast
- title show/episode
- url
- status subscribed/listened/want_to_listen

Privacy:

- owner_only default
- sensitive show/folder owner_sensitive option

## Adapter: MangaManualAdapter

sourceId: `manga.manual_or_paste`

Supported methods:

- manual current reading
- copied reading list
- purchase email
- URL clip
- AniList/MAL if available later

Parsers:

- `manga-progress-paste-parser`
- `receipt-email-parser`
- `manual-reading-parser`

Normalize:

- domain manga
- title
- status reading/completed/paused/want_to_read
- progress volume/chapter

Privacy:

- owner_only default
- private folders owner_sensitive

Avoid:

- manga app scraping
- page/text import

## Adapter: AnimeAdapter

sourceId: `anime.hybrid`

Supported methods:

- AniList API
- manual current watching
- copied watch list
- streaming current screen paste

Parsers:

- `anilist-api-payload-parser`
- `anime-progress-paste-parser`
- `manual-watching-parser`

Normalize:

- domain anime
- title
- status watching/completed/paused/dropped/want_to_watch
- progress episode
- score optional from AniList

Privacy:

- owner_only default
- no personality inference

## Adapter: BrowserBookmarkAdapter

sourceId: `browser_bookmarks.file_or_paste`

Supported methods:

- HTML bookmark export
- JSON bookmark export if browser provides
- URL list paste

Parsers:

- `bookmark-html-parser`
- `bookmark-json-parser`
- `url-list-parser`

Normalize:

- domain web_bookmark
- title
- url
- folder path
- added date if present

Privacy:

- folder-level rules
- private-like folders owner_sensitive
- title redaction option

Security:

- no raw HTML rendering
- unsafe URL schemes rejected

## Adapter: YouTubeTakeoutAdapter

sourceId: `youtube.takeout_or_clip`

Supported methods:

- Google Takeout ZIP
- YouTube URL clip
- playlist URL clip

Parsers:

- `google-takeout-youtube-parser`
- `youtube-url-parser`

Normalize:

- domain video/music depending source file
- title
- occurredAt watched/liked/subscribed date if present
- status watched/liked/saved/subscribed

Privacy:

- watch/search history owner_sensitive
- search history separate explicit selection
- AI off default

## MVP Adapter Build Order

1. UniversalPasteAdapter
2. BrowserBookmarkAdapter
3. NetflixViewingActivityAdapter
4. LineTextExportAdapter
5. XArchiveAdapter
6. FilmarksAdapter
7. TabelogAdapter
8. PodcastAdapter
9. GeraAdapter
10. MangaManualAdapter
11. AnimeAdapter with manual + AniList
12. SpotifyAdapter
13. AppleMusicAdapter as paste/manual first, API spike later
14. PrimeVideoAdapter
15. DisneyPlusAdapter
16. UNextAdapter

## Acceptance Criteria

- Every S-rank service has an adapter entry.
- Every adapter lists supported methods.
- Every adapter defines privacy default.
- Every adapter defines parser IDs.
- Manual/paste route exists when API/export is unavailable.
- Service-specific raw/third-party risks are explicit.
- Adapter output goes to Import Preview before save.

## 結論

SランクImportは、個別サービスごとに完全別実装するのではなく、共通Import Coreに各Source Adapterを挿す。

これにより、Netflix CSV、LINE text、X archive、Filmarks paste、食べログURL、GERA URL、Podcast OPML、漫画手入力、Spotify API、AniList APIなどを同じ安全基盤で扱える。
