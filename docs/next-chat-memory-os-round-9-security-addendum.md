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
6. `docs/memory-os-capture-import-implementation-architecture-round-8.md`
7. `docs/memory-os-capture-and-import-surface-authority-round-8.md`
8. `docs/memory-town-current-authority-order-round-8-ios-native.md`

---

# Absolute status

```txt
security perfection:
never claim

security architecture:
defined at contract level

threat model:
70 scenarios defined

verification gate:
defined

security schemas / fixtures:
not created

security code / infrastructure:
not created

security execution evidence:
not created

production:
NO-GO
```

設計書を作成したことは、安全性の証明ではない。

---

# Product priority

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

Capture / ImportのP0 security evidenceがない状態でTown implementationを優先しない。

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

# Most important security decisions

- every object endpoint performs object-level authorization
- pairing token cannot final Apply in P0
- upload authorization binds exact key / job / owner / size / checksum / expiry
- raw files stay in private quarantine
- parser runs outside public API, non-root, network denied, resource limited
- archive paths, links, sizes, ratios, nesting and entries are bounded
- Preview is immutable and hash-bound to Apply
- Apply is idempotent and rejects same key with different request hash
- App Group stores minimal intake only; secrets stay in Keychain
- private content never enters logs, analytics, push or crash breadcrumb
- account deletion epoch fences upload, parser, Preview, Apply, export and restored work
- backup restore cannot silently resurrect deleted account data
- E2EE is not claimed

---

# P0 threats requiring executable evidence

```txt
T-001 cross-user Import Job read
T-002 cross-user Preview / report read
T-003 pairing token brute force
T-004 pairing token log / URL leakage
T-005 browser unauthorized Apply
T-006 arbitrary signed-upload key
T-007 signed URL replay after cancellation / deletion
T-008 archive path traversal
T-009 archive links / special file escape
T-010 decompression bomb
T-011 parser RCE
T-012 parser network exfiltration
T-013 cross-job temp access
T-014 Preview / Apply TOCTOU
T-015 duplicate Apply
T-016 partial Apply shown as success
T-017 deletion while parser runs
T-018 backup resurrection
T-019 SSRF
T-020 Preview XSS
T-021 CSV formula injection
T-022 App Group secret leak
T-023 shared SQLite corruption
T-024 sensitive logs / crash report
T-025 notification / app-switcher leak
T-026 malicious image decode
T-027 public / enumerable object storage
T-028 third-party Portal script leak
T-029 malicious adapter update
T-030 supply-chain compromise
```

Additional T-031〜T-070 are documented in the threat model.

---

# Next correct sequence

## S1 machine-readable contracts

```txt
1. security issue code registry
2. ImportJob schema
3. PairingSession schema
4. UploadAuthorization schema
5. QuarantineObject schema
6. ImportPreview schema
7. ApplyConfirmation schema
8. AdapterManifest schema
9. DeletionFence schema
10. safe AuditEvent schema
11. positive fixtures
12. P0 negative fixtures
13. schema registry integration
14. machine validation
```

## S2 backend security vertical slice

```txt
15. Sign in with Apple server validation contract
16. object-level authorization matrix
17. PostgreSQL tenant / RLS fixtures
18. signed quarantine upload
19. private object storage policy
20. isolated worker runtime
21. Generic CSV adapter
22. immutable Preview
23. idempotent Apply
24. deletion epoch fence
```

## S3 iOS vertical slice

```txt
25. Share Extension URL / text
26. activation-rule tests
27. App Group minimal intake
28. GRDB concurrency / crash recovery
29. Keychain / Data Protection / backup verification
30. safe Preview / confirmation
```

## S4 Portal and file migration

```txt
31. iOS fileImporter signed upload
32. Generic JSON / Memory OS export adapter
33. one-time Portal pairing
34. CSP / CSRF / XSS / no-store evidence
35. browser token lifecycle
36. iOS final confirmation
```

## S5 adversarial and operational evidence

```txt
37. archive / JSON / CSV fuzzing
38. parser sandbox runtime tests
39. SSRF corpus
40. deletion race tests
41. backup restore deletion test
42. sensitive-data log canary scan
43. dependency / secret / container scans
44. SBOM / release provenance
45. incident / key rotation / restore runbooks
46. independent security review
47. unresolved Critical / High zero
48. unresolved P0 zero
```

Only after this:

```txt
49. TownSceneSnapshot Swift models
50. SpriteKit static Town prototype
```

---

# Hard stops

Do not proceed to production if any of the following is true:

- user ID from request body is trusted
- child resource endpoint lacks ownership check
- browser token can Apply
- signed URL can choose arbitrary object key
- parser has unrestricted network or host filesystem
- ZIP extraction lacks traversal / link / expansion limits
- Preview and Apply are not hash-bound
- duplicate confirmation can create duplicate Memory
- App Group contains refresh token in UserDefaults
- logs contain Memory body / filename / URL query / token
- raw archive has no TTL
- deletion does not fence active worker
- backup restore can resurrect deletion
- external review Critical / High remains open
- P0 security finding remains open

---

# Existing commits in Round 9

```txt
7a8e17d  security architecture
6869740  threat model
c045783  verification gate
5e88c50  security authority
b02d77f  repository SECURITY.md
```

This handoff commit follows those commits.
