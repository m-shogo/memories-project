# Memory OS Capture / Import Implementation Architecture — Round 8

最終更新: 2026-07-15

## Decision

Capture / Importは、iOS・Desktop Portal・backendへparserを分散させない。

```txt
iOS Quick Capture
+iOS File Intake
+Desktop Web Import Portal
        ↓
versioned Import Job API
        ↓
one canonical adapter / parser / dedupe / preview / apply pipeline
```

Binding implementation choice:

```txt
canonical product client:
Swift 6 + SwiftUI

local intake and confirmed cache:
GRDB / SQLite

bulk import authority:
Go Import Service

metadata and revisions:
PostgreSQL

raw archive and attachment staging:
S3-compatible object storage

Desktop Portal:
Vite + React + TypeScript thin client
```

The Portal is not a second product application. It does not own parser logic, confirmed Memory state, search, shelves or Memory Town.

---

# 1. Why this shape

A naive implementation creates three parser implementations:

```txt
Swift parser
+ browser TypeScript parser
+ Go server parser
```

This is prohibited because it creates:

- adapter-version drift
- different duplicate decisions
- preview / apply mismatch
- three security review surfaces
- three archive implementations
- three bug-fix paths
- inconsistent recovery behavior

Instead:

```txt
clients collect and upload
server parses and normalizes
clients display preview
server applies confirmed preview
```

Small URL / text capture may be normalized locally for immediate UX, but server normalization remains idempotent and compatible.

---

# 2. Repository topology candidate

```txt
apps/
  ios/
    MemoryOS.xcodeproj
    App/
    ShareExtension/
    Packages/
      MemoryCore/
      CaptureContracts/
      LocalDatabase/
      APIClient/
      TownDomain/
      TownRenderer/

  import-portal/
    src/
    public/

services/
  api/
    cmd/api/
    cmd/import-worker/
    internal/auth/
    internal/importjobs/
    internal/importadapters/
    internal/importpreview/
    internal/importapply/
    internal/sync/
    internal/storage/

contracts/
  openapi/
  json-schema/
  fixtures/

infra/
  migrations/
  local-dev/
```

Do not create separate repositories before build, ownership and deployment pressure justify them.

---

# 3. One import pipeline

All file-based surfaces converge here.

```txt
1. Intake created
2. Upload authorized
3. Raw file quarantined
4. File safety scan
5. Source adapter detection
6. Parse into normalized candidates
7. Duplicate analysis
8. Preview materialized
9. Explicit confirmation
10. Atomic apply
11. Sync to iOS
12. Raw file expiry / deletion
```

## 3.1 Import Job state machine

```txt
created
→ awaiting_upload
→ uploaded
→ quarantined
→ scanning
→ detecting_source
→ parsing
→ preview_ready
→ awaiting_confirmation
→ applying
→ applied
```

Failure / terminal states:

```txt
rejected
failed_retryable
failed_terminal
cancelled
expired
superseded
```

Rules:

- state transition is server-authoritative
- transitions are append-audited without Memory body content
- retry does not create a new confirmed Memory record
- cancelled / expired jobs cannot be confirmed
- parser version change invalidates an old preview
- confirmation must reference the exact preview hash

---

# 4. Surface-specific implementation

## 4.1 iOS Quick Capture

Inputs:

- URL
- plain text
- URL + selected text
- one image / screenshot

Flow:

```txt
MemoryShare.appex
→ NSItemProvider / UTType validation
→ App Group staged file
→ minimal GRDB ShareIntake row
→ extension completes
→ main app opens Import Preview
→ user confirms
→ local Memory transaction
→ sync outbox
```

The Share Extension must remain small.

It links only extension-safe packages:

```txt
CaptureContracts
ShareIntakeStore
FileValidation
SecureKeyAccess
```

It does not link:

- Town renderer
- search UI
- full sync engine
- AI client
- large import adapters
- database migrations beyond intake-safe schema checks

## 4.2 iOS File Intake

Flow:

```txt
SwiftUI fileImporter
→ security-scoped file access
→ local size / type preflight
→ create Import Job
→ request upload URL
→ background upload
→ server parse
→ preview in iOS
→ explicit confirmation
```

The iOS app does not fully expand arbitrary ZIP files in P0.

Local preflight may inspect:

- filename
- size
- declared UTType
- magic bytes
- simple uncompressed JSON / CSV header sample

Canonical archive extraction and service-specific parsing occur in the isolated server worker.

## 4.3 Desktop Web Import Portal

Technology:

```txt
Vite
+ React
+ TypeScript
```

Reason:

- drag and drop
- large preview table
- column mapping
- rejected-row display
- resumable / multipart upload UI
- no need for SSR or a second application server

The Portal is a static client served from CDN or the Go service.

It calls the same Import Job API used by iOS.

It does not contain:

- source-specific parser implementations
- duplicate authority
- final Memory apply logic
- persistent private browser database
- unrestricted Memory read APIs

---

# 5. PC pairing implementation

Preferred P0 flow:

```txt
iOS app
→ POST /v1/import-pairing-sessions
→ receives short-lived session + QR payload

Desktop Portal
→ opens pairing URL
→ receives upload-scoped browser token
→ uploads file
→ watches import job status

After preview_ready
→ iOS receives refresh / notification
→ iOS shows final preview
→ iOS confirms
```

Pairing token properties:

- short-lived
- one account
- one import scope
- one-use or tightly limited reuse
- cannot search Memory
- cannot fetch full existing records
- cannot confirm final apply in P0
- revocable from iOS
- invalid after account deletion or device unlink

Do not put long-lived account credentials in the QR payload.

---

# 6. Upload path

Do not proxy large archive bytes through the Go API process.

```txt
client
→ asks Go API for upload authorization
→ uploads directly to object storage
→ Go API verifies completion metadata
→ worker reads quarantined object
```

Initial implementation:

- simple signed single-object upload for bounded P0 sizes
- multipart upload only after larger limits are approved
- checksum required
- object key generated by server
- user filename stored separately as untrusted metadata

Raw upload objects never become confirmed attachment objects by renaming alone.

```txt
quarantine object
!=
confirmed retained object
```

---

# 7. Backend implementation

## 7.1 Go API

Recommended minimal stack:

```txt
net/http or a small router
pgx
sqlc
OpenAPI
structured logging
```

Do not begin with a large service framework.

## 7.2 Import worker

Start with a PostgreSQL-backed job queue.

```txt
import_job
import_job_attempt
import_job_event
```

Worker claim uses transactional row locking.

Do not add Kafka, RabbitMQ or Redis only to run the first import workers.

A separate queue may be introduced after measured throughput or isolation needs.

## 7.3 Adapter interface

```go
type ImportAdapter interface {
    ID() string
    Version() string
    Detect(ctx context.Context, sample FileSample) DetectionResult
    Parse(ctx context.Context, input QuarantinedInput, emit CandidateEmitter) error
    DuplicateKeys(candidate NormalizedCandidate) []DuplicateKey
    PreviewMetadata() AdapterPreviewMetadata
}
```

Adapters must be deterministic for the same:

```txt
adapter ID
+ adapter version
+ canonical input hash
+ parsing options
```

## 7.4 Initial adapters

Implementation order:

```txt
1. Generic CSV
2. Generic JSON array
3. Memory OS export package
4. first service-specific adapter
5. second service-specific adapter
```

Do not implement every named service before the generic pipeline works.

---

# 8. Preview / apply integrity

Preview is a materialized, versioned object.

```txt
ImportPreview
- previewId
- importJobId
- adapterId
- adapterVersion
- sourceObjectHash
- optionsHash
- candidateCount
- duplicateCount
- rejectedCount
- warnings
- previewHash
- expiresAt
```

Confirmation request includes:

```txt
previewId
previewHash
idempotencyKey
selected duplicate strategy
explicit user choices
```

The server rejects confirmation when:

- source object changed
- adapter version changed
- parsing options changed
- preview expired
- account changed
- job was cancelled
- preview hash mismatches

Apply is one logical transaction with recoverable chunking for very large imports.

No parser result may be silently re-evaluated between Preview and Apply.

---

# 9. Duplicate strategy

Preferred key order:

```txt
1. source + external account scope + external stable ID
2. source + canonical URL + source timestamp
3. source + normalized title + normalized timestamp
4. content fingerprint fallback
```

User-visible options:

- skip existing
- update only safe mutable fields
- keep both
- decide selected conflicts

Never merge two records only because an embedding similarity score is high.

Bulk duplicate decisions must be previewable and exportable as a report.

---

# 10. Local iOS database boundary

GRDB tables needed before UI implementation:

```txt
share_intake
staged_attachment
local_memory_record
local_memory_source
sync_outbox
sync_inbox_cursor
import_job_reference
import_preview_summary
```

The full bulk candidate set does not need to be copied into local SQLite before confirmation.

Store locally:

- summary counts
- paged preview cache as needed
- user decisions
- confirmed records after sync

The server remains the bulk parsing authority.

---

# 11. Security minimum

Before accepting ZIP / JSON / CSV:

- compressed size limit
- expanded size limit
- archive entry limit
- nesting limit
- compression-ratio limit
- path traversal rejection
- absolute path rejection
- symbolic link rejection
- magic-byte / MIME / extension cross-check
- JSON nesting / token / field-size limits
- CSV row / column / cell-size limits
- spreadsheet formula neutralization in downloadable reports
- parser network disabled by default
- parser CPU and wall-clock budget
- memory limit
- raw file expiry
- cancellation cleanup
- deletion fence

Parsers run outside the public API process.

---

# 12. Failure recovery

## Upload interrupted

```txt
job remains awaiting_upload or uploaded_partial
→ client resumes or cancels
```

## Extension terminated

```txt
staged file + intake transaction already exist
→ main app recovers on next launch
```

## Parser crash

```txt
attempt marked failed
→ bounded retry
→ same job and input hash
```

## App confirms twice

```txt
same idempotency key
→ same apply result
```

## App deleted during pending import

```txt
server job remains unconfirmed
→ expires and raw object is deleted
```

## Account deletion

Delete or invalidate:

- pending jobs
- pairing sessions
- upload tokens
- quarantined objects
- preview materializations
- background transfer manifests
- local App Group intake files

---

# 13. What not to build first

Do not begin with:

- all service adapters
- local-only ZIP parser parity
- browser-side parser engine
- Web shelves
- Web Memory Town
- generic AI schema inference for arbitrary archives
- Kafka / Redis infrastructure
- direct multipart upload for unlimited files
- automatic confirmation
- cross-platform client framework

---

# 14. Correct implementation sequence

```txt
P0-A Contracts
1. Import Job state schema
2. Import Preview / confirmation schema
3. adapter manifest and interface
4. upload quarantine contract
5. pairing session contract
6. deletion / expiry contract

P0-B Backend vertical slice
7. Go Import Job API
8. PostgreSQL job tables
9. object-storage quarantine upload
10. one worker
11. Generic CSV adapter
12. preview + idempotent apply

P0-C iOS capture
13. Share Extension URL / text
14. App Group intake recovery
15. main-app Preview
16. GRDB outbox sync

P0-D File migration
17. iOS fileImporter upload
18. Generic JSON adapter
19. Memory OS export adapter
20. duplicate preview

P0-E Desktop Portal
21. one-time pairing
22. drag-and-drop upload
23. progress / cancellation
24. preview summary
25. iOS final confirmation

Only after end-to-end Capture / Import evidence:
26. TownSceneSnapshot Swift models
27. SpriteKit static Town prototype
```

---

# 15. Implementation readiness verdict

```txt
architecture:
defined

single parser authority:
locked

server import vertical slice:
not implemented

iOS Share vertical slice:
not implemented

iOS file intake:
not implemented

Desktop Portal:
not implemented

Memory Town implementation priority:
blocked behind Capture / Import vertical slice
```

Implementation is authorized only as small vertical slices, not as parallel full-product construction.
