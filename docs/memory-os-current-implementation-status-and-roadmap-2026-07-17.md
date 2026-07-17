# Memory OS Current Implementation Status and Roadmap

最終更新: 2026-07-17

この文書は、設計済み・契約済み・部分実装・実環境未検証を混同しないための現在地正本である。

矛盾時は `docs/memory-os-current-authority-order-round-9-security.md` を優先する。

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
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier not implemented

object storage runtime:
not implemented

parser sandbox runtime:
not implemented

iOS / Desktop Portal:
not implemented

exact current HEAD remote GitHub Actions:
unconfirmed

production:
NO-GO
```

`Go backend未実装`は古い。一方、executable server、production repositories、real object storage、real sandbox、session issuer、sealed-spool verifier、iOS clientがないため、`backend完成`も誤り。正確な表現は **partial security vertical slice**。

---

# 2. Status matrix

| Area | Correct status | Evidence boundary | Remaining blocker |
|---|---|---|---|
| Security architecture / threat model | Defined | Round 9 contracts | Independent review and production evidence |
| Machine-readable security contracts | Advanced | 24 schemas, 23 positive fixtures | Runtime conformance evidence |
| Negative contract evidence | Advanced | 31 structural, 8 semantic rejections | Full CI and runtime adversarial tests |
| Object authorization | Contract complete | 8 cases: 2 allow / 6 deny | Real API/repository integration |
| PostgreSQL RLS foundation | Migration/tests created | FORCE RLS SQL, 9 table profiles, 14 logic cases | Production domain schema/repositories/deployment-role proof |
| PostgreSQL live workflow | Created | PostgreSQL 16 workflow and SQL scripts | Remote result unconfirmed; not Go↔DB production integration |
| Sign in with Apple contract | Contract complete | 16 cases: 1 allow / 15 deny | Code exchange, secret rotation, replay store, session issuer |
| Apple JWT/JWKS Go core | Partial | Verification and binding interfaces | Concrete composition and persistence |
| Signed upload OpenAPI/service | Partial | Exact request/object metadata binding | S3 signer, HEAD adapter, repository, lifecycle proof |
| Parser sandbox contract | Created | Profile and 16 unsafe mutations | Real supervisor/container/process runtime |
| Archive/JSON/CSV contracts | Created | 25 cases: 1 allow / 24 deny | Runtime corpus and fuzz evidence |
| Generic CSV parser/iterator | Partial | Bounded synchronous pull; sticky failure | Quarantine reader and isolated worker |
| CSV → Preview bridge | Reference | No hidden goroutine/channel | Production verified spool and commit path |
| Preview v2 hashing | Reference | Candidate + safe rejection hashes/counts | Production persistence/retry recovery |
| Preview spool manifest | Contract hardened | Attempt/source/format/count/byte/hash/TTL binding | Independent runtime verification |
| Preview filesystem | Partial | Linux descriptor-relative no-follow lifecycle | Startup reconciliation, expiry, deployment proof |
| Preview writer | Partial | Exact length-prefixed bytes, bounds, sticky terminal failure | Independent reader and crash reconciliation |
| Preview seal/publication | Partial | stream fsync, exclusive temp, linkat no-replace, directory fsync | Independent decode/count/re-hash verifier |
| AtomicMaterializer | Reference only | Hash/decision invariants | Forbidden for production PostgreSQL; parse occurs inside transaction callback |
| Apply service | Partial | iOS authority and exact-hash idempotency interfaces | Concrete Preview/Memory repository and deletion fencing |
| Executable Go API | Not implemented | No production `main` lifecycle | Auth/session/repositories/storage/worker composition |
| Object storage runtime | Not implemented | Interfaces/OpenAPI only | Private versioned bucket, signer, HEAD, lifecycle proof |
| Parser supervisor runtime | Not implemented | Contract only | Isolation, limits and artifact verification |
| iOS / Portal | Not implemented | Technology/design authority only | Client vertical slices and security evidence |
| Memory Town | Design mature; deferred | Round 1–5 contracts | Capture / Import P0 first |
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

They do **not** provide production Preview candidate/rejection/ready tables, deterministic commit keys, Apply/Memory tables, durable replay/session stores, production indexes or migration/rollback lifecycle.

Use:

```txt
PostgreSQL security/RLS foundation migration and SQL tests:
CREATED

production PostgreSQL domain schema/repositories:
NOT CREATED
```

---

# 4. Preview spool checkpoints

## 4.1 Filesystem lifecycle

Created:

- exact supervisor-owned `0700` root;
- descriptor-relative `mkdirat/openat`;
- `O_EXCL/O_NOFOLLOW` fixed `0600` entries;
- type/owner/mode/link checks;
- attempt device/inode substitution detection;
- partial-construction cancellation cleanup;
- unknown-entry fail-closed cleanup;
- Linux strong implementation and non-Linux fail-closed behavior.

## 4.2 Bounded writer

Created:

- separate accepted/rejected formats;
- `8-byte big-endian length + canonical bytes`;
- 100,000 aggregate records;
- 512 MiB aggregate bytes;
- 2 MiB per record;
- exact-file-byte SHA-256 including prefix;
- sticky cancellation/limit/short-write/`ENOSPC`/lifecycle failure;
- terminal close and no partial resume;
- exact-once writer claim.

## 4.3 Seal and manifest publication

Created:

- exact binding and TTL validation;
- accepted/rejected stream `fsync` before close;
- exclusive `manifest.tmp` with exact `0600` and no-follow semantics;
- deterministic compact JSON manifest;
- manifest `fsync` before publication;
- `linkat` no-replace publication to `manifest.json`;
- temp unlink followed by attempt-directory `fsync`;
- rollback of the final name on directory-sync failure;
- explicit `ErrSealDurabilityUncertain` when rollback durability cannot be proved;
- same-Sealer/same-input idempotency and conflicting-input rejection;
- non-Linux fail-closed behavior.

Detailed evidence:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md
```

## 4.4 Explicitly incomplete

- no independent strict manifest decoder;
- no independent length-prefixed stream decoder;
- no count/byte/hash re-verification;
- no truncation/append/malformed-length verifier;
- no startup reconciliation for crash residue such as `manifest.tmp` or both linked names;
- no TTL cleanup worker;
- no production mount/runtime evidence;
- no production PostgreSQL commit integration.

A published manifest is **not yet trusted**. Database work remains forbidden until the independent verifier passes.

---

# 5. Validation status

Confirmed for the targeted reconstructed package:

```txt
gofmt:
PASS

go test -race:
PASS

go vet:
PASS
```

Covered: successful publication, exact final mode/link count, same-input idempotency, binding conflict, stream-fsync failure, cancellation between stream syncs, short manifest write, manifest-fsync failure, existing final preservation, temp symlink attack, directory-sync rollback and durability-uncertain failure.

Not confirmed for the exact current repository HEAD:

- repository-integrated format/test/vet/race/fuzz suite;
- remote Actions success;
- live Go↔PostgreSQL integration;
- production object-storage behavior;
- production parser isolation;
- iOS/App Group behavior.

Targeted reconstruction is not full-repository or production evidence.

---

# 6. Correct implementation roadmap

## Gate 0 — trustworthy baseline

1. run repository validators;
2. run exact-current-HEAD Go format/test/vet/race/fuzz;
3. confirm remote Security Contracts, PostgreSQL and Import API workflows;
4. record exact HEAD and commands.

## Gate 1 — private spool filesystem

Status: **partial implementation**. Remaining: supervisor mount proof, startup reconciliation, expiry cleanup, crash residue handling and exact-current CI evidence.

## Gate 2 — bounded writer / seal / verifier

```txt
writer:
PARTIAL IMPLEMENTATION CREATED

seal/publication:
PARTIAL IMPLEMENTATION CREATED

independent verifier:
NOT IMPLEMENTED
```

Immediate sequence:

1. open attempt and fixed entries descriptor-relative with `O_NOFOLLOW`;
2. require final manifest regular `0600`, one link, and temp absent;
3. strictly decode manifest and validate all bindings/TTL/security constants;
4. independently decode both length-prefixed streams;
5. enforce record/byte bounds while reading;
6. independently count and SHA-256 exact bytes;
7. compare every count/byte/hash/format binding;
8. reject all mismatch before any database transaction.

## Gate 3 — interruption/tamper/retry evidence

Prove truncation, append, malformed lengths, hardlinks, cross-attempt substitution, crash residue, expiry and startup reconciliation.

## Gate 4 — production Preview PostgreSQL domain

Define candidate/rejection/ready Preview tables, commit-key uniqueness, immutability, contiguous ordinals, FORCE RLS and no partial reader visibility.

## Gate 5 — short atomic `pgx.CopyFrom`

Recheck epoch and all bindings, bulk-copy both streams, verify counts, insert ready Preview/job state atomically, then prove rollback and post-COMMIT retry recovery.

## Gates 6–10

6. private versioned object storage;
7. isolated parser supervisor;
8. executable API and concrete Apple auth/session repositories;
9. Apply/Memory/deletion fencing;
10. iOS Share Extension/App Group/confirmation, then limited Portal.

Memory Town remains after Capture / Import P0 unresolved count reaches zero.

---

# 7. Release language

Allowed:

```txt
security architecture defined
partial Go security vertical slice exists
Preview spool filesystem, writer and seal-publication checkpoints created
independent verifier and production runtime blockers remain
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
