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
Linux attempt filesystem lifecycle created
bounded accepted/rejected writer created
fsync / seal / manifest publication / verifier not implemented

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

`Go backend未実装`は古い。認証境界、transaction scope、Apple JWT/JWKS core、signed-upload core、CSV parser/iterator、Preview hash model、Apply service、Preview spool filesystemとbounded writerが存在する。

ただしexecutable server、production repositories、real object storage、real sandbox、session issuer、sealed spool verifier、iOS clientがないため、正しい表現は **partial security vertical slice**。

---

# 2. Status matrix

| Area | Correct status | Evidence boundary | Remaining blocker |
|---|---|---|---|
| Security architecture / threat model / verification gate | Defined | Round 9 contracts | Independent review and production evidence |
| Machine-readable security contracts | Advanced | 24 schemas, 23 positive contract fixtures | Runtime conformance evidence |
| Negative contract evidence | Advanced | 31 structural, 8 semantic rejections | Full CI and runtime adversarial tests |
| Object authorization contract | Contract complete | 8 cases: 2 allow / 6 deny | Real API/repository integration |
| PostgreSQL RLS foundation | Migration/tests created | 9 table profiles, 14 logic cases, FORCE RLS SQL | Production domain schema, Go repositories, deployment-role proof |
| PostgreSQL live SQL workflow | Created | PostgreSQL 16 workflow and SQL scripts | Remote result unconfirmed; not Go↔DB production integration |
| Sign in with Apple contract | Contract complete | 16 cases: 1 allow / 15 deny | Code exchange, secret rotation, replay store, session issuer |
| Apple verification Go core | Partial | JWT/JWKS verification and interfaces | Concrete persistence/exchange/session composition |
| Signed upload OpenAPI/service | Partial | 3 operations and exact binding interfaces | S3 signer, HEAD adapter, repository, lifecycle evidence |
| Parser sandbox contract | Created | Profile and 16 unsafe mutations | Real supervisor/container/process runtime |
| Archive/JSON/CSV contracts | Created | 25 cases: 1 allow / 24 deny | Runtime corpus and fuzz evidence |
| Generic CSV parser/iterator | Partial | Bounded synchronous pull; sticky failure | Quarantine reader and isolated worker process |
| CSV → Preview bridge | Reference | No hidden goroutines/channels | Production spool/seal/commit path |
| Preview v2 hashing | Reference | Candidate + safe rejection hashes/counts | Production persistence and retry recovery |
| Preview spool manifest | Contract hardened | Attempt/source/format/count/byte/hash/TTL bindings | Runtime seal and independent verification |
| Preview spool filesystem | Partial | Linux no-follow descriptor-relative lifecycle | Startup reconciliation, expiry, deployment proof |
| Preview spool writer | Partial | Exact length-prefixed bytes, bounds, sticky failure | fsync, atomic manifest publication, independent decode/re-hash |
| AtomicMaterializer | Reference only | Hash/decision invariants | Forbidden for production PostgreSQL because parse occurs in transaction callback |
| Apply service | Partial | iOS authority and exact-hash idempotency interfaces | Concrete Preview/Memory repository and deletion fencing |
| Executable Go API | Not implemented | No production `main` lifecycle | Auth/session, repositories, storage and worker composition |
| Object storage runtime | Not implemented | Interfaces/OpenAPI only | Private versioned bucket, signer, HEAD, lifecycle proof |
| Parser supervisor runtime | Not implemented | Contract only | Isolation, limits and artifact verification |
| iOS application | Not implemented | Native stack/design authority only | Share Extension, App Group, Preview and confirmation |
| Desktop Portal | Not implemented | Limited-portal design only | Pairing/upload UI and browser security evidence |
| Memory Town | Design mature; deferred | Round 1–5 design contracts | Capture / Import P0 first |
| Production | NO-GO | Multiple P0 runtime blockers | Zero unresolved P0 + independent review |

---

# 3. PostgreSQL wording correction

Created:

```txt
infra/postgresql/security/001_memory_os_import_rls.sql
infra/postgresql/security/002_memory_os_upload_authorization.sql
infra/postgresql/security/test_memory_os_import_rls.sql
infra/postgresql/security/test_memory_os_upload_authorization.sql
```

These prove/exercise privilege roles, transaction-local owner/epoch context, `ENABLE/FORCE RLS`, owner/epoch policies, immutable security-row restrictions and upload constraints.

They do **not** provide production models for Preview candidates, safe rejections, immutable ready Preview, deterministic commit keys, Apply, Memory, durable replay/session stores, production indexes or migration/rollback lifecycle.

Use:

```txt
PostgreSQL security/RLS foundation migration and SQL tests:
CREATED

production PostgreSQL domain schema/repositories:
NOT CREATED
```

Do not shorten this to `PostgreSQL complete`.

---

# 4. Preview spool implementation checkpoints

## 4.1 Filesystem attempt lifecycle

Implemented under `services/import-api/internal/previewspool`:

- supervisor-provisioned absolute canonical exact-`0700` root;
- descriptor-relative `mkdirat/openat`;
- `O_EXCL/O_NOFOLLOW` fixed-name exact-`0600` files;
- owner/type/mode/link checks;
- attempt device/inode substitution detection;
- partial-construction cancellation cleanup;
- unknown-entry fail-closed cleanup;
- idempotent successful cleanup;
- Linux strong implementation and non-Linux fail-closed behavior.

## 4.2 Bounded stream writer

Implemented:

- accepted/rejected format separation;
- `8-byte big-endian length + canonical bytes` records;
- maximum `100,000` aggregate records;
- maximum `512 MiB` aggregate bytes;
- maximum `2 MiB` per canonical record;
- exact-file-byte SHA-256 including length prefix;
- SHA-256 of empty bytes for zero rejected rows;
- at least one accepted row before successful close;
- no goroutines/channels;
- sticky cancellation, invalid input, limit, short-write, `ENOSPC`, filesystem and lifecycle failure;
- writable handles closed on terminal failure;
- no writer resume after partial record;
- exact-once writer claim;
- empty manifest placeholder removed before writing so final manifest is absent until seal.

Detailed checkpoint:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
```

## 4.3 Explicitly not complete

- no stream `fsync`;
- no `manifest.tmp` writer;
- no atomic rename to `manifest.json`;
- no attempt-directory sync;
- no sealed-state model;
- no independent reader/decode/count/re-hash;
- no append/truncation/malformed-length verifier;
- no startup reconciliation or TTL cleanup;
- no production mount/runtime evidence;
- no PostgreSQL commit integration.

---

# 5. Validation status rules

## Confirmed

- schemas, fixtures and validators are present;
- spool structural and semantic negative cases were targeted;
- filesystem and writer code/tests exist;
- independently reconstructed Linux package passed `gofmt` and `go test -race`;
- interruption reconstruction covers prefix-only cancellation and simulated `ENOSPC`;
- GitHub Actions workflows exist;
- PostgreSQL 16 jobs are declared.

## Not confirmed for exact current repository HEAD

- repository-integrated `gofmt`, `go test`, `go vet`, `go test -race` and fuzz suite;
- remote Actions success;
- live Go↔PostgreSQL integration;
- production object-storage behavior;
- production parser isolation;
- iOS/App Group behavior.

Historical or reconstructed PASS evidence does not equal current full-repository PASS.

---

# 6. Correct implementation roadmap

## Gate 0 — trustworthy baseline

1. run all repository validators;
2. run exact-current-HEAD Go format/test/vet/race/fuzz;
3. confirm remote Security Contracts, PostgreSQL and Import API workflows;
4. record exact HEAD and commands.

## Gate 1 — private spool filesystem

```txt
STATUS: PARTIAL IMPLEMENTATION
```

Still required: supervisor startup/mount proof, startup reconciliation, expiry cleanup, all fixed-entry substitution coverage, and exact current CI evidence.

## Gate 2 — bounded spool writer/seal/verifier

```txt
writer:
PARTIAL IMPLEMENTATION CREATED

seal/verifier:
NOT IMPLEMENTED
```

Next sequence:

1. sync and close accepted/rejected files;
2. write exclusive `manifest.tmp` from exact writer evidence;
3. sync manifest;
4. atomically rename to `manifest.json`;
5. sync attempt directory;
6. mark attempt sealed and prohibit further writes;
7. independently reopen streams and manifest;
8. decode/count/re-hash exact bytes;
9. reject any mismatch before DB work.

## Gate 3 — interruption/tamper/retry evidence

Prove flush/sync/rename failure, parser/supervisor crash, truncation/append, symlink/hardlink/cross-attempt substitution, malformed lengths, expiry, cleanup and abandoned-attempt reconciliation.

## Gate 4 — production Preview PostgreSQL domain

Define candidate, rejection and ready Preview tables, commit-key uniqueness, immutable state, contiguous ordinals, FORCE RLS and no partial reader visibility.

## Gate 5 — short atomic `pgx.CopyFrom`

Recheck epoch and all bindings, bulk-copy both streams, verify counts, insert ready Preview/job state atomically, then prove rollback and post-COMMIT acknowledgement-loss recovery.

## Gates 6–10

6. private versioned object storage;
7. isolated parser supervisor;
8. executable API and concrete Apple auth/session repositories;
9. Apply/Memory/deletion fencing;
10. iOS Share Extension/App Group/confirmation, then limited Portal.

Memory Town remains after Capture / Import P0 unresolved count reaches zero.

---

# 7. Immediate next task

```txt
Implement Preview spool seal and manifest publication only:
stream fsync
→ close confirmation
→ exclusive manifest.tmp
→ manifest fsync
→ atomic rename
→ directory fsync
→ sealed state
```

Do not add PostgreSQL, S3, parser-container or client work inside this checkpoint.

---

# 8. Release language

Allowed:

```txt
security architecture defined
partial Go security vertical slice exists
Preview spool filesystem and bounded writer checkpoints created
seal/verifier and production runtime blockers remain
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
