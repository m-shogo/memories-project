# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-16

## Current verdict

```txt
product hierarchy:
Capture / Import first

platform:
iOS canonical client + limited Desktop Import Portal

security architecture / threat model / verification gate:
defined

machine-readable security foundation:
22 schemas / 21 tracked contract fixtures

first executable Go backend security slice:
created

local Go test / vet / race:
PASS

concrete PostgreSQL / object storage / parser runtime / iOS / Portal:
incomplete

GitHub Actions remote result:
not confirmed by the available connector

production:
NO-GO
```

Securityについて「完璧」「安全が保証された」とは表現しない。

---

# 1. Authority order

矛盾時は上を優先する。

1. `memory-os-current-authority-order-round-9-security.md`
2. `memory-os-round9-s2-backend-security-slice-progress-2026-07-16.md`
3. `memory-os-round9-security-foundation-progress-2026-07-16.md`
4. `memory-os-capture-import-security-architecture-round-9.md`
5. `memory-os-capture-import-threat-model-round-9.md`
6. `memory-os-security-verification-gate-round-9.md`
7. `docs/schemas/memory-os-security/schema-registry.v1.json`
8. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
9. `contracts/openapi/memory-os-import-security.v1.openapi.json`
10. `infra/postgresql/security/001_memory_os_import_rls.sql`
11. `infra/postgresql/security/test_memory_os_import_rls.sql`
12. `services/import-api/README.md`
13. Round 9 validators and security workflows
14. Round 8 Capture / Import implementation architecture
15. prior privacy / persistence / deletion / worker-fencing contracts

Round 9は既存のprivacy・RLS・deletion契約を破棄せず、Capture / Import全体へ適用する。

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

Local iOS cache / intake:
GRDB / SQLite + Keychain + App Group

Memory Town:
SpriteKit only after Capture / Import P0 security blockers close
```

Parser、adapter、dedupe、Preview、ApplyをSwift・browser・Goへ重複実装しない。

---

# 3. Binding security decisions

## 3.1 Identity

- Sign in with Appleはserverで検証する。
- issuer、audience、RS256署名、期限、issued-at、nonce、subjectを必須とする。
- unknown `kid`はJWKSを1回だけ再取得し、その後はfail closedする。
- authorization codeはserver-side exchangeし、subject / client / conditional redirectを照合する。
- nonceとauthorization codeはsingle-use replay guardへ通す。
- accountの正本identityは`issuer + subject`。
- emailやprivate-relay emailだけでaccountを自動統合しない。
- client送信のaccount ID・email・subjectをauthorityにしない。

## 3.2 Object authorization

すべてのImport Job、pairing、upload、quarantine object、Preview、Apply、report、exportで以下を要求する。

- exact object lookup;
- same owner;
- same account epoch;
- exact operation authority;
- owner-scoped list query;
- missing / cross-ownerを区別しないgeneric response。

Browser pairing tokenはP0のfinal Apply不可。

## 3.3 PostgreSQL tenant isolation

- `ENABLE ROW LEVEL SECURITY`と`FORCE ROW LEVEL SECURITY`。
- runtime privilege roleは`NOLOGIN NOINHERIT NOBYPASSRLS`。
- runtime roleはuser table ownerにならない。
- verified principalだけがtransaction-local account ID / epochを設定する。
- role名は固定allowlistからのみ選ぶ。
- owner / epochは`USING`と`WITH CHECK`で強制する。
- contextなしはdeny。
- security-domain DELETEはdeletion runtimeだけ。
- Preview、Apply confirmation、Import Reportはinsert後immutable。

## 3.4 Signed quarantine upload

Clientが指定できるのは、容量・SHA-256・Content-Type・source surface・表示用filenameだけ。

Clientは以下を選べない。

- owner;
- account epoch;
- object key;
- bucket;
- authoritative object metadata。

Serverは短命signed PUTを一つのjob・generated key・length・checksum・typeへ固定する。完了時はStorage HEADをserverが実行し、object version IDまでscan ticketへ固定する。authorizationはscan queue投入と同じtransactionでconsumeする。

## 3.5 Parser / archive safety

Parserは以下を必須とする。

- non-root / non-privileged;
- all capabilities dropped;
- no privilege escalation;
- read-only root filesystem;
- no host path / device / Docker socket;
- no network / DNS / proxy / metadata service;
- job-specific `noexec,nosuid,nodev` tmpfs;
- no cross-job visibility;
- no cloud / DB / signing secrets;
- CPU / memory / PID / wall-clock / FD / temp / output limits;
- digest-pinned reviewed adapter artifact。

P0 archive上限:

```txt
compressed:        256 MiB
expanded:            1 GiB
single entry:       128 MiB
entries:             10,000
compression ratio:   100x
nested depth:           1
```

Traversal、absolute/drive path、NUL、links、special files、duplicate normalized path、case collision、encrypted/multi-volume archive、unknown method、malformed directory、deep JSON、duplicate JSON key、oversized CSV cellをrejectする。

## 3.6 Preview and Apply

- Previewはexact source object version、source checksum、adapter identity/digest、options hash、candidate hashesへ固定する。
- Preview候補は正規化してから保存する。
- Preview materialization authorityはworker leaseだけ。
- final Apply authorityはiOS userだけ。
- Applyはexact Preview ID + hashを要求する。
- Apply時に再parseしない。
- idempotency keyをrequest hashへ固定する。
- same completed requestは以前の結果を返し、再保存しない。
- same key + different requestはrejectする。
- created / updated / skippedの合計がcandidate countと一致しなければtransaction rollback。
- partial Applyをsuccess表示しない。

## 3.7 Deletion

account epochはjob、lease、upload、object、Preview、Apply、export、search、App Group、backup restorationへ伝播する。old epoch writeと削除後の復活を禁止する。

---

# 4. Executable backend status

Implemented under `services/import-api/`:

```txt
verified Principal
request-context Principal
scoped PostgreSQL transaction executor
Apple JWT / JWKS verification core
cryptographic opaque IDs
signed upload service and strict HTTP handlers
bounded Generic CSV parser
CSV-to-Preview streaming pipeline
immutable Preview materializer
idempotent iOS-only Apply service
```

Local evidence:

```txt
Go files:   25
unit tests: 52

go test ./...       PASS
go vet ./...        PASS
go test -race ./... PASS
```

This is a security vertical slice, not a production backend.

Not yet implemented:

- executable server composition and session issuer;
- concrete Apple code exchanger / client-secret rotation;
- concrete PostgreSQL repositories and Go driver composition;
- concrete S3-compatible signer / HEAD adapter / bucket policy;
- parser supervisor runtime;
- adapter artifact verification at execution;
- concrete Preview / Apply / Memory persistence;
- deletion-epoch cancellation and cleanup;
- iOS and Portal clients。

---

# 5. Hard stop conditions

Production authorization is forbidden while any condition remains:

- client identity field is trusted;
- Apple token / code / nonce validation is incomplete;
- email-only account linking exists;
- cross-user object checks or RLS fail;
- runtime DB role owns tables or bypasses RLS;
- browser token can Apply;
- signed upload accepts arbitrary key / owner / bucket / length / checksum;
- completion trusts client object metadata;
- quarantine is public or client-listable;
- parser has network、host mount、secret、unbounded resources;
- Preview / Apply exact hash binding or idempotency is absent;
- raw file TTL / cancellation cleanup is absent;
- deletion cannot fence active work and backup restore;
- private content enters logs、analytics、push、crash report;
- remote security CI is failing or unknown at release judgment time;
- unresolved P0 > 0;
- independent review has unresolved Critical / High。

---

# 6. Correct next sequence

## S2 backend continuation

```txt
1. extend PostgreSQL schema for Import Job, upload, Preview candidate, Apply and Memory rows
2. implement concrete PostgreSQL repositories
3. execute Go integration tests against PostgreSQL 16 with FORCE RLS
4. implement local versioned S3-compatible signer and object adapter
5. prove overwrite, checksum, expiry, cancellation and private-policy behavior
6. implement parser supervisor and safe worker entrypoint
7. verify adapter artifact digest at execution
8. implement deletion epoch fencing across queue, parser, Preview and Apply
9. add strict Preview / Apply HTTP handlers and executable service composition
10. add malicious corpus, fuzzing and log-canary tests
```

## S3 iOS

```txt
11. Share Extension URL / text
12. App Group minimal intake
13. GRDB writer / migration ownership and crash recovery
14. Keychain / Data Protection / backup inspection
15. safe Preview display and iOS final confirmation
```

## S4 Portal

```txt
16. one-time pairing
17. in-memory browser token lifecycle
18. CSP / XSS / no-store evidence
19. signed upload through the same OpenAPI boundary
```

## S5 release evidence

```txt
20. parser runtime inspection and fuzzing
21. deletion race and backup restore tests
22. dependency / secret / container scans
23. SBOM / provenance
24. incident / key rotation / restore runbooks
25. independent security review
26. unresolved Critical / High zero
27. unresolved P0 zero
```

Only after Capture / Import P0 unresolved zero:

```txt
28. TownSceneSnapshot Swift models
29. SpriteKit static Town prototype
```

---

# 7. Authorization language

Allowed only after evidence:

```txt
Capture / Import P0 security verification passed for version X and documented scope Y.
```

Forbidden:

```txt
Memory OS is perfectly secure.
Memory OS cannot be hacked.
All data is completely private.
```

Security readiness is versioned and must be reassessed after architecture、dependency、provider、adapter、data-flow change。
