# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-18

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
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier created
startup reconciliation / TTL cleanup not implemented

PostgreSQL:
RLS / upload persistence foundation migrations and SQL tests created
production domain schema / Go repositories not created

object storage / parser supervisor / iOS / Portal:
NOT IMPLEMENTED

exact current HEAD full repository Go suite:
CONFIRMED in a local golang:1.23 Linux container

exact current HEAD remote Actions:
UNCONFIRMED at commit time

production:
NO-GO
```

Do not claim perfect security, complete privacy, backend completion, Preview spool completion or production readiness.

---

# 1. Authority order

Conflicts are resolved from top to bottom:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-verifier-checkpoint-2026-07-17.md`
4. `docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md`
5. `docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md`
6. `docs/memory-os-preview-spool-commit-contract-round-9.md`
7. security schema registry and fixture index
8. current code under `services/import-api/`
9. `services/import-api/README.md`
10. `SECURITY.md`
11. Round 9 architecture, threat model and verification gate
12. OpenAPI, PostgreSQL migrations/tests and validators/workflows
13. Round 8 Capture / Import architecture
14. prior privacy / persistence / deletion contracts
15. historical progress and handoff documents

Historical documents record old snapshots and never override current code or this order.

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

Parser, adapter, dedupe, Preview and Apply logic are canonical in the backend and are not independently reimplemented across Swift/browser/Go.

---

# 3. Binding security decisions

## Identity and authorization

- Sign in with Apple is verified server-side with exact issuer, audience, RS256, expiry, issued-at, nonce and subject.
- Canonical identity is issuer + subject, not email.
- Client account/owner/epoch values are never authority.
- Every job, pairing, upload, object, Preview, report, Apply and export requires exact lookup, owner, epoch, state and operation authority.
- Browser pairing authority cannot final Apply.
- `ENABLE RLS` and `FORCE RLS` are mandatory.
- Runtime roles are `NOLOGIN NOINHERIT NOBYPASSRLS` and do not own user tables.
- Existing SQL is a security foundation, not the complete production domain schema.

## Upload and parser

- Server generates the owner/epoch/job-bound object key and authoritative storage fields.
- Upload authorization binds size, checksum, content type and expiry.
- Completion verifies server-side metadata and the exact object version.
- Parser runtime must be non-root, networkless, read-only, secretless, job-isolated and resource-bounded.
- Reviewed digest-pinned adapter artifacts are mandatory.

## CSV and Preview source

- Generic CSV is synchronous one-row pull.
- No hidden goroutine/channel/background persistence exists in iterator, bridge or spool writer.
- Cancellation and fatal failures are sticky.
- Normalized parser options are SHA-256-bound.
- Source rows strictly increase.
- Rejections contain only source row and stable `IMPORT_*` issue codes.

---

# 4. Preview spool and atomic commit authority

Production parsing inside a PostgreSQL transaction is forbidden.

```txt
version-bound source
→ transaction-free isolated parse
→ supervisor-owned bounded spool attempt
→ durable no-replace manifest publication
→ independent decode / count / re-hash
→ epoch/source/adapter/options recheck
→ one short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
→ COMMIT or full ROLLBACK
```

Manifest authority binds server-generated `spoolId`, job/owner/epoch, source key/version/size/checksum, adapter identity/reviewed digest, options digest, exact stream formats/counts/bytes/hashes, aggregate rows/bytes and a maximum 24-hour TTL. Path fields, symlink following, cross-attempt reuse and backup eligibility are forbidden.

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
- 100,000 aggregate records, 512 MiB aggregate bytes and 2 MiB per record;
- exact-file-byte SHA-256 including length prefixes;
- at least one accepted record;
- sticky cancellation/limit/short-write/`ENOSPC`/lifecycle errors;
- terminal failure closes writable handles and cannot resume;
- exact-once writer claim.

## Implemented seal/publication checkpoint

- validates exact job/owner/epoch/source/adapter/options/TTL bindings;
- fsyncs both stream files before closing them;
- creates exclusive no-follow `manifest.tmp` with exact `0600`;
- writes deterministic compact JSON and fsyncs it;
- publishes `manifest.json` with `linkat` no-replace semantics;
- unlinks temp and fsyncs the attempt directory;
- never overwrites an existing final manifest;
- rolls back the final name on directory-fsync failure;
- emits `ErrSealDurabilityUncertain` if rollback durability cannot be established;
- same-Sealer/same-input reseal is idempotent; conflicting input is rejected.

An ordinary rename is not the authority because it may replace an existing final name.

## Implemented independent verifier checkpoint

- descriptor-relative `O_NOFOLLOW` re-open of attempt, manifest and both streams;
- fixed-name allowlist; `manifest.tmp` residue and unknown entries reject;
- regular/`0600`/single-link/owner checks on every entry;
- strict single-value JSON decode with unknown fields forbidden;
- canonical re-serialization equality against the seal builder (duplicate keys, whitespace, reordering, non-UTC timestamps and altered security constants all reject);
- expiry enforced against the caller clock;
- exact job/owner/epoch/source/adapter/options expectation match required;
- bounded length-prefix re-decode with record/byte limits enforced while reading;
- independent re-count and exact-byte SHA-256 compared to every manifest stream binding;
- truncation, append, torn append, malformed lengths and same-length substitution proved;
- read-only, stateless, retryable; performs no deletion and no database work.

## Still incomplete and forbidden

- no startup reconciliation for `manifest.tmp`, both-name links or other crash residue;
- no TTL cleanup;
- no production PostgreSQL wiring.

A published manifest remains untrusted until its verification passes; the commit path must run the verifier and re-check epoch/job state inside its own transaction boundary. `preview.AtomicMaterializer` remains reference-only and is forbidden as the production PostgreSQL path.

---

# 5. Apply and deletion authority

- Final Apply is iOS-user-only and exact Preview hash-bound.
- Apply never reparses.
- Idempotency key binds the request hash.
- Created + updated + skipped accounts for every accepted candidate or rollback.
- Rejected rows never enter Apply.
- Account epoch fences jobs, leases, uploads, objects, spools, Preview, Apply, exports, caches and backup restoration.

---

# 6. Executable status

Partial Go security/reference code exists for verified principal/context, scoped PostgreSQL transactions, Apple JWT/JWKS, signed upload, bounded CSV, Preview hashing, reference Apply, account epoch guards, fuzz targets, Preview spool filesystem, bounded writer, durable no-replace manifest publication and the independent sealed-spool verifier.

Not implemented:

```txt
production executable server/session issuer
Apple code exchange/secret rotation/replay/session persistence
production account/session/repository composition
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
exact repository-integrated Go suite at code HEAD e75b7324e0388b264d90f67ee3094d788fadf5f4:
gofmt clean + go vet + go test -race + both fuzz smokes PASS
(local golang:1.23 Linux container)

remote Actions result for the pushed HEAD:
UNCONFIRMED at commit time
```

Earlier Import API remote runs failed at the Format check; the formatting and one test-only compile error were repaired at this checkpoint. A local container run is repository evidence, not production evidence.

---

# 7. Hard stops

Production remains forbidden while any remains:

- concrete Apple exchange/session/replay missing;
- cross-user authorization/RLS failure;
- browser final Apply;
- upload key/metadata not exact-bound;
- parser network/host/secrets/unbounded resources;
- untrusted parse inside production DB transaction;
- spool commit without a passed independent verification in the same flow, or without crash reconciliation;
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
0. confirm remote workflows for the pushed HEAD (local suite already confirmed)
1. implement startup reconciliation and TTL cleanup
2. create production Preview candidate/rejection/ready PostgreSQL schema
3. implement short atomic pgx.CopyFrom repository
4. prove epoch recheck, rollback and post-COMMIT retry recovery
5. implement private versioned object storage and parser supervisor
6. compose executable API/auth/repositories
7. implement Apply/Memory/deletion
8. begin iOS only after backend P0 closes
```

Memory Town remains after Capture / Import P0 blockers close.
