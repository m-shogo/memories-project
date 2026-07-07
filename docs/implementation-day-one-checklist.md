# Implementation Day One Checklist

## 目的

この文書は、Memory OS の設計フェーズから実装フェーズへ移る最初の日に、何を作り、何を作らないかを固定するためのchecklistである。

実装初日にやることを間違えると、後から安全性・DB・Import・Exportが崩れる。

## Day One Verdict

```txt
Go for fixture + foundation only.
No-Go for production import/save/API/export/embedding.
```

## Day One Goals

作る:

- synthetic fixtures directory skeleton
- first 10 fixture files
- expected detection/preview/policy snapshots
- fixture lint placeholder
- first migration slice draft
- RLS negative test skeleton
- SecurityGate v0
- ParserRegistry v0
- Detector confidence v0
- Preview DTO v0

作らない:

- memory_record保存
- source_item/user_activity本保存
- API connector
- OAuth provider connection
- Export package
- Embedding
- OCR
- persona activation
- LINE bulk import

## Step 1: Fixture Skeleton

Create:

```txt
fixtures/import/security/
fixtures/import/universal/
fixtures/import/streaming/
fixtures/import/anime-manga/
fixtures/import/restaurant/
fixtures/import/audio/
fixtures/import/message/
fixtures/import/media/
fixtures/import/persona/
fixtures/import/expected/
```

First files:

```txt
security/unsafe-url-schemes.txt
universal/title-list-basic.txt
universal/url-list-basic.txt
streaming/netflix-viewing-activity-standard.csv
anime-manga/manga-progress-list.txt
restaurant/tabelog-url-list.txt
audio/gera-episode-list.txt
message/line-copy-selected.txt
media/photo-with-exif.meta.json
persona/character-card.json
```

Expected snapshots:

```txt
expected/<fixture-id>.detection.json
expected/<fixture-id>.preview.json
expected/<fixture-id>.policy.json
```

## Step 2: Fixture Lint

Minimum lint rules:

- deny token-like patterns.
- deny real email-like patterns unless `.example.test`.
- deny phone-number-like patterns.
- deny non-example private domains.
- deny `simulationAllowed: true`.
- deny raw private title in expected snapshot.
- deny raw chat text in expected snapshot.

Day one lint can be simple but must exist.

## Step 3: First Migration Slice Draft

Create migration draft for:

```txt
app_user
source_ref
source_account_ref
import_job
import_input_file
import_detection_result
import_preview
import_preview_candidate
raw_object_ref
dedupe_key
deletion_tombstone
policy_decision
lifecycle_event
audit_event
outbox_event
key_reference
oauth_connection
```

Day one does not need production DB connection if project setup is not ready.

But schema draft must include:

- user_id
- key_algorithm/key_version for dedupe/tombstone
- raw retention/expiration fields
- privacy/export/AI defaults
- created_at/deleted_at

## Step 4: RLS Negative Test Skeleton

Create tests for:

- user B cannot read user A import_preview_candidate.
- missing current user fails closed.
- support role cannot see raw/private title.

Day one may use pseudo DB test if DB infra not ready.

But test names and expected behavior must exist.

## Step 5: SecurityGate v0

Implement only:

- max text size
- unsafe URL scheme detection
- HTML/SVG no raw render flag
- control character neutralization for display
- raw log ban helper

Do not implement:

- OCR
- antivirus
- full archive extraction

## Step 6: ParserRegistry v0

Implement:

- register parser metadata.
- list parsers by medium.
- select by user source + detector hints.
- return confidence.

First registered parser stubs:

```txt
line-based-title-list-parser
url-list-parser
table-like-history-parser
progress-list-parser
```

## Step 7: Detector Confidence v0

Implement:

- URL majority detection.
- known CSV header detection for Netflix fixture.
- progress pattern detection.
- chat timestamp/speaker detection.
- persona character-card JSON detection.
- image meta JSON detection.

Do not implement:

- high-risk auto commit.
- source selection by extension only.

## Step 8: Import Preview DTO v0

Implement DTO only.

```ts
interface ImportPreviewSummary {
  candidateCount: number;
  selectedByDefault: number;
  sensitiveCount: number;
  restrictedCount: number;
  lowConfidenceCount: number;
  duplicateCandidateCount: number;
  blockedCount: number;
}
```

```ts
interface ImportPreviewCandidate {
  id: string;
  medium: string;
  sourceId?: string;
  title?: string;
  url?: string;
  occurredAtText?: string;
  occurredAtPrecision: string;
  privacyLevel: string;
  aiAnalysisDefault: 'off';
  exportDefault: 'included' | 'excluded';
  selected: boolean;
  confidence: string;
  warnings: string[];
  simulationAllowed?: false;
}
```

## Step 9: Preview-only Golden Test

One golden flow:

```txt
title-list-basic.txt
→ detection low/title_list
→ preview 4 candidates
→ no save
→ policy preview_only
```

Second golden flow:

```txt
line-copy-selected.txt
→ detection message_conversation_context
→ preview 1 restricted summary candidate
→ rawStored=false
→ export excluded
→ no save
```

## Day One Acceptance Criteria

- first 10 fixtures exist.
- expected snapshots exist.
- fixture lint exists.
- SecurityGate rejects unsafe URL fixture.
- ParserRegistry can register parser stubs.
- Detector produces expected confidence for at least title/url/LINE/persona/image fixtures.
- Import Preview DTO can represent candidates.
- no memory_record/source_item/user_activity save path exists.
- no API/OAuth connector is implemented.

## Day One No-Go Checklist

Stop if any are true:

- real user data enters fixture.
- raw chat appears in expected snapshot.
- SecurityGate logs raw input.
- persona fixture sets simulationAllowed=true.
- LINE fixture creates raw export allowed.
- Preview code writes final records.
- API connector is started before token/OAuth foundation.

## Day Two Direction

Only after Day One passes:

1. add first migration slice real DB migration.
2. implement RLS negative tests against DB.
3. implement title/url/progress parsers fully.
4. render mobile Preview cards.
5. add Dedupe/Tombstone preview checks.

## 結論

実装初日は、機能を作る日ではなく、壊れない実装順を証明する日である。

最初にfixtures、SecurityGate、ParserRegistry、Detector、Preview DTOを作る。

保存・API・Export・Embeddingはまだ作らない。
