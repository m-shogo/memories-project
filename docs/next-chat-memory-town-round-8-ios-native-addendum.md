# Next Chat Addendum — Memory Town Round 8 iOS Native

最終更新: 2026-07-14

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## Read first

1. `docs/memory-town-current-authority-order-round-8-ios-native.md`
2. `docs/memory-os-capture-and-import-surface-authority-round-8.md`
3. `docs/ios-native-technology-stack-decision-round-8.md`
4. `docs/memory-town-ios-native-rendering-architecture-round-8.md`
5. `docs/memory-town-current-authority-order-round-7-editable-landscape.md`
6. `docs/memory-town-editable-landscape-model-contract-round-7.md`
7. `docs/memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`

## Product hierarchy — do not drift

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

Memory Town work must never displace Capture / Import readiness.

## Core platform decision

```txt
Canonical product client:
iOS native

Daily capture:
iOS Share Extension

Local export-file import:
iOS Files / SwiftUI fileImporter

Large JSON / CSV / ZIP migration:
limited Desktop Web Import Portal

Town renderer:
SpriteKit

Local database:
GRDB / SQLite

Service source:
Go API + PostgreSQL + S3-compatible object storage
```

`iOS only` does not mean every bulk migration must happen on an iPhone.

The Desktop Web Import Portal is not a general Web version of Memory OS.

Allowed Portal scope:

- one-time iOS pairing
- bulk upload
- archive inspection
- source adapter selection
- generic field mapping
- preview generation
- rejected-row report
- migration recovery

Not allowed without a new ADR:

- Web shelf
- Web Memory Town
- unrestricted browser search
- browser-local canonical Memory data
- shared-PC silent final confirmation

## Native target topology

```txt
MemoryOS.app
MemoryShare.appex
```

Shared through App Group:

- SQLite intake store
- staged attachments
- transfer manifests

Shared through Keychain access group:

- refresh credential
- encryption key material
- device secret

## Capture flows

### A. iOS Quick Capture

```txt
Share action
→ extension validation
→ App Group intake
→ main-app preview
→ explicit confirmation
→ Memory record
```

### B. iOS File Intake

```txt
Files / fileImporter
→ JSON / CSV / ZIP validation
→ local quarantine
→ source detection
→ preview
→ explicit confirmation
→ Memory record
```

### C. Desktop Bulk Import

```txt
iOS app creates one-time pairing
→ PC browser uploads JSON / CSV / ZIP
→ quarantine / scan / parse
→ preview ready
→ iOS final confirmation
→ duplicate-safe apply
```

Capture, upload and parser completion are not final Memory confirmation.

## Superseded production assumptions

- React / DOM production app
- PixiJS production Town renderer
- browser-first runtime
- PWA Share Target as core capture
- Share Extension as the only import route
- CloudKit as canonical service database
- SwiftData as canonical local database

Older documents remain useful for semantic state, privacy, layout and rendering boundaries unless they conflict with Round 8 authority.

## Town rule

```txt
Town semantic state
→ TownSceneSnapshot
→ SpriteKit scene
```

SpriteKit state is disposable and non-canonical.

Metal is not the first renderer.

```txt
SpriteKit first
→ profile on real devices
→ direct Metal only for a measured blocker
```

## Bulk import safety minimum

Before a bulk importer is implementation-ready, require:

- compressed / expanded size caps
- archive entry cap
- nested archive cap
- compression-ratio cap
- path traversal rejection
- symbolic-link rejection
- MIME / extension / magic-byte checks
- JSON depth / field-size limits
- CSV formula-injection handling
- parser CPU / wall-time budget
- parser network deny-by-default
- raw archive expiry / cleanup
- idempotent apply
- account deletion fence

## Next correct sequence

```txt
1. Capture surface topology contract
2. ShareIntake schema and lifecycle fixture
3. FileIntake JSON / CSV / ZIP schema
4. one-time PC pairing session contract
5. upload quarantine and archive-safety fixtures
6. import source-adapter manifest schema
7. generic JSON / CSV mapper contract
8. Import Preview and confirmation schema
9. App Group writer ownership / locking contract
10. staged attachment and raw archive expiry / cleanup
11. GRDB schema v1
12. local FTS5 index contract
13. sync outbox / inbox revision contract
14. OpenAPI import boundary v1
15. account binding and deletion fence
16. Share Extension URL / text / image prototype
17. iOS Files JSON / CSV / ZIP prototype
18. Desktop Web Import Portal pairing prototype
19. duplicate-safe bulk apply evidence
20. TownSceneSnapshot Swift models
21. SpriteKit scene adapter fixture
22. native static Town prototype
23. bounded pan / tap evidence
24. water / sky motion full-reduced-off
25. terrain dirty-chunk edit prototype
26. accessibility equivalent navigation
27. performance / privacy / adversarial review
28. implementation authorization judgment
```

## Current status

```txt
technology selection:
complete at design level

Capture / Import surface correction:
complete at design level

native Town architecture:
complete at design level

Git authority:
updated

README integration:
pending

current-product-direction integration:
pending

old WebGL doc deprecation banner:
pending

Capture / Import schemas and fixtures:
not created

Xcode project:
not created

Desktop Import Portal:
not created

implementation:
NO-GO
```
