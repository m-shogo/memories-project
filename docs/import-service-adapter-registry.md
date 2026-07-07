# Import Service Adapter Registry

## 目的

この文書は、Memory OS のImport対象サービスを、medium、adapter、parser、input method、privacy default、implementation statusへ対応づけるregistryである。

実装時に「このサービスはどのparserへ行くか」「APIなのかpasteなのか」「Exportできるのか」「privacy defaultは何か」を迷わないようにする。

## Registry Schema

```ts
interface ServiceAdapterRegistryEntry {
  serviceId: string;
  displayName: string;
  priority: 'S' | 'A' | 'B' | 'later';
  primaryMedium: ImportMedium;
  secondaryMediums: ImportMedium[];
  adapterId: string;
  parserIds: string[];
  supportedMethods: ImportMethod[];
  firstImplementationMode: 'paste_first' | 'file_first' | 'api_first' | 'manual_first' | 'catalog_only' | 'preview_only';
  privacyDefault: 'owner_only' | 'owner_sensitive' | 'restricted';
  exportDefault: 'included' | 'excluded';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  noGo: string[];
}
```

## S Rank Registry

### Apple Music

```ts
{
  serviceId: 'apple_music',
  displayName: 'Apple Music',
  priority: 'S',
  primaryMedium: 'music_listening_activity',
  secondaryMediums: ['title_list', 'url_clip', 'export_archive_context'],
  adapterId: 'AppleMusicHybridAdapter',
  parserIds: ['music-list-paste-parser', 'apple-music-export-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'url_clip', 'csv_file', 'official_export_file'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_complete_history_promise', 'no_account_scraping', 'no_write_scope']
}
```

### Spotify

```ts
{
  serviceId: 'spotify',
  displayName: 'Spotify',
  priority: 'S',
  primaryMedium: 'music_listening_activity',
  secondaryMediums: ['url_clip', 'podcast'],
  adapterId: 'SpotifyAdapter',
  parserIds: ['spotify-api-payload-parser', 'music-list-paste-parser', 'url-list-parser'],
  supportedMethods: ['api_oauth', 'url_clip', 'manual_entry'],
  firstImplementationMode: 'api_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_write_scope', 'no_playback_control', 'no_personality_diagnosis']
}
```

### Last.fm

```ts
{
  serviceId: 'lastfm',
  displayName: 'Last.fm',
  priority: 'S',
  primaryMedium: 'music_listening_activity',
  secondaryMediums: [],
  adapterId: 'LastFmAdapter',
  parserIds: ['lastfm-api-payload-parser'],
  supportedMethods: ['api_key_public', 'manual_entry'],
  firstImplementationMode: 'api_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_write_scrobble_mvp', 'no_username_leak_logs']
}
```

### Netflix

```ts
{
  serviceId: 'netflix',
  displayName: 'Netflix',
  priority: 'S',
  primaryMedium: 'streaming_watch_activity',
  secondaryMediums: ['title_list'],
  adapterId: 'NetflixViewingActivityAdapter',
  parserIds: ['netflix-viewing-activity-csv-parser', 'streaming-title-list-paste-parser'],
  supportedMethods: ['csv_file', 'manual_entry'],
  firstImplementationMode: 'file_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_shared_profile_inference', 'no_taste_diagnosis']
}
```

### Amazon Prime Video

```ts
{
  serviceId: 'prime_video',
  displayName: 'Amazon Prime Video',
  priority: 'S',
  primaryMedium: 'streaming_watch_activity',
  secondaryMediums: ['email_receipt_context', 'url_clip'],
  adapterId: 'PrimeVideoManualAdapter',
  parserIds: ['streaming-title-list-paste-parser', 'receipt-email-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'receipt_or_email_forward', 'url_clip'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_account_scraping', 'no_purchase_history_raw_export_default']
}
```

### Disney+

```ts
{
  serviceId: 'disney_plus',
  displayName: 'Disney+',
  priority: 'S',
  primaryMedium: 'streaming_watch_activity',
  secondaryMediums: ['title_list', 'url_clip'],
  adapterId: 'DisneyPlusManualAdapter',
  parserIds: ['streaming-title-list-paste-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'url_clip'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_account_scraping']
}
```

### U-NEXT

```ts
{
  serviceId: 'unext',
  displayName: 'U-NEXT',
  priority: 'S',
  primaryMedium: 'streaming_watch_activity',
  secondaryMediums: ['anime_manga_progress', 'email_receipt_context'],
  adapterId: 'UNextManualAdapter',
  parserIds: ['streaming-title-list-paste-parser', 'anime-progress-paste-parser', 'receipt-email-parser'],
  supportedMethods: ['manual_entry', 'receipt_or_email_forward', 'url_clip'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_account_scraping']
}
```

### LINE

```ts
{
  serviceId: 'line',
  displayName: 'LINE',
  priority: 'S',
  primaryMedium: 'message_conversation_context',
  secondaryMediums: ['image_media_context'],
  adapterId: 'LineTextExportAdapter',
  parserIds: ['line-text-export-parser', 'chat-snippet-paste-parser', 'screenshot-metadata-parser'],
  supportedMethods: ['user_uploaded_file', 'manual_entry'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'restricted',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_bulk_raw_default', 'no_evidence_package', 'no_intent_analysis', 'no_partner_truth_verdict']
}
```

### X / Twitter

```ts
{
  serviceId: 'x_twitter',
  displayName: 'X / Twitter',
  priority: 'S',
  primaryMedium: 'social_post_activity',
  secondaryMediums: ['url_clip', 'export_archive_context'],
  adapterId: 'XArchiveAdapter',
  parserIds: ['x-archive-parser', 'social-post-url-parser', 'social-post-paste-parser'],
  supportedMethods: ['official_export_file', 'url_clip', 'manual_entry'],
  firstImplementationMode: 'file_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_dm_default', 'no_api_polling_mvp', 'no_surveillance']
}
```

### 食べログ

```ts
{
  serviceId: 'tabelog',
  displayName: '食べログ',
  priority: 'S',
  primaryMedium: 'restaurant_food_activity',
  secondaryMediums: ['url_clip', 'email_receipt_context'],
  adapterId: 'TabelogAdapter',
  parserIds: ['tabelog-url-parser', 'restaurant-list-paste-parser', 'reservation-email-parser'],
  supportedMethods: ['url_clip', 'manual_entry', 'receipt_or_email_forward'],
  firstImplementationMode: 'url_clip',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_location_pattern_inference', 'no_companion_inference']
}
```

### GERA

```ts
{
  serviceId: 'gera',
  displayName: 'GERA',
  priority: 'S',
  primaryMedium: 'audio_episode_activity',
  secondaryMediums: ['url_clip'],
  adapterId: 'GeraEpisodeAdapter',
  parserIds: ['gera-url-parser', 'radio-episode-list-paste-parser'],
  supportedMethods: ['url_clip', 'manual_entry'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_personality_inference']
}
```

### Podcast

```ts
{
  serviceId: 'podcast',
  displayName: 'Podcast',
  priority: 'S',
  primaryMedium: 'audio_episode_activity',
  secondaryMediums: ['url_clip'],
  adapterId: 'PodcastAdapter',
  parserIds: ['opml-parser', 'rss-feed-parser', 'radio-episode-list-paste-parser'],
  supportedMethods: ['opml_file', 'rss_feed', 'url_clip', 'manual_entry'],
  firstImplementationMode: 'file_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_sensitive_show_inference']
}
```

### Filmarks

```ts
{
  serviceId: 'filmarks',
  displayName: 'Filmarks',
  priority: 'S',
  primaryMedium: 'movie_activity',
  secondaryMediums: ['url_clip'],
  adapterId: 'FilmarksAdapter',
  parserIds: ['filmarks-list-paste-parser', 'filmarks-url-parser'],
  supportedMethods: ['manual_entry', 'url_clip'],
  firstImplementationMode: 'paste_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_profile_scraping', 'no_taste_diagnosis']
}
```

### Manga outside listed services

```ts
{
  serviceId: 'manga_manual',
  displayName: 'Manga manual/import',
  priority: 'S',
  primaryMedium: 'anime_manga_progress',
  secondaryMediums: ['email_receipt_context', 'url_clip', 'image_media_context'],
  adapterId: 'MangaManualAdapter',
  parserIds: ['manga-progress-paste-parser', 'manga-purchase-email-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'receipt_or_email_forward', 'url_clip'],
  firstImplementationMode: 'manual_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_app_scraping', 'no_manga_page_raw_import']
}
```

### Anime outside listed services

```ts
{
  serviceId: 'anime_manual',
  displayName: 'Anime manual/import',
  priority: 'S',
  primaryMedium: 'anime_manga_progress',
  secondaryMediums: ['streaming_watch_activity', 'url_clip'],
  adapterId: 'AnimeManualAdapter',
  parserIds: ['anime-progress-paste-parser', 'streaming-title-list-paste-parser'],
  supportedMethods: ['manual_entry', 'url_clip'],
  firstImplementationMode: 'manual_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_taste_diagnosis']
}
```

### Movie outside listed services

```ts
{
  serviceId: 'movie_manual',
  displayName: 'Movie manual/import',
  priority: 'S',
  primaryMedium: 'movie_activity',
  secondaryMediums: ['url_clip', 'email_receipt_context'],
  adapterId: 'MovieManualAdapter',
  parserIds: ['movie-manual-parser', 'ticket-email-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'url_clip', 'receipt_or_email_forward'],
  firstImplementationMode: 'manual_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_taste_diagnosis']
}
```

### Radio outside listed services

```ts
{
  serviceId: 'radio_manual',
  displayName: 'Radio manual/import',
  priority: 'S',
  primaryMedium: 'audio_episode_activity',
  secondaryMediums: ['url_clip'],
  adapterId: 'RadioManualAdapter',
  parserIds: ['radio-episode-list-paste-parser', 'url-list-parser'],
  supportedMethods: ['manual_entry', 'url_clip'],
  firstImplementationMode: 'manual_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_personality_inference']
}
```

## A Rank Registry

### Browser Bookmarks

```ts
{
  serviceId: 'browser_bookmarks',
  displayName: 'Browser Bookmarks',
  priority: 'A',
  primaryMedium: 'web_bookmark',
  secondaryMediums: ['url_clip'],
  adapterId: 'BrowserBookmarkAdapter',
  parserIds: ['bookmark-html-parser', 'bookmark-json-parser', 'url-list-parser'],
  supportedMethods: ['html_bookmark_file', 'user_uploaded_file'],
  firstImplementationMode: 'file_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_raw_html_rendering', 'no_private_title_logs']
}
```

### YouTube Takeout

```ts
{
  serviceId: 'youtube_takeout',
  displayName: 'YouTube Takeout',
  priority: 'A',
  primaryMedium: 'streaming_watch_activity',
  secondaryMediums: ['music_listening_activity', 'export_archive_context'],
  adapterId: 'YouTubeTakeoutAdapter',
  parserIds: ['google-takeout-youtube-parser', 'youtube-url-parser'],
  supportedMethods: ['takeout_archive', 'url_clip'],
  firstImplementationMode: 'file_first',
  privacyDefault: 'owner_sensitive',
  exportDefault: 'excluded',
  aiAnalysisDefault: 'off',
  noGo: ['no_search_history_default', 'no_google_oauth_blanket_scope']
}
```

### Steam

```ts
{
  serviceId: 'steam',
  displayName: 'Steam',
  priority: 'A',
  primaryMedium: 'game_activity',
  secondaryMediums: ['url_clip', 'email_receipt_context'],
  adapterId: 'SteamAdapter',
  parserIds: ['steam-owned-games-parser', 'steam-recently-played-parser', 'game-list-paste-parser'],
  supportedMethods: ['api_key_public', 'manual_entry'],
  firstImplementationMode: 'api_first',
  privacyDefault: 'owner_only',
  exportDefault: 'included',
  aiAnalysisDefault: 'off',
  noGo: ['no_life_score_from_playtime']
}
```

## Registry Rules

- New service must map to a primaryMedium.
- New service must have at least one non-scraping method.
- API method cannot be the only method for S-rank unless official export/paste is impossible and API is safe.
- No service may bypass Import Preview.
- No service may set AI analysis on by default.
- Sensitive services default Export excluded.
- Every service must list noGo strings.

## 結論

Service Adapter Registryにより、サービス名からmedium、parser、method、privacy default、No-Goが一意に辿れる。

実装ではこのregistryをコード化し、SourceSelector/Detector/Previewが同じ定義を参照する。
