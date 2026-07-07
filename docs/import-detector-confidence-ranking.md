# Import Detector Confidence Ranking

## 目的

この文書は、Import Detector が入力をどの媒体・サービス・Parserへ振り分けるか、そのconfidenceをどう決めるかを固定する。

Memory OSでは、拡張子だけで判定しない。

同じ `.csv` でもNetflix、Letterboxd、Goodreads、StoryGraph、独自表がありえる。

同じ `.zip` でもGoogle Takeout、X archive、Memory OS export、ただの画像zipがありえる。

Detectorは「当てにいく」のではなく、「間違って保存しない」ための仕組みである。

## Detector Goals

- 正しいparser候補を出す。
- confidenceを明示する。
- 低confidenceではImport Preview前にuser selectionを求める。
- unsafe inputをSecurityGateへ戻す。
- service-specific parserへ飛ばす前にmediumを推定する。

## Detection Signals

```ts
type DetectionSignal =
  | 'user_selected_source'
  | 'file_extension'
  | 'mime_type'
  | 'magic_bytes'
  | 'archive_manifest'
  | 'csv_headers'
  | 'json_shape'
  | 'xml_root'
  | 'html_bookmark_signature'
  | 'line_pattern'
  | 'url_host'
  | 'text_keywords'
  | 'date_pattern'
  | 'progress_pattern'
  | 'service_export_marker'
  | 'media_metadata'
  | 'export_manifest'
  | 'persona_like_marker';
```

## Signal Trust Order

Highest trust:

1. user_selected_source + compatible content
2. export manifest with known schema
3. archive manifest with known structure
4. stable CSV headers / JSON shape
5. URL host
6. known HTML/XML structure
7. line pattern / date pattern / progress pattern
8. extension / MIME only

Extension and MIME are hints only.

## Confidence Levels

```ts
type DetectionConfidence =
  | 'high'
  | 'medium'
  | 'low'
  | 'needs_user_selection';
```

### high

Use only when:

- multiple strong signals match.
- schema is known.
- parser can validate sample rows.
- no conflicting strong signal.

Examples:

- Netflix CSV known headers + date/title rows.
- OPML root + outline subscription shape.
- Memory OS export manifest with packageClass.
- X archive known structure.

### medium

Use when:

- likely service/medium but not enough for automatic commit.
- parser can produce preview candidates.
- user can correct in Preview.

Examples:

- list of streaming titles pasted after user selects Prime Video.
- GERA episode URL list.
- restaurant list with 食べログ URLs.

### low

Use when:

- content looks like a general list.
- service cannot be confidently detected.
- multiple medium candidates compete.

Examples:

- pasted title list with no source.
- mixed URL/text list.
- unknown CSV columns.

### needs_user_selection

Use when:

- detector cannot safely choose.
- schema drift detected.
- content may be sensitive and source ambiguous.
- multiple parsers produce plausible output.

## Detection Result Contract

```ts
interface ImportDetectionResult {
  sourceCandidates: Array<{
    sourceId: string;
    medium: ImportMedium;
    parserId: string;
    confidence: DetectionConfidence;
    reasons: string[];
    warnings: string[];
  }>;
  selectedCandidate?: string;
  requiresUserSelection: boolean;
  securityFlags: string[];
}
```

## Tie-breaking Rules

### User-selected source wins only if compatible

If user chooses Netflix but file is an SVG, do not force Netflix parser.

Result:

- needs_user_selection or security error.

### Sensitive medium beats convenience

If content might be chat/DM/message, default to message_conversation_context even if it also looks like title list.

### Persona-like marker beats generic text

If a file looks like a character card or system prompt, classify persona_like_context, not generic note.

### Export manifest beats archive extension

If zip contains Memory OS export manifest, classify export_archive_context before generic archive.

### Unsafe signal blocks parser

Unsafe URL scheme, active SVG/HTML, path traversal, zip bomb, XML entity should block or restrict before parser output.

## Medium Detection Examples

### title_list

Signals:

- plain lines.
- no URL majority.
- no chat timestamp/speaker pattern.
- no progress pattern majority.

Confidence:

- low without user source.
- medium with selected medium.

### url_clip

Signals:

- majority lines are safe URLs.
- known hosts can suggest service.

Confidence:

- high for known service URL when host/path matches.
- medium for mixed URL list.
- deny unsafe schemes.

### streaming_watch_activity

Signals:

- Netflix CSV headers.
- user-selected streaming service + title/date lines.
- watchlist/history keywords.

Confidence:

- high for known CSV.
- medium for paste.

### music_listening_activity

Signals:

- Spotify URL host.
- Spotify API JSON shape.
- Last.fm recent tracks shape.
- artist/track line patterns.

Confidence:

- high for API JSON.
- medium for playlist paste.

### audio_episode_activity

Signals:

- OPML root.
- RSS feed root.
- episode numbering.
- known GERA/radio hosts.

Confidence:

- high for OPML/RSS.
- medium for episode list.

### anime_manga_progress

Signals:

- N巻まで / N話まで.
- watching/reading/completed/dropped labels.
- AniList API shape.

Confidence:

- high for API shape.
- medium for progress list.

### message_conversation_context

Signals:

- chat timestamp pattern.
- speaker markers.
- LINE export markers.
- screenshot metadata indicating chat app.

Confidence:

- high for LINE export known pattern.
- medium for selected snippets.
- restricted default.

### image_media_context

Signals:

- magic bytes image.
- safe mime image.
- EXIF presence.
- screenshot metadata.

Confidence:

- high for image file.
- medium for image-like metadata stub.

### persona_like_context

Signals:

- character card fields.
- system prompt markers.
- persona name/description/greeting fields.
- roleplay transcript format.
- user asks to import a personality/persona bundle.

Confidence:

- high for character card JSON.
- medium for prompt/roleplay logs.

## Schema Drift Handling

If known source changes shape:

- downgrade confidence.
- add `schema_drift_detected` warning.
- do not commit automatically.
- preserve sample hash for debugging without raw content.

Examples:

- Netflix CSV header changed.
- X archive folder changed.
- LINE timestamp format changed.
- Memory OS export manifest version newer than supported.

## Detector No-Go

Detector must not:

- infer user's personality.
- infer relationship meaning.
- classify adult/private content with shame copy.
- run OCR by default.
- fetch URLs from the internet by default.
- execute imported HTML/SVG.
- choose a high-risk parser purely by extension.
- commit records.

## P0 Tests

1. `.csv` with Netflix headers => high Netflix parser.
2. `.csv` with unknown headers => needs_user_selection.
3. `.zip` with Memory OS manifest => export_archive_context.
4. `.zip` with path traversal => security block.
5. URL list with javascript scheme => unsafe URL rejected.
6. LINE snippet => message_conversation_context restricted.
7. Character card JSON => persona_like_context simulationAllowed=false.
8. Image file with EXIF => image_media_context EXIF stripped flag.
9. Mixed pasted list => low confidence, user selection required.
10. User-selected source incompatible with content => needs_user_selection.

## 結論

Detectorは、便利な自動判定ではなく、安全な誤判定防止機構である。

High confidenceは厳しく、low/mediumではPreviewとuser correctionに逃がす。

これにより、媒体カテゴリが増えても、Import Coreが危険な自動保存へ流れない。
