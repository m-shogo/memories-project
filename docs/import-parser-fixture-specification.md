# Import Parser Fixture Specification

## 目的

この文書は、Memory OS の Import Parser / Detector / Adapter / Policy を実装する前に、必ず用意する fixture と期待結果を定義する。

Importは外部データを扱うため、実装前にfixtureがないと次の事故が起きる。

- Parserがサービス形式を誤解する
- 仕様変更に気づけない
- malicious fileでactive contentが動く
- private titleがlogに出る
- 重複排除が効かない
- 削除済み記録が再Importで復活する
- parser修正で過去データの意味が変わる

## 原則

### 1. Fixtures must be synthetic

fixtureには実ユーザーの個人データを入れない。

禁止:

- 実LINE本文
- 実X archive
- 実Netflix履歴
- 実ブックマーク
- 実メール
- 実OAuth token
- 実private URL

許可:

- 架空タイトル
- 架空URL
- 架空日付
- 架空会話
- 架空レシート
- 架空profile label

### 2. Fixture tests must assert normalized output

Parser testは「parseできた」だけでは足りない。

必ず以下を検証する。

- detected source
- parser id/version
- record count
- extracted title/date/status/progress/url
- confidence
- privacy default
- rawStored default
- AI analysis default
- export default
- warnings

### 3. Security fixtures are P0

Import parserは便利機能ではなく攻撃面でもある。

malicious fixtureを先に作る。

### 4. Regression fixtures are permanent

一度作ったfixtureは、サービス形式変更やparser bug修正後も残す。

旧形式も読み続けられるか、明確にunsupportedにする。

## Directory Layout

```txt
fixtures/import/
  README.md
  browser-bookmarks/
  netflix/
  line/
  x-archive/
  filmarks/
  tabelog/
  podcast/
  gera/
  manga-anime/
  spotify/
  apple-music/
  youtube-takeout/
  books-library/
  recipes/
  games/
  security/
  dedupe/
  tombstone/
  expected/
```

## Fixture Manifest

Each fixture has a manifest.

```ts
interface ImportFixtureManifest {
  fixtureId: string;
  fixturePath: string;
  sourceHint?: string;
  inputKind: 'file_upload' | 'paste_text' | 'url_clip' | 'email_forward' | 'manual_entry';
  expectedDetection: {
    sourceId: string;
    parserId: string;
    confidence: 'high' | 'medium' | 'low' | 'needs_user_selection';
  };
  expectedCounts: {
    rawRecords: number;
    candidates: number;
    selectedByDefault: number;
    sensitive: number;
    duplicates: number;
    unsupported: number;
  };
  expectedDefaults: {
    rawStored: boolean;
    aiAnalysisDefault: 'off' | 'allowed_after_user_request';
    exportDefault: 'included' | 'excluded';
  };
  expectedWarnings: string[];
}
```

## Required Fixture Groups

### 1. Browser Bookmarks

Files:

```txt
fixtures/import/browser-bookmarks/chrome-bookmarks-normal.html
fixtures/import/browser-bookmarks/safari-bookmarks-normal.html
fixtures/import/browser-bookmarks/private-folder-bookmarks.html
fixtures/import/browser-bookmarks/bookmarks-url-list.txt
```

Must cover:

- normal folder
- private-like folder
- http/https URLs
- unsupported schemes
- duplicate URL
- title redaction default for private-like folder

Expected:

- raw HTML never rendered
- private folder owner_sensitive
- unsafe URL rejected
- logs contain no private title

### 2. Netflix

Files:

```txt
fixtures/import/netflix/viewing-activity-standard.csv
fixtures/import/netflix/viewing-activity-no-time.csv
fixtures/import/netflix/viewing-activity-duplicate.csv
fixtures/import/netflix/viewing-activity-shared-profile.csv
fixtures/import/netflix/viewing-activity-copy-paste.txt
```

Must cover:

- title/date rows
- same title watched twice
- same title same date duplicate
- date precision = date
- shared profile warning

Expected:

- domain movie/tv
- status watched
- privacy owner_sensitive
- AI off
- export excluded or user-selected

### 3. LINE

Files:

```txt
fixtures/import/line/line-export-ja.txt
fixtures/import/line/line-copy-selected-snippet.txt
fixtures/import/line/line-export-timestamp-variant.txt
fixtures/import/line/line-deleted-reimport.txt
```

Must cover:

- timestamp parse
- speaker direction
- third-party raw risk
- summary-only default
- deleted tombstone match

Expected:

- rawStored=false
- privacy restricted for relationship/family-like snippets
- AI off
- export excluded
- no intent analysis

### 4. X / Twitter Archive

Files:

```txt
fixtures/import/x-archive/x-archive-minimal.zip
fixtures/import/x-archive/x-archive-own-posts.json
fixtures/import/x-archive/x-archive-likes-sensitive.json
fixtures/import/x-archive/x-post-url-list.txt
fixtures/import/x-archive/x-thread-copy-paste.txt
```

Must cover:

- own posts
- likes/bookmarks sensitivity
- URL clip
- copied thread text
- no DMs by default

Expected:

- own posts owner_only
- likes/bookmarks owner_sensitive
- DMs excluded or unsupported by default

### 5. Filmarks

Files:

```txt
fixtures/import/filmarks/filmarks-watched-list-paste.txt
fixtures/import/filmarks/filmarks-review-rating-paste.txt
fixtures/import/filmarks/filmarks-url-list.txt
```

Must cover:

- title
- rating
- watched date if present
- review fragment
- TMDb enrichment candidate only

Expected:

- no API assumption
- domain movie
- no taste/personality inference

### 6. 食べログ

Files:

```txt
fixtures/import/tabelog/tabelog-url-list.txt
fixtures/import/tabelog/tabelog-saved-list-paste.txt
fixtures/import/tabelog/tabelog-reservation-email.txt
fixtures/import/tabelog/tabelog-companion-sensitive.txt
```

Must cover:

- restaurant URL
- restaurant name + area
- reservation date
- companions as sensitive if present

Expected:

- domain restaurant
- title/store owner_only
- date/location/companions owner_sensitive
- no relationship/location inference

### 7. Podcast / Radio / GERA

Files:

```txt
fixtures/import/podcast/subscriptions.opml
fixtures/import/podcast/rss-feed-sample.xml
fixtures/import/podcast/episode-url-list.txt
fixtures/import/gera/gera-episode-url-list.txt
fixtures/import/gera/gera-list-paste.txt
fixtures/import/radio/radio-program-list.txt
```

Must cover:

- OPML parse
- RSS URL
- episode title
- show title
- listened/want_to_listen status

Expected:

- domain podcast/radio
- owner_only by default
- sensitive show/folder owner_sensitive option

### 8. Manga / Anime

Files:

```txt
fixtures/import/manga-anime/manga-progress-list.txt
fixtures/import/manga-anime/anime-progress-list.txt
fixtures/import/manga-anime/manga-purchase-email.txt
fixtures/import/manga-anime/anilist-api-sample.json
```

Must cover:

- volume/chapter progress
- episode progress
- completed/paused/watching/reading
- purchase email
- AniList IDs

Expected:

- no app scraping
- no page/text content import
- no personality inference

### 9. Spotify / Apple Music

Files:

```txt
fixtures/import/spotify/spotify-playlist-paste.txt
fixtures/import/spotify/spotify-recently-played-api.json
fixtures/import/spotify/spotify-url-list.txt
fixtures/import/apple-music/apple-music-playlist-paste.txt
fixtures/import/apple-music/apple-data-export-sample.csv
```

Must cover:

- playlist paste
- track/artist/album fields
- recently played time
- URL list
- Apple export partial data

Expected:

- listening history owner_sensitive option
- public playlist owner_only
- no complete Apple Music history promise

### 10. Google Takeout / YouTube

Files:

```txt
fixtures/import/youtube-takeout/takeout-youtube-watch-history.zip
fixtures/import/youtube-takeout/youtube-url-list.txt
fixtures/import/youtube-takeout/youtube-search-history-sensitive.json
```

Must cover:

- watch history
- search history explicitly selected only
- liked videos
- playlist URL

Expected:

- watch/search history owner_sensitive
- search history separate warning
- AI off

### 11. Books / Library

Files:

```txt
fixtures/import/books-library/goodreads-export.csv
fixtures/import/books-library/storygraph-export.csv
fixtures/import/books-library/book-list-paste.txt
fixtures/import/books-library/library-loan-manual.txt
fixtures/import/books-library/isbn-list.txt
```

Must cover:

- read date
- rating
- ISBN
- manual loan history restricted
- catalog enrichment only

Expected:

- library loan history restricted/manual
- Calil not treated as loan history

### 12. Recipes / Cookpad

Files:

```txt
fixtures/import/recipes/cookpad-url-list.txt
fixtures/import/recipes/manual-cooked-memory.txt
fixtures/import/recipes/recipe-full-text-should-not-store.txt
```

Must cover:

- URL clip
- title/date/photo memo fields
- full recipe text not stored by default

Expected:

- recipe body not copied by default
- user memo allowed

### 13. Games / Steam

Files:

```txt
fixtures/import/games/steam-owned-games-api.json
fixtures/import/games/steam-recently-played-api.json
fixtures/import/games/game-list-paste.txt
fixtures/import/games/purchase-email.txt
```

Must cover:

- owned games
- recently played
- playtime
- purchase email

Expected:

- playtime not interpreted as life value

## Security Fixtures

### malicious-bookmarks.html

Must contain synthetic examples of:

- active tags
- event-like attributes
- unsafe URL schemes
- embedded resources
- hidden content

Expected:

- no execution
- unsafe schemes rejected
- raw HTML not rendered

### csv-formula-injection.csv

Must contain formula-like cells.

Expected:

- formulas never evaluated
- re-export neutralizes formula-like cells

### xml-external-entity.opml

Expected:

- external entity resolution disabled
- no network access

### archive-path-traversal.zip

Expected:

- path traversal rejected
- absolute paths rejected

### zip-bomb-small-synthetic.zip

Expected:

- uncompressed size limit triggers
- import stops safely

## Dedupe Fixtures

Files:

```txt
fixtures/import/dedupe/netflix-same-file-twice.csv
fixtures/import/dedupe/netflix-same-title-date.csv
fixtures/import/dedupe/spotify-lastfm-same-track.json
fixtures/import/dedupe/filmarks-manual-same-movie.txt
fixtures/import/dedupe/tabelog-same-chain-different-branch.txt
```

Expected:

- exact same import returns existing job or duplicate preview
- same file different scope allowed
- Spotify/Last.fm same track/time high-confidence link
- same restaurant chain different branch not auto-merged
- same title only creates candidate or separate record

## Tombstone Fixtures

Files:

```txt
fixtures/import/tombstone/deleted-line-reimport.txt
fixtures/import/tombstone/deleted-bookmark-reimport.html
fixtures/import/tombstone/deleted-netflix-row-reimport.csv
```

Expected:

- candidate selected=false by default
- reason includes previously_deleted_candidate
- no shame copy
- restore requires explicit user action

## Expected Output Files

For each fixture:

```txt
fixtures/import/expected/<fixture-id>.detection.json
fixtures/import/expected/<fixture-id>.preview.json
fixtures/import/expected/<fixture-id>.policy.json
```

Expected outputs must not include raw sensitive text.

## Test Matrix

Every parser must be tested across:

- valid input
- malformed input
- empty input
- huge input limit
- duplicate input
- private/sensitive input
- unsupported source
- schema drift

## CI Requirements

P0 parser tests must run in CI.

CI must fail if:

- active content executes
- raw private title appears in snapshot
- wrong parser is selected with high confidence
- Import Preview is skipped
- policy default is unsafe
- deletion tombstone match is ignored

## 結論

Import実装前にfixtureを作る。

Fixtureなしでparserを実装すると、サービス形式変更・重複・security・private leakageを見逃す。

SランクImportは、まずsynthetic fixtureとexpected previewを固定してから実装する。
