# Import Medium Parser Contracts

## 目的

この文書は、媒体カテゴリごとのParser Contractを定義し、実装時にParser/Normalizer/Adapterが返すfieldを揃えるための仕様である。

サービスごとにParser出力がバラバラになると、Preview、Dedup、Policy、Search、Exportが破綻する。

そのため、媒体ごとに共通のintermediate recordを持つ。

## Common Parser Output

すべてのparserは、まず以下を返す。

```ts
interface ParsedImportItemBase {
  parserId: string;
  parserVersion: string;
  medium: ImportMedium;
  sourceHint?: string;
  originalIndex?: number;
  lineNumbers?: number[];
  confidence: 'high' | 'medium' | 'low' | 'needs_user_selection';
  warnings: string[];
  rawStored: false;
}
```

Rules:

- rawStored is false by default.
- raw text must not be included unless a policy-approved raw field explicitly exists.
- parser output can include extracted fields, not raw file content.

## Time Contract

```ts
interface ParsedTimeFields {
  occurredAtText?: string;
  occurredAt?: string;
  occurredAtPrecision: 'exact_timestamp' | 'date' | 'month' | 'year' | 'period' | 'unknown';
  timezone?: string;
  timezoneSource?: 'source' | 'user_profile' | 'service_default' | 'inferred' | 'unknown';
}
```

Rules:

- Do not invent exact time when only date exists.
- Do not convert unknown timezone silently.
- Preserve original date text for preview.

## URL Contract

```ts
interface ParsedUrlFields {
  url?: string;
  normalizedUrl?: string;
  urlHost?: string;
  urlSafety: 'safe_http' | 'unsafe_scheme' | 'malformed' | 'unknown';
}
```

Unsafe schemes are rejected before commit.

## Title List Parser

Parser ID:

```txt
line-based-title-list-parser
```

Input:

- plain text lines
- copied list

Output:

```ts
interface ParsedTitleListItem extends ParsedImportItemBase, ParsedTimeFields {
  medium: 'title_list';
  title: string;
  subtitle?: string;
  status?: string;
  userMemo?: string;
}
```

Default privacy:

- owner_only
- AI off

## URL List Parser

Parser ID:

```txt
url-list-parser
```

Output:

```ts
interface ParsedUrlListItem extends ParsedImportItemBase, ParsedUrlFields {
  medium: 'url_clip';
  title?: string;
  serviceCandidate?: string;
}
```

Default privacy:

- depends on host/service.
- unknown URL owner_sensitive until reviewed.

## Streaming Watch Activity Parser

Parser IDs:

- `netflix-viewing-activity-csv-parser`
- `streaming-title-list-paste-parser`
- `watchlist-paste-parser`

Output:

```ts
interface ParsedStreamingWatchItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'streaming_watch_activity';
  title: string;
  seriesTitle?: string;
  seasonNumber?: number;
  episodeNumber?: number;
  episodeTitle?: string;
  activityType: 'watched' | 'watching' | 'want_to_watch' | 'purchased' | 'rented';
  profileLabelHash?: string;
  sharedProfilePossible?: boolean;
}
```

Default privacy:

- owner_sensitive
- AI off
- Export excluded by default

Dedupe hints:

- normalized title
- episode/season
- occurred date bucket
- profile hash

## Music Listening Activity Parser

Parser IDs:

- `music-list-paste-parser`
- `spotify-api-payload-parser`
- `lastfm-api-payload-parser`
- `apple-music-export-parser`

Output:

```ts
interface ParsedMusicListeningItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'music_listening_activity';
  trackTitle?: string;
  artistName?: string;
  albumTitle?: string;
  playlistTitle?: string;
  activityType: 'listened' | 'saved' | 'liked' | 'playlist_item' | 'currently_playing';
  externalTrackId?: string;
  isPrivatePlaylist?: boolean;
  isRecentOrCurrent?: boolean;
}
```

Default privacy:

- public playlist owner_only
- recent/current/private owner_sensitive
- AI off

Dedupe hints:

- externalTrackId
- artist + track + timestamp window
- Last.fm/Spotify cross-source time window

## Audio Episode Activity Parser

Parser IDs:

- `opml-parser`
- `rss-feed-parser`
- `radio-episode-list-paste-parser`
- `gera-url-parser`

Output:

```ts
interface ParsedAudioEpisodeItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'audio_episode_activity';
  showTitle: string;
  episodeTitle?: string;
  episodeNumber?: string;
  stationOrNetwork?: string;
  activityType: 'subscribed' | 'listened' | 'want_to_listen' | 'saved';
  feedUrl?: string;
}
```

Default privacy:

- owner_only
- owner_sensitive for private/sensitive folders or shows

## Movie Activity Parser

Parser IDs:

- `filmarks-list-paste-parser`
- `letterboxd-csv-parser`
- `movie-manual-parser`
- `ticket-email-parser`

Output:

```ts
interface ParsedMovieActivityItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'movie_activity';
  title: string;
  releaseYear?: number;
  activityType: 'watched' | 'want_to_watch' | 'rated' | 'reviewed' | 'ticket_reserved';
  ratingText?: string;
  reviewSnippet?: string;
  theaterName?: string;
}
```

Default privacy:

- owner_only
- review/rating/theater owner_sensitive option

## Anime / Manga Progress Parser

Parser IDs:

- `anime-progress-paste-parser`
- `manga-progress-paste-parser`
- `anilist-api-payload-parser`
- `manga-purchase-email-parser`

Output:

```ts
interface ParsedAnimeMangaProgressItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'anime_manga_progress';
  title: string;
  mediaType: 'anime' | 'manga' | 'unknown';
  activityType: 'watching' | 'reading' | 'completed' | 'paused' | 'dropped' | 'want_to_watch' | 'want_to_read' | 'purchased';
  episodeProgress?: number;
  volumeProgress?: number;
  chapterProgress?: number;
  scoreText?: string;
  externalMediaId?: string;
}
```

Default privacy:

- owner_only
- private folder owner_sensitive

Hard deny:

- manga/comic page raw content

## Book / Library Parser

Parser IDs:

- `goodreads-csv-parser`
- `storygraph-csv-parser`
- `isbn-list-parser`
- `book-list-paste-parser`
- `library-loan-manual-parser`

Output:

```ts
interface ParsedBookActivityItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'book_reading_activity' | 'library_activity';
  title: string;
  authorName?: string;
  isbn?: string;
  activityType: 'reading' | 'completed' | 'want_to_read' | 'owned' | 'borrowed' | 'returned';
  pageProgress?: number;
  ratingText?: string;
  shelfName?: string;
}
```

Default privacy:

- owner_only for general reading list
- restricted for library loan history if sensitive

## Restaurant / Food Parser

Parser IDs:

- `tabelog-url-parser`
- `restaurant-list-paste-parser`
- `reservation-email-parser`
- `manual-restaurant-parser`

Output:

```ts
interface ParsedRestaurantFoodItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'restaurant_food_activity';
  restaurantName?: string;
  areaText?: string;
  genreText?: string;
  activityType: 'visited' | 'want_to_go' | 'reserved' | 'saved' | 'ate';
  reservationTimeText?: string;
  partySize?: number;
  companionMentioned?: boolean;
}
```

Default privacy:

- restaurant title owner_only
- date/location/companions owner_sensitive
- no relationship inference

## Recipe / Cooking Parser

Parser IDs:

- `recipe-url-parser`
- `manual-cooked-memory-parser`
- `recipe-title-list-parser`

Output:

```ts
interface ParsedRecipeCookingItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'recipe_cooking_activity';
  recipeTitle?: string;
  dishName?: string;
  activityType: 'cooked' | 'want_to_cook' | 'saved_recipe';
  userMemo?: string;
  fullRecipeBodyDetected?: boolean;
}
```

Default privacy:

- owner_only
- family/health/diet notes owner_sensitive
- full recipe body not stored by default

## Game Activity Parser

Parser IDs:

- `steam-owned-games-parser`
- `steam-recently-played-parser`
- `game-list-paste-parser`
- `game-purchase-email-parser`

Output:

```ts
interface ParsedGameActivityItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'game_activity';
  title: string;
  platform?: string;
  activityType: 'owned' | 'played' | 'recently_played' | 'purchased' | 'want_to_play';
  playtimeMinutes?: number;
  externalGameId?: string;
}
```

Default privacy:

- owner_only
- playtime owner_sensitive option
- no discipline/life score

## Social Post Activity Parser

Parser IDs:

- `x-archive-parser`
- `social-post-url-parser`
- `social-post-paste-parser`

Output:

```ts
interface ParsedSocialPostItem extends ParsedImportItemBase, ParsedTimeFields, ParsedUrlFields {
  medium: 'social_post_activity';
  postId?: string;
  authorHandleHash?: string;
  relationType: 'own_post' | 'liked' | 'bookmarked' | 'reposted' | 'reference';
  textSnippet?: string;
  containsThirdPartyText?: boolean;
}
```

Default privacy:

- own posts owner_only
- likes/bookmarks owner_sensitive
- DMs excluded/restricted summary-only

## Message / Conversation Context Parser

Parser IDs:

- `line-text-export-parser`
- `chat-snippet-paste-parser`
- `email-snippet-parser`

Output:

```ts
interface ParsedMessageContextItem extends ParsedImportItemBase, ParsedTimeFields {
  medium: 'message_conversation_context';
  conversationLabelHash?: string;
  speakerDirection?: 'self' | 'other' | 'unknown';
  messageCount?: number;
  safeSummary?: string;
  rawTextDetected: boolean;
  relationshipContextPossible: boolean;
}
```

Default privacy:

- restricted
- rawStored=false
- AI off
- Export excluded
- no evidence package

## Image / Media Context Parser

Parser IDs:

- `image-metadata-parser`
- `screenshot-metadata-parser`
- `media-attachment-parser`

Output:

```ts
interface ParsedImageMediaItem extends ParsedImportItemBase, ParsedTimeFields {
  medium: 'image_media_context';
  mediaKind: MediaImportKind;
  width?: number;
  height?: number;
  safeMimeType?: string;
  exifGpsPresent?: boolean;
  exifGpsStripped: boolean;
  ocrPerformed: false;
  facePresencePossible?: boolean;
  minorPossible?: boolean;
  screenshotTextPossible?: boolean;
  copyrightedPagePossible?: boolean;
}
```

Default privacy:

- owner_sensitive/restricted
- OCR off
- EXIF GPS stripped
- Export excluded by default

## Persona-like Context Parser

Parser IDs:

- `persona-bundle-detector`
- `character-card-parser`
- `roleplay-log-parser`
- `prompt-file-parser`

Output:

```ts
interface ParsedPersonaLikeItem extends ParsedImportItemBase {
  medium: 'persona_like_context';
  personaKind: PersonaImportKind;
  identityBoundaryClass: IdentityBoundaryClass;
  simulationAllowed: false;
  rawChatDetected?: boolean;
  realPersonPossible?: boolean;
  deceasedPossible?: boolean;
  partnerOrFamilyPossible?: boolean;
}
```

Default privacy:

- owner_sensitive/restricted
- Export excluded
- no activation
- no merge into self identity

## Export Archive Context Parser

Parser IDs:

- `memory-os-export-manifest-parser`
- `external-app-export-detector`

Output:

```ts
interface ParsedExportArchiveItem extends ParsedImportItemBase {
  medium: 'export_archive_context';
  packageClass?: ExportPackageClass;
  containsRaw?: boolean;
  containsMedia?: boolean;
  containsSealed?: boolean;
  containsThirdPartyRaw?: boolean;
  containsPersonaLikeData?: boolean;
  containsMinorData?: boolean;
  manifestPolicyVersion?: string;
}
```

Default privacy:

- preview_only until classification
- no policy bypass
- tombstone check required

## Normalizer Contract

Every parsed item normalizes to:

```ts
interface CanonicalImportCandidate {
  candidateId: string;
  medium: ImportMedium;
  sourceId: string;
  domain: string;
  title?: string;
  url?: string;
  occurredAt?: string;
  occurredAtPrecision: TimePrecision;
  status?: string;
  progress?: Record<string, unknown>;
  activityType?: string;
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  exportDefault: 'included' | 'excluded';
  rawStored: false;
  simulationAllowed?: false;
  confidence: ImportConfidence;
  warnings: string[];
  policyHints: string[];
}
```

## Acceptance Criteria

- Every medium parser outputs a typed intermediate record.
- Every parser sets confidence and warnings.
- Every parser avoids raw storage by default.
- Time precision is explicit.
- Unsafe URLs are rejected before commit.
- Sensitive media/persona fields set restricted defaults.
- Normalizer output can feed Import Preview without service-specific hacks.

## 結論

媒体ごとのParser Contractを固定することで、Import Preview、Policy、Dedupe、Search、Exportが安定する。

サービスごとの違いはAdapterで吸収するが、Parser出力の形は媒体カテゴリで揃える。
