# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-17

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

previous Go security-slice baseline:
go test / vet / race PASS before the latest Preview spool changes

latest CSV iterator / RowEvent / Preview v2 additions:
committed; remote CI result not confirmed by the available connector

concrete PostgreSQL / object storage / parser runtime / spool / iOS / Portal:
incomplete

production:
NO-GO
```

Securityについて「完璧」「安全が保証された」とは表現しない。

---

# 1. Authority order

矛盾時は上を優先する。

1. `memory-os-current-authority-order-round-9-security.md`
2. `memory-os-preview-spool-commit-contract-round-9.md`
3. `memory-os-round9-s2-backend-security-slice-progress-2026-07-16.md`
4. `memory-os-round9-security-foundation-progress-2026-07-16.md`
5. `memory-os-capture-import-security-architecture-round-9.md`
6. `memory-os-capture-import-threat-model-round-9.md`
7. `memory-os-security-verification-gate-round-9.md`
8. `docs/schemas/memory-os-security/schema-registry.v1.json`
9. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
10. `contracts/openapi/memory-os-import-security.v1.openapi.json`
11. `infra/postgresql/security/001_memory_os_import_rls.sql`
12. `infra/postgresql/security/test_memory_os_import_rls.sql`
13. `services/import-api/README.md`
14. Round 9 validators and security workflows
15. Round 8 Capture / Import implementation architecture
16. prior privacy / persistence / deletion / worker-fencing contracts

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
- ready Preview、Apply confirmation、Import Reportはinsert後immutable。

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

## 3.6 CSV parsing and options binding

- Generic CSVは1行ずつ同期pullする。
- hidden goroutine、channel、background persistenceを使用しない。
- cancellationまたはfatal parse error後は同じiteratorを再開しない。
- mapping、delimiter、date layout、timezone、limitsを正規化してSHA-256へ固定する。
- P0 timezoneはembedded tzdataによる`UTC`と`Asia/Tokyo`だけ。
- caller申告のoptions hashと実options hashが違う場合、DB処理開始前にrejectする。
- accepted / rejectedを問わずSourceRowは単調増加し、重複・巻戻しを禁止する。
- rejected rowはSourceRowと`IMPORT_[A-Z0-9_]+`だけを保持し、raw cell値を保持しない。

## 3.7 Preview atomic visibility

Atomic visibilityは必要だが、source parse中に長時間PostgreSQL transactionを開く方式は禁止する。

Production required flow:

```txt
version-bound source
→ parser sandboxでtransaction外parse
→ bounded private spool
→ accepted / rejected streamとmanifestを再hash
→ canonical account epochを再確認
→ client-side pgx.CopyFromによる短いtransaction
→ candidates + safe rejections + immutable ready Previewを同時commit
```

Binding rules:

- source object version / checksum;
- adapter ID / version / reviewed artifact digest;
- normalized options digest;
- accepted stream hash / count;
- rejected stream hash / count;
- final Preview v2 hash。

`preview.AtomicMaterializer`はhash・row decision invariantを検証するvertical-slice reference only。production PostgreSQL repositoryへ直接接続しない。

## 3.8 Apply

- final Apply authorityはiOS userだけ。
- Applyはexact Preview ID + hashを要求する。
- Apply時に再parseしない。
- idempotency keyをrequest hashへ固定する。
- same completed requestは以前の結果を返し、再保存しない。
- same key + different requestはrejectする。
- created / updated / skippedの合計がaccepted candidate countと一致しなければtransaction rollback。
- rejected rowはApply対象ではない。
- partial Applyをsuccess表示しない。

## 3.9 Deletion

account epochはjob、lease、upload、object、spool、Preview、Apply、export、search、App Group、backup restorationへ伝播する。old epoch writeと削除後の復活を禁止する。

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
synchronous Generic CSV iterator
canonical CSV options digest
CSV → Preview RowEvent bridge
Preview v2 candidate / safe-rejection hash model
reference AtomicMaterializer
idempotent iOS-only Apply service
account epoch checkpoint guard
fuzz targets for CSV and Apple compact JWT
```

Current validation language:

```txt
previous backend baseline:
go test / go vet / go test -race PASS

latest iterator / atomic Preview / pipeline additions:
committed with unit tests
remote CI status unavailable from the current connector
therefore not yet recorded as PASS
```

This is a security vertical slice, not a production backend.

Not yet implemented:

- executable server composition and session issuer;
- concrete Apple code exchanger / client-secret rotation;
- concrete account-control and tenant PostgreSQL repositories;
- concrete S3-compatible signer / HEAD adapter / bucket policy;
- parser supervisor runtime;
- adapter artifact verification at execution;
- bounded encrypted/ephemeral Preview spool writer and reader;
- spool manifest schema and verifier;
- client-side `pgx.CopyFrom` atomic Preview commit repository;
- concrete Apply / Memory persistence;
- deletion-epoch spool cancellation and cleanup;
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
- untrusted source parse occurs while a production DB transaction is open;
- spool lacks private bounded storage, manifest binding, re-hash and cleanup;
- candidate / rejection bulk commit is not all-or-nothing;
- Preview / Apply exact hash binding or idempotency is absent;
- raw file / spool TTL or cancellation cleanup is absent;
- deletion cannot fence active work and backup restore;
- private content enters logs、analytics、push、crash report;
- remote security CI is failing or unknown at release judgment time;
- unresolved P0 > 0;
- independent review has unresolved Critical / High。

---

# 6. Correct next sequence

```txt
1. confirm current Go CI / format / vet / race result
2. define machine-readable PreviewSpoolManifest schema
3. implement private bounded spool writer and reader
4. add spool tamper / truncation / cross-job / expiry tests
5. implement concrete pgx CopyFrom commit repository
6. prove parsing completes before transaction start
7. prove candidate / rejection / Preview rollback together
8. recheck canonical account epoch immediately before commit
9. delete spool after success / failure / cancellation / expiry
10. implement concrete S3-compatible storage adapter
11. implement parser supervisor runtime
12. implement concrete idempotent Apply repository
13. begin iOS Share Extension only after backend P0 blockers close
```

Memory Town remains after Capture / Import P0 security blockers close.
