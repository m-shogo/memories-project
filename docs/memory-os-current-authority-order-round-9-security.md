# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-20

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
startup reconciliation + TTL cleanup created

PostgreSQL:
RLS / upload persistence foundation migrations and SQL tests created
production Preview domain schema created with live SQL tests
atomic Go Preview commit repository created (live-tested)

object storage adapter:
CREATED (live-tested against MinIO)

parser supervisor:
PROCESS BOUNDARY CREATED (live-tested; network namespace is deployment work)

supervised import flow:
COMPOSED AND LIVE-TESTED END TO END

canonical adapter record contract:
CREATED, CROSS-LANGUAGE MACHINE-VALIDATED; real Generic CSV adapter wired through the supervised worker

iOS / Portal:
NOT IMPLEMENTED

exact current HEAD full repository Go suite:
CONFIRMED in a local golang:1.23 Linux container

remote Actions:
canonical-record HEAD 0c91e37 CONFIRMED green (Import API run 29992738696, Security Contracts run 29992738481 incl. the canonical record validator)

production:
NO-GO
```

Do not claim perfect security, complete privacy, backend completion, Preview spool completion or production readiness.

---

# 1. Authority order

Conflicts are resolved from top to bottom:

1. `docs/memory-os-current-authority-order-round-9-security.md`
2. `docs/memory-os-current-implementation-status-and-roadmap-2026-07-17.md`
3. `docs/memory-os-importctl-checkpoint-2026-07-23.md`
4. `docs/memory-os-canonical-record-checkpoint-2026-07-21.md`
4. `docs/memory-os-import-flow-checkpoint-2026-07-20.md`
4. `docs/memory-os-parser-supervisor-checkpoint-2026-07-20.md`
4. `docs/memory-os-object-storage-checkpoint-2026-07-19.md`
5. `docs/memory-os-preview-commit-repository-checkpoint-2026-07-19.md`
6. `docs/memory-os-preview-domain-checkpoint-2026-07-18.md`
7. `docs/memory-os-preview-spool-reconciliation-checkpoint-2026-07-18.md`
8. `docs/memory-os-preview-spool-verifier-checkpoint-2026-07-17.md`
9. `docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md`
10. `docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md`
11. `docs/memory-os-preview-spool-commit-contract-round-9.md`
12. security schema registry and fixture index
13. current code under `services/import-api/`
14. `services/import-api/README.md`
15. `SECURITY.md`
16. Round 9 architecture, threat model and verification gate
17. OpenAPI, PostgreSQL migrations/tests and validators/workflows
18. Round 8 Capture / Import architecture
19. prior privacy / persistence / deletion contracts
20. historical progress and handoff documents

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
- Existing SQL provides the security foundation and the production Preview domain; Apply/Memory production persistence does not exist yet.

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

## Implemented reconciliation checkpoint

- one exclusive startup pass under the manager lock, deterministic name order;
- classifies sealed / unsealed / temp-residue / completed-publication / unknown;
- removes only fixed-name crash residue and expired sealed attempts;
- completes the linkat crash window when both manifest names share exactly one inode with two links;
- quarantines foreign names, symlinks, unknown entries, non-canonical manifests and conflicting temp inodes in place, without deletion;
- never deletes a sealed unexpired attempt; kept attempts still pass independent verification;
- cancellation returns a partial report and re-running is safe; non-Linux fails closed.

## Implemented Preview PostgreSQL domain checkpoint

- `memory_os.preview_ready` / `preview_candidate` / `preview_rejection` with FORCE RLS and the standard owner/epoch policy;
- worker-only INSERT, no UPDATE for any runtime role, deletion-runtime-only DELETE;
- globally unique deterministic `commit_key`; one ready Preview per job and per spool attempt;
- `state = 'ready'` only — no `building` Preview can exist;
- exact seal-evidence bindings (source key/version/length/hash, adapter, options, counts, bytes, stream hashes, TTL) as database CHECKs;
- rejection rows structurally cannot hold raw user values (source row + `IMPORT_*` codes only);
- `assert_preview_complete` proves exact counts and contiguous `1..n` ordinals under invoker RLS before COMMIT;
- live PostgreSQL 16 SQL tests in the Security Contracts workflow.

## Implemented commit repository checkpoint

- one short atomic worker-role transaction from `previewspool.VerifiedSpool` evidence to committed Preview;
- PostgreSQL forbids `COPY FROM` under RLS, so bulk loading is the contract-allowed parameterized `INSERT ... unnest` equivalent with FORCE RLS in force;
- deterministic commit key excludes the spool attempt ID; identical retries return the committed Preview (also after acknowledgement loss), conflicting retries reject;
- completeness gate, rollback, stale-binding rejection and the end-to-end spool→verify→commit flow proven on live PostgreSQL 16, locally and in CI.

## Still incomplete and forbidden

- no supervisor composition wiring verifier and committer as one production flow;
- no reviewed canonical-record contract for candidate JSON;
- no deletion-fence recheck integration;
- no production mount/runtime evidence;
- no operator alerting for quarantined residue;
- RLS contract fixture not yet extended to the three preview domain tables.

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
private versioned S3 signer/HEAD/lifecycle
isolated parser supervisor runtime
concrete Apply/Memory persistence and complete deletion fencing
iOS and Desktop Portal
```

Validation wording:

```txt
code HEAD 3f9ab51 (docs only; code identical to 5c3dc4b)
(local golang:1.23 Linux container + fresh postgres:16 + MinIO):
gofmt clean + go vet + go test ./... + go test -race ./... (17 packages,
live DB/object-store/supervision/import-flow tests included) + both 5s fuzz smokes PASS

remote workflows at import-flow HEAD 381c514:
Import API Security Slice run 29793196253 SUCCESS (live import-flow tests executed)
Security Contracts run 29793196257 SUCCESS
```

Earlier Import API remote runs had failed at the Format check until the verifier checkpoint repaired the suite; every push since has run green. CI evidence is repository evidence, not production evidence.

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
0. confirm remote workflows for the importctl HEAD
1. compose executable API/auth/repositories
2. implement Apply/Memory/deletion
3. begin iOS only after backend P0 closes
```

Memory Town remains after Capture / Import P0 blockers close.
