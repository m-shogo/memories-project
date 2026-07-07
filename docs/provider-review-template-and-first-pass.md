# Provider Review Template and First Pass

## 目的

この文書は、API/Export/Manual connectorを実装する前に、providerごとのreviewを必ず通すためのtemplateと、最初にreviewするprovider候補を定義する。

API仕様・利用規約・scopeは変わりうる。

したがって、この文書は実装時の最終確認ではなく、reviewの型である。

実装直前には必ず公式ドキュメントを再確認する。

## Provider Review Template

```md
# Provider Review: <Provider>

## Verdict

- Go / No-Go / Research Spike

## Import Priority

- User priority: S/A/B
- Implementation priority: M0/M1/M2/M3/M4

## Connection Method

- paste/manual
- URL clip
- file/export
- API OAuth
- API key/public
- catalog enrichment only

## Official Data Paths

- Official API:
- Official export:
- Data download:
- RSS/OPML:
- Manual/copy route:

## MVP Allowed Scope

- Read-only scopes only.
- Exact scopes must be checked against official docs at implementation time.

## MVP Denied Scope

- write
- delete
- message/DM unless separately reviewed
- account management
- playback/control actions unless explicitly needed and reviewed

## Importable Data

- fields
- history windows
- IDs
- timestamps
- titles
- URLs

## Sensitive Data

- private history
- shared profile
- third-party data
- minors/family
- location/time
- likes/bookmarks/private playlists

## Privacy Defaults

- privacyLevel:
- aiAnalysisDefault:
- exportDefault:
- rawStored:

## Dedupe Keys

- source-native key:
- canonical activity key:
- tombstone key:

## Rate Limit / Cost Risks

- expected rate limits:
- retry policy:
- backoff:
- incremental sync:

## Terms / Policy Risks

- scraping prohibited
- API data use restrictions
- redistribution restrictions
- AI/LLM restrictions

## Fixture Requirements

- API response fixture
- export file fixture
- paste fixture
- security fixture if applicable

## Go/No-Go

Go if:

- Import Preview exists
- Policy Evaluation exists
- token encryption exists if API
- source_account_ref exists if account-linked
- fixture exists

No-Go if:

- only scraping route works
- write scope needed for MVP
- token cannot be stored securely
- private raw would sync without preview
```

## First Pass Provider Order

### 1. Netflix

Reason:

- S-rank.
- file/manual first.
- no OAuth needed for first value.
- strong streaming_watch_activity fixture.

Implementation mode:

```txt
file_first + paste fallback
```

Review needs:

- CSV/export format fixture.
- shared profile warning.
- duplicate title/date behavior.
- no personality/taste inference.

MVP Go condition:

- Parser handles synthetic CSV.
- Import Preview shows owner_sensitive/export excluded.

### 2. LINE selected copy

Reason:

- S-rank.
- high personal value.
- high risk.
- must prove summary-only/restricted behavior.

Implementation mode:

```txt
paste_first selected snippet only
```

Review needs:

- rawStored=false.
- restricted default.
- export excluded.
- no intent analysis.
- no evidence package.

MVP Go condition:

- selected snippet becomes safe summary candidate only.

No-Go:

- bulk raw import.
- partner truth/intent analysis.

### 3. 食べログ

Reason:

- S-rank.
- URL/list/manual can work without API.
- motivates user quickly.

Implementation mode:

```txt
url_clip + paste/manual
```

Review needs:

- no scraping.
- URL/title/area extraction only.
- location/date/companions owner_sensitive.
- no relationship inference.

MVP Go condition:

- URL list turns into restaurant candidates.

### 4. Manga / Anime Progress Manual

Reason:

- S-rank.
- low API dependency.
- very strong motivation source.

Implementation mode:

```txt
manual_first + paste progress parser
```

Review needs:

- progress syntax.
- no manga page raw import.
- no app scraping.
- private folder optional sensitive.

MVP Go condition:

- N巻まで/N話まで parsed.

### 5. GERA / Podcast

Reason:

- S-rank.
- URL/list/OPML/RSS can work early.

Implementation mode:

```txt
paste/url first, OPML/RSS next
```

Review needs:

- show/episode model.
- listened/want_to_listen.
- no personality inference.

MVP Go condition:

- episode list becomes audio candidates.

### 6. Filmarks

Reason:

- S-rank.
- paste/URL first.
- good movie activity model.

Implementation mode:

```txt
paste/url first
```

Review needs:

- no profile scraping.
- review/rating sensitivity.
- TMDb enrichment later.

MVP Go condition:

- watched list/title/date/rating candidates.

### 7. Browser Bookmarks

Reason:

- A-rank but technically foundational.
- exercises HTML security/private title handling.

Implementation mode:

```txt
file_first
```

Review needs:

- raw HTML never rendered.
- unsafe schemes rejected.
- private folder title redacted.

MVP Go condition:

- synthetic bookmark fixture safe.

### 8. Spotify

Reason:

- S-rank.
- API feasible but gated by OAuth/token security.

Implementation mode:

```txt
API after OAuth gate + URL/paste fallback
```

Review needs:

- official scope verification at implementation time.
- read-only minimal scopes.
- no playback control/write.
- token encryption.
- revocation.
- source_account_ref.
- rate limit handling.

MVP Go condition:

- token/OAuth foundation implemented.
- API response fixture with no tokens.
- Preview-only first.

### 9. AniList

Reason:

- strong anime/manga API candidate.
- user priority aligns with anime/manga progress.

Implementation mode:

```txt
API after OAuth/API review + manual fallback
```

Review needs:

- read-only list/progress.
- no write/update in MVP.
- GraphQL query allowlist.
- ID/alias normalization.

MVP Go condition:

- API fixture maps to anime_manga_progress candidate.

### 10. Last.fm

Reason:

- useful music bridge.
- supports scrobble history independent of Spotify/Apple Music.

Implementation mode:

```txt
public API key first if data is public/user-selected
```

Review needs:

- username privacy.
- recent/loved/top separation.
- Spotify dedupe by time window.

MVP Go condition:

- recent track fixture maps to music_listening_activity.

## Apple Music Special Handling

Apple Music is S-rank but not first API implementation.

Reason:

- complete listening history availability is not assumed.
- developer/user token flow needs dedicated review.
- Last.fm/export/paste may be better first path.

First mode:

```txt
paste/export/manual first
research_spike before API promise
```

No-Go:

- “complete Apple Music history” promise.
- scraping.
- write actions.

## X / Twitter Special Handling

X is S-rank but not first API implementation.

Reason:

- API cost/terms can change.
- likes/bookmarks/DMs are sensitive.
- archive/url/paste route is safer first.

First mode:

```txt
archive/url/paste first
API only after cost/terms review
```

No-Go:

- DM import default.
- API polling MVP.
- surveillance or evidence use.

## Provider Review Acceptance

A provider review is complete when:

- official path identified or manual fallback accepted.
- importable fields listed.
- privacy defaults set.
- export default set.
- dedupe keys identified.
- fixtures defined.
- No-Go listed.
- implementation mode assigned.

## 結論

Providerごとの実装は、勢いで始めない。

まずNetflix/LINE/食べログ/漫画アニメ/GERA/Filmarks/Bookmarksで、non-APIの価値と安全性を証明する。

APIはSpotify/AniList/Last.fmから。ただしtoken/OAuth gate後。

Apple MusicとXはSランクだが、API-firstではなくresearch/export/paste/archive-firstで進める。
