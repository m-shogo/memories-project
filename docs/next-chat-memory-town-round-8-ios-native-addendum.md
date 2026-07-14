# Next Chat Addendum — Memory Town Round 8 iOS Native

最終更新: 2026-07-14

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## Read first

1. `docs/memory-town-current-authority-order-round-8-ios-native.md`
2. `docs/ios-native-technology-stack-decision-round-8.md`
3. `docs/memory-town-ios-native-rendering-architecture-round-8.md`
4. `docs/memory-town-current-authority-order-round-7-editable-landscape.md`
5. `docs/memory-town-editable-landscape-model-contract-round-7.md`
6. `docs/memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`

## Core decision

```txt
iOS only
Swift 6
SwiftUI
SpriteKit
GRDB / SQLite
Share Extension + App Group
Go API + PostgreSQL + S3-compatible object storage
```

Metal is not the first renderer.

```txt
SpriteKit first
→ profile on real devices
→ direct Metal only for a measured blocker
```

## Superseded production assumptions

- React / DOM production app
- PixiJS production Town renderer
- browser-first runtime
- PWA Share Target as core capture
- CloudKit as canonical service database
- SwiftData as canonical local database

Older documents remain useful for semantic state, privacy, layout and rendering boundaries unless they conflict with Round 8.

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

## Share rule

```txt
Share action
→ intake
→ preview required
→ explicit confirmation
→ Memory record
```

Never treat OS Share as final Memory confirmation.

## Town rule

```txt
Town semantic state
→ TownSceneSnapshot
→ SpriteKit scene
```

SpriteKit state is disposable and non-canonical.

## Local data rule

Use GRDB / SQLite for:

- explicit migrations
- FTS5
- transactions
- deterministic export
- shared App Group coordination
- recovery inspection

## Cloud rule

Use Go API + PostgreSQL as service source of truth.

CloudKit may only be revisited as an optional non-canonical convenience after an explicit ADR.

## Next correct sequence

```txt
1. iOS project topology contract
2. ShareIntake schema
3. App Group writer ownership / locking contract
4. staged attachment expiry and cleanup
5. GRDB schema v1
6. local FTS5 index contract
7. sync outbox / inbox revision contract
8. OpenAPI v1 skeleton
9. account binding and deletion fence
10. TownSceneSnapshot Swift models
11. SpriteKit scene adapter fixture
12. native static Town prototype
13. bounded pan / tap evidence
14. water / sky motion full-reduced-off
15. terrain dirty-chunk edit prototype
16. Share Extension URL / text / image prototype
17. background upload recovery
18. accessibility equivalent navigation
19. performance / privacy / adversarial review
20. implementation authorization judgment
```

## Current status

```txt
technology selection:
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

native schemas / fixtures:
not created

Xcode project:
not created

implementation:
NO-GO
```
