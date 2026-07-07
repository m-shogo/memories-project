# Import Medium Fixture Backlog

## 目的

この文書は、媒体カテゴリごとのfixture作成順、expected snapshot、P0 test観点を固定する。

Import実装では、parserコードより先にfixtureを作る。

## Fixture Priority

```txt
F0: Security fixtures
F1: Universal paste/url fixtures
F2: S-rank non-API medium fixtures
F3: Sensitive medium fixtures
F4: API response fixtures
F5: Export/re-import fixtures
```

## F0: Security Fixtures

Create first:

```txt
fixtures/import/security/malicious-bookmarks.html
fixtures/import/security/active-svg.svg
fixtures/import/security/csv-formula-injection.csv
fixtures/import/security/xml-external-entity.opml
fixtures/import/security/archive-path-traversal.zip
fixtures/import/security/oversized-paste.txt
fixtures/import/security/unsafe-url-schemes.txt
```

Expected:

- no active content execution.
- unsafe URL rejected.
- raw HTML/SVG not rendered.
- CSV formulas neutralized on re-export.
- XXE disabled.
- archive traversal rejected.
- logs contain no raw content.

## F1: Universal Paste / URL Fixtures

Create:

```txt
fixtures/import/universal/title-list-basic.txt
fixtures/import/universal/url-list-basic.txt
fixtures/import/universal/table-like-date-title.txt
fixtures/import/universal/progress-list-basic.txt
fixtures/import/universal/mixed-low-confidence.txt
```

Expected snapshots:

```txt
fixtures/import/expected/universal-title-list-basic.detection.json
fixtures/import/expected/universal-title-list-basic.preview.json
fixtures/import/expected/universal-title-list-basic.policy.json
```

Test:

- title lines become candidates.
- URLs parsed and normalized.
- date precision is explicit.
- low confidence asks user selection.
- no save occurs in preview-only prototype.

## F2: S-rank Non-API Medium Fixtures

### Streaming Watch Activity

Create:

```txt
fixtures/import/streaming/netflix-viewing-activity-standard.csv
fixtures/import/streaming/netflix-viewing-activity-duplicates.csv
fixtures/import/streaming/prime-video-list-paste.txt
fixtures/import/streaming/disney-plus-watchlist-paste.txt
fixtures/import/streaming/unext-history-paste.txt
```

Expected:

- owner_sensitive default.
- AI off.
- shared profile warning when fixture says shared.
- duplicate Netflix title/date detected.

### Anime / Manga Progress

Create:

```txt
fixtures/import/anime-manga/manga-progress-list.txt
fixtures/import/anime-manga/anime-progress-list.txt
fixtures/import/anime-manga/manga-purchase-email.txt
fixtures/import/anime-manga/manga-page-image-denied.meta.json
```

Expected:

- progress parsed.
- manga page raw denied/metadata-only.
- no app scraping path.

### Restaurant / Food

Create:

```txt
fixtures/import/restaurant/tabelog-url-list.txt
fixtures/import/restaurant/tabelog-saved-list-paste.txt
fixtures/import/restaurant/reservation-email.txt
fixtures/import/restaurant/companion-sensitive.txt
```

Expected:

- restaurant title owner_only.
- date/location/companion owner_sensitive.
- no relationship inference.

### Audio Episode

Create:

```txt
fixtures/import/audio/podcast-subscriptions.opml
fixtures/import/audio/rss-feed-sample.xml
fixtures/import/audio/gera-episode-list.txt
fixtures/import/audio/radio-program-list.txt
```

Expected:

- OPML subscriptions parsed.
- episode URL/list parsed.
- owner_only default.
- sensitive show/folder can be owner_sensitive.

### Movie Activity

Create:

```txt
fixtures/import/movie/filmarks-watched-list-paste.txt
fixtures/import/movie/filmarks-rating-review-paste.txt
fixtures/import/movie/letterboxd-diary.csv
fixtures/import/movie/cinema-ticket-email.txt
```

Expected:

- title/date/rating parsed.
- review snippet owner_sensitive option.
- TMDb enrichment not required in parser test.

## F3: Sensitive Medium Fixtures

### Message / Conversation

Create:

```txt
fixtures/import/message/line-export-ja.txt
fixtures/import/message/line-copy-selected.txt
fixtures/import/message/line-deleted-reimport.txt
fixtures/import/message/chat-screenshot-meta.json
```

Expected:

- restricted default.
- rawStored=false.
- Export excluded.
- tombstone match selected=false.
- OCR off for screenshot.

### Social Post

Create:

```txt
fixtures/import/social/x-archive-minimal.zip
fixtures/import/social/x-own-posts.json
fixtures/import/social/x-likes-sensitive.json
fixtures/import/social/x-thread-url-list.txt
```

Expected:

- own posts owner_only.
- likes/bookmarks owner_sensitive.
- DMs excluded.
- no surveillance.

### Media / Image

Create:

```txt
fixtures/import/media/photo-with-exif.meta.json
fixtures/import/media/food-photo-safe.meta.json
fixtures/import/media/minor-photo.meta.json
fixtures/import/media/line-screenshot.meta.json
fixtures/import/media/medical-document-photo.meta.json
fixtures/import/media/cover-art-reference.meta.json
fixtures/import/media/manga-page-denied.meta.json
```

Expected:

- EXIF GPS stripped.
- OCR off.
- minors restricted/export excluded.
- chat/doc screenshots restricted.
- manga page metadata-only.

### Persona-like

Create:

```txt
fixtures/import/persona/fictional-character-notes.txt
fixtures/import/persona/roleplay-log.txt
fixtures/import/persona/ai-companion-log.txt
fixtures/import/persona/character-card.json
fixtures/import/persona/real-person-style-sample.txt
fixtures/import/persona/deceased-person-records.txt
fixtures/import/persona/partner-family-chat-persona.txt
```

Expected:

- simulationAllowed=false.
- Export excluded by default for persona-like.
- real person/deceased/partner/family restricted.
- fictional notes allowed as creative notes only.

## F4: API Response Fixtures

Create after token/OAuth gates.

```txt
fixtures/import/api/spotify-recently-played.json
fixtures/import/api/spotify-playlists.json
fixtures/import/api/lastfm-recent-tracks.json
fixtures/import/api/anilist-media-list.json
fixtures/import/api/steam-owned-games.json
fixtures/import/api/tmdb-movie-search.json
fixtures/import/api/google-books-isbn.json
```

Expected:

- no tokens in fixture.
- source account hash synthetic.
- rate limit/error fixture included later.
- privacy defaults correct.

## F5: Export / Re-import Fixtures

Create:

```txt
fixtures/import/export/memoryos-standard-export-manifest.json
fixtures/import/export/memoryos-sensitive-summary-export-manifest.json
fixtures/import/export/memoryos-media-archive-manifest.json
fixtures/import/export/persona-like-export-manifest.json
fixtures/import/export/raw-archive-requires-review-manifest.json
fixtures/import/export/deleted-records-reimport-manifest.json
```

Expected:

- manifest has risk flags but no raw private titles.
- re-import checks tombstones.
- persona bundle re-import no activation.
- media archive requires reauth/scope review.

## Expected Snapshot Rules

Each fixture should have:

```txt
.detection.json
.preview.json
.policy.json
```

Snapshots must not include:

- real personal data.
- raw chat text.
- private title.
- private URL.
- OAuth/API token.
- full image binary.

## Fixture Naming Rules

```txt
<medium>/<source>-<scenario>.<ext>
```

Examples:

```txt
streaming/netflix-viewing-activity-standard.csv
message/line-deleted-reimport.txt
persona/character-card.json
media/minor-photo.meta.json
```

## CI Gates

CI fails if:

- fixture contains forbidden real-looking token patterns.
- expected snapshot includes raw sensitive text.
- malicious fixture is parsed as safe.
- media/persona fixture enables export by default incorrectly.
- persona fixture sets simulationAllowed=true.
- chat screenshot fixture performs OCR by default.
- re-import fixture bypasses tombstone.

## First Fixture Implementation Order

Recommended exact order:

1. `security/unsafe-url-schemes.txt`
2. `universal/title-list-basic.txt`
3. `universal/url-list-basic.txt`
4. `streaming/netflix-viewing-activity-standard.csv`
5. `anime-manga/manga-progress-list.txt`
6. `restaurant/tabelog-url-list.txt`
7. `audio/gera-episode-list.txt`
8. `message/line-copy-selected.txt`
9. `media/photo-with-exif.meta.json`
10. `persona/character-card.json`

This order proves the broadest surface with the least implementation cost.

## 結論

媒体Importは、fixtureから始める。

最初にUniversal + Security + S-rank non-API fixturesを作ることで、APIが未実装でもSランク体験の大部分を安全に検証できる。
