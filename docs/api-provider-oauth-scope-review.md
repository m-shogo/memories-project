# API Provider OAuth Scope Review

## 目的

この文書は、Memory OS がAPI connectorを実装する前に、providerごとのscope・接続方式・禁止事項・安全defaultを整理するためのreview checklistである。

API connectorはSランクImportを強くするが、token・scope・rate limit・terms・privacyのリスクが大きい。

したがって、providerごとにscope reviewを通すまで実装しない。

## 共通Gate

API connector実装前に必須:

- Import Preview exists.
- Policy Evaluation exists.
- key_reference exists.
- oauth_connection exists.
- source_account_ref exists.
- token encryption helper exists.
- revocation flow exists.
- audit without raw exists.
- provider terms reviewed.
- minimal read-only scopes selected.
- fixture/API response sample exists.

## Provider Review Format

```ts
interface ProviderOAuthReview {
  provider: string;
  priority: 'S' | 'A' | 'B' | 'later';
  connectorMode: 'api_first' | 'file_first' | 'paste_first' | 'research_spike';
  allowedScopes: string[];
  deniedScopes: string[];
  importableData: string[];
  sensitiveData: string[];
  previewDefaults: {
    privacy: 'owner_only' | 'owner_sensitive' | 'restricted';
    aiAnalysis: 'off' | 'allowed_after_user_request';
    exportDefault: 'included' | 'excluded';
  };
  productionBlockers: string[];
}
```

## Spotify

Priority: S

Connector mode:

```txt
api_first + url/paste fallback
```

Allowed MVP scopes:

- user-read-recently-played
- user-library-read
- playlist-read-private
- playlist-read-collaborative
- user-top-read
- user-read-currently-playing

Denied MVP scopes:

- playlist-modify-public
- playlist-modify-private
- user-modify-playback-state
- user-read-email unless specifically needed
- user-read-private unless specifically needed

Importable:

- recently played
- saved tracks
- saved albums
- playlists
- followed/saved shows if scope allows
- top artists/tracks
- currently playing

Sensitive:

- recently played
- private playlists
- current playback
- explicit/private listening context

Defaults:

- public/selected playlists: owner_only
- recently played/currently playing/private playlists: owner_sensitive
- AI analysis off
- export user-selected

Production blockers:

- OAuth token encryption
- source_account_ref
- rate limit handling
- no playback modification

## Last.fm

Priority: S/A

Connector mode:

```txt
api_key_public first; OAuth only if write/private actions needed
```

Allowed:

- user.getRecentTracks
- user.getLovedTracks
- user.getTopArtists
- user.getTopAlbums
- user.getTopTracks
- weekly charts

Denied MVP:

- write/scrobble actions
- destructive/account changes

Importable:

- scrobbles
- loved tracks
- top artists/albums/tracks

Sensitive:

- complete listening profile
- late-night or private listening patterns

Defaults:

- owner_sensitive for recent listening
- owner_only for user-selected top lists
- AI off

Production blockers:

- API terms review
- username privacy warning
- dedupe with Spotify by time/window

## AniList

Priority: S

Connector mode:

```txt
api_first + manual/paste fallback
```

Allowed MVP:

- read user anime/manga list
- read status/progress/score
- read media metadata

Denied MVP:

- updating list entries
- deleting entries
- posting social activity

Importable:

- watching/reading
- completed
- paused
- dropped
- planning
- progress
- score
- favorites if user selects

Sensitive:

- private lists
- ratings/favorites depending user

Defaults:

- owner_only for normal progress
- owner_sensitive for private list/favorites if flagged
- AI off

Production blockers:

- OAuth flow review
- GraphQL query allowlist
- rate limit handling
- title alias normalization

## Apple Music

Priority: S

Connector mode:

```txt
research_spike + paste/export fallback first
```

Allowed initial:

- playlist/library paste
- Apple Data & Privacy export if user provides
- Last.fm fallback

API/MusicKit allowed only after:

- Apple Developer/MusicKit review
- token flow understood
- exact accessible data confirmed
- user music token handling defined

Denied:

- claiming full listening history before proof
- account scraping
- write actions

Importable potential:

- library items
- playlists
- catalog metadata
- purchase/download records from export

Sensitive:

- listening history if available
- private playlists

Defaults:

- owner_sensitive for listening history
- owner_only for selected playlist/library
- AI off

Production blockers:

- API capability proof
- developer token handling
- user token encryption
- no false promise of complete history

## X / Twitter

Priority: S

Connector mode:

```txt
archive/url/paste first; API later only after cost/terms review
```

Allowed MVP:

- official archive ZIP
- post/thread URL clip
- copied post/thread paste

API denied initially:

- broad timeline polling
- DM import
- write/post actions
- surveillance-like monitoring

Importable:

- own posts from archive
- selected URLs
- selected copied posts
- likes/bookmarks only if user selects and archive provides

Sensitive:

- likes/bookmarks
- DMs
- protected/limited posts
- political/health/private interests

Defaults:

- own posts owner_only
- likes/bookmarks owner_sensitive
- DMs excluded or restricted summary-only if ever supported
- AI off

Production blockers:

- API terms/cost review
- no scraping
- no surveillance/blame use

## Google / YouTube

Priority: S/A

Connector mode:

```txt
Takeout first; API later for selected playlists/subscriptions/metadata
```

Allowed MVP:

- Google Takeout upload
- YouTube URL clip
- playlist URL clip

API caution:

- minimal read scopes only
- avoid broad Google account scope
- avoid Gmail/Drive unless separate connector safety design exists

Importable:

- watch history from Takeout
- liked videos if selected
- subscriptions
- playlists
- video metadata

Sensitive:

- search history
- watch history
- health/politics/religion/relationship content

Defaults:

- watch/search history owner_sensitive
- search history separate explicit selection
- AI off
- export excluded by default unless user opts in

Production blockers:

- Takeout parser fixture
- search history warning
- no blanket Google OAuth

## Steam

Priority: A/S for games

Connector mode:

```txt
api_first where profile visibility allows + paste/email fallback
```

Allowed:

- owned games when visible/authorized
- recently played
- playtime

Denied MVP:

- account modification
- trading/inventory-sensitive scopes

Importable:

- owned games
- recently played
- playtime

Sensitive:

- playtime can imply habits; do not judge

Defaults:

- owner_only
- AI off

Production blockers:

- profile visibility handling
- no life discipline score from playtime

## TMDb

Priority: A

Connector mode:

```txt
catalog_enrichment_only
```

Allowed:

- movie/tv metadata lookup
- IDs
- title/year/cast/crew metadata

Denied:

- treating TMDb as user activity

Defaults:

- catalog data not user-sensitive by itself
- user activity remains governed by source

Production blockers:

- attribution/terms review
- cache policy

## Google Books / Open Library / NDL / Calil

Priority: A

Connector mode:

```txt
catalog_enrichment_only + optional user-provided file/manual
```

Allowed:

- book metadata
- ISBN lookup
- cover metadata
- library holdings/availability for Calil

Denied:

- treating Calil as user loan history
- high-volume scraping
- storing full copyrighted text

Sensitive:

- user reading/loan history, not public catalog data

Defaults:

- catalog enrichment owner_only by link
- library loan history restricted/manual

Production blockers:

- terms/rate limit review
- cache policy
- no loan-history assumption

## Provider-specific Issue Template

Before implementing any connector, create/review:

```txt
Provider:
Connection method:
Scopes:
Denied scopes:
Data returned:
Privacy defaults:
Rate limits:
Terms concerns:
Token storage:
Revocation behavior:
Fixture path:
Import Preview fields:
Policy tests:
Go/No-Go:
```

## API Connector Go/No-Go

Go only if:

- allowed scopes are read-only/minimal.
- token encryption exists.
- revocation exists.
- fixture exists.
- Import Preview exists.
- Policy Evaluation exists.
- source_account_ref exists.
- provider-specific privacy defaults exist.

No-Go if:

- write scope needed for MVP.
- raw/private data would sync without preview.
- API terms unclear for intended use.
- token would be stored plaintext.
- user cannot disconnect.
- provider returns mixed account/profile data without warning.

## 結論

API connectorは、便利だから先に作るのではない。

Memory OSでは、providerごとのscope・privacy・terms・token・revocation・fixture・policyをreviewしてから作る。

特にSランクでも、Apple MusicとXはAPI-firstではなく、research/export/paste-firstで進める。

Spotify、AniList、Last.fmはAPI候補だが、Import Previewとtoken encryptionが先である。
