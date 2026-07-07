# Import Sanitization and Private Content Handling

## 目的

この文書は、Memory OS の Import が外部ファイル・URL・CSV・HTML bookmark・Takeout・OPML・JSON・メールなどを受け取る入口であることを前提に、悪意ある入力や highly private な趣味データを安全に扱うための仕様である。

Import は便利な入口であると同時に、セキュリティ・プライバシー・羞恥・第三者情報の入口でもある。

## 最上位原則

### 1. Treat every import as hostile input

ユーザーが自分でアップロードしたファイルでも、安全とは限らない。

Memory OS は、すべてのImport入力を敵対的入力として扱う。

### 2. Never execute imported content

ImportされたHTML、SVG、CSV、JSON、XML、OPML、Markdown、PDF、EPUB、メール本文などに含まれる active content / external resource を実行しない。

### 3. Parse, do not render

Import Previewでは、raw HTMLをそのままDOMに描画しない。

必要なtitle/url/date/tagだけを安全なparserで抽出し、UIにはescape済みテキストとして表示する。

### 4. Highly private hobby content is normal private data

恥ずかしいお気に入り、私的な視聴履歴、健康・恋愛・孤独・趣味の深い領域に関わるデータは、異常なデータではない。

Memory OSでは、羞恥や罪悪感を煽らず、owner_sensitiveまたはrestrictedとして安全に扱う。

### 5. No shame copy

Import Previewで、恥ずかしい内容を責めない、からかわない、強調しない。

## Import Attack Surfaces

```ts
type ImportAttackSurface =
  | 'html_bookmark_file'
  | 'csv_file'
  | 'json_file'
  | 'xml_or_opml_file'
  | 'zip_or_takeout_archive'
  | 'email_forward'
  | 'url_clip'
  | 'image_metadata'
  | 'pdf_or_epub'
  | 'markdown_or_text'
  | 'third_party_api_payload';
```

## Required Sanitization Rules

### HTML bookmark files

Risks:

- active tags
- event-like attributes
- unsafe URL schemes
- embedded resources
- hidden content
- malformed HTML

Rules:

- never render raw HTML.
- parse bookmarks with a safe parser.
- only extract allowed fields: title, url, folder path, added date, tags if present.
- reject or neutralize unsafe URL schemes.
- normalize URL before storing.
- store original file only if user explicitly chooses raw retention.
- default rawStored=false.

Allowed URL schemes:

```ts
type AllowedImportedUrlScheme = 'https' | 'http';
```

Disallowed by default:

- javascript:
- data:
- file:
- blob:
- about:
- chrome:
- extension:
- intent:

### CSV files

Risks:

- spreadsheet formula injection
- delimiter confusion
- encoding issues
- oversized fields
- hidden newlines

Rules:

- parse as data, not spreadsheet.
- neutralize formula-like cells when exporting back to CSV.
- limit field length.
- preserve original text as escaped plain text only.
- never evaluate formulas.

### JSON files

Risks:

- huge nested objects
- prototype pollution in JS runtimes
- unexpected schema
- hidden raw sensitive content

Rules:

- parse with size/depth limits.
- validate against source-specific schema.
- ignore unknown fields by default.
- never merge arbitrary imported objects into internal objects.
- use plain data DTOs.

### XML / OPML files

Risks:

- external entities
- entity expansion
- nested payloads

Rules:

- disable external entity resolution.
- disable network access during parsing.
- enforce size/depth/entity limits.
- extract only subscription title/url/category/date if needed.

### ZIP / Takeout archives

Risks:

- huge archives
- nested archives
- path traversal
- misleading filenames
- duplicate paths
- unsupported file types

Rules:

- inspect archive manifest before extraction.
- enforce total uncompressed size limit.
- enforce file count limit.
- reject path traversal.
- reject absolute paths.
- ignore hidden/system files unless explicitly supported.
- parse only whitelisted file paths/formats.
- do not auto-import everything.

### URL clips

Risks:

- unsafe URL scheme
- tracking parameters
- private tokens embedded in URLs
- highly private sites
- work/internal URLs

Rules:

- normalize and validate URL.
- warn on private-looking tokens.
- strip tracking parameters where safe.
- do not fetch page content automatically for sensitive domains.
- store title/url/user memo/date by default.
- full page content import requires explicit user action.

### Images and metadata

Risks:

- EXIF precise location
- device identifiers
- timestamp exposure
- private people/children

Rules:

- do not store precise EXIF location by default.
- show metadata preview.
- allow stripping location/device metadata.
- minor/child-related media is restricted by default.

## Highly Private Favorites Handling

Private or embarrassing favorites are not dirty data.

They should be quietly protected.

```ts
type PrivateHobbyKind =
  | 'highly_private_interest'
  | 'embarrassing_private_interest'
  | 'health_or_body_interest'
  | 'relationship_or_loneliness_content'
  | 'political_or_religious_content'
  | 'mental_health_related_content'
  | 'minor_related_content'
  | 'work_or_internal_content';
```

Default behavior:

- privacyLevel = owner_sensitive.
- not shown in casual timeline by default.
- not used for proactive tips by default.
- not sent to LLM by default.
- safe summary only unless user opens it.
- excluded from Export by default unless explicitly selected.
- hidden/seal suggestion shown quietly.

Do not:

- shame the user.
- display private titles loudly in bulk import summary.
- generate jokes or comments about the content.
- infer personality, relationship state, morality, or life value.
- surface it in notifications.
- show it on shared screens by default.

Use:

```txt
一部の記録はプライベート性が高い可能性があります。
既定では検索・Tip・AI分析・Exportから除外できます。
```

Do not use:

```txt
恥ずかしいお気に入りが見つかりました。
あなたの私的な趣味を分析します。
```

## Import Preview UX

Import Preview must show:

- source name
- file type
- record count
- unsupported count
- risky URL count
- sensitive candidate count
- rawStored default
- AI analysis default
- Export default
- sealed/hidden suggestion

But it must not show private titles in the top summary.

Example:

```txt
120件のブックマークを検出しました。
そのうち12件はプライベート性が高い可能性があります。
これらは既定ではAI分析・Tip・Exportから除外されます。
```

## Safe Preview Modes

```ts
type ImportPreviewMode =
  | 'normal_preview'
  | 'privacy_preserving_summary'
  | 'title_redacted_preview'
  | 'user_confirm_to_reveal';
```

Rules:

- sensitive candidates use privacy_preserving_summary by default.
- title reveal requires user action.
- shared-screen safe mode should hide sensitive titles.
- import logs and analytics must not contain private titles.

## Storage Defaults

### For normal hobby items

- rawStored=false unless needed.
- summary allowed.
- catalog enrichment allowed.
- AI analysis off until user asks.

### For sensitive hobby items

- rawStored=false.
- privacyLevel=owner_sensitive or restricted.
- Tip disabled.
- AI analysis disabled.
- Export excluded by default.
- Search snippet suppression enabled.

### For private bookmarks

- do not fetch content by default.
- store URL/title only if user confirms.
- allow title redaction.
- allow folder-level private import rule.

## Folder-level Rules

Browser bookmarks often contain private folders.

Memory OS should allow folder-level handling:

```ts
type FolderImportRule =
  | 'import_normally'
  | 'import_as_sensitive'
  | 'redact_titles'
  | 'metadata_only'
  | 'skip_folder';
```

This lets the user import safely without reviewing every private item one by one.

## Security P0 Tests

1. imported HTML active content is not executed.
2. imported HTML event-like attributes are ignored.
3. unsafe URL scheme is rejected or neutralized.
4. data URL is rejected by default.
5. CSV formula-like content is neutralized on re-export.
6. XML external entity resolution is disabled.
7. archive path traversal is rejected.
8. archive uncompressed size limit is enforced.
9. unknown JSON fields cannot overwrite internal fields.
10. imported raw HTML is never rendered in Import Preview.
11. import logs contain no private titles.
12. private bookmarks default to owner_sensitive.
13. private bookmarks are excluded from proactive tips by default.
14. private bookmarks are excluded from Export by default.
15. sensitive imported URLs are not fetched automatically.
16. EXIF precise location is stripped or disabled by default.
17. import preview can hide sensitive titles.
18. unsupported files are ignored safely.

## Policy Reasons

```ts
type ImportSanitizationPolicyReason =
  | 'active_content_removed'
  | 'unsafe_url_scheme_rejected'
  | 'csv_formula_neutralized'
  | 'archive_path_rejected'
  | 'archive_size_limit_exceeded'
  | 'xml_external_entity_disabled'
  | 'sensitive_hobby_detected'
  | 'private_content_owner_sensitive_default'
  | 'private_title_hidden_in_preview'
  | 'raw_import_disabled_by_default';
```

## 結論

ImportはMemory OSの入口であり、攻撃面でもある。

趣味インポートでは、ブックマークや履歴に恥ずかしい・健康・メンタル・恋愛・仕事関連の内容が入るのは自然なこと。

Memory OSはそれを責めず、からかわず、AI分析せず、既定で守る。

安全なImportは、すべての外部入力を実行せず、rawを描画せず、必要な情報だけを抽出し、sensitiveなものを静かに保護することで成立する。
