# Memory OS Import API — Security Vertical Slice

This Go module is the first executable backend security slice for Capture / Import.

It is intentionally incomplete. It does not expose a production server and must not be described as a production backend.

## Implemented reference and boundary code

- private verified-principal/request-context boundary;
- fixed PostgreSQL role allowlist and transaction-local account ID/epoch setup;
- RS256 Apple identity-token verification and bounded JWKS cache;
- authorization-code/replay/account-binding interfaces;
- signed quarantine-upload authorization core and strict handlers;
- exact owner/epoch/job/key/size/checksum/type/expiry/object-version binding interfaces;
- cryptographically random opaque IDs;
- bounded Generic CSV parser and synchronous sticky iterator;
- canonical parser-options SHA-256 binding;
- synchronous CSV-to-Preview RowEvent bridge without goroutines/channels;
- safe rejected-row records;
- Preview v2 accepted/rejected hash model;
- reference AtomicMaterializer invariant tests;
- iOS-only exact-hash idempotent Apply interfaces;
- account-state/epoch checkpoint guards;
- CSV and Apple compact-JWT fuzz targets;
- Linux Preview spool attempt filesystem lifecycle;
- bounded Preview spool accepted/rejected stream writer.

## Preview spool contract

```txt
docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json
docs/schemas/memory-os-security/preview-spool-semantic-case-set.v1.schema.json
docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-negative-cases.round9.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-semantic-cases.round9.v1.json
scripts/validate-memory-os-preview-spool.py
```

The contract binds one server-generated attempt, exact source/adapter/options evidence, fixed stream formats, counts, byte lengths, hashes and a maximum 24-hour TTL. It forbids manifest path fields, symlink following, cross-attempt reuse, backup eligibility and database transactions during parsing.

## Filesystem checkpoint

Implemented under `internal/previewspool`:

- Linux strong implementation; non-Linux fails closed;
- supervisor-provisioned canonical exact-`0700` root;
- validated single-segment `spoolId`;
- descriptor-relative `mkdirat/openat`;
- `O_CREAT | O_EXCL | O_NOFOLLOW` exact-`0600` fixed entries;
- type/owner/mode/link checks;
- attempt device/inode substitution rejection;
- cancellation cleanup at partial creation stages;
- unknown-entry fail-closed and idempotent successful cleanup.

## Bounded writer checkpoint

Implemented:

- accepted format `memory-os-preview-candidate-v1-length-prefixed`;
- rejected format `memory-os-preview-rejection-v1-length-prefixed`;
- records are `8-byte unsigned big-endian length + canonical bytes`;
- `100,000` aggregate-record limit;
- `512 MiB` aggregate-byte limit;
- `2 MiB` canonical-record limit;
- exact-file-byte SHA-256 including length prefixes;
- SHA-256 of empty bytes for zero rejected rows;
- at least one accepted record before successful close;
- no goroutine/channel;
- sticky cancellation, invalid input, limit, short-write, `ENOSPC`, filesystem and lifecycle errors;
- terminal failures close writable handles and cannot resume;
- exact-once writer claim;
- empty manifest placeholder is removed before stream writing;
- successful close returns evidence but does not fsync, seal or publish a manifest.

Detailed evidence:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
```

## Critical production boundary

`preview.AtomicMaterializer` consumes source rows inside its transaction callback. It is reference-only and must not be connected to production PostgreSQL for untrusted imports.

Required flow:

```txt
version-bound quarantine object
→ isolated transaction-free parser
→ private bounded accepted/rejected spool
→ stream fsync and atomic manifest seal
→ independent decode/count/re-hash
→ epoch and binding recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

## Not implemented

- executable HTTP server/session issuer;
- Apple code-exchange secret signing/rotation;
- concrete replay/account/session repositories;
- production Preview candidate/rejection/ready tables;
- concrete PostgreSQL repositories and `pgx.CopyFrom` path;
- S3-compatible signer/HEAD/lifecycle;
- stream fsync/seal and atomic manifest publication;
- independent spool decoder/count/re-hash verifier;
- startup reconciliation and TTL cleanup;
- real parser supervisor and artifact verification;
- concrete Apply/Memory persistence and complete deletion fencing;
- iOS and Desktop Portal clients.

## Validation

```txt
independently reconstructed Linux filesystem/writer package:
gofmt + go test -race PASS

exact repository-integrated Go suite:
UNCONFIRMED

remote workflow result:
UNCONFIRMED
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
