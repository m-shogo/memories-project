# iOS Native Technology Stack Decision — Round 8

最終更新: 2026-07-14

## Decision

Memory OSは初期提供対象をiOSへ限定する。

本番clientはWebView shellではなく、native iOS applicationとして実装する。

```txt
Swift 6
+ SwiftUI
+ UIKit where required by system integration
+ SpriteKit for Memory Town
+ Metal only behind measured performance needs
+ GRDB / SQLite local-first store
+ App Group shared intake store
+ URLSession / BackgroundTasks
+ Sign in with Apple
+ StoreKit 2
+ Go API
+ PostgreSQL
+ S3-compatible object storage
```

Deployment target candidate:

```txt
iOS 18+
```

Release前に実利用端末分布を確認して最終固定する。

---

# 1. Why native iOS

Memory OSの主要価値は、他アプリから人生の断片を軽く取り込むことにある。

必要なOS統合:

- Share Extension
- App Groups
- Keychain access group
- background URLSession
- BackgroundTasks
- Photo / File intake
- Universal Links / deep links
- APNs
- StoreKit
- system accessibility
- device data protection

iOSだけを対象にする場合、cross-platform frameworkの最大の利点は使わない一方、Share Extension・background lifecycle・file protection・Widget等ではnative bridgeを維持し続ける必要がある。

したがって、最初からSwiftを正本とする。

---

# 2. Client UI

## Adopt

```txt
SwiftUI
```

Responsibilities:

- Capture / Quick Add
- Import Preview
- Shelf / Search / Update
- Reflection
- Settings
- Export
- Town editor controls
- conflict resolution
- accessibility equivalent navigation

Use UIKit only when:

- Share Extension host requires UIViewController integration
- Photos / Files system controller integration needs it
- a proven SwiftUI defect blocks production behavior
- advanced text or gesture behavior cannot be implemented safely in SwiftUI

UIKit is an escape hatch, not the default UI architecture.

## State management

Initial choice:

```txt
Swift Observation
+ explicit feature state
+ async/await
+ actors for mutable services
```

Do not adopt a large state-management framework at project creation.

Reason:

- single-platform app
- dependency longevity
- extension-safe shared modules
- state ownership remains explicit
- domain commands already provide deterministic boundaries

A reducer framework may be reconsidered only after navigation, undo/redo and sync conflicts produce measurable complexity.

---

# 3. Memory Town renderer

## Adopt

```txt
SpriteKit
```

Memory Town is:

- fixed-view 2.5D
- sprite based
- bounded pan
- no free 3D camera
- no avatar physics gameplay
- many layered ambient animations
- editable semantic terrain projected to visual nodes

This matches a native 2D scene graph better than a browser renderer or full game engine.

### Primary SpriteKit responsibilities

- scene graph
- texture atlas rendering
- deterministic depth ordering
- bounded camera pan
- sprite animation
- water / light / wind effects
- particle effects
- selection and placement previews
- dirty-chunk replacement
- scene snapshot application

### SwiftUI / SpriteKit boundary

```txt
Memory Domain
+ Feature Progress
+ Town Layout
+ Environment
→ TownSceneSnapshot
→ SpriteKit scene adapter
```

SpriteKit never accesses:

- database directly
- memory body text
- sync API directly
- growth rule calculation
- user account state

The renderer consumes privacy-safe `TownSceneSnapshot` only.

## SKTileMapNode policy

`SKTileMapNode` may be used as an internal projection optimization, but it is not the landscape source of truth.

Persist:

- semantic terrain region
- road / river graph
- district socket
- parcel / anchor
- object instance

Do not persist:

- SpriteKit node ID
- atlas frame name as semantic identity
- adjacency mask
- final tile selection
- screen coordinate

## Metal policy

Do not start with direct Metal rendering.

Use SpriteKit first, and profile on real devices.

Direct Metal or a custom `MTKView` renderer is permitted only when a measured P0 problem cannot be solved by:

- texture atlases
- node pooling
- chunk replacement
- hidden-node removal
- precomputed sort order
- lower motion mode
- lower shader resolution
- reduced particle count

Likely Metal candidates later:

- large continuous water distortion
- batched shoreline mesh
- high-density forest instancing
- custom compositing beyond SpriteKit capability

Metal is an optimization boundary, not the initial architecture.

---

# 4. Why not the alternatives

## Capacitor + PixiJS

Not selected for production iOS.

Reasons:

- WKWebView runtime remains between app and renderer
- Share Extension still needs native Swift code
- App Group and background transfer still need native ownership
- two UI/runtime stacks must be debugged
- WebView process memory competes with a large sprite scene
- accessibility and system navigation are harder to keep canonical

PixiJS remains useful only for:

- browser-based visual experiments
- remote concept demos
- asset composition tools

It is not the production renderer authority.

## React Native

Not selected.

Reasons:

- cross-platform reuse has no initial value
- Share Extension requires native target work anyway
- complex graphics need another renderer dependency
- native lifecycle failures cross JS/native boundaries
- Memory OS should minimize infrastructure layers around private data

## Unity

Not selected for the primary app.

Reasons:

- Memory OS is mostly forms, lists, search, system sharing and privacy controls
- Unity adds a second application lifecycle and build pipeline
- Share Extension cannot be implemented as the Unity scene itself
- binary size, startup and embedding complexity are unnecessary for fixed-view 2D
- native accessibility equivalence still has to be built separately

Unity would be reconsidered only if Memory Town becomes a substantially interactive game, which is a permanent non-goal under the current product constitution.

## SceneKit / RealityKit

Not selected.

The town is authored as 2.5D sprites and does not need true perspective, 3D assets, lighting simulation or free camera movement.

## Direct Metal

Not selected initially because it would force the project to own batching, resource lifetime, scene graph, hit testing, camera and tooling before product value is proven.

---

# 5. Local persistence

## Adopt

```txt
SQLite
+ GRDB
```

Do not use SwiftData as the canonical local store for the first production version.

Reasons:

- explicit migrations
- predictable SQL schema
- SQLite FTS5 for local search
- transaction boundaries matching command batches
- deterministic export
- easier recovery and forensic inspection
- shared App Group container support
- explicit multi-process coordination between app and Share Extension

Apple's extension guidance explicitly allows SQLite in a shared container and requires synchronized access.

## Database topology

```txt
App Group container
├─ memory.sqlite
├─ share-intake/
├─ staged-attachments/
└─ transfer-manifests/
```

Recommended process ownership:

```txt
Share Extension:
append minimal intake record
copy validated attachment to staging
finish quickly

Main app:
consume intake
show Import Preview
confirm Memory Domain write
perform enrichment and sync
```

The Share Extension must not run long AI processing or perform large relational migrations.

## Local search

```txt
SQLite FTS5
```

Use for:

- title
- normalized source text
- user notes
- tags explicitly accepted by user
- searchable import metadata

Embeddings are not required for normal capture or exact retrieval.

---

# 6. Security and privacy

## Key storage

```txt
Keychain
+ Keychain Access Group for app / extension shared secrets
```

Store:

- refresh credential
- local encryption key material
- device registration secret

Do not store authentication tokens in UserDefaults.

## File protection

Apply iOS Data Protection classes to:

- database
- staged attachments
- exports
- caches containing memory-derived data

Background access requirements must be decided per file class rather than weakening the entire container.

## Encryption

```txt
TLS in transit
server-side encryption at rest
optional application-level envelope encryption for highly sensitive payloads
CryptoKit for client cryptographic operations
```

Do not claim end-to-end encryption until key recovery, multi-device sync, search, export and account deletion have a complete protocol and adversarial review.

---

# 7. Share Extension architecture

Targets:

```txt
MemoryOS.app
MemoryShare.appex
```

Shared Swift packages:

- MemoryCore
- CaptureContracts
- ShareIntakeStore
- SecureKeyAccess
- FileValidation
- APIContracts

Flow:

```txt
NSItemProvider input
→ UTType validation
→ size / count / filename safety checks
→ normalized ShareIntake
→ App Group SQLite transaction
→ attachment staging
→ extension completion
→ main app Import Preview
→ confirmed Memory record
```

P0 supported input:

- URL
- plain text
- one image / screenshot
- URL plus selected text

P1:

- multiple images
- PDF
- audio file

Do not accept arbitrary executable or package formats.

---

# 8. Networking and background work

## Adopt

```txt
URLSession
+ async/await
+ background URLSession for long attachment transfer
+ BackgroundTasks for deferred sync / indexing
```

Rules:

- every mutation has idempotency key
- upload and record creation are separate states
- extension and app use distinct background session identifiers
- App Group is used for transfer manifests
- retry never duplicates Memory records
- background failure never deletes local confirmed data

No WebSocket is required for initial sync.

---

# 9. Cloud architecture

## Do not use CloudKit as the sole source of truth

CloudKit is attractive for Apple-only sync, but it is not selected as canonical storage because Memory OS needs:

- server-side import processors
- account-level export and deletion audit
- configurable AI providers
- future web export / recovery path
- billing entitlement checks
- deterministic server validation
- operational observability
- portability beyond a single vendor database

CloudKit may be evaluated later for optional device backup or lightweight private metadata, but never as an undocumented second source of truth.

## Adopt

```txt
Go API
+ PostgreSQL
+ S3-compatible object storage
```

### Go service responsibilities

- authentication exchange
- sync API
- capture normalization
- import preview jobs
- export generation
- deletion workflow
- notification scheduling
- provider-neutral AI orchestration
- rate limiting and audit

### PostgreSQL responsibilities

- Memory Domain source of truth
- Share Intake server state
- revisions and idempotency
- Town Layout and Feature Progress
- relational search metadata
- full-text search
- optional pgvector indexes after explicit adoption
- row-level security defense in depth

### Object storage

Store:

- original attachments when user chose cloud retention
- thumbnails
- generated exports
- approved Town asset packs

Do not place large image or PDF binary data inside PostgreSQL rows.

### Initial operations choice

Use managed PostgreSQL and managed S3-compatible storage.

Keep schema and migration tooling portable so a provider change does not require product data migration logic to be rewritten.

---

# 10. Authentication and billing

## Authentication

```txt
Sign in with Apple
```

The backend stores its own stable account ID and binds Apple credentials to it.

Do not use the Apple subject identifier as the only internal primary key.

## Billing

```txt
StoreKit 2
```

Backend verifies and records entitlement state.

Town growth, capture limits and privacy controls must not be manipulated to create coercive subscription pressure.

---

# 11. API contract

Adopt versioned HTTP JSON APIs described by OpenAPI.

```txt
OpenAPI contract
→ generated Swift client types
→ Go server request / response validation
```

Rules:

- semantic IDs remain stable
- server never exposes private payloads in TownSceneSnapshot
- all writes carry expected revision or idempotency key
- schema evolution is additive within a major version
- export format is not identical to internal API response format

GraphQL is not selected initially.

---

# 12. Project module structure

```txt
MemoryOS.xcodeproj

Targets
├─ MemoryOS
├─ MemoryShare
└─ MemoryOSTests

Packages
├─ MemoryCore
├─ MemoryDomain
├─ CaptureDomain
├─ ShareIntake
├─ LocalDatabase
├─ SyncEngine
├─ SearchEngine
├─ ExportEngine
├─ TownDomain
├─ TownSceneProjection
├─ TownSpriteKitRenderer
├─ DesignSystem
├─ APIClient
└─ TestSupport
```

Dependency direction:

```txt
UI targets
→ feature modules
→ domain contracts
→ persistence / network adapters
```

`TownSpriteKitRenderer` depends on `TownSceneProjection`, not on `MemoryDomain` or `LocalDatabase`.

`MemoryShare` depends on the minimal extension-safe modules only.

---

# 13. Testing

## Adopt

- Swift Testing for domain and adapter tests
- XCTest / XCUITest where system UI or extension launching requires it
- snapshot tests for SwiftUI and Town scene outputs
- deterministic TownSceneSnapshot fixtures
- database migration tests
- Share Extension payload matrix tests
- real-device performance tests

Required device classes before Town authorization:

- oldest supported iPhone
- current standard iPhone
- current Pro-class iPhone

Measure:

- cold start
- Share Extension completion time
- database migration time
- 10k / 100k record search
- Town node count
- frame pacing
- thermal behavior
- memory warning recovery
- background upload recovery

---

# 14. Asset pipeline

```txt
Aseprite source
→ deterministic export
→ validation
→ texture atlas build
→ manifest generation
→ Xcode asset packaging
```

Requirements:

- nearest-neighbor sampling for approved pixel assets
- stable semantic asset keys
- atlas frame names are render details, not Town identity
- provenance and license manifest
- device-scale visual review
- atlas size and memory budget checks

---

# 15. Migration from current WebGL decision

Superseded for production iOS:

```txt
React / DOM UI
PixiJS / WebGL renderer
browser-first runtime
```

Retained unchanged:

- Memory-first hierarchy
- five-state separation
- logical grid
- semantic terrain regions
- road / river graph
- parcel / footprint
- district sockets
- command batches
- Draft Town
- deterministic scene snapshot
- accessibility equivalent UI
- fallback and reduced motion requirements

Replacement mapping:

```txt
React / DOM UI
→ SwiftUI

PixiJS scene graph
→ SpriteKit scene graph

WebGL shader / filter candidate
→ SpriteKit effect first, Metal only after profiling

browser IndexedDB candidate
→ GRDB / SQLite

service worker / web background work
→ URLSession background transfer + BackgroundTasks
```

No Town semantic data migration should be needed when changing renderers.

---

# 16. Final stack

```txt
Platform
  iOS only

Language
  Swift 6

UI
  SwiftUI
  UIKit only at system boundaries

Town
  SpriteKit
  Metal only for measured bottlenecks

Local data
  GRDB / SQLite
  FTS5
  App Group shared container

Security
  Keychain
  Data Protection
  CryptoKit where protocol requires

System integration
  Share Extension
  URLSession
  BackgroundTasks
  PhotoKit / Files / UTType
  APNs

Cloud
  Go API
  PostgreSQL
  S3-compatible object storage

Auth / billing
  Sign in with Apple
  StoreKit 2

Contracts
  OpenAPI
  versioned export format
```

## Status

```txt
technology direction:
LOCKED AT DESIGN LEVEL

prototype evidence:
PENDING

production implementation:
NO-GO until native architecture fixtures and device evidence exist
```
