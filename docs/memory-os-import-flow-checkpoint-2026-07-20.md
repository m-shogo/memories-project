# Memory OS Supervised Import Flow Checkpoint

最終更新: 2026-07-20

## Verdict

```txt
supervised import flow (fetch → parse → seal → verify → decode → commit):
COMPOSED AND LIVE-TESTED END TO END

executable HTTP server / session issuer / clients:
NOT IMPLEMENTED

production:
NO-GO
```

Every security boundary built in the previous checkpoints now runs as **one flow** against live PostgreSQL 16 and MinIO — the first complete production-shaped import path, still without any HTTP surface.

## Implemented files

```txt
services/import-api/internal/importflow/flow.go
services/import-api/internal/importflow/flow_linux_test.go
services/import-api/internal/objectstore/client.go        (GetObjectVersion, ProvisionVersionedBucket)
services/import-api/internal/previewspool/records_linux.go (CollectSealedRecords)
services/import-api/internal/previewspool/records_unsupported.go
```

## The composed flow

```txt
HEAD recheck: current object version/length/checksum must equal the binding
→ version-pinned GET into a private exclusive 0600 scratch file
  (streaming length + SHA-256 verification; over-length data rejected)
→ supervised transaction-free parse (parsersup) into a bounded spool
→ durable fsync / no-replace seal
→ independent decode / re-count / re-hash verification (previewspool.Verifier)
→ sealed-evidence cross-check against the supervisor's evidence
→ CollectSealedRecords: streams re-read with verifier safety checks and the
  recomputed evidence must equal the verified evidence byte for byte
→ interim canonical-record decode (sourceRow ordering/uniqueness, IMPORT_* codes)
→ one short atomic commit (previewcommit) → COMMIT or full ROLLBACK
```

The downloaded source copy is always removed; a committed attempt's sealed spool is left to the TTL reconciler (bounded by the seal expiry). A **newer object version than the binding fails closed** (`ErrSourceBindingMismatch`) — the quarantine object must not change between scan and import.

## Interim canonical-record contract

Pending the reviewed adapter record contract, the flow decodes records as JSON objects carrying a 1-based `sourceRow` (strictly increasing per stream, globally unique); rejected records additionally carry only `IMPORT_[A-Z0-9_]+` issue codes. Anything else is `ErrCanonicalRecordInvalid` and nothing reaches the database. This rule is explicitly interim and is superseded by the reviewed contract when it lands.

## Live evidence (6 end-to-end tests + GET pinning)

- happy path: uploaded source → committed Preview with exact candidate/rejection rows, job `preview_ready`, and the bound object version stored on the ready row;
- re-parse with a new spool attempt returns the one committed Preview (idempotent across attempts);
- current-version drift after binding fails closed with no durable state and no spool residue;
- checksum-mismatched bindings fail closed;
- worker failure cleans up completely (no DB rows, no spool entry);
- invalid canonical records stop the flow before any database work;
- `GetObjectVersion` proven on MinIO: version-pinned bytes, checksum/length divergence rejected, missing versions rejected.

Concurrency finding: migration 001's role DDL is cluster-wide, so parallel test packages serialize migration application on one PostgreSQL advisory lock, and the flow package provisions its own database (`memory_os_importflow`).

## Validation language

```txt
local golang:1.23 + postgres:16 + minio (fresh), exact HEAD 5c3dc4bc2179800c8530961a773963f96797f4d5:
gofmt clean + go vet + go test ./... + go test -race ./... (17 packages,
all live suites included) + both 5s fuzz smokes PASS

remote workflows (pushed HEAD 381c514):
Import API Security Slice run 29793196253 SUCCESS
(importflow live suite 11.579s executed under race, plus non-race parsersup bounds step)
Security Contracts run 29793196257 SUCCESS
```

## Residual risks

- the interim canonical-record contract is not the reviewed adapter contract;
- committed attempts rely on the TTL reconciler for spool removal (bounded ≤ seal TTL);
- flow composition runs in-process; production job orchestration (queue, retry policy, deletion-fence recheck timing) is not designed here;
- no executable server, session issuance or clients.

## Immediate next task

```txt
Design-first: reviewed canonical adapter record contract
(schema + fixtures + validator) binding genericcsv output to the flow decode,
then wire the real adapter through the supervised worker.
```

Do not add executable-server or client wiring in that checkpoint.

## Checkpoint after that

A minimal CLI harness over this package (`internal/importflow`) — point it at a
local CSV file and the `scripts/dev-up.sh` stack, print the committed Preview
to the terminal. This is the first checkpoint that produces a visible,
runnable result; it exists to close the feedback loop before investing in an
HTTP server, and its logic carries forward unchanged into the executable API
checkpoint.
