# Memory OS Current Authority Order — Round 9 Security

最終更新: 2026-07-16

## Current verdict

```txt
product hierarchy:
Capture / Import first

platform:
iOS canonical client + limited Desktop Import Portal

security architecture:
defined at contract level

threat model:
70 attack / abuse scenarios defined

S1 machine-readable security contracts:
created

S1 targeted payload validation:
PASS

repository validator:
created and locally exercised against generated repository payloads

GitHub Actions workflow:
created; remote run result not yet confirmed

backend / iOS / Portal security implementation:
not created

production:
NO-GO
```

Securityについて「完璧」「安全が保証された」とは表現しない。

---

# 1. Authority order

矛盾時は上を優先する。

1. `memory-os-current-authority-order-round-9-security.md`
2. `memory-os-capture-import-security-architecture-round-9.md`
3. `memory-os-capture-import-threat-model-round-9.md`
4. `memory-os-security-verification-gate-round-9.md`
5. `memory-os-round9-security-s1-validation-report-2026-07-16.md`
6. `docs/schemas/memory-os-security/schema-registry.v1.json`
7. `docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json`
8. `scripts/validate-memory-os-security.py`
9. `memory-os-capture-import-implementation-architecture-round-8.md`
10. `memory-os-capture-and-import-surface-authority-round-8.md`
11. `memory-town-current-authority-order-round-8-ios-native.md`
12. prior product / privacy / persistence / deletion contracts

Round 9は既存のprivacy、RLS、deletion、worker fencingを破棄せず、Capture / Import全体へ拡張する。

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
Go Import Service / isolated worker

Metadata / revisions:
PostgreSQL

Raw quarantine:
private S3-compatible object storage

Local confirmed cache / intake:
GRDB / SQLite

Memory Town:
SpriteKit, after Capture / Import security evidence
```

Parser logicをSwift、browser、Goへ重複実装しない。

---

# 3. Active S1 machine contracts

Schemas:

```txt
core.v1.schema.json
security-issue-code-registry.v1.schema.json
import-job.v1.schema.json
pairing-session.v1.schema.json
upload-authorization.v1.schema.json
quarantine-object.v1.schema.json
import-preview.v1.schema.json
apply-confirmation.v1.schema.json
adapter-manifest.v1.schema.json
deletion-fence.v1.schema.json
safe-audit-event.v1.schema.json
security-negative-case-set.v1.schema.json
```

Validation inventory:

```txt
schemas: 12
positive fixtures: 10
negative cases: 24
schema-level negative rejections: 22
semantic negative rejections: 2
network schema resolution: disabled
```

The two semantic checks are:

- adapter artifact digest equals reviewed artifact digest;
- deletion fence contains every mandatory cleanup scope.

Re-run command:

```bash
python -m pip install -r requirements-security-validation.txt
python scripts/validate-memory-os-security.py
```

The GitHub Actions workflow is `.github/workflows/security-contracts.yml`.

---

# 4. Binding security decisions

## Identity and ownership

- client-provided user IDをtrustしない
- every object endpointでobject-level authorization
- import job / pairing / upload / Preview / report / Apply / Exportをtenant fence
- account epochを全pending workへ伝播
- browser pairing tokenはfinal Apply不可

## Upload and storage

- exact server-generated quarantine key
- size / checksum / expiry / job / owner / epoch binding
- public object access禁止
- raw filenameをobject keyにしない
- raw archiveはshort TTL
- quarantine objectとconfirmed objectを別identityにする

## Parser and adapter

- public API process外
- non-root
- read-only root filesystem
- job-specific temp
- outbound network deny by default
- CPU / memory / wall-clock limits
- dynamic code / script execution禁止
- adapterはversioned reviewed artifact
- reviewed digestと実行digestを一致させる

## Preview and Apply

- materialized immutable Preview
- source / adapter / options / candidate hash
- exact Preview hash confirmation
- iOS appがP0の最終confirmation authority
- idempotency key + request hash
- no silent reparse at Apply
- partial applyをsuccess表示しない

## iOS / App Group

- Extension writes minimal intake only
- secretはKeychain
- raw tokenをUserDefaultsへ置かない
- main-app-only migration
- synchronized SQLite access
- raw intake / Preview cacheをbackup対象にしない
- private contentをlog / push / app switcherへ出さない

## Portal

- thin upload / mapping UI only
- no Web shelf / Town / unrestricted search
- no third-party analytics P0
- strict CSP / no-store / no private browser DB
- token short-lived / revocable / memory-only after bootstrap

## Deletion and audit

- job、lease、pairing、upload、object、Preview、Apply、export、search、push、App Group、backup tombstoneをfence
- backup restore後にdeletion tombstoneを再適用
- old epoch worker writeを拒否
- Audit Eventへ本文、raw filename、raw URL、token、email、user noteを入れない

---

# 5. Hard stop conditions

以下が一つでもある場合、Production authorizationを出さない。

- cross-user resource negative testなし
- browser pairing tokenがfinal Apply可能
- signed URLがarbitrary key / unlimited upload可能
- parserがAPI process内
- parser outbound network unrestricted
- archive traversal / link / expanded-size protectionなし
- Preview / Apply hash bindingなし
- idempotent Applyなし
- reviewed adapter digestと実行digestが不一致
- private contentがlog / analytics / notificationへ入る
- App Group DB writer / migration ownership不明
- raw archive TTL / cleanup evidenceなし
- account deletion中workerがwrite可能
- backup restoreでdeleted data復活
- production secretがclient / repository / logへ入る
- independent review Critical / High unresolved
- unresolved P0 security finding > 0

---

# 6. Correct next sequence

## S1.5 repository and authorization integration

1. confirm the GitHub Actions security-contract workflow result;
2. add cross-user authorization case schema and fixtures;
3. add object-level authorization matrix;
4. add PostgreSQL tenant / RLS contract and negative fixtures;
5. add Sign in with Apple server-validation contract;
6. add signed-upload request / response OpenAPI boundary;
7. add worker sandbox runtime contract;
8. add archive limit profile and fixtures.

## S2 backend security vertical slice

9. authentication and account binding;
10. PostgreSQL Import Job tables with tenant ownership;
11. signed private quarantine upload;
12. isolated worker process;
13. Generic CSV adapter;
14. immutable Preview;
15. idempotent Apply;
16. deletion epoch fence.

## S3 iOS security vertical slice

17. Share Extension URL / text;
18. activation-rule tests;
19. App Group minimal intake;
20. GRDB concurrency / crash recovery;
21. Keychain / Data Protection / backup verification;
22. safe Preview / confirmation.

## S4 Portal and file migration

23. iOS fileImporter signed upload;
24. Generic JSON / Memory OS export adapter;
25. one-time Portal pairing;
26. CSP / CSRF / XSS / no-store evidence;
27. browser token lifecycle;
28. iOS final confirmation.

## S5 adversarial and operational evidence

29. archive / JSON / CSV fuzzing;
30. parser sandbox runtime tests;
31. SSRF corpus;
32. deletion race tests;
33. backup restore deletion test;
34. sensitive-data log canary scan;
35. dependency / secret / container scans;
36. SBOM / release provenance;
37. incident / key rotation / restore runbooks;
38. independent security review;
39. unresolved Critical / High zero;
40. unresolved P0 zero.

Only after Capture / Import P0 unresolved zero:

41. TownSceneSnapshot Swift models;
42. SpriteKit static Town prototype.

---

# 7. Implementation authorization language

Allowed later, only with evidence:

```txt
Capture / Import P0 security verification passed for version X and documented scope Y.
```

Not allowed:

```txt
Memory OS is perfectly secure.
Memory OS cannot be hacked.
All data is completely private.
```

Security readiness is versioned and must be reassessed after architecture, dependency, provider, adapter or data-flow changes.
