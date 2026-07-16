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
3. `docs/memory-os-capture-import-security-architecture-round-9.md`
4. `docs/memory-os-capture-import-threat-model-round-9.md`
5. `docs/memory-os-security-verification-gate-round-9.md`
6. `docs/memory-os-round9-security-s1-validation-report-2026-07-16.md`
7. `docs/schemas/memory-os-security/schema-registry.v1.json`
8. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
9. `scripts/validate-memory-os-security.py`
10. `docs/memory-os-capture-import-implementation-architecture-round-8.md`

---

# Absolute status

```txt
security perfection:
never claim

security architecture:
defined at contract level

threat model:
70 scenarios defined

S1 machine contracts:
created

S1 targeted payload validation:
PASS

re-runnable repository validator:
created and locally exercised against generated repository payloads

GitHub Actions workflow:
created; remote run result not yet confirmed

backend / iOS / Portal security implementation:
not created

production:
NO-GO
```

設計書・schema・fixtureを作成したことは、本番安全性の証明ではない。

---

# Binding stack

```txt
iOS:
Swift 6 + SwiftUI
Share Extension
GRDB / SQLite
Keychain / App Group

Bulk Import Portal:
Vite + React + TypeScript thin client

Backend:
Go API + isolated Import Worker
PostgreSQL
private S3-compatible quarantine storage

Town later:
SpriteKit
Metal only after measured blocker
```

Parser、adapter、dedupe、Preview、ApplyをSwift / browser / Goへ三重実装しない。

---

# S1 inventory

```txt
schemas: 12
positive fixtures: 10
negative cases: 24
schema negative rejections: 22
semantic negative rejections: 2
network schema resolution: disabled
```

Active schemas:

```txt
core
security issue-code registry
ImportJob
PairingSession
UploadAuthorization
QuarantineObject
ImportPreview
ApplyConfirmation
AdapterManifest
DeletionFence
SafeAuditEvent
SecurityNegativeCaseSet
```

Validator:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
```

Expected output:

```txt
Memory OS security contract validation PASS
schemas: 12
positive fixtures: 10
schema negative rejections: 22
semantic negative rejections: 2
network schema resolution: disabled
```

The two semantic rules are:

1. adapter execution digest must equal reviewed digest;
2. deletion fence must include every mandatory scope.

---

# Most important security decisions

- every object endpoint performs object-level authorization
- client user ID is never authority
- account epoch follows all pending work
- pairing token cannot final Apply in P0
- upload authorization binds exact key / job / owner / epoch / size / checksum / expiry
- raw files stay in private quarantine
- parser runs outside public API, non-root, network denied, resource limited
- adapter code is a reviewed, digested artifact
- Preview is immutable and hash-bound to Apply
- Apply is iOS-authorized, idempotent and cannot silently reparse
- App Group stores minimal intake only; secrets stay in Keychain
- private content never enters logs, analytics, push or crash breadcrumbs
- account deletion fences upload, worker, Preview, Apply, export, search and restored backups
- E2EE is not claimed

---

# Current hard stops

Do not proceed to production if any of the following is true:

- user ID from request body is trusted
- child resource endpoint lacks ownership check
- browser token can Apply
- signed URL can choose arbitrary object key
- parser has unrestricted network or host filesystem
- ZIP extraction lacks traversal / link / expansion limits
- Preview and Apply are not hash-bound
- duplicate confirmation can create duplicate Memory
- adapter review digest and executing digest differ
- App Group contains refresh token in UserDefaults
- logs contain Memory body / filename / URL query / token
- raw archive has no TTL
- deletion does not fence active worker
- backup restore can resurrect deletion
- external review Critical / High remains open
- P0 security finding remains open

---

# Next correct sequence

## S1.5 repository and authorization integration

```txt
1. confirm GitHub Actions workflow result
2. cross-user authorization case schema
3. object-level authorization matrix
4. PostgreSQL tenant / RLS contract
5. RLS positive / negative fixtures
6. Sign in with Apple server-validation contract
7. signed upload OpenAPI boundary
8. worker sandbox runtime contract
9. archive limit profile and fixtures
```

## S2 backend security vertical slice

```txt
10. authentication and account binding
11. Import Job database tables
12. signed private quarantine upload
13. isolated worker process
14. Generic CSV adapter
15. immutable Preview
16. idempotent Apply
17. deletion epoch fence
```

## S3 iOS security vertical slice

```txt
18. Share Extension URL / text
19. activation-rule tests
20. App Group minimal intake
21. GRDB concurrency / crash recovery
22. Keychain / Data Protection / backup verification
23. safe Preview / confirmation
```

## S4 Portal and file migration

```txt
24. iOS fileImporter signed upload
25. Generic JSON / Memory OS export adapter
26. one-time Portal pairing
27. CSP / CSRF / XSS / no-store evidence
28. browser token lifecycle
29. iOS final confirmation
```

## S5 adversarial and operational evidence

```txt
30. archive / JSON / CSV fuzzing
31. parser sandbox runtime tests
32. SSRF corpus
33. deletion race tests
34. backup restore deletion test
35. sensitive-data log canary scan
36. dependency / secret / container scans
37. SBOM / release provenance
38. incident / key rotation / restore runbooks
39. independent security review
40. unresolved Critical / High zero
41. unresolved P0 zero
```

Only after this:

```txt
42. TownSceneSnapshot Swift models
43. SpriteKit static Town prototype
```

---

# Round 9 implementation commits

```txt
7a8e17d  security architecture
6869740  threat model
c045783  verification gate
5e88c50  security authority
b02d77f  SECURITY.md
96d6d5e  initial Round 9 handoff

S1 commits continue from:
afb37aa  security core schema
...
82e8f70  security-contract GitHub Actions workflow
98d44e5  updated Round 9 authority
```

Do not infer that omitted intermediate SHAs were not committed; every schema, fixture and harness change was committed directly to `so`.
