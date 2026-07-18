# Memory OS Preview Commit Repository Checkpoint

最終更新: 2026-07-19

## Verdict

```txt
Preview spool package (filesystem / writer / seal / verifier / reconciliation):
PARTIAL IMPLEMENTATION

production Preview PostgreSQL domain schema:
CREATED (SQL + live SQL tests)

atomic Preview commit repository (Go ↔ PostgreSQL):
PARTIAL IMPLEMENTATION CREATED

executable server / object storage / parser supervisor / clients:
NOT IMPLEMENTED

production:
NO-GO
```

This checkpoint closes Gate 5's core: the first real Go↔PostgreSQL production-shaped path, from independently verified spool evidence to one short atomic commit transaction, with retry and rollback proven against live PostgreSQL 16.

## Implemented files

```txt
services/import-api/internal/previewcommit/commitkey.go
services/import-api/internal/previewcommit/committer.go
services/import-api/internal/previewcommit/commitkey_test.go
services/import-api/internal/previewcommit/committer_db_test.go
services/import-api/internal/previewcommit/committer_e2e_linux_test.go
services/import-api/go.mod / go.sum (github.com/jackc/pgx/v5 v5.7.6)
.github/workflows/import-api-security-slice.yml (postgres:16 service)
```

## Commit transaction

```txt
BEGIN
→ SET LOCAL ROLE memory_worker_runtime
→ SET LOCAL app.current_account_id / app.current_account_epoch
→ idempotent-retry check on the deterministic commit key
→ verify import job binding and preview_building state under FORCE RLS
→ insert preview_ready (claims the commit key; parent first for the composite FK)
→ parameterized bulk-insert preview_candidate rows
→ parameterized bulk-insert preview_rejection rows
→ SELECT memory_os.assert_preview_complete(preview_id)
→ conditional UPDATE import_job → preview_ready
→ COMMIT — any error is a full ROLLBACK with no durable state
```

The committer accepts only `previewspool.VerifiedSpool` evidence plus decoded rows; it never parses source content and validates row counts and TTL expiry before opening the transaction.

### COPY FROM finding

PostgreSQL **rejects `COPY FROM` on tables with row-level security** (`0A000`). The commit contract explicitly allows "an equivalent parameterized protocol", so bulk loading is one parameterized `INSERT ... SELECT FROM unnest(...)` statement per stream, executed as the worker role with FORCE RLS in force. Disabling or bypassing RLS for COPY was rejected as an option.

## Deterministic commit key

`DeriveCommitKey` binds owner, epoch, job, source key/version/length/checksum, adapter identity/artifact, options digest and both stream counts/hashes. The spool attempt ID is deliberately excluded so an identical re-parse in a new attempt reaches the idempotent path. `DerivePreviewHash` is the domain-separated final Preview hash including both stream hashes and counts.

Retry semantics proven on live PostgreSQL:

- same key → returns the existing committed Preview (`AlreadyCommitted`), also after the job already moved to `preview_ready` (post-COMMIT acknowledgement-loss recovery);
- different key for the same job → `ErrCommitConflict`;
- concurrent duplicate inserts surface as unique violations mapped to `ErrCommitConflict`, and a retry then takes the idempotent path.

## Live tests

9 top-level tests (8 gated on `MEMORY_OS_TEST_DATABASE_URL`; the package skips cleanly without it):

- commit key determinism, domain separation and per-field binding (15 mutations + spool-ID exclusion);
- atomic persistence of ready row, candidates, rejections and job state;
- duplicate retry returns the one existing Preview; conflicting retry rejects;
- free-form rejection codes and candidate ordinal gaps roll back everything (job state, zero rows);
- missing job, stale-epoch job and wrong job state reject before any insert;
- input validation (nil pool, invalid preview ID, zero clock, row/evidence mismatch, expired spool);
- Linux end-to-end: real bounded spool write → fsync/no-replace seal → independent verification → commit, with the committed row carrying the recomputed stream evidence.

Test setup applies migrations 001–003 itself, so the Go suite provisions and proves the schema on a fresh database.

## Validation language

```txt
local golang:1.23 + postgres:16-alpine (fresh database), exact HEAD 0f2a86abf93313affcb81b5b12fcf79daddfc09b:
gofmt clean + go vet + go test -race ./... (14 packages, live DB tests included) + both 5s fuzz smokes PASS
package skips cleanly when MEMORY_OS_TEST_DATABASE_URL is unset

remote Import API workflow with the new postgres service
(pushed HEAD a942532, run 29649255941):
SUCCESS — live DB tests executed (not skipped) against the service container
Security Contracts run 29649255942: SUCCESS
```

## Residual risks

- pgx v5.7.6 pinned (v5.10+ requires Go 1.25); dependency updates must re-run the full suite;
- the committer trusts the caller to run `previewspool.Verifier.Verify` in the same flow — the future supervisor composition must wire them together as in the end-to-end test;
- canonical-record JSON schema for candidates is not yet a reviewed contract (adapter output remains untrusted until that contract exists);
- no canonical-epoch/deletion-fence recheck beyond the RLS owner/epoch context (the deletion-fence table integration is not wired);
- no executable server, object storage or parser supervisor.

## Immediate next task

```txt
Implement the signed-upload S3-compatible storage adapter only:
private versioned bucket client (presigned PUT, exact-metadata HEAD)
→ bind owner/epoch/job/key/size/checksum/type/expiry
→ verify object version on completion
→ lifecycle/quarantine rules as configuration evidence
→ integration tests against a local S3-compatible container
```

Do not add parser-container, executable-server or client wiring in that checkpoint.
