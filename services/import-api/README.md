# Memory OS Import API — Security Vertical Slice

This Go module is the first executable backend security slice for Capture / Import.

It is intentionally incomplete. It does not yet expose a production server and must not be described as a production backend.

## Implemented reference and boundary code

- private verified-principal model;
- verified-principal request-context boundary;
- fixed PostgreSQL privilege-role allowlist;
- transaction-local account ID / account epoch setup;
- RS256 Apple identity-token verification;
- exact issuer, audience, time-window, nonce and subject checks;
- duplicate-key and credential-size rejection for identity-token JSON;
- Apple JWKS retrieval with fixed HTTPS origin, response limits and bounded cache;
- authorization-code subject / client / redirect binding interfaces;
- replay-guard and canonical `issuer + subject` account-binding interfaces;
- signed quarantine-upload authorization core;
- strict upload HTTP handlers with unknown-field and body-size rejection;
- upload completion endpoint that rejects client-supplied authoritative metadata;
- exact owner / epoch / job / key / size / checksum / type / expiry binding;
- server-side object metadata verification interface;
- object-version binding before scan queueing;
- atomic authorization consumption interface;
- cryptographically random opaque ID generation;
- bounded Generic CSV parsing with explicit mapping, deterministic fingerprints and row decisions;
- synchronous one-row-at-a-time CSV iterator with sticky cancellation and terminal failures;
- canonical CSV options normalization and SHA-256 binding, limited to embedded UTC / Asia-Tokyo rules in P0;
- synchronous CSV-to-Preview RowEvent bridge with no goroutines, channels or separate persistence;
- safe rejected-row records containing only source row and stable `IMPORT_*` issue codes;
- Preview v2 hash model binding accepted candidates, safe rejection report, counts, source version, adapter digest and options digest;
- reference AtomicMaterializer tests proving ordering, exclusive decisions and all-or-error finalization behavior;
- strict Apply HTTP boundary that rejects owner / epoch injection;
- iOS-user-only Apply service with exact Preview hash, request-bound idempotency and full candidate accounting;
- Generic CSV and Apple compact-JWT fuzz targets;
- canonical account-state / epoch checkpoint guard;
- required fenced wrappers that checkpoint upload, Preview and Apply before irreversible writes.

## Machine contracts now available

The repository also contains a hardened Preview spool manifest contract and dedicated semantic validator:

```txt
docs/schemas/memory-os-security/preview-spool-manifest.v1.schema.json
docs/schemas/memory-os-security/preview-spool-semantic-case-set.v1.schema.json
docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-negative-cases.round9.v1.json
docs/fixtures/memory-os-security/preview-spool-manifest-semantic-cases.round9.v1.json
scripts/validate-memory-os-preview-spool.py
```

The contract binds one server-generated parse attempt, exact source/adapter/options evidence, fixed accepted/rejected record formats, counts, byte lengths, hashes and a maximum 24-hour TTL. It forbids manifest path fields, symlink following, cross-attempt reuse, backup eligibility and database transactions during parsing.

A contract is not a runtime implementation.

## Critical production boundary

The in-process `preview.AtomicMaterializer` consumes its row source inside the transaction callback. It is a vertical-slice reference for hashing and invariants only.

It must not be connected to a production PostgreSQL repository for large or untrusted imports.

Required production flow:

```txt
version-bound quarantine object
→ isolated transaction-free parser
→ supervisor-owned bounded accepted/rejected spool
→ sealed manifest and independent stream re-hash
→ canonical account epoch and binding recheck
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

- executable HTTP server composition and session-token issuer;
- Apple authorization-code exchange client-secret signing and rotation;
- concrete replay/account/session repositories;
- canonical account-control PostgreSQL repository;
- production Preview candidate / rejection / ready tables;
- concrete PostgreSQL repositories and driver composition;
- client-side `pgx.CopyFrom` Preview commit repository;
- concrete S3-compatible signer and object-store HEAD adapter;
- private versioned bucket policy/lifecycle integration;
- parser supervisor runtime;
- supervisor-owned `0700` spool attempt directory;
- fixed exclusive `0600` stream/manifest files;
- canonical spool writer, seal, reader, re-hash and terminal cleanup;
- concrete Generic CSV quarantine reader and adapter artifact verification;
- concrete idempotent Apply repository and Memory persistence;
- atomic deletion-epoch increment, worker lease cancellation and storage cleanup;
- iOS and Desktop Portal clients.

These remain production blockers.

## Validation commands

```bash
# From repository root
python scripts/validate-memory-os-preview-spool.py

# From services/import-api
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

The previous Go baseline passed at its recorded snapshot. The exact current HEAD full Go suite and remote workflow result are not claimed by this README until rerun and recorded.

No live secrets, user content or production endpoints are used by the existing tests.
