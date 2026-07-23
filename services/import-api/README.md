# Memory OS Import API — Security Vertical Slice

This Go module is the first executable backend security slice for Capture / Import.

It is intentionally incomplete. It does not expose a production server and must not be described as a production backend.

## Implemented reference and boundary code

- verified-principal/request-context boundary;
- fixed PostgreSQL role allowlist and transaction-local account ID/epoch setup;
- Apple RS256 identity-token verification and bounded JWKS cache;
- authorization-code/replay/account-binding interfaces;
- signed quarantine-upload core and strict handlers;
- exact owner/epoch/job/key/size/checksum/type/expiry/version bindings;
- bounded Generic CSV parser and synchronous sticky iterator;
- canonical parser-options SHA-256 binding;
- synchronous CSV-to-Preview bridge without goroutines/channels;
- safe rejected-row records and Preview v2 hashes;
- reference AtomicMaterializer and Apply interfaces;
- account epoch guards and CSV/JWT fuzz targets;
- Linux Preview spool filesystem lifecycle;
- bounded accepted/rejected stream writer;
- stream fsync and durable no-replace manifest publication;
- independent sealed-spool decode/count/re-hash verifier;
- startup crash-residue reconciliation and TTL cleanup;
- atomic Preview commit repository against live PostgreSQL;
- SDK-free SigV4 quarantine object store adapter against live MinIO;
- prlimit-bounded digest-pinned parser worker supervision;
- supervised import flow composed end to end (fetch → parse → verify → commit) against live PostgreSQL and MinIO;
- canonical adapter record contract with cross-language fixture enforcement;
- real Generic CSV adapter emitting canonical records inside the supervised worker;
- importctl harness and separate parser-worker binary: the first visible end-to-end run.

## Preview spool contract

```txt
docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json
docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json
scripts/validate-memory-os-preview-spool.py
```

The contract binds one server-generated attempt, exact source/adapter/options evidence, fixed stream formats, counts, bytes, hashes and a maximum 24-hour TTL. It forbids path fields, symlink following, cross-attempt reuse, backup eligibility and database transactions during parsing.

## Filesystem and bounded writer

Implemented under `internal/previewspool`:

- Linux strong implementation; non-Linux fails closed;
- canonical supervisor-owned exact-`0700` root;
- descriptor-relative `mkdirat/openat`;
- fixed `0600` entries with `O_EXCL/O_NOFOLLOW`;
- type/owner/mode/link and attempt-inode checks;
- cancellation cleanup and unknown-entry fail-closed behavior;
- accepted/rejected records as `8-byte big-endian length + canonical bytes`;
- 100,000 aggregate records, 512 MiB aggregate bytes and 2 MiB per record;
- exact-file-byte SHA-256;
- sticky cancellation, limit, short-write, `ENOSPC` and lifecycle failures;
- no partial writer resume.

## Seal and manifest publication

Implemented:

```txt
accepted.spool fsync
→ rejected.spool fsync
→ close both streams
→ create exclusive manifest.tmp (0600 / no-follow)
→ write deterministic compact JSON
→ fsync manifest.tmp
→ linkat no-replace publication as manifest.json
→ unlink manifest.tmp
→ fsync attempt directory
```

An ordinary rename is not used because it can overwrite an existing final name. Existing `manifest.json` or `manifest.tmp` entries are rejected.

Handled failures publish no final manifest. Directory-fsync failure rolls back the final name; inability to prove rollback durability produces `ErrSealDurabilityUncertain` and requires reconciliation.

## Independent sealed-spool verifier

Implemented:

```txt
verified root descriptor
→ descriptor-relative O_NOFOLLOW attempt open (0700 / owner checked)
→ fixed-name allowlist; manifest.tmp residue and unknown entries reject
→ manifest.json regular / 0600 / single link / bounded size
→ strict single-value JSON decode, unknown fields forbidden
→ canonical re-serialization equality against the seal builder
→ expiry check against the caller clock
→ exact job/owner/epoch/source/adapter/options expectation match
→ streams re-opened O_NOFOLLOW, regular / 0600 / single link
→ bounded length-prefix re-decode with record/byte limits enforced while reading
→ independent re-count and exact-byte SHA-256
→ recomputed evidence must equal every manifest stream binding
```

Verification is read-only, stateless and retryable; it deletes nothing and performs no database work. Truncation, appended records, torn appends, zero/oversized length prefixes and same-length content substitution are all rejected before any commit path can start.

## Startup reconciliation and TTL cleanup

Implemented in `previewspool.Reconciler`: a single exclusive startup pass that classifies every root entry (sealed / unsealed / temp residue / completed publication / unknown), removes only fixed-name crash residue and expired sealed attempts, completes the linkat-publication crash window when both names share one inode, quarantines everything unclassifiable in place, and never deletes a sealed unexpired attempt. A cancelled pass is safe to re-run.

Detailed evidence:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-verifier-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-reconciliation-checkpoint-2026-07-18.md
```

## Atomic Preview commit repository

Implemented in `internal/previewcommit` (pgx v5, live-tested):

```txt
BEGIN
→ SET LOCAL ROLE memory_worker_runtime + owner/epoch context
→ idempotent-retry check on the deterministic commit key
→ verify job binding and preview_building state under FORCE RLS
→ insert preview_ready (claims the commit key)
→ parameterized bulk-insert candidates and rejections
→ assert_preview_complete
→ mark the job preview_ready → COMMIT, full ROLLBACK on any error
```

PostgreSQL forbids `COPY FROM` under row-level security, so bulk loading uses the contract-allowed equivalent: one parameterized `INSERT ... SELECT FROM unnest(...)` per stream with FORCE RLS in force. The deterministic commit key excludes the spool attempt ID, so an identical re-parse returns the committed Preview; a conflicting retry is rejected. Live tests (gated on `MEMORY_OS_TEST_DATABASE_URL`, self-applying migrations 001–003) prove atomicity, retry, rollback and the full spool → seal → verify → commit flow.

## Quarantine object storage adapter

Implemented in `internal/objectstore` (no SDK; SigV4 on the standard library, pinned to the documented AWS test vector):

- presigned PUT whose signature covers `content-length`, `content-type` and `x-amz-checksum-sha256` as signed headers, so the store itself rejects altered or missing bindings and substituted content;
- exact `quarantine/{job}/{upload}` keys with dot-segment rejection; 15-minute presign cap;
- SigV4-signed HEAD with checksum mode returning the exact version ID, ETag, length, type and hex SHA-256;
- live MinIO tests (gated on `MEMORY_OS_TEST_S3_ENDPOINT`) prove the round trip, per-upload version IDs on a versioned bucket, tamper/expiry rejection and not-found handling.

## Isolated parser supervision

Implemented in `internal/parsersup` (Linux; non-Linux fails closed): the supervisor verifies the pinned worker SHA-256, spawns the worker in its own process group with an explicit credential-free environment (credential-shaped names rejected), applies `prlimit64` AS/CPU/NOFILE/`FSIZE=0`/`CORE=0` before consuming output, streams tagged length-prefixed frames synchronously into the bounded spool writer under wall-clock and output caps, seals on clean exit and kills + fail-closed-cleans on any violation, crash or timeout. The worker holds no spool, database, storage or credential handles. Network-namespace isolation is deployment work and is not claimed. Twelve targeted tests cover digest mismatch, env minimality, memory/CPU/file-write kills, timeout, protocol violations, output caps and end-to-end seal + independent verification.

## Supervised import flow

Implemented in `internal/importflow`, composing every boundary above into one flow with no HTTP surface:

```txt
HEAD recheck (current object version/length/checksum must equal the binding)
→ version-pinned GET into a private exclusive scratch file
  (streaming length + SHA-256 verification via objectstore.GetObjectVersion)
→ supervised transaction-free parse (parsersup) into a sealed spool
→ independent decode/count/re-hash verification (previewspool.Verifier)
→ sealed-evidence cross-check against the supervisor's own evidence
→ CollectSealedRecords re-reads the verified streams under the same safety checks
→ canonical record decode (internal/canonrecord: strict bytes, fingerprint,
  stream/type agreement, sourceRow ordering/uniqueness)
→ one short atomic commit (previewcommit) → COMMIT or full ROLLBACK
```

A newer object version than the binding, a checksum mismatch, a worker crash or an invalid canonical record all fail closed with no durable database state and no spool residue. Six live end-to-end tests (gated on `MEMORY_OS_TEST_DATABASE_URL` + `MEMORY_OS_TEST_S3_ENDPOINT`) prove the happy path, idempotent re-parse, version-drift rejection, checksum-mismatch rejection, worker-crash cleanup and invalid-record rejection against live PostgreSQL and MinIO.

Records are governed by the canonical adapter record contract (`docs/schemas/memory-os-security/preview-canonical-record.v1.schema.json`): the frame payload bytes must equal the deterministic Go serialization, candidate fingerprints are recomputed on decode, and rejection records structurally cannot carry raw user values. The shared 22-case fixture is enforced by both `internal/canonrecord` tests and `scripts/validate-memory-os-canonical-records.py`, and `internal/csvworker` runs the real Generic CSV adapter through the supervised worker in the end-to-end tests.

## importctl harness (cmd/importctl, cmd/parser-worker)

The first visible end-to-end run, and a development tool only: `scripts/dev-import.sh` builds the separate digest-pinned `parser-worker` binary plus `importctl`, then imports a local CSV through the full supervised pipeline against the `scripts/dev-up.sh` stack and prints the committed Preview (candidates, rejections, counts, job state). The harness computes the worker digest when no pin is supplied and labels it as not a reviewed pin; a mismatched pin refuses to run. It connects as the dev stack's superuser for read-back (RLS does not bind superusers) and must never target production. Four live tests cover the full CLI path, the one-preview-per-job conflict, configuration validation and pin mismatch.

## Critical production boundary

`preview.AtomicMaterializer` parses inside its transaction callback. It remains reference-only and must not be connected to production PostgreSQL for untrusted imports; `internal/importflow` is the production-shaped replacement, though it still runs the harness worker rather than a reviewed adapter artifact.

## Not implemented

- executable HTTP server/session issuer;
- Apple code exchange/secret rotation and concrete replay/session stores;
- a reviewed worker-artifact registry (the binary exists; its pin is operator-supplied);
- network-namespace/seccomp/container deployment evidence for the parser supervisor;
- production TLS/scoped-credential/lifecycle deployment evidence for object storage;
- concrete Apply/Memory persistence and complete deletion fencing;
- iOS and Desktop Portal clients.

## Validation

```txt
exact repository-integrated Go suite
(code HEAD 80c3b4ecdfe67a7d79a0ec71a51e3a7c5c9bb41a, local golang:1.23 Linux container + fresh postgres:16 + MinIO):
gofmt clean + go vet + go build ./cmd/... + go test ./... + go test -race ./... (20 packages,
live DB/object-store/supervision/flow/CLI suites included) + both 5s fuzz smokes PASS

Preview spool contract validator:
PASS

remote workflows:
recorded after the push completes
```

Earlier remote Import API runs had failed at the Format check; five unformatted sources and one pointer-receiver compile error in `internal/upload/service_test.go` were repaired at the verifier checkpoint, and the branch has run green since.

Local iteration against live PostgreSQL/MinIO no longer requires hand-typed Docker commands:

```bash
# repository root
scripts/dev-up.sh                # start postgres + minio, wait for health
scripts/dev-test.sh -race ./...  # go test in a golang container on the same network
scripts/dev-down.sh              # tear the stack down
```

Re-run against the exact current HEAD:

```bash
# repository root
python scripts/validate-memory-os-preview-spool.py

# services/import-api
test -z "$(gofmt -l .)"
go test ./...
go vet ./...
go test -race ./...

GOMAXPROCS=4 go test -run='^$' -fuzz=FuzzParserNeverPanicsOrExpandsLimits -fuzztime=5s -timeout=30s ./internal/adapters/genericcsv
GOMAXPROCS=4 go test -run='^$' -fuzz=FuzzParseCompactTokenNeverPanics -fuzztime=5s -timeout=30s ./internal/appleauth
```

Do not record current-HEAD `PASS` until those commands and remote workflows run on that exact commit.
