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

security verification gate:
defined

machine-readable security contracts:
not created

backend / iOS / Portal implementation:
not created

security execution evidence:
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
5. `memory-os-capture-import-implementation-architecture-round-8.md`
6. `memory-os-capture-and-import-surface-authority-round-8.md`
7. `memory-town-current-authority-order-round-8-ios-native.md`
8. `ios-native-technology-stack-decision-round-8.md`
9. `memory-town-ios-native-rendering-architecture-round-8.md`
10. `memory-town-current-authority-order-round-7-editable-landscape.md`
11. prior product / privacy / persistence / deletion contracts

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

# 3. Binding security decisions

## Identity and ownership

- client-provided user IDをtrustしない
- every object endpointでobject-level authorization
- import job / pairing / upload / Preview / report / Apply / Exportをtenant fence
- account deletion epochをpending workへ伝播
- browser pairing tokenはfinal Apply不可

## Upload and storage

- exact server-generated quarantine key
- size / checksum / expiry / job / owner binding
- public object access禁止
- raw filenameをobject keyにしない
- raw archiveはshort TTL
- quarantine objectとconfirmed objectを別identityにする

## Parser

- public API process外
- non-root
- read-only root FS
- job-specific temp
- network deny by default
- resource limits
- no dynamic code / script execution
- adapterはversioned reviewed artifact

## Preview and Apply

- materialized immutable Preview
- source / adapter / options / candidate hash
- exact Preview hash confirmation
- idempotency key + request hash
- no silent reparse at Apply
- partial applyをsuccess表示しない

## iOS / App Group

- extension writes minimal intake only
- secretはKeychain
- raw tokenをUserDefaultsへ置かない
- main-app-only migration
- synchronized SQLite access
- raw intake / Preview cache backup除外
- private contentをlog / push / app switcherへ出さない

## Portal

- thin upload / mapping UI only
- no Web shelf / Town / unrestricted search
- no third-party analytics P0
- strict CSP / no-store / no private browser DB
- token short-lived / revocable / memory-only after bootstrap

## Deletion

- DBだけでなくjob、lease、upload token、object、Preview、cache、export、search、push、App Groupを削除 / fence
- backup restore後にdeletion tombstoneを再適用
- old epoch worker writeを拒否

---

# 4. Hard stop conditions

以下が一つでもある場合、Production implementation authorizationを出さない。

- cross-user resource negative testなし
- browser pairing tokenがfinal Apply可能
- signed URLがarbitrary key / unlimited upload可能
- parserがAPI process内
- parser outbound network unrestricted
- archive traversal / link / expanded-size protectionなし
- Preview / Apply hash bindingなし
- idempotent Applyなし
- private contentがlog / analytics / notificationへ入る
- App Group DB writer / migration ownership不明
- raw archive TTL / cleanup evidenceなし
- account deletion中workerがwrite可能
- backup restoreでdeleted data復活
- production secretがclient / repository / logへ入る
- independent review Critical / High unresolved
- unresolved P0 security finding > 0

---

# 5. Correct next sequence

```txt
S1 machine contracts
1. SecurityIssueCode registry
2. ImportJob schema
3. PairingSession schema
4. UploadAuthorization schema
5. QuarantineObject schema
6. ImportPreview / ApplyConfirmation schema
7. AdapterManifest schema
8. DeletionFence schema
9. AuditEvent safe-field schema
10. positive / negative fixtures

S2 backend vertical slice
11. auth / account binding
12. object-level authorization matrix
13. signed quarantine upload
14. isolated worker
15. Generic CSV adapter
16. Preview hash + idempotent Apply
17. deletion epoch fence

S3 iOS vertical slice
18. Share Extension URL / text
19. App Group crash recovery
20. Keychain / Data Protection / backup tests
21. main-app Preview / confirmation

S4 migration surfaces
22. iOS fileImporter upload
23. Generic JSON / Memory OS export adapter
24. Portal one-time pairing
25. XSS / CSRF / browser privacy tests

S5 adversarial evidence
26. archive / JSON / CSV fuzzing
27. SSRF corpus
28. deletion race / backup restore
29. supply-chain CI gates
30. independent security review

Only after Capture / Import P0 unresolved zero:
31. TownSceneSnapshot Swift models
32. SpriteKit static Town prototype
```

---

# 6. Implementation authorization language

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

Security readiness is versioned and must be reassessed after architecture, dependency, provider, adapter or data-flow change.
