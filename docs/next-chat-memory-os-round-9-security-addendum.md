# Next Chat Addendum — Memory OS Round 9 Security

最終更新: 2026-07-16

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

毎回、小さくcommit / pushする。

---

# Read first

1. `SECURITY.md`
2. `docs/memory-os-current-authority-order-round-9-security.md`
3. `docs/memory-os-round9-security-foundation-progress-2026-07-16.md`
4. `docs/memory-os-capture-import-security-architecture-round-9.md`
5. `docs/memory-os-capture-import-threat-model-round-9.md`
6. `docs/memory-os-security-verification-gate-round-9.md`
7. `docs/schemas/memory-os-security/schema-registry.v1.json`
8. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
9. `contracts/openapi/memory-os-import-security.v1.openapi.json`
10. `infra/postgresql/security/001_memory_os_import_rls.sql`
11. `infra/postgresql/security/test_memory_os_import_rls.sql`
12. `.github/workflows/security-contracts.yml`

---

# Absolute status

```txt
security perfection:
never claim

security architecture / threat model / verification gate:
defined

registered schemas:
22

tracked contract fixtures:
21

validators:
created for schema, authorization, RLS, Apple auth,
signed upload and parser/archive safety

PostgreSQL RLS migration / integration test:
created

GitHub Actions:
workflow created; remote result not confirmed by available connector

Go / iOS / Portal / object-storage implementation:
not created

production:
NO-GO
```

設計、schema、validator、SQL testの存在は本番安全性の証明ではない。

---

# Binding stack

```txt
iOS:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain / App Group

Desktop migration support:
Vite + React + TypeScript thin Portal

Backend:
Go API
PostgreSQL with FORCE RLS
private S3-compatible quarantine
isolated parser supervisor / worker

Town later:
SpriteKit
Metal only after measured blocker
```

Parser、adapter、dedupe、Preview、ApplyをSwift / browser / Goへ三重実装しない。

---

# Current evidence

```txt
registered schemas:                 22
tracked fixtures:                   21
generic negative cases:             24
object authorization cases:          8  (2 allow / 6 deny)
PostgreSQL RLS cases:                14  (4 allow / 10 deny)
Sign in with Apple cases:            16  (1 allow / 15 deny)
parser sandbox unsafe mutations:     16  (all deny)
archive / JSON / CSV cases:          25  (1 allow / 24 deny)
signed upload OpenAPI operations:     3
PostgreSQL tables / profiles:         9 / 9
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

The current execution environment could not resolve GitHub for a local clone. Do not convert that limitation into a false CI PASS claim.

---

# Binding security decisions

## Identity

- Sign in with Apple is verified server-side.
- Exact issuer, audience, RS256 signature, time, nonce and subject are required.
- Unknown `kid` triggers one JWKS refresh, then fails closed.
- Authorization code is exchanged server-side and replay is rejected.
- Redirect URI must match when one existed in the original request.
- Canonical account binding is `issuer + subject`.
- Email and private-relay email are not identity and cannot auto-link accounts.
- Client account ID / email / subject are not authority.

## Authorization and RLS

- Every child resource requires object lookup, same owner, same epoch and operation authority.
- Missing and cross-owner resources use generic not-found behavior.
- Browser pairing token cannot final Apply.
- User-owned security tables use `ENABLE RLS` + `FORCE RLS`.
- Runtime privilege roles are `NOLOGIN NOINHERIT NOBYPASSRLS` and do not own tables.
- Account ID / epoch are transaction-local server context only.
- Only deletion runtime may DELETE.
- Preview, Apply confirmation and Import Report are immutable.

## Signed upload

- Client cannot choose owner, epoch, key or bucket.
- Authorization binds one owner / epoch / job / generated key / size / SHA-256 / content type / expiry.
- Signed URL is no-store and not logged or sent to analytics.
- Completion trusts object-storage HEAD metadata, not client metadata.
- Completion atomically consumes authorization before scan queueing.
- Cancelled / deleted account work is rejected.

## Parser sandbox

- non-root, non-privileged, no capability, no escalation;
- read-only root filesystem;
- no host path, devices or Docker socket;
- no network, DNS, proxy or metadata service;
- one job tmpfs with `noexec,nosuid,nodev`;
- no cross-job visibility;
- no cloud, DB or signing secrets;
- bounded CPU / memory / PID / time / descriptors / temp / output;
- supervisor-staged read-only input;
- supervisor-collected schema-validated output;
- digest-pinned, signed, provenance-verified image and adapter.

## Archive / structured files

P0:

```txt
compressed:        256 MiB
expanded:            1 GiB
single entry:       128 MiB
entries:             10,000
ratio:               100x
nested depth:          1
```

Reject traversal, absolute/drive paths, NUL, links, special files, duplicate normalized paths, case collisions, encrypted/multi-volume archive, unknown methods, malformed central directory, excessive JSON depth, duplicate JSON keys and oversized CSV cells.

---

# Hard stops

Do not authorize production if any is true:

- client identity fields are trusted;
- Apple token/code/nonce validation is incomplete;
- email-only account linking exists;
- child resource lacks ownership and epoch checks;
- runtime DB role owns table or bypasses RLS;
- DB auth context can be set from unverified request input;
- browser token can Apply;
- signed upload accepts arbitrary key / owner / bucket / size / checksum;
- upload completion trusts client metadata;
- quarantine is public or client-listable;
- parser has network, host mounts, secrets or unbounded resources;
- archive traversal / link / expansion protections are absent;
- Preview and Apply are not hash-bound and idempotent;
- private content enters logs / analytics / push / crash reports;
- raw archive has no TTL / cancellation cleanup;
- deletion cannot fence active work and backup restore;
- remote CI is failing or unconfirmed at release judgment time;
- unresolved P0 > 0;
- independent review has unresolved Critical / High.

---

# Next correct sequence

## S2 backend security vertical slice

```txt
1. create Go module and verified Apple-auth context
2. implement transaction-scoped SET LOCAL account ID / epoch + SET ROLE
3. run PostgreSQL migration and tests in a local integration environment
4. implement signed-upload storage adapter using a local S3-compatible emulator
5. prove exact key / header / size / checksum / expiry enforcement
6. implement parser supervisor and actual sandbox runtime manifest
7. create malicious ZIP / JSON / CSV corpus and fuzz harness
8. implement one Generic CSV adapter
9. materialize immutable Preview
10. implement idempotent Apply
11. implement deletion epoch fence and cancellation cleanup
```

## S3 iOS

```txt
12. Share Extension URL / text
13. App Group minimal intake
14. GRDB writer / migration ownership and crash recovery
15. Keychain / Data Protection / backup inspection
16. safe Preview and iOS final confirmation
```

## S4 Portal

```txt
17. one-time pairing
18. in-memory browser token lifecycle
19. CSP / XSS / no-store evidence
20. signed upload through the same OpenAPI boundary
```

## S5 evidence

```txt
21. parser runtime inspection
22. archive / JSON / CSV fuzzing
23. deletion race and backup restore tests
24. sensitive-data log canary scan
25. dependency / secret / container scans
26. SBOM / provenance
27. incident / key rotation / restore runbooks
28. independent security review
29. unresolved Critical / High zero
30. unresolved P0 zero
```

Only after this:

```txt
31. TownSceneSnapshot Swift models
32. SpriteKit static Town prototype
```

---

# Recent key commits

```txt
6634551  security foundation progress report
643c14d  Round 9 authority through parser boundary
4180c88  SECURITY.md status synchronization
```

Many intermediate commits created each schema, fixture, validator, SQL migration, integration test and CI step. Do not squash away security history without an explicit release decision.
