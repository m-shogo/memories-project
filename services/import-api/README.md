# Memory OS Import API — Security Vertical Slice

This Go module is the first executable backend security slice for Capture / Import.
It is intentionally small and does not yet expose a production server.

## Implemented

- private verified-principal model;
- verified-principal request-context boundary;
- fixed PostgreSQL privilege-role allowlist;
- transaction-local account ID / account epoch setup;
- RS256 Apple identity-token verification;
- exact issuer, audience, time-window, nonce and subject checks;
- duplicate-key and credential-size rejection for identity-token JSON;
- Apple JWKS retrieval with a fixed HTTPS origin, response limits and bounded cache;
- authorization-code subject / client / redirect binding interfaces;
- replay-guard and canonical `issuer + subject` account-binding interfaces;
- signed quarantine-upload authorization core;
- strict upload HTTP handlers with unknown-field and body-size rejection;
- upload completion endpoint that rejects all client-supplied metadata bodies;
- exact owner / epoch / job / key / size / checksum / type / expiry binding;
- server-side object metadata verification;
- object-version binding before scan queueing;
- atomic authorization consumption interface;
- cryptographically random opaque ID generation;
- bounded Generic CSV parsing with explicit mapping, deterministic fingerprints and row-level warning/rejection decisions;
- synchronous one-row-at-a-time CSV iterator with sticky cancellation and terminal failures;
- canonical CSV options normalization and SHA-256 binding, limited to embedded UTC / Asia-Tokyo rules in P0;
- synchronous CSV-to-Preview RowEvent bridge with no goroutines, channels or separate persistence;
- safe rejected-row records containing only source row and stable `IMPORT_*` issue codes;
- Preview v2 hash model binding accepted candidates, safe rejection report, counts, source object version, adapter digest and options digest;
- reference AtomicMaterializer tests proving row ordering, exclusive decisions and all-or-error finalization behavior;
- strict Apply HTTP boundary that rejects owner / epoch injection;
- iOS-user-only Apply service with exact Preview hash, request-bound idempotency and full candidate accounting;
- Generic CSV and Apple compact-JWT fuzz targets;
- canonical account-state / epoch checkpoint guard;
- required fenced wrappers that checkpoint upload, Preview and Apply before irreversible writes.

## Important implementation boundary

The current in-process `preview.AtomicMaterializer` consumes its row source inside the transaction callback. It is a vertical-slice reference for hashing and invariants only.

It must not be connected to a production PostgreSQL repository for large imports.

The required production path is defined in:

```txt
docs/memory-os-preview-spool-commit-contract-round-9.md
```

Production must parse outside the database transaction, create a bounded verified spool, and use one short client-side bulk-copy transaction to insert candidates, safe rejections and the immutable ready Preview together.

## Deliberately not implemented yet

- executable HTTP server and session-token issuer;
- Apple authorization-code exchange client-secret signing;
- canonical account-control PostgreSQL repository;
- concrete PostgreSQL repositories / driver composition;
- concrete S3-compatible signer and object-store adapter;
- parser supervisor runtime;
- bounded Preview spool writer, reader and manifest verifier;
- client-side `pgx.CopyFrom` Preview commit repository;
- concrete Generic CSV quarantine reader and adapter artifact verification;
- concrete idempotent Apply repository and Memory persistence;
- atomic deletion-epoch increment, worker lease cancellation and storage cleanup.

These missing parts remain production blockers. Do not describe this module as a secure production backend.

## Validation

```bash
go test ./...
go test -race ./...
go vet ./...

GOMAXPROCS=4 go test -run='^$' -fuzz=FuzzParserNeverPanicsOrExpandsLimits -fuzztime=5s -timeout=30s ./internal/adapters/genericcsv
GOMAXPROCS=4 go test -run='^$' -fuzz=FuzzParseCompactTokenNeverPanics -fuzztime=5s -timeout=30s ./internal/appleauth
```

No live secrets, user content or production endpoints are used by the tests.
