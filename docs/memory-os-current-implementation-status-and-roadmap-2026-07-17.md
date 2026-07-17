# Memory OS Current Implementation Status and Roadmap

最終更新: 2026-07-17

この文書は、設計済み・契約済み・部分実装・実環境未検証を混同しないための現在地正本である。

矛盾時は `docs/memory-os-current-authority-order-round-9-security.md` を最優先し、この文書を実装状況の次点正本とする。

---

# 1. Executive verdict

```txt
product priority:
Capture / Import first

security architecture:
DEFINED

machine-readable contracts:
ADVANCED

Go backend:
PARTIAL SECURITY VERTICAL SLICE
not a production backend

PostgreSQL:
RLS / upload persistence foundation exists
production domain schema and repositories do not

Preview spool:
manifest contract hardened
Linux filesystem attempt lifecycle created
stream writer / seal / verifier not implemented

object storage runtime:
not implemented

parser sandbox runtime:
not implemented

iOS / Desktop Portal:
not implemented

remote GitHub Actions result for current HEAD:
unconfirmed

production:
NO-GO
```

「Go backend未実装」は古い。`services/import-api/`には認証境界、transaction scope、Apple JWT/JWKS core、signed upload core、CSV parser/iterator、Preview hash model、Apply service、Preview spool filesystem boundaryが存在する。

ただし、executable server、production repositories、real object storage、real sandbox、session issuer、stream spool runtime、iOS clientが存在しないため、「backend実装済み」も不正確。正確な表現は **partial security vertical slice**。

---

# 2. Status matrix

| Area | Correct status | Evidence boundary | Remaining blocker |
|---|---|---|---|
| Security architecture / threat model / verification gate | Defined | Human-readable Round 9 contracts | Independent review and production evidence |
| Machine-readable security contracts | Advanced | 24 registered schemas, 23 positive contract fixtures | Runtime conformance evidence |
| Negative contract evidence | Advanced | 31 structural rejections, 8 semantic rejections | Full CI result and runtime adversarial tests |
| Object authorization contract | Contract complete | 8 cases: 2 allow / 6 deny | Real API/repository integration |
| PostgreSQL RLS contract | Contract and foundation migration created | 9 table profiles, 14 logic cases, FORCE RLS SQL | Production domain schema, Go repository and deployment-role proof |
| PostgreSQL live SQL test | Created | PostgreSQL 16 workflow and SQL scripts exist | Remote result unconfirmed; not Go↔DB production integration |
| Sign in with Apple contract | Contract complete | 16 cases: 1 allow / 15 deny | Code exchange, secret rotation, replay store, session issuer |
| Apple verification Go core | Partial | JWT/JWKS validation and binding interfaces | Concrete persistence/exchange/session composition |
| Signed upload OpenAPI | Created | 3 operations and validator | Concrete private versioned storage enforcement |
| Signed upload Go service | Partial | Exact request/object metadata binding interfaces | Signer, HEAD adapter, repository, lifecycle evidence |
| Parser sandbox contract | Created | Profile and 16 unsafe mutations | Real supervisor/container/process runtime |
| Archive/JSON/CSV safety contracts | Created | 25 cases: 1 allow / 24 deny | Runtime corpus and fuzz evidence |
| Generic CSV parser and iterator | Partial | Bounded synchronous pull; sticky failure | Concrete quarantine reader and isolated worker process |
| CSV → Preview bridge | Reference | No hidden goroutines/channels; one row per call | Production spool and commit path |
| Preview v2 hashing | Reference | Candidate + safe rejection hashes/counts | Production persistence and retry recovery |
| Preview spool manifest | Contract hardened | Attempt ID, formats, counts, bytes, TTL and semantic validator | Runtime writer/seal/verifier |
| Preview spool filesystem lifecycle | Partial implementation | Linux `mkdirat/openat`, `O_EXCL/O_NOFOLLOW`, inode checks, fixed modes/names, partial cleanup tests | Full repository CI; writer/reader; expiry/reconciliation; production deployment proof |
| AtomicMaterializer | Reference only | Invariant tests | Forbidden for production PostgreSQL because parse occurs inside callback transaction |
| Apply service | Partial | iOS authority and exact-hash idempotency interfaces | Concrete Preview/Memory repository and deletion fencing |
| Executable Go API | Not implemented | No production `main` composition/server lifecycle | Auth/session, repositories, storage and worker composition |
| Object storage runtime | Not implemented | Interfaces and SQL/OpenAPI only | Private versioned bucket, signer, HEAD, lifecycle proof |
| Parser supervisor runtime | Not implemented | Contract only | Isolation, limits, artifact verification |
| iOS application | Not implemented | Native stack/design authority only | Share Extension, App Group, Preview and final confirmation |
| Desktop Import Portal | Not implemented | Limited-portal design only | Pairing/upload UI and web security evidence |
| Memory Town | Design mature; deferred | Round 1–5 design contracts | Capture / Import P0 blockers first |
| Production | NO-GO | Multiple P0 runtime blockers | Zero unresolved P0 + independent review |

---

# 3. PostgreSQL wording correction

The repository contains RLS and upload-security foundations:

```txt
infra/postgresql/security/001_memory_os_import_rls.sql
infra/postgresql/security/002_memory_os_upload_authorization.sql
infra/postgresql/security/test_memory_os_import_rls.sql
infra/postgresql/security/test_memory_os_upload_authorization.sql
```

They prove or exercise privilege roles, transaction-local owner/epoch context, `ENABLE/FORCE RLS`, owner/epoch policies, immutable security-row restrictions and upload binding constraints.

They do **not** yet provide production models for Preview candidates, safe rejections, immutable ready Preview, deterministic commit keys, Apply, Memory, durable replay/session stores, production indexes or migration/rollback lifecycle.

Use:

```txt
PostgreSQL security/RLS foundation migration and SQL tests:
CREATED

production PostgreSQL domain schema/repositories:
NOT CREATED
```

Do not shorten this to “PostgreSQL complete”.

---

# 4. Preview spool filesystem checkpoint

Created under:

```txt
services/import-api/internal/previewspool/storage.go
services/import-api/internal/previewspool/storage_linux.go
services/import-api/internal/previewspool/storage_unsupported.go
services/import-api/internal/previewspool/storage_linux_test.go
```

Current Linux behavior:

- opens only a supervisor-provisioned absolute canonical root owned by the effective user with exact `0700` mode;
- constrains `spoolId` to one safe path segment;
- creates attempt directories with descriptor-relative `mkdirat`;
- opens attempt directories with `O_DIRECTORY | O_NOFOLLOW`;
- creates fixed accepted/rejected/manifest files with `openat`, `O_CREAT | O_EXCL | O_NOFOLLOW` and exact `0600` mode;
- verifies directory/file type, owner, mode and regular-file link count;
- captures attempt device/inode and rejects directory substitution at cleanup;
- cleans every partial creation stage on cancellation;
- rejects unexpected entries rather than recursively deleting unknown content;
- unlinks substituted fixed-name symlinks without following their targets;
- makes successful cleanup idempotent;
- fails closed on non-Linux platforms instead of silently using a weaker implementation.

Targeted evidence:

```txt
independent reconstructed Linux mini-module:
gofmt + go test -race PASS

actual repository full Go suite:
UNCONFIRMED

remote GitHub Actions:
UNCONFIRMED
```

Limitations still open:

- no canonical record serialization;
- no row/byte limit writer;
- no fsync/seal protocol;
- no manifest writer;
- no independent reader/rehash;
- no expiry scanner or startup reconciliation;
- no disk-full/short-write/crash recovery tests;
- no real supervisor/runtime mount evidence;
- no production DB integration.

---

# 5. Validation status rules

## Confirmed

- schemas, fixtures and validators are present;
- spool structural and semantic negative cases were targeted;
- Go reference code and filesystem tests exist;
- the new filesystem package passed targeted Linux `go test -race` in an independently reconstructed mini-module;
- GitHub Actions workflows exist;
- PostgreSQL 16 jobs are declared.

## Not confirmed for current repository HEAD

- repository-integrated `gofmt`, `go test`, `go vet`, `go test -race` and fuzz suite;
- remote Actions success;
- live Go↔PostgreSQL integration;
- production object-storage behavior;
- production parser isolation;
- iOS/App Group behavior.

Historical PASS claims apply only to the recorded snapshot. Targeted mini-module evidence does not equal full-repository PASS.

---

# 6. Correct implementation roadmap

## Gate 0 — trustworthy baseline

1. run all repository-integrated validators;
2. run exact-current-HEAD Go format/test/vet/race/fuzz;
3. confirm remote Security Contracts, PostgreSQL and Import API workflows;
4. record exact HEAD and commands.

## Gate 1 — private spool filesystem boundary

```txt
STATUS: PARTIAL CHECKPOINT CREATED
```

Created: private root verification, exclusive attempt/files, no-follow operations, inode substitution detection, cancellation cleanup and idempotent cleanup.

Still required before closing Gate 1:

- supervisor startup ownership/mount verification;
- startup reconciliation of abandoned attempts;
- expiry cleanup worker;
- hardlink/substitution coverage for every fixed entry;
- disk-full and close/fsync failure behavior;
- full-repository and remote CI evidence.

## Gate 2 — bounded canonical spool writer/reader

1. encode exact length-prefixed candidate/rejection formats;
2. enforce 100,000 aggregate rows and 512 MiB aggregate bytes during write;
3. compute exact file-byte counts/hashes;
4. flush/fsync and close streams before manifest publication;
5. atomically publish/seal manifest;
6. independently reopen, decode, count and re-hash;
7. reject mismatch before any DB transaction.

## Gate 3 — interruption, tamper and retry evidence

Prove cancellation at every write/flush/seal stage, disk-full/short-write, parser/supervisor crash, truncation/append, symlink/hardlink/cross-attempt substitution, malformed lengths, expiry, cleanup and abandoned-attempt reconciliation.

## Gate 4 — production Preview PostgreSQL domain

Define candidate, rejection and ready Preview tables, commit-key uniqueness, immutable state, contiguous ordinals, FORCE RLS and no partial reader visibility.

## Gate 5 — short atomic `pgx.CopyFrom`

Recheck epoch and all bindings, bulk-copy both streams, verify counts, insert ready Preview and job state atomically, then prove rollback and post-COMMIT acknowledgement-loss recovery.

## Gate 6 — real object storage

Implement private versioned S3-compatible signer/HEAD/lifecycle, exact binding and overwrite/version/expiry/deletion tests.

## Gate 7 — isolated parser supervisor

Implement real non-root networkless process/container, resource limits, exact staged input and reviewed adapter artifact verification.

## Gate 8 — executable API and concrete auth

Compose server lifecycle, Apple code exchange/secret rotation, replay/account/session stores and concrete upload/Preview/Apply repositories.

## Gate 9 — Apply, Memory and deletion

Implement deterministic Memory persistence, exact accounting, account-epoch fencing, deletion race/non-resurrection and safe operational evidence.

## Gate 10 — clients

After backend P0: iOS Share Extension, App Group recovery, Preview/final confirmation, then limited Desktop Portal and its CSP/XSS/token evidence.

Memory Town remains after Capture / Import P0 unresolved count reaches zero.

---

# 7. Immediate next task

```txt
Implement bounded canonical Preview spool stream writers:
8-byte big-endian length prefix
+ exact canonical bytes
+ accepted/rejected format separation
+ aggregate row/byte limits
+ sticky terminal failure
+ no goroutines/channels
+ cancellation/disk-short-write tests
```

Do not add PostgreSQL, S3, parser-container or client work inside this checkpoint.

---

# 8. Release language

Allowed:

```txt
security architecture defined
partial Go security vertical slice exists
Preview spool filesystem lifecycle checkpoint created
production runtime blockers remain
production NO-GO
```

Forbidden without exact evidence:

```txt
security complete
backend complete
PostgreSQL complete
Preview spool complete
all tests pass
production ready
```
