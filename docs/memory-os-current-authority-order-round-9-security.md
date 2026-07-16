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

machine-readable security schemas:
22 registered

contract fixtures:
21 tracked

re-runnable validators:
created for schema, authorization, PostgreSQL RLS, Apple auth,
signed upload OpenAPI, parser sandbox and archive safety

PostgreSQL RLS migration and live-test SQL:
created

GitHub Actions workflow:
created; remote result not confirmed by the available connector

Go / iOS / Portal / object-storage implementation:
not created

production:
NO-GO
```

Securityについて「完璧」「安全が保証された」とは表現しない。

---

# 1. Authority order

矛盾時は上を優先する。

1. `memory-os-current-authority-order-round-9-security.md`
2. `memory-os-round9-security-foundation-progress-2026-07-16.md`
3. `memory-os-capture-import-security-architecture-round-9.md`
4. `memory-os-capture-import-threat-model-round-9.md`
5. `memory-os-security-verification-gate-round-9.md`
6. `docs/schemas/memory-os-security/schema-registry.v1.json`
7. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
8. `contracts/openapi/memory-os-import-security.v1.openapi.json`
9. `infra/postgresql/security/001_memory_os_import_rls.sql`
10. `infra/postgresql/security/test_memory_os_import_rls.sql`
11. Round 9 security validators under `scripts/`
12. `memory-os-capture-import-implementation-architecture-round-8.md`
13. `memory-os-capture-and-import-surface-authority-round-8.md`
14. `memory-town-current-authority-order-round-8-ios-native.md`
15. prior privacy / persistence / deletion / worker-fencing contracts

Round 9は既存契約を破棄せず、Capture / Import全体へ適用する。

---

# 2. Binding architecture

```txt
Daily capture:
iOS Share Extension

Local file intake:
iOS Files / fileImporter

Bulk migration:
limited Desktop Web Import Portal

Canonical import engine:
Go API + isolated parser supervisor / worker

Metadata and revisions:
PostgreSQL with FORCE RLS

Raw quarantine:
private S3-compatible object storage

Local confirmed cache / intake:
GRDB / SQLite

Memory Town:
SpriteKit only after Capture / Import P0 security blockers close
```

Parser、adapter、dedupe、Preview、ApplyをSwift / browser / Goへ重複実装しない。

---

# 3. Active security foundation

## 3.1 Identity

Sign in with Apple server validation requires:

- exact issuer;
- exact audience allowlist;
- RS256 only;
- verified JWKS key and signature;
- expiration and issued-at window;
- single-use nonce;
- single-use authorization code and exact client binding;
- redirect URI equality when one existed in the original request;
- canonical account identity from `issuer + subject`;
- no email-only auto-linking;
- no trust in client-provided account ID, email or subject.

## 3.2 Object authorization

Every Import Job, pairing session, upload authorization, quarantine object, Preview, Apply confirmation, report and export requires:

- object-level lookup;
- same owner;
- same account epoch;
- authority allowed for the exact operation;
- owner-scoped list query;
- generic not-found behavior for missing and cross-owner resources.

Browser pairing token cannot final Apply in P0.

## 3.3 PostgreSQL tenant isolation

- `ENABLE ROW LEVEL SECURITY`;
- `FORCE ROW LEVEL SECURITY`;
- runtime privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS`;
- runtime roles do not own user tables;
- account ID and epoch are transaction-local values set from verified server auth;
- missing context denies access;
- owner / epoch are enforced by `USING` and `WITH CHECK`;
- only `memory_deletion_runtime` may DELETE security-domain rows;
- materialized Preview, Apply confirmation and Import Report cannot be updated after insert.

## 3.4 Signed quarantine upload

Client may request an upload using only:

- exact content length;
- SHA-256;
- declared content type;
- source surface;
- untrusted display filename if present.

Client cannot choose:

- owner;
- account epoch;
- object key;
- bucket;
- authoritative storage metadata.

Server issues one short-lived signed PUT bound to one job and one generated quarantine key. Completion performs a server-side object-storage metadata lookup and atomically consumes the authorization before scan queueing.

## 3.5 Parser sandbox

Parser process must be:

- non-root;
- non-privileged;
- all Linux capabilities dropped;
- no privilege escalation;
- read-only root filesystem;
- no host path, device or Docker socket mounts;
- no network, DNS, proxy or metadata service;
- one job-specific tmpfs with `noexec,nosuid,nodev`;
- no cross-job visibility;
- no cloud, DB or signing secrets;
- bounded by CPU, memory, PIDs, wall-clock, file descriptors, temp and output size;
- digest-pinned, signature-verified and provenance-verified.

Input is staged read-only by a supervisor. Output is collected and schema-validated by the supervisor.

## 3.6 Archive / JSON / CSV safety

P0 limits:

```txt
compressed archive: 256 MiB
expanded archive:     1 GiB
single entry:        128 MiB
entry count:          10,000
compression ratio:   100x
nested depth:           1
```

Reject traversal, absolute paths, Windows drive paths, NUL, excessive names, links, special files, duplicate normalized paths, case-fold collisions, encrypted/multi-volume archives, unknown compression methods, malformed central directories, excessive JSON depth, duplicate JSON keys and oversized CSV cells.

## 3.7 Preview / Apply / deletion

- Preview is materialized and immutable;
- source, adapter, options and candidates are hash-bound;
- Apply references exact Preview hash;
- no Apply-time silent reparse;
- P0 final authority is iOS app only;
- idempotency key is bound to request hash;
- partial apply is not success;
- deletion epoch fences jobs, leases, uploads, objects, Preview, Apply, export, search, caches, App Group files and backup restoration.

---

# 4. Evidence inventory

```txt
registered schemas:                 22
tracked contract fixtures:          21
generic negative cases:             24
object authorization cases:          8  (2 allow / 6 deny)
PostgreSQL RLS logic cases:          14  (4 allow / 10 deny)
Sign in with Apple cases:            16  (1 allow / 15 deny)
parser sandbox unsafe mutations:     16  (all deny)
archive / JSON / CSV cases:          25  (1 allow / 24 deny)
signed upload OpenAPI operations:     3
PostgreSQL RLS tables:                9
PostgreSQL policy profiles:           9
```

Re-run:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
python scripts/validate-memory-os-authorization.py
python scripts/validate-memory-os-postgresql-rls.py
python scripts/validate-memory-os-apple-auth.py
python scripts/validate-memory-os-signed-upload-openapi.py
python scripts/validate-memory-os-parser-security.py
```

The repository also contains a PostgreSQL 16 integration-test job. Its remote run has not been confirmed.

---

# 5. Hard stop conditions

Production authorization is forbidden while any condition remains:

- client-provided account ID becomes identity authority;
- Apple issuer / audience / signature / nonce / subject is not verified server-side;
- email alone can link accounts;
- cross-user resource negative tests are absent or failing;
- runtime DB role owns tables or has `BYPASSRLS`;
- account / epoch DB context can be set by an unverified client value;
- browser token can final Apply;
- signed upload can choose arbitrary key, owner, bucket, size or checksum;
- upload completion trusts client object metadata;
- quarantine bucket is public or client-listable;
- parser has network, host filesystem, secrets or unbounded resources;
- archive traversal / link / expansion protections are absent;
- Preview / Apply hash binding or idempotency is absent;
- raw archive has no TTL and cancellation cleanup;
- account deletion cannot fence active workers and restored backups;
- private content enters logs, analytics, push or crash breadcrumbs;
- remote security CI is failing or unknown at release judgment time;
- unresolved P0 finding is greater than zero;
- independent review has unresolved Critical / High findings.

---

# 6. Correct next sequence

## S2 backend security vertical slice

1. create Go module and verified Apple-auth context;
2. implement transaction-scoped `SET LOCAL` account ID / epoch and `SET ROLE`;
3. apply PostgreSQL migration in local integration environment;
4. implement signed-upload adapter against a local S3-compatible emulator;
5. prove exact key / header / size / checksum / expiry enforcement;
6. implement parser supervisor and actual sandbox runtime manifest;
7. build malicious ZIP / JSON / CSV corpus and fuzz harness;
8. implement Generic CSV adapter;
9. materialize immutable Preview;
10. implement idempotent Apply;
11. implement deletion epoch fence and cancellation cleanup.

## S3 iOS security vertical slice

12. Share Extension URL / text;
13. App Group minimal intake;
14. GRDB writer / migration ownership and crash recovery;
15. Keychain / Data Protection / backup inspection;
16. safe Preview and iOS final confirmation.

## S4 Portal

17. one-time pairing;
18. in-memory browser token lifecycle;
19. strict CSP / no-store / XSS tests;
20. signed upload through the same OpenAPI boundary.

## S5 adversarial and operational evidence

21. parser sandbox runtime tests;
22. archive / JSON / CSV fuzzing;
23. deletion race and backup-restore tests;
24. sensitive-data log canary scan;
25. dependency / secret / container scans;
26. SBOM and release provenance;
27. incident / key rotation / restore runbooks;
28. independent security review;
29. unresolved Critical / High zero;
30. unresolved P0 zero.

Only after Capture / Import P0 unresolved zero:

31. TownSceneSnapshot Swift models;
32. SpriteKit static Town prototype.

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

Security readiness is versioned and must be reassessed after architecture, dependency, provider, adapter or data-flow changes.
