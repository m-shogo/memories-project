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
- stream fsync and durable no-replace manifest publication.

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

Detailed evidence:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md
```

## Critical production boundary

A published manifest is still untrusted. No database transaction may consume it until an independent reader strictly decodes the manifest and both streams, independently counts and hashes exact bytes, and verifies every binding.

`preview.AtomicMaterializer` parses inside its transaction callback. It remains reference-only and must not be connected to production PostgreSQL for untrusted imports.

Required flow:

```txt
version-bound quarantine object
→ isolated transaction-free parser
→ private bounded spool
→ durable no-replace manifest publication
→ independent decode/count/re-hash
→ epoch and binding recheck
→ one short pgx.CopyFrom transaction
→ immutable ready Preview
→ COMMIT or full ROLLBACK
```

## Not implemented

- executable HTTP server/session issuer;
- Apple code exchange/secret rotation and concrete replay/session stores;
- production Preview candidate/rejection/ready tables;
- concrete PostgreSQL repositories and `pgx.CopyFrom` path;
- S3-compatible signer/HEAD/lifecycle;
- independent spool manifest/stream verifier;
- malformed-length/truncation/append/substitution proof;
- startup reconciliation and TTL cleanup;
- real parser supervisor and artifact verification;
- concrete Apply/Memory persistence and complete deletion fencing;
- iOS and Desktop Portal clients.

## Validation

```txt
independently reconstructed Linux spool package:
gofmt + go test -race + go vet PASS

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
