# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-17

## Current verdict

```txt
product hierarchy:
Capture / Import first

platform:
iOS canonical client + limited Desktop Import Portal

security architecture / threat model / verification gate:
DEFINED

machine-readable security foundation:
24 registered schemas
23 positive contract fixtures
31 structural rejection cases
8 semantic rejection cases

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

Preview spool:
manifest contract hardened
Linux attempt filesystem lifecycle created
bounded accepted/rejected writer created
fsync / seal / manifest publication / independent verifier not implemented

PostgreSQL:
RLS / upload persistence foundation migrations and SQL tests created
production domain schema / Go repositories not created

object storage / parser supervisor / iOS / Portal:
NOT IMPLEMENTED

exact current HEAD full repository and remote Actions:
UNCONFIRMED

production:
NO-GO
```

Do not claim perfect security, complete privacy, backend completion, Preview spool completion or production readiness.

---

# 1. Authority order

Conflicts are resolved from top to bottom:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md`
4. `docs/memory-os-preview-spool-commit-contract-round-9.md`
5. security schema registry and fixture index
6. current code under `services/import-api/`
7. `services/import-api/README.md`
8. `SECURITY.md`
9. Round 9 architecture, threat model and verification gate
10. OpenAPI, PostgreSQL migrations/tests and validators/workflows
11. Round 8 Capture / Import architecture
12. prior privacy / persistence / deletion contracts
13. historical progress and handoff documents

Historical documents record an old snapshot and never override current code or this order.

---

# 2. Binding technology direction

```txt
iOS canonical client:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain + App Group

limited bulk migration:
Desktop Import Portal
Vite + React + TypeScript

canonical backend:
Go API
PostgreSQL with FORCE RLS
private versioned S3-compatible quarantine
isolated parser supervisor / worker

Memory Town after Capture / Import P0:
SpriteKit
Metal only after measured need
```

Earlier PixiJS/WebGL Town documents are design exploration, not the current binding runtime for the iOS-only product.

Parser, adapter, dedupe, Preview and Apply logic are canonical in the backend and are not independently reimplemented across Swift/browser/Go.

---

# 3. Binding security decisions

## Identity

- Sign in with Apple is verified server-side.
- Require exact issuer, audience, RS256, expiry, issued-at, nonce and subject.
- Unknown `kid` refreshes JWKS once and then fails closed.
- Authorization code binds subject/client/redirect where applicable.
- Nonce and code are replay-protected.
- Canonical identity is issuer + subject, not email.
- Client account/owner/epoch fields are never authority.

## Object authorization and PostgreSQL

- Every job, pairing, upload, object, Preview, report, Apply and export requires exact lookup, owner, epoch, state and operation authority.
- Browser pairing authority cannot final Apply.
- `ENABLE RLS` and `FORCE RLS` are mandatory.
- Runtime roles are fixed, `NOLOGIN NOINHERIT NOBYPASSRLS`, and do not own user tables.
- Verified server principals set transaction-local owner and epoch.
- Missing context denies.
- Existing SQL migrations are security foundations, not the complete production schema.

## Upload and parser

- Server generates owner, epoch, job-bound object key and authoritative storage fields.
- Upload authorization binds size, checksum, content type and expiry.
- Completion verifies server-side metadata and exact object version.
- Parser is non-root, networkless, read-only, secretless, job-isolated and resource-bounded.
- Reviewed digest-pinned adapter artifacts are required.
- Traversal, links, special files, collisions, encrypted/multivolume archives, deep/duplicate-key JSON and oversized CSV are rejected.

## CSV and Preview source

- Generic CSV is synchronous one-row pull.
- No hidden goroutine/channel/background persistence in iterator, bridge or spool writer.
- Cancellation and fatal failures are sticky.
- Normalized parser options are SHA-256-bound; caller mismatch rejects before DB work.
- P0 timezone authority is embedded UTC and Asia/Tokyo.
- Source rows strictly increase.
- Rejections contain only source row and stable `IMPORT_*` codes.

---

# 4. Preview spool and atomic commit authority

Production parsing inside a PostgreSQL transaction is forbidden.

```txt
version-bound source
→ transaction-free isolated parse
→ supervisor-owned bounded spool attempt
→ fsync / seal / atomic manifest publication
→ independent decode / count / re-hash
→ epoch/source/adapter/options recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

Manifest binds server-generated `spoolId`, job/owner/epoch, source key/version/size/checksum, adapter identity/reviewed digest, options digest, exact accepted/rejected formats/counts/bytes/hashes, aggregate rows/bytes and maximum 24-hour TTL. Path fields, symlink following, cross-attempt reuse and backup eligibility are forbidden.

## Implemented filesystem checkpoint

- Linux-only strong implementation; non-Linux fails closed;
- exact supervisor-owned `0700` root;
- descriptor-relative `mkdirat/openat`;
- `O_EXCL/O_NOFOLLOW` fixed-name `0600` entries;
- owner/type/mode/link checks;
- attempt device/inode substitution rejection;
- cancellation cleanup and unknown-entry fail-closed cleanup.

## Implemented bounded writer checkpoint

- separate accepted/rejected streams;
- `8-byte big-endian length + canonical bytes`;
- `100,000` aggregate record limit;
- `512 MiB` aggregate byte limit;
- `2 MiB` per-record limit;
- exact-file-byte SHA-256 including length prefix;
- at least one accepted record;
- sticky cancel/limit/short-write/`ENOSPC`/lifecycle errors;
- terminal failure closes writable handles and cannot resume;
- empty manifest placeholder removed before writing;
- successful close returns evidence but does not seal.

## Still forbidden / incomplete

- no stream fsync;
- no exclusive `manifest.tmp` writer;
- no atomic rename/directory fsync/sealed state;
- no independent reader/decode/count/re-hash;
- no startup reconciliation or TTL cleanup;
- no production PostgreSQL wiring.

`preview.AtomicMaterializer` remains reference-only and is forbidden as the production PostgreSQL path.

---

# 5. Apply and deletion authority

- Final Apply is iOS-user-only and exact Preview hash-bound.
- Apply never reparses.
- Idempotency key binds request hash.
- Created + updated + skipped accounts for every accepted candidate or rollback.
- Rejected rows never enter Apply.
- Account epoch fences jobs, leases, uploads, objects, spools, Preview, Apply, exports, caches and backup restoration.

---

# 6. Executable status

Partial Go security/reference code exists for:

```txt
verified Principal/context
scoped PostgreSQL transaction executor
Apple JWT/JWKS core
signed-upload core and strict handlers
bounded CSV parser and synchronous iterator
canonical options digest
CSV → Preview RowEvent bridge
Preview v2 candidate/rejection hashing
reference AtomicMaterializer
idempotent iOS-only Apply interfaces
account epoch checkpoints
CSV/JWT fuzz targets
Linux Preview spool filesystem lifecycle
bounded Preview spool accepted/rejected writer
```

Not implemented:

```txt
production executable server/session issuer
Apple code exchange/secret rotation/replay/session persistence
production account/session/repository composition
spool fsync/seal/manifest publication
independent spool reader/decode/count/re-hash
startup reconciliation/expiry cleanup/crash recovery
production Preview candidate/rejection/ready schema
pgx.CopyFrom Preview repository
private versioned S3 signer/HEAD/lifecycle
isolated parser supervisor runtime
concrete Apply/Memory persistence and complete deletion fencing
iOS and Desktop Portal
```

Validation wording:

```txt
independently reconstructed Linux filesystem/writer package:
gofmt + go test -race PASS

exact current repository full Go suite:
UNCONFIRMED

remote Actions current result:
UNCONFIRMED
```

Targeted reconstruction is not full-repository or production evidence.

---

# 7. Hard stops

Production remains forbidden while any remains:

- client identity/storage authority trusted;
- concrete Apple exchange/session/replay missing;
- cross-user authorization/RLS failure;
- browser final Apply;
- upload key/metadata not exact-bound;
- parser network/host/secrets/unbounded resources;
- untrusted parse inside production DB transaction;
- spool without fixed formats, limits, fsync, atomic seal, independent re-hash and terminal cleanup;
- partial candidate/rejection/Preview visibility;
- missing epoch recheck immediately before commit;
- deletion resurrection possible;
- private content in logs/analytics/notifications/crash reports;
- remote CI unknown at release judgment;
- unresolved P0 > 0;
- unresolved independent Critical/High finding.

---

# 8. Correct next sequence

```txt
0. confirm exact current HEAD validators / Go format-test-vet-race-fuzz / remote workflows
1. implement stream fsync and close confirmation
2. write exclusive manifest.tmp from exact writer evidence
3. fsync manifest, atomic rename to manifest.json, fsync attempt directory
4. mark sealed and prohibit further writes
5. implement independent reader/decode/count/re-hash verifier
6. implement startup reconciliation and TTL cleanup
7. prove truncation, append, malformed length, hardlink and crash cases
8. create production Preview candidate/rejection/ready PostgreSQL schema
9. implement short atomic pgx.CopyFrom repository
10. prove epoch recheck, rollback and post-COMMIT retry recovery
11. implement private versioned object storage and parser supervisor
12. compose executable API/auth/repositories
13. implement Apply/Memory/deletion
14. begin iOS only after backend P0 closes
```

Memory Town remains after Capture / Import P0 blockers close.
