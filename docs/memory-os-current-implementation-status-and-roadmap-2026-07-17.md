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
contract hardened
runtime not implemented

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

「Go backend未実装」は古い。`services/import-api/`には認証境界、transaction scope、Apple JWT/JWKS core、signed upload core、CSV parser/iterator、Preview hash model、Apply serviceなどが存在する。

ただし、executable server、production repositories、real object storage、real sandbox、session issuer、iOS clientが存在しないため、「backend実装済み」も不正確である。正確な表現は **partial security vertical slice**。

---

# 2. Status matrix

| Area | Correct status | Evidence boundary | Remaining blocker |
|---|---|---|---|
| Security architecture / threat model / verification gate | Defined | Human-readable Round 9 contracts | Independent review and production evidence |
| Machine-readable security contracts | Advanced | 24 registered schemas, 23 positive contract fixtures | Runtime conformance evidence |
| Negative contract evidence | Advanced | 31 structural rejections, 8 semantic rejections | Full CI result and runtime adversarial tests |
| Object authorization contract | Contract complete | 8 cases: 2 allow / 6 deny | Real API/repository authorization integration |
| PostgreSQL RLS contract | Contract and foundation migration created | 9 table profiles, 14 logic cases, FORCE RLS SQL | Production domain schema, Go repository and deployment-role proof |
| PostgreSQL live SQL test | Created | PostgreSQL 16 workflow and SQL scripts exist | Remote run result unconfirmed; not a Go↔DB production integration test |
| Sign in with Apple contract | Contract complete | 16 cases: 1 allow / 15 deny | Concrete code exchange, client-secret rotation, replay store, session issuer |
| Apple verification Go core | Partial implementation | JWT/JWKS validation and binding interfaces | Concrete persistence/exchange/session composition |
| Signed upload OpenAPI | Created | 3 operations and validator | Concrete private versioned storage enforcement |
| Signed upload Go service | Partial implementation | Exact request/object metadata binding interfaces | S3-compatible signer, HEAD adapter, repository, lifecycle evidence |
| Parser sandbox contract | Created | Sandbox profile and 16 unsafe mutations | Real supervisor/container/process runtime |
| Archive/JSON/CSV safety contracts | Created | 25 cases: 1 allow / 24 deny | Selected library/runtime corpus and fuzz evidence |
| Generic CSV parser and iterator | Partial implementation | Bounded parser; synchronous pull; sticky failure | Concrete quarantine reader and isolated worker process |
| CSV → Preview bridge | Reference implementation | No hidden goroutines/channels; one row per call | Production spool and commit path |
| Preview v2 hashing | Reference implementation | Candidate + safe rejection hashes/counts | Production persistence and retry recovery |
| Preview spool manifest | Contract hardened | Attempt ID, formats, counts, bytes, TTL and semantic validator | Filesystem writer/reader/rehash/cleanup runtime |
| AtomicMaterializer | Reference only | Invariant tests | Forbidden for production PostgreSQL because parse occurs inside callback transaction |
| Apply service | Partial implementation | iOS-only authority and exact-hash idempotency interfaces | Concrete Preview/Memory repository and deletion fencing |
| Executable Go API | Not implemented | No production `main` composition/server lifecycle | Auth/session, repositories, storage and worker composition |
| Object storage runtime | Not implemented | Interfaces and SQL/OpenAPI only | Private versioned bucket, signer, HEAD, overwrite/TTL/cancellation proof |
| Parser supervisor runtime | Not implemented | Contract only | Process/container isolation, resource limits, artifact verification |
| iOS application | Not implemented | Native stack/design authority only | Share Extension, App Group, Preview and final confirmation |
| Desktop Import Portal | Not implemented | Limited-portal design only | Pairing/upload UI, CSP/XSS/token evidence |
| Memory Town | Design mature; implementation deferred | Round 1–5 design contracts | Capture / Import P0 blockers must close first |
| Production | NO-GO | Multiple P0 runtime blockers | Zero unresolved P0 + independent review |

---

# 3. PostgreSQL wording correction

The repository contains:

```txt
infra/postgresql/security/001_memory_os_import_rls.sql
infra/postgresql/security/002_memory_os_upload_authorization.sql
infra/postgresql/security/test_memory_os_import_rls.sql
infra/postgresql/security/test_memory_os_upload_authorization.sql
```

These are valuable executable security foundations. They prove or exercise:

- privilege-role attributes;
- transaction-local owner/epoch context;
- `ENABLE RLS` and `FORCE RLS`;
- owner/epoch `USING` and `WITH CHECK` behavior;
- immutable security-row role restrictions;
- upload authorization binding columns and constraints.

They do **not** yet provide the production data model for:

- normalized Preview candidates;
- safe rejection records;
- immutable ready Preview rows with both stream hashes;
- deterministic Preview commit keys;
- Apply operations and Memory records;
- durable replay/account/session stores;
- production indexes, retention and migration/rollback lifecycle.

Therefore use:

```txt
PostgreSQL security/RLS foundation migration and SQL integration tests:
CREATED

production PostgreSQL schema/repositories:
NOT CREATED
```

Do not shorten this to “PostgreSQL complete”.

---

# 4. Validation status rules

## Confirmed

- machine-readable schemas and fixtures are present;
- dedicated validators are present;
- Preview spool schema structural mutations were targeted and rejected;
- Preview spool semantic validator was targeted with six invalid cases;
- Go unit/reference code exists;
- GitHub Actions workflows exist;
- PostgreSQL 16 service jobs are declared in workflow configuration.

## Not confirmed for current HEAD

- full local `gofmt`, `go test`, `go vet`, `go test -race` and fuzz suite after every latest change;
- remote GitHub Actions success for the current `so` HEAD;
- live Go↔PostgreSQL integration;
- production-equivalent object storage behavior;
- production-equivalent parser isolation;
- iOS/App Group behavior.

Historical PASS claims must be labeled with the commit/snapshot they applied to. Do not carry them forward after code changes without rerunning.

---

# 5. Correct implementation roadmap

The next work is intentionally boundary-first rather than feature-first.

## Gate 0 — establish a trustworthy baseline

1. run repository-integrated security validators;
2. run `gofmt` check, `go test ./...`, `go vet ./...`, `go test -race ./...`;
3. run both short fuzz smoke targets;
4. confirm remote Security Contracts, live PostgreSQL and Import API workflow results;
5. record exact HEAD and commands, without claiming production readiness.

## Gate 1 — private spool filesystem boundary

1. create a supervisor-owned private root;
2. create one server-generated `spoolId` directory per parse attempt with mode `0700`;
3. create fixed-name accepted/rejected/manifest files with exclusive `0600` semantics;
4. use descriptor-relative, no-follow filesystem operations;
5. reject existing files, non-regular files, symlinks, hardlinks and unsafe modes;
6. make cleanup idempotent and safe after partial construction.

## Gate 2 — bounded canonical spool writer/reader

1. encode exact length-prefixed candidate and rejection formats;
2. enforce 100,000 aggregate row and 512 MiB aggregate spool limits while writing;
3. compute stream byte lengths/counts/hashes from exact file bytes;
4. write manifest only after both streams close successfully;
5. seal the attempt;
6. independently reopen, decode, count and re-hash before database work;
7. reject manifest/stream mismatches without opening a transaction.

## Gate 3 — interruption, tamper and retry evidence

Prove:

- cancellation during every write/flush/seal stage;
- disk-full/short-write behavior;
- parser crash and supervisor restart;
- truncation and append after manifest creation;
- symlink/hardlink and cross-job/cross-attempt substitution;
- malformed length prefix and oversized internal record;
- expiry during parse and before commit;
- cleanup after success, failure, cancellation and expiry;
- rerunning an abandoned attempt never resumes partial bytes.

## Gate 4 — production Preview PostgreSQL domain

1. define candidate, rejection and ready Preview tables;
2. bind owner, epoch, job, source, adapter, options and stream evidence;
3. define deterministic commit-key uniqueness;
4. enforce immutable ready state and contiguous ordinals;
5. extend FORCE RLS tests for all new tables;
6. prohibit API/Portal visibility of partial state.

## Gate 5 — short atomic `pgx.CopyFrom` repository

1. verify canonical account epoch immediately before commit;
2. verify source version/size/checksum and adapter artifact;
3. bulk-copy accepted and rejected streams in one transaction;
4. verify inserted counts and ordinals;
5. insert final ready Preview and update Import Job in the same transaction;
6. prove rollback on candidate, rejection and finalization failures;
7. prove post-COMMIT acknowledgement-loss retry returns exactly one Preview.

## Gate 6 — real object storage

1. implement S3-compatible signer and HEAD adapter;
2. require private non-listable versioned quarantine storage;
3. bind exact headers, size, checksum, content type and generated key;
4. test overwrite/version substitution, expiry and cancellation;
5. implement lifecycle cleanup and deletion-epoch revocation.

## Gate 7 — isolated parser supervisor

1. launch a real non-root networkless process/container;
2. enforce read-only root, capability drop, seccomp/MAC and resource limits;
3. stage exact version-bound read-only input;
4. verify reviewed adapter artifact digest before execution;
5. keep credentials and private logs outside parser reach;
6. archive malicious/fuzz corpus evidence.

## Gate 8 — executable API and concrete auth

1. compose server lifecycle and graceful cancellation;
2. implement Apple authorization-code exchange and client-secret rotation;
3. implement replay/account/session repositories;
4. wire scoped PostgreSQL transactions and concrete upload/Preview/Apply repositories;
5. add strict Preview/Apply HTTP boundaries and safe error mapping.

## Gate 9 — Apply, Memory persistence and deletion

1. implement deterministic Memory write/duplicate policy;
2. preserve exact Preview accounting;
3. fence active jobs, signed URLs, spools and Apply by account epoch;
4. prove deletion race and backup-restore non-resurrection;
5. add sensitive-log canary and supply-chain gates.

## Gate 10 — client vertical slices

Only after backend P0 gates:

1. iOS Share Extension for URL/text;
2. minimal App Group intake and crash recovery;
3. safe Preview presentation and final iOS confirmation;
4. limited Desktop Portal pairing/upload;
5. CSP/XSS/browser-token tests.

Memory Town implementation remains after Capture / Import P0 unresolved count reaches zero.

---

# 6. Immediate next task

```txt
Implement supervisor-owned Preview spool attempt storage:
0700 attempt directory
+ fixed exclusive 0600 files
+ no-follow descriptor-relative operations
+ idempotent terminal cleanup
+ cancellation and substitution tests
```

Do not add PostgreSQL persistence or object-storage networking inside this task. Keep the first implementation checkpoint limited to filesystem ownership, lifecycle and interruption semantics.

---

# 7. Release language

Allowed:

```txt
security architecture defined
contract and reference implementation advanced
partial Go security vertical slice exists
production runtime blockers remain
production NO-GO
```

Forbidden:

```txt
security complete
backend complete
PostgreSQL complete
safe by design therefore production-ready
all tests pass
```

The last phrase is forbidden unless the exact current HEAD, commands and remote workflow results are recorded.
