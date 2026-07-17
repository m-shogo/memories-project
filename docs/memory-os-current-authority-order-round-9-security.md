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
runtime not implemented

PostgreSQL:
RLS / upload persistence foundation migrations and SQL tests created
production domain schema / Go repositories not created

concrete object storage / parser runtime / iOS / Portal:
NOT IMPLEMENTED

current HEAD remote GitHub Actions result:
UNCONFIRMED

production:
NO-GO
```

Securityについて「完璧」「安全が保証された」「backend完成」とは表現しない。

---

# 1. Authority order

矛盾時は上を優先する。

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-preview-spool-commit-contract-round-9.md`
4. `docs/schemas/memory-os-security/schema-registry.v1.json`
5. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
6. `services/import-api/README.md`
7. `SECURITY.md`
8. `docs/memory-os-capture-import-security-architecture-round-9.md`
9. `docs/memory-os-capture-import-threat-model-round-9.md`
10. `docs/memory-os-security-verification-gate-round-9.md`
11. `contracts/openapi/memory-os-import-security.v1.openapi.json`
12. `infra/postgresql/security/001_memory_os_import_rls.sql`
13. `infra/postgresql/security/002_memory_os_upload_authorization.sql`
14. PostgreSQL security test SQL and Round 9 validators/workflows
15. Round 8 Capture / Import implementation architecture
16. prior privacy / persistence / deletion / worker-fencing contracts
17. historical progress and next-chat handoff documents

Historical progress documents record what was true at their commit. They do not override current code, schema registries, this authority or the current implementation status document.

Round 9 applies existing privacy, RLS and deletion principles across Capture / Import; it does not discard them.

---

# 2. Binding product and technology direction

```txt
Daily capture:
iOS Share Extension

Local file intake:
iOS Files / fileImporter

Bulk migration:
limited Desktop Import Portal

Canonical import engine:
Go API + isolated parser supervisor / worker

Canonical metadata and revisions:
PostgreSQL with FORCE RLS

Raw quarantine:
private versioned S3-compatible object storage

Local iOS intake/cache:
GRDB / SQLite + Keychain + App Group

Memory Town:
iOS SpriteKit only after Capture / Import P0 security blockers close
```

React / DOM is used for the limited Desktop Import Portal, not as the current canonical Memory Town runtime. Earlier PixiJS/WebGL Town documents remain historical design exploration unless a later explicit authority changes the native iOS direction.

Parser, adapter, dedupe, Preview and Apply logic must not be independently reimplemented in Swift, browser and Go.

---

# 3. Binding security decisions

## 3.1 Identity

- Sign in with Apple is verified server-side.
- Require exact issuer, audience, RS256 signature, expiry, issued-at, nonce and subject.
- Unknown `kid` refreshes JWKS once, then fails closed.
- Authorization code exchange binds subject, client and original redirect when applicable.
- Nonce and authorization code use single-use replay protection.
- Canonical account identity is `issuer + subject`, not email.
- Client account ID, email and subject are not authority.

## 3.2 Object authorization

Every Import Job, pairing, upload, quarantine object, Preview, Apply, report and export requires:

- exact object lookup;
- same owner;
- same account epoch;
- exact operation authority;
- owner-scoped list query;
- generic not-found/denied behavior that does not disclose cross-owner existence.

Browser pairing authority cannot perform final Apply in P0.

## 3.3 PostgreSQL tenant isolation

- `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` are mandatory.
- Runtime privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS`.
- Runtime roles do not own user tables.
- Only verified server principals set transaction-local account ID and epoch.
- Role names come from a fixed allowlist.
- Owner and epoch are enforced through `USING` and `WITH CHECK`.
- Missing context denies access.
- Security-domain DELETE is reserved for deletion runtime.
- Ready Preview, Apply confirmation and Import Report are immutable.

The existing migrations are security foundations, not the complete production domain schema.

## 3.4 Signed quarantine upload

The client may submit bounded declaration fields such as size, checksum, content type, source surface and a display filename. It may not choose owner, epoch, object key, bucket, version or authoritative object metadata.

Server behavior:

- generate one job-bound object key;
- issue short-lived exact-bound PUT authorization;
- verify real object metadata with server-side HEAD;
- require an object version ID;
- consume authorization atomically with scan enqueue;
- bind scan work to exact object version, size, checksum and type.

## 3.5 Parser and archive safety

Parser runtime requires:

- non-root, non-privileged execution;
- all capabilities dropped and no privilege escalation;
- read-only root filesystem;
- no host paths, devices or Docker socket;
- no network, DNS, proxy or metadata-service access;
- one job/attempt-specific `noexec,nosuid,nodev` private temp area;
- no cross-job visibility;
- no cloud, database or signing credentials;
- CPU, memory, PID, wall-clock, FD, temp and output limits;
- reviewed digest-pinned adapter artifact.

P0 archive bounds:

```txt
compressed:        256 MiB
expanded:            1 GiB
single entry:       128 MiB
entries:             10,000
compression ratio:   100x
nested depth:           1
```

Traversal, absolute/drive paths, NUL, links, special files, duplicate normalized paths, case collisions, encrypted/multi-volume archives, unsupported methods, malformed archives, deep JSON, duplicate JSON keys and oversized CSV cells are rejected.

## 3.6 CSV parsing and options binding

- Generic CSV uses synchronous one-row pull.
- No hidden goroutine, channel or background persistence is permitted in the iterator/bridge.
- Cancellation and fatal parse failures are sticky; a partial iterator is not resumed.
- Mapping, delimiter, date layout, timezone and limits are normalized and SHA-256-bound.
- P0 timezone authority is embedded `UTC` and `Asia/Tokyo` only.
- Caller-supplied options digest mismatch is rejected before database work.
- Source rows are strictly increasing.
- Rejected records contain only source row and stable `IMPORT_[A-Z0-9_]+` issue codes.

## 3.7 Preview spool and atomic visibility

Parsing a source while a production PostgreSQL transaction is open is forbidden.

```txt
version-bound source
→ transaction-free isolated parse
→ supervisor-owned bounded accepted/rejected spool
→ sealed manifest and independent stream re-hash
→ canonical account epoch and binding recheck
→ short client-side pgx.CopyFrom transaction
→ candidates + safe rejections + immutable ready Preview
```

Current machine contract binds:

- server-generated spool attempt ID;
- job/owner/epoch;
- source object key/version/size/checksum;
- adapter ID/version/reviewed artifact digest;
- normalized options digest;
- exact accepted/rejected record formats, counts, byte lengths and hashes;
- aggregate source-row/spool-byte limits;
- creation/expiry with maximum 24-hour spool TTL;
- no manifest path fields, symlink following, cross-attempt reuse or backup eligibility.

`preview.AtomicMaterializer` is reference/invariant code only and is forbidden as the production PostgreSQL path.

## 3.8 Apply

- Final Apply authority is iOS user only.
- Exact Preview ID and hash are required.
- Apply does not reparse.
- Idempotency key is bound to request hash.
- Same completed request returns the prior result.
- Same key with different request is rejected.
- Created + updated + skipped must equal accepted candidate count or the transaction rolls back.
- Rejected rows are never Apply input.
- Partial Apply is never reported as success.

## 3.9 Deletion

Account epoch propagates to jobs, leases, uploads, objects, spool attempts, Preview, Apply, exports, search, App Group files and backup restoration. Old-epoch writes and deletion resurrection are forbidden.

---

# 4. Executable backend status

Implemented under `services/import-api/` as a partial security vertical slice:

```txt
verified Principal and request-context boundary
fixed-role scoped PostgreSQL transaction executor
Apple JWT/JWKS verification core
cryptographic opaque IDs
signed-upload service and strict HTTP handlers
bounded Generic CSV parser
synchronous Generic CSV iterator
canonical CSV options digest
CSV → Preview RowEvent bridge
Preview v2 candidate/rejection hash model
reference AtomicMaterializer
idempotent iOS-only Apply service
account epoch checkpoint guard
CSV and Apple compact-JWT fuzz targets
```

Not implemented:

```txt
executable production server and session issuer
concrete Apple code exchanger / secret rotation / replay store
production account/session/repository composition
production Preview candidate/rejection/ready schema
client-side pgx.CopyFrom Preview commit repository
private versioned S3-compatible signer / HEAD adapter / lifecycle
supervisor-owned spool runtime writer/reader/rehash/cleanup
isolated parser supervisor runtime
concrete Apply / Memory persistence
complete deletion fencing and cleanup
native iOS client and limited Desktop Portal
```

Validation language:

```txt
historical local Go baseline:
PASS at its recorded snapshot

current HEAD full Go and remote workflow result:
not confirmed in this authority update
```

Never copy a historical PASS forward after code changes without rerunning against the exact HEAD.

---

# 5. Hard stops

Production authorization remains forbidden while any condition remains:

- client identity fields are trusted;
- Apple token/code/nonce validation or concrete session issuance is incomplete;
- email-only account linking exists;
- cross-user authorization or RLS fails;
- runtime DB role owns tables or bypasses RLS;
- browser authority can Apply;
- upload can choose arbitrary key/owner/bucket/size/checksum;
- completion trusts client object metadata;
- quarantine is public or client-listable;
- parser has network, host mount, secrets or unbounded resources;
- untrusted parse occurs inside a production DB transaction;
- spool lacks private creation, exact format/limits, independent re-hash and cleanup;
- candidate/rejection/Preview commit is not all-or-nothing;
- exact Preview/Apply hash binding or idempotency is absent;
- deletion cannot fence active work and backup restoration;
- private content reaches logs, analytics, notifications or crash reports;
- remote security CI is failing or unknown at release judgment time;
- unresolved P0 is greater than zero;
- independent review has unresolved Critical or High findings.

---

# 6. Correct next sequence

```txt
0. confirm exact current HEAD validators, Go format/test/vet/race/fuzz and remote workflows
1. implement supervisor-owned 0700 Preview spool attempt directory
2. implement fixed exclusive 0600 accepted/rejected/manifest files
3. implement canonical bounded stream writer, seal and independent reader/rehash
4. prove cancellation, disk failure, crash, tamper, symlink, cross-job and expiry cleanup
5. create production Preview candidate/rejection/ready PostgreSQL schema
6. implement short client-side pgx.CopyFrom commit repository
7. prove epoch recheck, all-or-nothing rollback and post-COMMIT retry recovery
8. implement concrete private versioned object-storage signer/HEAD/lifecycle
9. implement isolated parser supervisor and adapter artifact verification
10. compose executable API, concrete Apple exchange/session and repositories
11. implement Apply/Memory persistence and deletion fencing
12. begin iOS Share Extension only after backend P0 blockers close
13. add limited Desktop Portal after the native confirmation path is safe
```

Memory Town remains after Capture / Import P0 blockers close.
