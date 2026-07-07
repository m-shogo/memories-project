# Import Pre-implementation Readiness Checklist

## 目的

この文書は、Memory OS のImport機能を実装に入る直前まで進めるためのチェックリストである。

ここを満たすまで実装に入らない。

## Architecture Decision

決定済み:

- Import Coreは共通基盤。
- Source Adapterはサービス固有の意味づけ。
- Parserはファイル/テキスト形式の読み取り。
- Detectorは中身・manifest・ユーザー選択・confidenceでsource/formatを推定。
- 拡張子だけでは判定しない。
- Import Previewは必須。
- Policy Evaluation後に保存する。

## MVP Scope

### Phase S0: Must build first

- Universal paste/manual import foundation
- Source selector
- Parser registry
- Source detector
- Import Preview
- Privacy/safety classifier
- Safe commit
- Audit without raw

### Phase S1: First concrete adapters

- Browser bookmarks
- Netflix CSV
- LINE text/copy
- X archive
- Filmarks paste/URL
- 食べログ URL/list
- Podcast OPML/RSS
- GERA URL/list
- Manga/anime manual progress

### Phase S2: API adapters

- Spotify API
- AniList API
- Last.fm API
- TMDb enrichment
- Google Books/Open Library/NDL/Calil enrichment
- Apple Music research spike

### Phase S3: Streaming manual bridges

- Prime Video paste/email/manual
- Disney+ paste/manual
- U-NEXT paste/email/manual

## Required Docs Before Implementation

Already created:

- `docs/import-architecture-decision.md`
- `docs/universal-paste-import-spec.md`
- `docs/import-preview-ux-spec.md`
- `docs/s-rank-import-adapter-specs.md`
- `docs/s-rank-import-user-guides.md`
- `docs/user-priority-s-rank-imports.md`
- `docs/hobby-import-service-method-matrix.md`
- `docs/import-sanitization-and-private-content.md`

Still useful but not blocking:

- concrete JSON schema examples
- parser fixture examples
- UI wireframe notes
- adapter test case table

## Domain Model Checklist

Must define before coding:

```ts
type ImportJobStatus =
  | 'created'
  | 'security_checked'
  | 'detected'
  | 'parsed'
  | 'preview_ready'
  | 'user_confirmed'
  | 'policy_checked'
  | 'committed'
  | 'cancelled'
  | 'failed';
```

```ts
interface ImportJob {
  id: string;
  inputKind: ImportInputKind;
  sourceId?: string;
  parserId?: string;
  detectorConfidence?: ImportConfidence;
  status: ImportJobStatus;
  createdAt: string;
  previewId?: string;
  policyDecisionIds: string[];
}
```

```ts
interface ImportPreview {
  id: string;
  importJobId: string;
  sourceSummary: ImportSourceSummary;
  safetySummary: ImportSafetySummary;
  candidates: ImportPreviewCandidate[];
}
```

```ts
interface ImportPreviewCandidate {
  id: string;
  canonical: CanonicalImportRecord;
  selected: boolean;
  editable: boolean;
  confidence: ImportConfidence;
  warnings: string[];
  policyHints: string[];
}
```

## Security Checklist

P0:

- no active content execution.
- raw HTML never rendered.
- unsafe URL schemes rejected.
- CSV formula-like content neutralized on export.
- XML external entities disabled.
- archive path traversal rejected.
- archive size and file count limits.
- logs contain no raw imported content.
- private titles not logged.
- token storage encrypted.
- OAuth scopes minimized.

## Privacy Checklist

P0:

- rawStored=false by default.
- AI analysis off by default.
- private/sensitive candidates owner_sensitive/restricted.
- LINE raw summary-only default.
- X likes/bookmarks owner_sensitive.
- streaming watch history owner_sensitive.
- 食べログ companions/location owner_sensitive.
- private bookmarks excluded from tips/export by default.
- user can skip records before save.

## UX Checklist

P0:

- Import Preview before save.
- clear source detection confidence.
- user can correct service/source.
- user can edit title/date/status/progress.
- user can bulk set privacy.
- user can skip low-confidence records.
- sensitive title reveal is user action.
- mobile UI avoids giant horizontal tables.
- Cancel is always available before commit.

## Policy Checklist

P0 policy checks before commit:

- allowed source
- raw storage allowed?
- third-party content allowed?
- sensitive content default?
- minor/family/partner/deceased/corporate restrictions
- surveillance/evidence misuse prevention
- import resurrection guard for deleted records
- export default decision
- LLM allowed or not

## Test Fixtures Needed

Create fixtures before coding:

```txt
fixtures/import/netflix-viewing-activity.csv
fixtures/import/letterboxd-diary.csv
fixtures/import/line-chat-export.txt
fixtures/import/x-archive-minimal.zip
fixtures/import/browser-bookmarks.html
fixtures/import/opml-subscriptions.opml
fixtures/import/filmarks-list-paste.txt
fixtures/import/tabelog-list-paste.txt
fixtures/import/gera-episode-list.txt
fixtures/import/manga-progress-list.txt
fixtures/import/anime-progress-list.txt
fixtures/import/spotify-playlist-paste.txt
fixtures/import/malicious-bookmarks.html
fixtures/import/csv-formula-injection.csv
fixtures/import/archive-path-traversal.zip
```

Fixtures must contain synthetic data, not real personal data.

## First Implementation Slice

Recommended first coding slice:

1. ImportJob model
2. ImportIntake type
3. SecurityGate for paste/text/file metadata
4. UniversalPasteParser
5. SourceSelector
6. ImportPreview DTO
7. Save nothing yet; preview-only prototype

This gives visible value without dangerous writes.

Second slice:

1. Safe commit for manual/paste records
2. SourceRef creation
3. Policy evaluation stub
4. Audit without raw

Third slice:

1. Netflix CSV parser
2. Browser bookmark parser
3. LINE text parser with summary-only default

## Non-negotiable Gates

Do not implement API connectors before:

- Import Preview exists.
- Policy evaluation exists.
- token encryption plan exists.
- source adapter interface exists.

Do not implement LINE bulk import before:

- summary-only default exists.
- third-party raw policy exists.
- Evidence Package Blocker exists.

Do not implement Export from imports before:

- Export Safety and Re-authentication design is implemented.

## Open Questions

Non-blocking:

- exact DB schema names
- frontend framework details
- whether ImportJob raw temp data is in object storage or DB
- retention period for uncommitted raw import files
- final OAuth provider implementation

Blocking before production:

- token encryption and rotation
- raw temporary storage retention
- ImportJob deletion/cancellation semantics
- rate limits for APIs
- terms review for service APIs
- privacy policy wording

## 結論

Import実装は、まずUniversal Paste + Previewから入る。

API connectorsはその後。

拡張子ごとの分岐ではなく、Source Adapter + Parser Registry + Detector + Import Preview + Policyで作る。

これで、Sランクサービスを安全に、かつユーザーのやる気が出る順に実装できる。
