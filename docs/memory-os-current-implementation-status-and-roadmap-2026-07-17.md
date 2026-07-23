# Memory OS Current Implementation Status and Roadmap

最終更新: 2026-07-20

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
production Preview domain schema (SQL + live tests) created
atomic Go Preview commit repository created (live-tested)

Preview spool:
manifest contract hardened
Linux attempt filesystem lifecycle created
bounded accepted/rejected writer created
stream fsync + no-replace manifest publication created
independent decode / count / re-hash verifier created
startup reconciliation + TTL cleanup created

object storage runtime:
signed-upload adapter created (live-tested against MinIO)

parser sandbox runtime:
process-boundary supervisor created (live-tested); network namespace remains deployment work

supervised import flow:
composed and live-tested end to end (fetch → parse → verify → commit)

canonical adapter record contract:
created and cross-language machine-validated; real Generic CSV adapter wired through the supervised worker

iOS / Desktop Portal:
not implemented

exact current HEAD Go suite:
confirmed in a local golang:1.23 Linux container

remote GitHub Actions:
import-flow HEAD 381c514 confirmed green (Import API run 29793196253 with live flow tests, Security Contracts run 29793196257)

production:
NO-GO
```

`Go backend未実装`は古い。一方、executable server、production repositories、real object storage、real sandbox、session issuer、iOS clientがないため、`backend完成`も誤り。正確な表現は **partial security vertical slice**。

---

# 2. Status matrix

| Area | Correct status | Evidence boundary | Remaining blocker |
|---|---|---|---|
| Security architecture / threat model | Defined | Round 9 contracts | Independent review and production evidence |
| Machine-readable security contracts | Advanced | 24 schemas, 23 positive fixtures | Runtime conformance evidence |
| Negative contract evidence | Advanced | 31 structural, 8 semantic rejections | Full CI and runtime adversarial tests |
| Object authorization | Contract complete | 8 cases: 2 allow / 6 deny | Real API/repository integration |
| PostgreSQL RLS foundation | Migration/tests created | FORCE RLS SQL, 9 table profiles, 14 logic cases | Deployment-role proof |
| Preview PostgreSQL domain | Created (SQL) | preview_ready/candidate/rejection, commit key, immutability, completeness gate, live SQL tests | Fixture-contract extension, deployment-role proof |
| Preview commit repository | Partial | Atomic worker-role transaction, deterministic commit key, idempotent/conflicting retry, rollback, e2e spool→DB proof on live PostgreSQL | Canonical-record contract, deletion-fence recheck |
| Supervised import flow | Composed | fetch → parse → seal → verify → decode → commit proven on live PostgreSQL + MinIO; drift/checksum/crash/bad-record fail closed | Job orchestration, deletion-fence timing |
| Canonical adapter record contract | Created | Schema + 22-case fixture cross-validated by Go and Python; genericcsv wired through the supervised worker end to end | Separate digest-pinned worker binary, independent human review |
| PostgreSQL live workflow | Created and green | PostgreSQL 16 jobs in both workflows, remote runs confirmed | Deployment-role and production-environment proof |
| Sign in with Apple contract | Contract complete | 16 cases: 1 allow / 15 deny | Code exchange, secret rotation, replay store, session issuer |
| Apple JWT/JWKS Go core | Partial | Verification and binding interfaces | Concrete composition and persistence |
| Signed upload OpenAPI/service | Partial | Exact request/object metadata binding | Concrete repository composition, lifecycle proof |
| Object storage adapter | Partial | SDK-free SigV4 presign binding length/type/checksum as signed headers, versioned HEAD, MinIO live tests | TLS + scoped production credentials, lifecycle configuration evidence |
| Parser sandbox contract | Created | Profile and 16 unsafe mutations | Container/namespace deployment evidence |
| Parser supervisor | Partial | Digest-pinned worker, credential-free env, prlimit AS/CPU/FSIZE bounds, frame protocol, kill+fail-closed cleanup, e2e seal+verify | Network namespace/seccomp deployment, reviewed adapter artifact, fork-freeze shim |
| Archive/JSON/CSV contracts | Created | 25 cases: 1 allow / 24 deny | Runtime corpus and fuzz evidence |
| Generic CSV parser/iterator | Partial | Bounded synchronous pull; sticky failure | Quarantine reader and isolated worker |
| CSV → Preview bridge | Reference | No hidden goroutine/channel | Production verified spool and commit path |
| Preview v2 hashing | Reference | Candidate + safe rejection hashes/counts | Production persistence/retry recovery |
| Preview spool manifest | Contract hardened | Attempt/source/format/count/byte/hash/TTL binding | Production commit integration |
| Preview filesystem | Partial | Linux descriptor-relative no-follow lifecycle | Deployment mount proof |
| Preview writer | Partial | Exact length-prefixed bytes, bounds, sticky terminal failure | Production commit integration |
| Preview seal/publication | Partial | stream fsync, exclusive temp, linkat no-replace, directory fsync | Production commit integration |
| Preview verifier | Partial | Strict canonical decode, bounded re-scan, exact re-count/re-hash, binding/expiry rejection | Commit-path integration |
| Preview reconciliation | Partial | Startup classification, residue removal, publication completion, TTL cleanup, fail-closed quarantine | Deployment supervisor exclusivity proof, quarantine alerting |
| AtomicMaterializer | Reference only | Hash/decision invariants | Forbidden for production PostgreSQL; parse occurs inside transaction callback |
| Apply service | Partial | iOS authority and exact-hash idempotency interfaces | Concrete Preview/Memory repository and deletion fencing |
| Runtime-role DB access | Partial | pgx scoped executor + concrete upload repository; FORCE RLS proven with runtime roles (42501 privilege probe, tenant isolation, full upload lifecycle) | NOSUPERUSER production login, scan worker, remaining repositories |
| Executable Go API | Not implemented | No production `main` lifecycle | HTTP main, session middleware, Apple exchange composition |
| Object storage runtime | Adapter created | SigV4 signer/HEAD proven on live versioned MinIO bucket | Production bucket policy, lifecycle and TLS deployment proof |
| Parser supervisor runtime | Process boundary created | prlimit-bounded digest-pinned worker with targeted isolation tests | Network namespace, seccomp and container deployment evidence |
| iOS / Portal | Not implemented | Technology/design authority only | Client vertical slices and security evidence |
| Memory Town | Design mature; deferred | Round 1–5 contracts | Capture / Import P0 first |
| Production | NO-GO | Multiple P0 runtime blockers | Zero unresolved P0 + independent review |

---

# 3. PostgreSQL wording correction

Created:

```txt
infra/postgresql/security/001_memory_os_import_rls.sql
infra/postgresql/security/002_memory_os_upload_authorization.sql
infra/postgresql/security/003_memory_os_preview_domain.sql
infra/postgresql/security/test_memory_os_import_rls.sql
infra/postgresql/security/test_memory_os_upload_authorization.sql
infra/postgresql/security/test_memory_os_preview_domain.sql
```

These prove/exercise privilege roles, transaction-local owner/epoch context, `ENABLE/FORCE RLS`, owner/epoch policies, immutable security-row restrictions, upload constraints, and now the production Preview domain: `preview_ready` / `preview_candidate` / `preview_rejection` with deterministic commit keys, one-ready-Preview-per-job, exact seal-evidence bindings, structurally safe rejections and the `assert_preview_complete` contiguity gate.

The atomic Go commit repository over this schema now exists in `services/import-api/internal/previewcommit` (live-tested; note PostgreSQL forbids `COPY FROM` under RLS, so it uses the contract-allowed parameterized `INSERT ... unnest` equivalent).

They do **not** provide Apply/Memory tables, durable replay/session stores or a production migration/rollback lifecycle.

Use:

```txt
PostgreSQL security/RLS foundation + Preview domain migrations and SQL tests:
CREATED

atomic Go Preview commit repository:
PARTIAL IMPLEMENTATION CREATED (live-tested)

Apply/Memory persistence:
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

## 4.4 Independent sealed-spool verifier

Created:

- descriptor-relative `O_NOFOLLOW` re-open of attempt, manifest and both streams;
- fixed-name allowlist with `manifest.tmp`-residue and unknown-entry rejection;
- regular/`0600`/single-link/owner checks on every entry;
- strict single-value JSON decode with unknown fields forbidden;
- canonical re-serialization equality against the seal builder;
- expiry enforcement against the caller clock;
- exact job/owner/epoch/source/adapter/options expectation matching;
- bounded length-prefix re-decode with record/byte limits enforced while reading;
- independent re-count and exact-byte SHA-256 of both streams;
- stream mismatch, malformed framing and binding mismatch as distinct rejections;
- stateless retryable read-only verification;
- non-Linux fail-closed behavior.

Detailed evidence:

```txt
docs/memory-os-preview-spool-stream-writer-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-seal-checkpoint-2026-07-17.md
docs/memory-os-preview-spool-verifier-checkpoint-2026-07-17.md
```

## 4.5 Startup reconciliation and TTL cleanup

Created:

- one exclusive startup pass under the manager lock, deterministic name order;
- sealed / unsealed / temp-residue / completed-publication / unknown classification;
- fixed-name-only removal of crash residue and expired sealed attempts;
- completion of the linkat crash window when both manifest names share one inode;
- fail-closed in-place quarantine of everything unclassifiable, with a reportable list;
- sealed unexpired attempts never deleted and still verifiable afterwards;
- resumable cancellation and non-Linux fail-closed behavior.

Detailed evidence:

```txt
docs/memory-os-preview-spool-reconciliation-checkpoint-2026-07-18.md
```

## 4.6 Explicitly incomplete

- no production mount/runtime evidence;
- no deployment proof of exclusive startup reconciliation;
- no operator alerting for quarantined residue;
- no production PostgreSQL commit integration.

A published manifest is untrusted until its verification passes; verification is now implemented, and the commit path must run it (and re-check epoch/job state) inside its own transaction boundary.

---

# 5. Validation status

Confirmed for the exact repository-integrated module at code HEAD `5c3dc4bc2179800c8530961a773963f96797f4d5` in a local `golang:1.23` Linux container with fresh `postgres:16` and MinIO:

```txt
gofmt -l . (empty):
PASS

go vet ./...:
PASS

go test ./... + go test -race ./... (17 packages, live DB/object-store/supervision/import-flow tests included):
PASS

both 5s fuzz smokes:
PASS

scripts/validate-memory-os-preview-spool.py and validate-memory-os-security.py:
PASS
```

The previously failing suite (five unformatted sources and one pointer-receiver compile error) was repaired at the verifier checkpoint; every push since has run green.

Also confirmed after push: Import API Security Slice run 29793196253 (live import-flow tests executed against the CI postgres + MinIO services) and Security Contracts run 29793196257 succeeded on pushed HEAD `381c514` (code identical to `5c3dc4b`).

Not confirmed:

- live Go↔PostgreSQL integration;
- production object-storage behavior;
- production parser isolation;
- iOS/App Group behavior.

A local container run is repository evidence, not production or deployment evidence.

---

# 6. Correct implementation roadmap

## Gate 0 — trustworthy baseline

1. run repository validators — done at this checkpoint (Preview spool and security validators);
2. run exact-current-HEAD Go format/test/vet/race/fuzz — done at this checkpoint in a local `golang:1.23` Linux container;
3. confirm remote Security Contracts, PostgreSQL and Import API workflows — Import API runs had failed on formatting/vet since before the seal checkpoint; repaired here, and the pushed verifier HEAD ran green;
4. record exact HEAD and commands — recorded in the verifier checkpoint document.

## Gate 1 — private spool filesystem

Status: **partial implementation**. Startup reconciliation, expiry cleanup and crash-residue handling are now created; remaining: supervisor mount proof and deployment exclusivity evidence.

## Gate 2 — bounded writer / seal / verifier

```txt
writer:
PARTIAL IMPLEMENTATION CREATED

seal/publication:
PARTIAL IMPLEMENTATION CREATED

independent verifier:
PARTIAL IMPLEMENTATION CREATED
```

## Gate 3 — interruption/tamper/retry evidence

Proved at the verifier boundary: truncation, appended records, torn appends, malformed length prefixes, same-length content substitution, hard links, symlinks, wrong modes, temp residue, spoofed spool IDs and expiry.

Proved at the reconciliation boundary: crash-residue classification, publication completion, TTL removal, fail-closed quarantine and mid-pass cancellation resumability.

Gate 3 is closed at the package boundary; production still requires deployment-level exclusivity and mount evidence.

Immediate sequence (Gate 4):

1. define candidate/rejection/ready Preview tables with deterministic commit keys;
2. enforce immutability, contiguous ordinals and FORCE RLS profiles;
3. prove no partial reader visibility with SQL tests before any Go repository code.

## Gate 4 — production Preview PostgreSQL domain

Status: **SQL created and live-tested**. `preview_ready`/`preview_candidate`/`preview_rejection` exist with commit-key uniqueness, immutability, ordinal bounds + `assert_preview_complete` contiguity gate, FORCE RLS and atomic-only visibility. Remaining: fixture-contract extension and deployment-role proof.

## Gate 5 — short atomic commit repository

Status: **partial implementation created and live-tested**. PostgreSQL rejects `COPY FROM` under row-level security, so bulk loading uses the contract-allowed equivalent parameterized `INSERT ... unnest` protocol as the worker role with FORCE RLS in force. Atomicity, deterministic commit-key idempotency, conflicting-retry rejection, rollback and the end-to-end spool→verify→commit flow are proven against live PostgreSQL 16 (locally and in CI). Remaining: supervisor composition, canonical-record contract and deletion-fence recheck.

## Gate 6 — private versioned object storage

Status: **adapter created and live-tested** (SDK-free SigV4 presign + versioned HEAD against MinIO). Remaining: production bucket policy, lifecycle and TLS deployment evidence.

## Gate 7 — isolated parser supervisor

Status: **process boundary created and live-tested** (digest pinning, credential-free env, kernel resource bounds, frame protocol, fail-closed cleanup, end-to-end seal+verify). Remaining: network-namespace/seccomp/container deployment evidence and reviewed adapter artifacts.

## Gate 8 — supervised flow composition

Status: **composed and live-tested end to end** (importflow). Remaining: reviewed canonical adapter record contract and production job orchestration.

## Gate 8.5 — canonical adapter record contract

Status: **created and cross-language machine-validated**. One schema + shared 22-case fixture enforced by both `internal/canonrecord` tests and `scripts/validate-memory-os-canonical-records.py` (CI-gated); the real Generic CSV adapter now runs through the supervised worker in the end-to-end flow, replacing the interim placeholder decode. Remaining: a separately built digest-pinned worker binary (arrives with the CLI checkpoint) and independent human review (global blocker).

## Gate 9 — minimal CLI harness

Status: **created, live-tested, and executed for real** (`cmd/importctl` + `cmd/parser-worker` + `scripts/dev-import.sh`). One command imports a local CSV through the full supervised pipeline — presigned upload, digest-pinned separate worker binary, seal, independent verification, canonical decode, atomic commit — and prints the committed Preview. The CLI is a dev tool (superuser read-back; never production). Remaining: the executable API reads through runtime roles instead.

## Gates 10–12

10. executable API and concrete Apple auth/session repositories;
11. Apply/Memory/deletion fencing;
12. iOS Share Extension/App Group/confirmation, then limited Portal.

Memory Town remains after Capture / Import P0 unresolved count reaches zero.

---

# 7. Release language

Allowed:

```txt
security architecture defined
partial Go security vertical slice exists
Preview spool filesystem, writer, seal-publication, independent-verifier and reconciliation checkpoints created
production Preview PostgreSQL domain schema and atomic commit repository created with live tests
signed-upload object storage adapter created with live MinIO tests
process-boundary parser supervisor created with targeted isolation tests
supervised import flow composed and live-tested end to end
repository-integrated Go suite passes in a Linux container at the recorded HEAD
reviewed adapter contract, executable server and client blockers remain
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
