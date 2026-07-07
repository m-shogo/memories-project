# Import Medium MVP Tickets

## 目的

この文書は、媒体カテゴリごとのMVP実装チケットを、実装順に並べたbacklogである。

実装はまだ始めない。

ただし、実装に入るときに「何から作るか」を迷わないようにする。

## Ticket Format

```ts
interface ImportMvpTicket {
  id: string;
  title: string;
  dependsOn: string[];
  scope: string[];
  notInScope: string[];
  acceptance: string[];
}
```

## M0 Foundation Tickets

### IMP-M0-001 SecurityGate v0

Depends on:

- fixture security backlog

Scope:

- paste size limit
- unsafe URL scheme rejection
- no HTML/SVG rendering
- control character display neutralization
- archive path traversal placeholder check
- log counts only

Not in scope:

- full antivirus/CDR
- full archive unpacking
- OCR

Acceptance:

- unsafe URL fixture rejected.
- active SVG/HTML not rendered.
- logs contain no raw input.

### IMP-M0-002 ParserRegistry v0

Scope:

- register parserId/parserVersion.
- select parser by medium/source hints.
- return confidence and warnings.

Acceptance:

- can register universal/title/url/progress parsers.
- low confidence returns needs_user_selection.

### IMP-M0-003 Import Preview DTO v0

Scope:

- PreviewSummary
- PreviewCandidate
- privacy defaults
- warnings
- selected flag

Acceptance:

- no save path.
- P0 policy hints can be attached.

### IMP-M0-004 SourceSelector v0

Scope:

- user-selected source overrides weak detector.
- supported S-rank source list.

Acceptance:

- unknown input asks source selection.
- selected source visible in preview.

## M1 Universal Medium Tickets

### IMP-M1-001 Title List Parser

Depends on:

- IMP-M0-001
- IMP-M0-002
- IMP-M0-003

Scope:

- one non-empty line = one title candidate.
- optional default status.
- optional default date.

Acceptance:

- title-list fixture creates candidates.
- privacy owner_only.
- AI off.

### IMP-M1-002 URL List Parser

Scope:

- extract URLs line by line.
- normalize host.
- reject unsafe schemes.
- domain-based source hints.

Acceptance:

- URL fixture parses safe URLs.
- unsafe scheme rejected.
- no fetch/scraping by default.

### IMP-M1-003 Table-like Date/Title Parser

Scope:

- parse simple date + title lines.
- set occurredAtPrecision=date.

Acceptance:

- Netflix-like paste fixture parses.
- exact timestamp not invented.

### IMP-M1-004 Progress List Parser

Scope:

- parse N巻まで, N話まで, 完了, 視聴中, 読書中.

Acceptance:

- manga/anime progress fixture parses.
- domain can be user-selected.

## M2 S-rank Non-API Medium Tickets

### IMP-M2-001 Netflix CSV Parser

Scope:

- parse viewing activity CSV.
- date/title.
- duplicate rows.
- shared profile warning field.

Acceptance:

- owner_sensitive default.
- AI off.
- duplicate candidate marked.
- no direct memory save.

### IMP-M2-002 Streaming Paste Adapter

Scope:

- Prime Video / Disney+ / U-NEXT list paste.
- current watching manual.

Acceptance:

- owner_sensitive default.
- status watched/watching/want_to_watch.
- shared profile warning supported.

### IMP-M2-003 Manga/Anime Progress Adapter

Scope:

- manual/paste progress.
- anime/manga domain selection.
- purchase email basic extraction later.

Acceptance:

- no page/raw image import.
- owner_only default.
- private folder can become owner_sensitive.

### IMP-M2-004 Restaurant/Food Adapter

Scope:

- 食べログ URL/list paste.
- reservation email text.
- companion/date/location sensitivity.

Acceptance:

- restaurant title owner_only.
- companion/location owner_sensitive.
- no relationship inference.

### IMP-M2-005 Audio Episode Adapter

Scope:

- GERA/radio list paste.
- podcast OPML minimal.
- RSS URL later.

Acceptance:

- show title/episode parsed.
- listened/want_to_listen status.

### IMP-M2-006 Filmarks/Movie Adapter

Scope:

- watched list paste.
- rating/review fragment.
- URL clip.

Acceptance:

- no API assumption.
- owner_only/owner_sensitive review option.
- no taste/personality inference.

## M3 Sensitive Medium Tickets

### IMP-M3-001 LINE Selected Snippet Parser

Scope:

- selected copy/paste only.
- timestamp/speaker direction if obvious.
- summary-only candidate.

Not in scope:

- bulk raw import.
- intent analysis.
- evidence package.

Acceptance:

- restricted default.
- rawStored=false.
- Export excluded.

### IMP-M3-002 Browser Bookmark Parser

Scope:

- bookmark HTML metadata.
- folder path.
- private folder flag.
- unsafe URL rejection.

Acceptance:

- raw HTML not rendered.
- private title not logged.
- owner_sensitive for private-like folder.

### IMP-M3-003 Image Media Metadata Parser

Scope:

- metadata-only image parsing.
- dimensions/mime/size.
- EXIF GPS stripped flag.
- OCR off.

Not in scope:

- face recognition.
- OCR.
- raw media export.

Acceptance:

- chat screenshot OCR denied.
- minor/photo flags restrict export.

### IMP-M3-004 Persona-like Detector

Scope:

- detect character card / roleplay log / AI companion log / writing style sample.
- set simulationAllowed=false.

Not in scope:

- persona agent.
- style imitation.

Acceptance:

- persona export default excluded.
- no merge into self profile.

### IMP-M3-005 Export Archive Re-import Detector

Scope:

- parse Memory OS export manifest.
- detect package class and risk flags.
- require tombstone check.

Acceptance:

- no policy bypass.
- persona/media flags retained.

## M4 API Medium Tickets

### IMP-M4-001 Spotify API Connector Spike

Blocked until:

- token encryption
- OAuth revocation
- Import Preview
- provider scope review

Scope:

- read-only scopes.
- recently played / saved / playlists.
- preview only.

Acceptance:

- no write scopes.
- owner_sensitive for recent/current/private.

### IMP-M4-002 AniList API Connector Spike

Scope:

- read list/progress.
- no write/update.

Acceptance:

- progress parsed.
- no personality inference.

### IMP-M4-003 Last.fm API Connector

Scope:

- recent/loved/top tracks.
- username privacy warning.

Acceptance:

- Spotify/Last.fm dedupe candidate by time window.

### IMP-M4-004 TMDb Catalog Enrichment

Scope:

- movie/tv metadata only.
- not user activity.

Acceptance:

- external id links canonical item.
- user activity privacy inherited from source.

### IMP-M4-005 Book Catalog Enrichment

Scope:

- ISBN/title metadata from catalog APIs.
- no loan history assumption.

Acceptance:

- Calil availability not treated as user history.

## M5 Safe Commit Tickets

### IMP-M5-001 Safe Commit Low-risk Manual/Paste

Blocked until:

- Import Preview
- Policy Evaluation
- Dedupe/Tombstone
- RLS negative tests

Scope:

- create source_ref.
- create source_item/user_activity for low-risk candidates.
- no memory_record auto summary yet.

Acceptance:

- tombstone candidate not committed by default.
- low confidence not auto-merged.
- audit counts only.

### IMP-M5-002 Search Projection for Low-risk Records

Blocked until:

- lifecycle model
- search_document invalidation

Scope:

- create safe search_document for owner_only low-risk records.

Acceptance:

- hidden/sealed/deleted not searchable.
- no private raw in search document.

## No-Go Tickets

Do not create until later:

- `LINE bulk raw import`
- `Full media archive export`
- `Persona agent activation`
- `Import-time embedding all items`
- `One-click raw archive export`
- `X API polling`
- `Apple Music full history promise`

## 結論

媒体ImportのMVPは、Universal + S-rank non-API + sensitive preview-only + API later の順番で進める。

最初に価値を出すのは、APIではなく、paste/url/manual/CSV/OPML/metadata previewである。
