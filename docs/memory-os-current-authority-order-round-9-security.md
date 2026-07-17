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
Linux filesystem attempt lifecycle checkpoint created
stream writer / seal / verifier not implemented

PostgreSQL:
RLS / upload persistence foundation migrations and SQL tests created
production domain schema / Go repositories not created

concrete object storage / parser supervisor / iOS / Portal:
NOT IMPLEMENTED

current HEAD full repository and remote Actions result:
UNCONFIRMED

production:
NO-GO
```

Do not claim perfect security, complete privacy, backend completion or production readiness.

---

# 1. Authority order

Conflicts are resolved from top to bottom:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-commit-contract-round-9.md`
4. `docs/schemas/memory-os-security/schema-registry.v1.json`
5. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
6. current code under `services/import-api/`
7. `services/import-api/README.md`
8. `SECURITY.md`
9. Round 9 architecture / threat model / verification gate
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

Earlier PixiJS/WebGL Town documents are design exploration, not the current binding runtime choice for the iOS-only product.

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
- Existing SQL migrations are security foundations, not the complete production domain schema.

## Upload

- Server generates owner, epoch, job-bound object key and authoritative storage fields.
- Authorization binds size, checksum, content type and expiry.
- Completion verifies actual server-side metadata and exact object version.
- Authorization consumption and scan enqueue are atomic.
- Quarantine is private, non-listable and versioned.

## Parser

- non-root, no privilege escalation, capabilities dropped;
- read-only root and job-private `noexec,nosuid,nodev` temp;
- no network, metadata endpoint, host mounts, secrets or cross-job access;
- bounded CPU, memory, PID, wall time, FD, temp and output;
- reviewed digest-pinned adapter artifact;
- path traversal, links, special files, collisions, encrypted/multivolume archives, deep/duplicate-key JSON and oversized CSV are rejected.

## CSV and Preview source

- Generic CSV is synchronous one-row pull.
- No hidden goroutine/channel/background persistence in iterator or bridge.
- Cancellation/fatal parse failures are sticky.
- Normalized parser options are SHA-256-bound; caller mismatch rejects before DB work.
- P0 timezone authority is embedded UTC and Asia/Tokyo.
- Source rows strictly increase.
- Rejections contain only source row and stable `IMPORT_*` codes.

## Preview spool and atomic commit

Production parsing inside a PostgreSQL transaction is forbidden.

```txt
version-bound source
→ transaction-free isolated parse
→ one supervisor-owned bounded spool attempt
→ seal and independent re-hash
→ epoch/source/adapter/options recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

Manifest authority binds:

- server-generated `spoolId`;
- job/owner/epoch;
- source key/version/size/checksum;
- adapter ID/version/reviewed artifact digest;
- normalized options digest;
- exact accepted/rejected formats, counts, bytes and hashes;
- aggregate rows/bytes and maximum 24-hour TTL;
- no path fields, symlink following, cross-attempt reuse or backup eligibility.

Current filesystem checkpoint under `internal/previewspool`:

- Linux-only strong implementation;
- supervisor-provisioned exact `0700` root;
- descriptor-relative `mkdirat/openat`;
- `O_EXCL/O_NOFOLLOW` fixed-name `0600` files;
- owner/type/mode/link checks;
- attempt device/inode substitution rejection;
- cancellation cleanup at each construction stage;
- unknown-entry fail-closed cleanup;
- non-Linux fail-closed behavior.

This checkpoint does not serialize records, enforce stream byte/row limits, write/seal manifests, re-hash streams or commit PostgreSQL rows.

`preview.AtomicMaterializer` remains reference-only and is forbidden as the production PostgreSQL path.

## Apply and deletion

- Final Apply is iOS-user-only and exact Preview hash-bound.
- Apply never reparses.
- Idempotency key binds request hash.
- Created + updated + skipped accounts for all accepted candidates or rollback.
- Rejected rows never enter Apply.
- Account epoch fences jobs, leases, uploads, objects, spools, Preview, Apply, exports, caches and backup restoration.

---

# 4. Executable status

Implemented as partial Go security/reference code:

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
Linux Preview spool attempt filesystem lifecycle
```

Not implemented:

```txt
production executable server/session issuer
Apple code exchange/secret rotation/replay/session persistence
production account/session/repository composition
canonical spool record writer/seal/reader/rehash
startup reconciliation/expiry cleanup/disk-failure recovery
production Preview candidate/rejection/ready schema
pgx.CopyFrom Preview repository
private versioned S3 signer/HEAD/lifecycle
isolated parser supervisor runtime
concrete Apply/Memory persistence
complete deletion fencing
native iOS and Desktop Portal
```

Validation wording:

```txt
Preview spool filesystem reconstructed mini-module:
gofmt + go test -race PASS

exact current repository full Go suite:
UNCONFIRMED

remote Actions current result:
UNCONFIRMED
```

Targeted package evidence is not full-repository or production evidence.

---

# 5. Hard stops

Production remains forbidden while any remains:

- client identity/storage authority trusted;
- concrete Apple exchange/session/replay missing;
- cross-user authorization/RLS failure;
- browser final Apply;
- upload key/metadata not exact-bound;
- parser network/host/secrets/unbounded resources;
- untrusted parse inside production DB transaction;
- spool without fixed formats, limits, seal, independent re-hash and terminal cleanup;
- partial candidate/rejection/Preview visibility;
- missing epoch recheck immediately before commit;
- deletion resurrection possible;
- private content in logs/analytics/notifications/crash reports;
- remote CI unknown at release judgment;
- unresolved P0 > 0;
- unresolved independent Critical/High finding.

---

# 6. Correct next sequence

```txt
0. confirm exact current HEAD validators / Go format-test-vet-race-fuzz / remote workflows
1. implement canonical bounded accepted/rejected stream writers
2. add sticky cancellation, short-write and disk-limit failure tests
3. implement stream close/fsync, manifest publication and seal protocol
4. implement independent reader/decode/count/re-hash verifier
5. implement startup reconciliation and TTL cleanup of abandoned attempts
6. prove truncation, append, malformed length, hardlink and crash cases
7. create production Preview candidate/rejection/ready PostgreSQL schema
8. implement short atomic pgx.CopyFrom commit repository
9. prove epoch recheck, rollback and post-COMMIT retry recovery
10. implement private versioned object storage and parser supervisor
11. compose executable API/auth/repositories
12. implement Apply/Memory/deletion
13. begin iOS only after backend P0 closes
```

Memory Town remains after Capture / Import P0 blockers close.
