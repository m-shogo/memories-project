# Memory Town Current Authority Order — Round 8 iOS Native

最終更新: 2026-07-14

## Current verdict

```txt
product hierarchy:
Capture / Import first, Town later

platform:
iOS canonical product client

application UI:
SwiftUI native

capture integration:
iOS Share Extension
+ iOS Files / fileImporter
+ limited Desktop Web Import Portal

Memory Town renderer:
SpriteKit

Metal:
measured escalation only

local source:
GRDB / SQLite

cloud source:
Go API + PostgreSQL + object storage

native prototype:
not created

implementation:
NO-GO
```

---

## Authority order

矛盾時は上を優先する。

1. `memory-town-current-authority-order-round-8-ios-native.md`
2. `memory-os-capture-and-import-surface-authority-round-8.md`
3. `ios-native-technology-stack-decision-round-8.md`
4. `memory-town-ios-native-rendering-architecture-round-8.md`
5. `memory-town-current-authority-order-round-7-editable-landscape.md`
6. `memory-town-editable-landscape-model-contract-round-7.md`
7. `memory-town-landscape-editing-tools-and-phases-round-7.md`
8. `memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`
9. `memory-town-current-authority-order-round-6-attachment-scenery.md`
10. `memory-town-current-authority-order-round-5-memory-first.md`
11. prior Memory Town contracts and fixtures

---

## Product hierarchy correction

```txt
1. Capture / Import
2. Retrieval / Search / Update
3. Privacy / Safety / Portability
4. Reflection / Resurfacing
5. Town visualization
6. Town customization / editor
```

`iOS only` means the full product experience and canonical installed client are iOS-first.

It does not mean:

- all JSON / CSV / ZIP migration must happen on an iPhone
- Share Extension alone is the complete Capture strategy
- a desktop file system cannot be used for bulk import support

Memory Town work must not displace Capture / Import readiness.

---

## Superseded production decisions

The following previous production assumptions are superseded:

```txt
React / DOM as production iOS UI
PixiJS as production Town renderer
WebGL / browser runtime as production app core
IndexedDB or browser storage as local source
PWA share target as primary capture route
Share Extension as the only import route
```

This does not invalidate the semantic and safety work contained in older documents.

Retain:

- Memory-first hierarchy
- Town as visible side effect
- five-state separation
- logical grid
- parcel / footprint
- semantic terrain regions
- road / river graph
- district sockets
- Draft Town
- atomic command batches
- deterministic projection
- reduced motion
- functional accessibility equivalent
- privacy-safe TownSceneSnapshot
- Import Preview before Memory Domain write
- portability and source provenance

---

## Binding platform decision

```txt
MemoryOS.app
+ MemoryShare.appex
+ limited Desktop Web Import Portal
```

Initial release does not include Android or a general-purpose production web application.

The Desktop Web Import Portal is an allowed support surface with a narrow scope:

- bulk JSON / CSV / ZIP upload
- archive inspection
- service adapter selection
- mapping
- Import Preview generation
- migration recovery

It is not:

- a Web shelf
- a Web Memory Town
- unrestricted browser search
- a browser-local Memory source of truth

The portal consumes versioned API and import contracts. It does not force the iOS app to retain a WebView runtime.

A future web viewer or export portal must also consume versioned API and export contracts.

---

## Binding renderer decision

```txt
Town semantic state
→ TownSceneSnapshot
→ SpriteKit
```

Direct Metal is not an initial requirement.

`SKTileMapNode`, atlas frame names, `SKNode` identities and `zPosition` values are render details, never Town source of truth.

---

## Binding persistence decision

```txt
local:
GRDB / SQLite

shared capture:
App Group container

secrets:
Keychain access group

cloud:
PostgreSQL behind Go API

bulk upload staging:
quarantined object storage
```

SwiftData and CloudKit are not selected as canonical production sources.

Browser storage is not a canonical Memory or raw archive store.

---

## Binding Capture flows

### A. iOS Quick Capture

```txt
host app Share button
→ MemoryShare extension
→ UTType / size / count validation
→ App Group ShareIntake transaction
→ staged attachment
→ extension completes
→ main app Import Preview
→ explicit confirmation
→ Memory Domain write
→ optional async enrichment / sync
```

### B. iOS File Intake

```txt
Files / fileImporter / Open in Memory OS
→ JSON / CSV / ZIP validation
→ local quarantine
→ source adapter detection
→ Import Preview
→ explicit confirmation
→ Memory Domain write
```

### C. Desktop Bulk Import

```txt
iOS app creates one-time pairing session
→ desktop opens QR / short URL
→ drag and drop JSON / CSV / ZIP
→ upload quarantine / scan / parse
→ preview ready notification
→ iOS final confirmation
→ duplicate-safe Memory Domain apply
```

Capture action, upload completion and parser completion do not create a confirmed Memory record by themselves.

---

## Required native modules

```txt
MemoryCore
MemoryDomain
CaptureDomain
ShareIntake
FileIntake
ImportContracts
ImportPreview
LocalDatabase
SyncEngine
SearchEngine
ExportEngine
TownDomain
TownSceneProjection
TownSpriteKitRenderer
DesignSystem
APIClient
TestSupport
```

App Extension must link only extension-safe minimal modules.

Server-side import modules are separately required:

```txt
ImportSessionService
UploadService
QuarantineService
ArchiveInspector
SourceDetector
AdapterRegistry
ParserWorker
PreviewProjector
ImportApplyService
CleanupService
```

---

## Next correct sequence

```txt
1. Capture surface topology contract
2. ShareIntake schema and lifecycle fixture
3. FileIntake JSON / CSV / ZIP schema
4. PC pairing session and upload-scope contract
5. archive quarantine / ZIP-bomb / path-traversal fixtures
6. import source-adapter manifest schema
7. generic JSON / CSV mapping contract
8. Import Preview schema and confirmation authority
9. App Group concurrency and crash-recovery contract
10. staged attachment / raw archive expiry and cleanup
11. local GRDB schema v1
12. sync revision / idempotency contract
13. OpenAPI import boundary v1
14. Sign in with Apple account binding contract
15. account deletion fence across intake / upload / jobs
16. Share Extension URL / text / image prototype
17. iOS Files JSON / CSV / ZIP prototype
18. Desktop Web Import Portal pairing prototype
19. duplicate-safe bulk apply evidence
20. local search / export evidence
21. SpriteKit scene snapshot adapter contract
22. native E0 Town scene skeleton
23. bounded pan / tap prototype
24. static sea / river / sky composition
25. motion full / reduced / off prototype
26. dirty-chunk terrain edit prototype
27. oldest supported iPhone evidence
28. accessibility equivalent navigation
29. security and privacy review
30. implementation authorization judgment
```

---

## Hard stop conditions

Do not authorize production implementation if:

- Share Extension writes directly to final Memory Domain without preview
- Share Extension is treated as the only Capture / Import route
- all bulk import is forced onto an iPhone
- the Desktop Import Portal expands into an unrestricted Web Memory OS without an ADR
- upload or parser completion silently confirms Memory records
- extension and app write shared SQLite without coordination
- unknown archives can expand without size / entry / ratio / nesting limits
- parser workers have unrestricted network access
- raw archives have no expiry / cleanup policy
- parser or apply retry can duplicate records
- renderer reads raw private Memory fields
- SpriteKit node state becomes canonical layout state
- CloudKit silently becomes a second source of truth
- direct Metal begins without measured SpriteKit failure
- Town failure blocks Capture / Search / Export
- background retry can duplicate records
- account deletion leaves App Group files, upload objects, parser jobs, background tasks or atlases
- accessibility requires interacting with the scene canvas only

---

## Documentation migration status

```txt
Round 8 technology decision:
created

native Town architecture:
created

Capture and Import surface authority:
created

Round 8 authority:
updated with Capture-first correction

README integration:
pending

current-product-direction integration:
pending

old WebGL architecture deprecation banner:
pending

native Capture / Import schemas and fixtures:
not created

native app prototype:
not created

Desktop Import Portal prototype:
not created
```
