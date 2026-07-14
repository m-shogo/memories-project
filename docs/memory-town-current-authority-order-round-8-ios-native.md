# Memory Town Current Authority Order — Round 8 iOS Native

最終更新: 2026-07-14

## Current verdict

```txt
platform:
iOS only

application UI:
SwiftUI native

capture integration:
iOS Share Extension

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
2. `ios-native-technology-stack-decision-round-8.md`
3. `memory-town-ios-native-rendering-architecture-round-8.md`
4. `memory-town-current-authority-order-round-7-editable-landscape.md`
5. `memory-town-editable-landscape-model-contract-round-7.md`
6. `memory-town-landscape-editing-tools-and-phases-round-7.md`
7. `memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`
8. `memory-town-current-authority-order-round-6-attachment-scenery.md`
9. `memory-town-current-authority-order-round-5-memory-first.md`
10. prior Memory Town contracts and fixtures

---

## Superseded production decisions

The following previous production assumptions are superseded:

```txt
React / DOM as production iOS UI
PixiJS as production Town renderer
WebGL / browser runtime as production app core
IndexedDB or browser storage as local source
PWA share target as primary capture route
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

---

## Binding platform decision

```txt
MemoryOS.app
+ MemoryShare.appex
```

Initial release does not include Android or a production web application.

A future web viewer or export portal must consume versioned API and export contracts. It must not force the iOS app to retain a WebView runtime.

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
```

SwiftData and CloudKit are not selected as canonical production sources.

---

## Binding Share flow

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

Share action alone does not create a confirmed Memory record.

---

## Required native modules

```txt
MemoryCore
MemoryDomain
CaptureDomain
ShareIntake
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

---

## Next correct sequence

```txt
1. iOS project topology contract
2. ShareIntake schema and lifecycle fixture
3. App Group concurrency and crash-recovery contract
4. local GRDB schema v1
5. sync revision / idempotency contract
6. OpenAPI boundary v1
7. Sign in with Apple account binding contract
8. attachment retention and encryption contract
9. SpriteKit scene snapshot adapter contract
10. native E0 scene skeleton
11. bounded pan / tap prototype
12. static sea / river / sky composition
13. motion full / reduced / off prototype
14. dirty-chunk terrain edit prototype
15. Share Extension URL / text / image prototype
16. oldest supported iPhone evidence
17. background / memory warning / deletion fencing tests
18. accessibility equivalent navigation
19. security and privacy review
20. implementation authorization judgment
```

---

## Hard stop conditions

Do not authorize production implementation if:

- Share Extension writes directly to final Memory Domain without preview
- extension and app write shared SQLite without coordination
- renderer reads raw private Memory fields
- SpriteKit node state becomes canonical layout state
- CloudKit silently becomes a second source of truth
- direct Metal begins without measured SpriteKit failure
- Town failure blocks Capture / Search / Export
- background retry can duplicate records
- staged attachments have no expiry / cleanup policy
- account deletion leaves App Group files, background tasks or atlases
- accessibility requires interacting with the scene canvas only

---

## Documentation migration status

```txt
Round 8 technology decision:
created

native Town architecture:
created

Round 8 authority:
created

README integration:
pending

current-product-direction integration:
pending

old WebGL architecture deprecation banner:
pending

native schemas / fixtures:
not created

native app prototype:
not created
```
