# Memory OS Import API — Security Vertical Slice

This Go module is the first executable backend security slice for Capture / Import.

It is intentionally incomplete. It does not expose a production server and must not be described as a production backend.

## Implemented reference and boundary code

- private verified-principal model and request-context boundary;
- fixed PostgreSQL privilege-role allowlist and transaction-local account ID/epoch setup;
- RS256 Apple identity-token verification, duplicate-key rejection and bounded JWKS cache;
- authorization-code/replay/account-binding interfaces;
- signed quarantine-upload authorization core and strict HTTP handlers;
- exact owner/epoch/job/key/size/checksum/type/expiry and object-version binding interfaces;
- cryptographically random opaque IDs;
- bounded Generic CSV parser;
- synchronous one-row CSV iterator with sticky cancellation/failure;
- canonical parser-options normalization and SHA-256 binding;
- synchronous CSV-to-Preview RowEvent bridge with no goroutines/channels;
- safe rejected-row records with source row and stable `IMPORT_*` codes only;
- Preview v2 accepted/rejected hash model;
- reference AtomicMaterializer invariant tests;
- iOS-only exact-hash idempotent Apply service interfaces;
- account-state/epoch checkpoint guards;
- Generic CSV and Apple compact-JWT fuzz targets;
- Linux Preview spool attempt filesystem lifecycle.

## Preview spool contracts

```txt
docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json
docs/schemas/memory-os-security/preview-spool-semantic-case-set.v1.schema.json
docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-negative-cases.round9.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-semantic-cases.round9.v1.json
scripts/validate-memory-os-preview-spool.py
```

The contract binds one server-generated parse attempt, source/adapter/options evidence, fixed accepted/rejected formats, counts, byte lengths, hashes and a maximum 24-hour TTL. It forbids manifest path fields, symlink following, cross-attempt reuse, backup eligibility and database transactions during parsing.

## Preview spool filesystem checkpoint

Implemented under `internal/previewspool`:

- Linux-only strong implementation; non-Linux fails closed;
- supervisor-provisioned absolute canonical root with exact `0700` mode and owner check;
- validated single-segment `spoolId`;
- descriptor-relative `mkdirat/openat`;
- fixed accepted/rejected/manifest filenames;
- `O_CREAT | O_EXCL | O_NOFOLLOW`, exact `0600` mode;
- directory/file type, owner, mode and regular-file link-count checks;
- captured attempt device/inode and substitution rejection;
- cancellation cleanup after each partial creation stage;
- unknown-entry fail-closed cleanup;
- idempotent successful cleanup;
- symlink cleanup that unlinks the link without following the target.

Targeted evidence:

```txt
independently reconstructed Linux mini-module:
gofmt + go test -race PASS

actual repository full Go suite:
UNCONFIRMED

remote workflow result:
UNCONFIRMED
```

This is not the complete spool runtime. Canonical record encoding, bounded stream writing, fsync/seal, manifest publication, independent reader/re-hash, expiry reconciliation and PostgreSQL commit are still missing.

## Critical production boundary

`preview.AtomicMaterializer` consumes its source inside the transaction callback. It is a reference for hashing/invariants only and must not be connected to production PostgreSQL for untrusted imports.

Required production flow:

```txt
version-bound quarantine object
→ isolated transaction-free parser
→ supervisor-owned bounded accepted/rejected spool
→ sealed manifest and independent stream re-hash
→ account epoch and binding recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

See:

```txt
docs/memory-os-preview-spool-commit-contract-round-9.md
docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md
```

## Deliberately not implemented yet

- executable HTTP server and session issuer;
- Apple authorization-code exchange secret signing/rotation;
- concrete replay/account/session repositories;
- production Preview candidate/rejection/ready tables;
- concrete PostgreSQL repositories and `pgx.CopyFrom` commit path;
- concrete S3-compatible signer/HEAD adapter and lifecycle;
- canonical accepted/rejected stream writer and limits;
- stream fsync/seal and manifest writer;
- independent spool reader/decode/count/re-hash verifier;
- startup reconciliation and TTL cleanup;
- disk-full/short-write/crash recovery evidence;
- parser supervisor runtime and adapter artifact verification;
- concrete Apply/Memory persistence;
- complete deletion fencing and cleanup;
- iOS and Desktop Portal clients.

## Validation commands

```bash
# repository root
python scripts/validate-memory-os-preview-spool.py

# services/import-api
test -z "$(gofmt -l .)"
go test ./...
go vet ./...
go test -race ./...

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParserNeverPanicsOrExpandsLimits \
  -fuzztime=5s -timeout=30s ./internal/adapters/genericcsv

GOMAXPROCS=4 go test -run='^$' \
  -fuzz=FuzzParseCompactTokenNeverPanics \
  -fuzztime=5s -timeout=30s ./internal/appleauth
```

Do not write `PASS` for the current repository HEAD until these commands and the remote workflows run against that exact HEAD.

No live secrets, user content or production endpoints are used by the current tests.
