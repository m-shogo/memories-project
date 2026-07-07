# Import Architecture Decision

## 目的

この文書は、Memory OS のImport機能を実装前にどう分解するかを決めるための設計判断である。

ユーザーの問い:

- Import機能は一緒なのか
- サービスごとに作るのか
- 拡張子で分けるのか
- 内部で柔軟に調整するのか

結論:

Memory OSのImportは、単一のImport Pipelineを中心にしつつ、Source Adapter、File Parser、Content Detector、Normalizer、Preview、Policy、Committerを分離する。

つまり、1つの巨大Importでも、サービスごとの完全別実装でも、拡張子だけ分岐でもない。

## Architecture Decision

採用する方式:

```txt
One Import Core
+ Source Adapters
+ Parser Registry
+ Content Detectors
+ Normalizers
+ Import Preview
+ Policy Evaluation
+ Safe Commit
```

## なぜ1つの共通基盤にするか

Importで必ず共通する処理がある。

- ファイル/テキスト/URL/API payloadを受け取る
- サイズ制限
- active content無効化
- sourceRef作成
- parse
- normalize
- duplicate detection
- privacy/safety classification
- Import Preview
- user confirmation
- save
- audit without raw

これをサービスごとに別実装すると、セキュリティ・UX・重複処理が壊れる。

## なぜサービス別Adapterも必要か

サービスごとに意味が違う。

例:

- Netflix CSVのDateは視聴日
- Spotify recently playedのplayed_atは再生日
- LINE textのtimestampは会話時刻
- 食べログURLは訪問日ではなく店舗参照
- Filmarks ratingはユーザー評価
- AniList progressは視聴/読書進捗

同じCSV/JSONでも意味が違うため、service adapterが必要。

## なぜ拡張子だけで分けないか

拡張子はヒントであり、真実ではない。

問題:

- `.csv` でもNetflix、Letterboxd、Goodreads、StoryGraphで意味が違う。
- `.json` でもX archive、Google Takeout、browser exportでschemaが違う。
- `.zip` でもGoogle Takeout、X archive、Apple data exportでmanifestが違う。
- `.html` でもbrowser bookmarksか保存ページか不明。
- 拡張子偽装がありうる。

したがって、拡張子は `FileTypeHint` として扱い、Content Detectorで中身を見る。

## Core Types

```ts
type ImportInputKind =
  | 'file_upload'
  | 'paste_text'
  | 'url_clip'
  | 'api_connection'
  | 'email_forward'
  | 'manual_entry';

type ImportSourceKind =
  | 'service_export'
  | 'service_api'
  | 'service_clip'
  | 'manual_claim'
  | 'catalog_enrichment'
  | 'unknown';

type ImportConfidence = 'high' | 'medium' | 'low' | 'needs_user_selection';
```

## Import Pipeline

```txt
1. Intake
2. Security Gate
3. Type Detection
4. Source Detection
5. Parser Selection
6. Parse to RawImportRecords
7. Normalize to CanonicalImportRecords
8. Deduplicate
9. Privacy/Safety Classification
10. Import Preview
11. User Correction / Scope Selection
12. Policy Evaluation
13. Commit to Memory Records
14. Audit without raw
```

## 1. Intake

Inputs:

- uploaded file
- pasted text
- URL
- OAuth/API token result
- forwarded email
- manual form

Output:

```ts
interface ImportIntake {
  inputId: string;
  inputKind: ImportInputKind;
  declaredService?: string;
  filename?: string;
  mimeType?: string;
  sizeBytes?: number;
  textSample?: string;
  receivedAt: string;
}
```

## 2. Security Gate

Before parsing:

- size limit
- file count limit
- archive manifest inspection
- no active content execution
- URL scheme validation
- XML external entities disabled
- CSV formula neutralization on re-export
- raw HTML never rendered

If security gate fails, do not parse further.

## 3. Type Detection

Detection uses multiple hints:

```ts
interface TypeDetectionSignal {
  filenameExtension?: string;
  mimeType?: string;
  magicBytes?: string;
  archiveManifest?: string[];
  textSample?: string;
  userSelectedSource?: string;
}
```

Extension is only one signal.

## 4. Source Detection

Example source detectors:

- Netflix CSV detector
- Letterboxd CSV detector
- Goodreads CSV detector
- X archive detector
- Google Takeout detector
- Browser Bookmark HTML detector
- LINE text export detector
- OPML detector
- Podcast RSS detector
- Filmarks paste detector
- 食べログ URL detector
- GERA URL/list detector
- Spotify API payload detector
- AniList GraphQL payload detector

Detection result:

```ts
interface SourceDetectionResult {
  sourceId: string;
  service: string;
  format: string;
  confidence: ImportConfidence;
  reasons: string[];
  parserCandidates: string[];
  requiresUserSelection: boolean;
}
```

If confidence is low, ask the user to choose the service.

## 5. Parser Selection

Parser Registry:

```ts
interface ImportParser {
  parserId: string;
  supports(input: ImportIntake, detection: SourceDetectionResult): boolean;
  parse(input: SanitizedImportInput): Promise<RawImportRecord[]>;
}
```

Parser examples:

- `netflix-viewing-activity-csv-parser`
- `letterboxd-csv-parser`
- `x-archive-parser`
- `line-text-export-parser`
- `browser-bookmark-html-parser`
- `opml-parser`
- `universal-title-list-paste-parser`
- `url-list-parser`
- `receipt-email-parser`

## 6. RawImportRecord

```ts
interface RawImportRecord {
  rawRecordId: string;
  sourceRef: string;
  originalIndex?: number;
  extractedFields: Record<string, unknown>;
  rawText?: string;
  rawStored: boolean;
  parseWarnings: string[];
}
```

Rules:

- rawStored=false by default.
- rawText may exist only during import job unless user explicitly retains raw.
- logs must not contain rawText.

## 7. CanonicalImportRecord

```ts
interface CanonicalImportRecord {
  canonicalId: string;
  domain:
    | 'music'
    | 'movie'
    | 'tv'
    | 'anime'
    | 'manga'
    | 'book'
    | 'library'
    | 'recipe'
    | 'restaurant'
    | 'radio'
    | 'podcast'
    | 'social'
    | 'message'
    | 'web_bookmark'
    | 'game'
    | 'other';
  title?: string;
  url?: string;
  occurredAt?: string;
  status?: string;
  progress?: Record<string, unknown>;
  userMemo?: string;
  sourceRef: string;
  evidenceType:
    | 'api_imported'
    | 'file_imported'
    | 'paste_imported'
    | 'url_clipped'
    | 'manual_claim'
    | 'email_imported';
  confidence: ImportConfidence;
  privacyLevel: 'owner_only' | 'owner_sensitive' | 'restricted';
  aiAnalysisDefault: 'off' | 'allowed_after_user_request';
  exportDefault: 'included' | 'excluded';
}
```

## Source Adapter

Service-specific Adapter responsibilities:

```ts
interface SourceAdapter {
  sourceId: string;
  displayName: string;
  supportedInputKinds: ImportInputKind[];
  detect?(input: ImportIntake): SourceDetectionResult;
  parserIds: string[];
  normalize(raw: RawImportRecord): CanonicalImportRecord;
  privacyDefaults(record: CanonicalImportRecord): PrivacyDecision;
  enrichmentPlan?(record: CanonicalImportRecord): EnrichmentRequest[];
}
```

Adapter examples:

- AppleMusicAdapter
- SpotifyAdapter
- XArchiveAdapter
- NetflixViewingActivityAdapter
- PrimeVideoPasteAdapter
- DisneyPlusPasteAdapter
- UNextPasteAdapter
- LineTextExportAdapter
- TabelogUrlAdapter
- RadikoUrlAdapter
- GeraEpisodeAdapter
- PodcastOpmlAdapter
- FilmarksPasteAdapter
- MangaManualAdapter
- AnimeAniListAdapter

## Parser vs Adapter

Parser reads format.

Adapter interprets service meaning.

Example:

```txt
CSV Parser:
  reads rows and columns.

Netflix Adapter:
  interprets Title as watched title and Date as watched date.

Letterboxd Adapter:
  interprets Rating, WatchedDate, Tags, Review.

Goodreads Adapter:
  interprets Bookshelf, Date Read, My Rating.
```

## Detector vs User Selection

The system may auto-detect.

But if uncertain, user selection wins.

Flow:

```txt
Detected candidates:
- Netflix Viewing Activity CSV: 70%
- Generic CSV: 30%

Ask:
これはNetflixの視聴履歴CSVですか？
```

Do not silently guess when confidence is low.

## Universal Paste Import

Universal paste is first-class.

It does not replace service adapters. It creates rough records, then asks user to confirm.

Use cases:

- Filmarks watched list
- 食べログ saved restaurant list
- Prime Video history
- Disney+ watchlist
- U-NEXT history
- GERA episode list
- manga progress list
- anime progress list
- Apple Music playlist copy

## Import Preview is mandatory

No import writes directly to Memory.

Preview shows:

- detected source
- record count
- confidence
- date range
- privacy defaults
- sensitive candidate count
- unsupported count
- duplicate count
- rawStored default
- AI analysis default
- Export default

## Save Strategy

After preview and confirmation:

- create SourceRef
- create MemoryRecords or HobbyActivity records
- store canonical data
- store raw only if user explicitly chooses
- attach policy decision
- attach provenance

## Implementation Modules

Suggested modules:

```txt
import-core/
  intake/
  security/
  detection/
  parsers/
  adapters/
  normalizers/
  preview/
  policy/
  commit/
  audit/
```

## Anti-patterns

Do not:

- create one giant import function.
- create fully separate import logic per service.
- route by extension only.
- render imported HTML.
- write records before preview.
- send imported data to LLM before policy.
- store raw by default.
- treat paste import as lower class.
- treat service API records as more true than user manual records.

## Acceptance Criteria

- Import Core exists as one pipeline.
- Each service uses Source Adapter.
- Each file/text format uses Parser Registry.
- Extension is only a hint.
- Content Detector can identify common source exports.
- Low confidence asks user to select source.
- Import Preview always happens before commit.
- Policy runs before save, search, LLM, tips, and export.
- Manual/paste import is first-class.

## 結論

Memory OSのImportは、一緒に作る。ただし中身は分離する。

共通基盤は1つ。

サービスごとのAdapterを持つ。

拡張子ごとのParserを持つ。

拡張子だけでは決めない。

中身・manifest・ユーザー選択・parser confidenceを使って柔軟に判定する。

これにより、Apple Music、Spotify、Netflix、X、LINE、Filmarks、食べログ、GERA、漫画、アニメ、映画、Podcastなどを同じImport体験で扱える。
