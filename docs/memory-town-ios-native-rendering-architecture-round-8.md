# Memory Town iOS Native Rendering Architecture — Round 8

最終更新: 2026-07-14

## Decision

Memory Townのproduction rendererはSpriteKitを採用する。

```txt
Town semantic state
→ TownSceneSnapshot
→ native scene projection
→ SpriteKit scene graph
```

本書は`memory-town-webgl-architecture.md`のproduction renderer部分をiOS向けに置き換える。

WebGL文書から保持するもの:

- renderer responsibility boundary
- five-state separation
- logical grid
- deterministic scene snapshot
- privacy-safe projection
- fallback / reduced motion
- semantic state and render state separation

置き換えるもの:

```txt
React / DOM → SwiftUI
PixiJS → SpriteKit
WebGL effect → SpriteKit effect, then Metal only if measured
```

---

# 1. Scene ownership

```txt
Memory Domain State
Town Feature Progress State
Town Layout State
Town Environment State
→ application projector
→ TownSceneSnapshot
→ TownSceneController
→ MemoryTownScene
```

`MemoryTownScene`はDB、API、Memory本文へ直接accessしない。

Renderer input must not include:

- raw title
- body text
- person name
- private image URL
- precise location
- authentication token
- billing state

---

# 2. SwiftUI boundary

SwiftUI owns:

- navigation
- town loading / failure / fallback state
- building summary sheet
- editor toolbar
- undo / redo
- conflict and validation messages
- VoiceOver equivalent controls
- motion / sound / low-power settings
- route to shelf / search / export

SpriteKit owns:

- world rendering
- camera transform
- scene hit testing
- visual selection
- placement preview
- water / cloud / wind / particle motion
- short non-blocking reactions

Rule:

```txt
SpriteKit tap
→ semantic interaction ID
→ SwiftUI feature action
```

SpriteKit does not directly present a shelf or edit Memory Domain data.

---

# 3. Scene graph

```txt
MemoryTownScene
├─ worldRoot
│  ├─ skyLayer
│  ├─ distantLayer
│  ├─ terrainLayer
│  ├─ waterLayer
│  ├─ pathLayer
│  ├─ structureLayer
│  ├─ vegetationLayer
│  ├─ raisedDecorLayer
│  ├─ semanticOverlayLayer
│  └─ ambientLayer
├─ editorPreviewLayer
├─ selectionLayer
└─ debugLayer
```

`debugLayer`はrelease buildで無効化できること。

Sky / distant layers may use a weaker camera transform for subtle parallax, but must respect Reduce Motion.

---

# 4. Coordinate system

Persist only logical coordinates.

```txt
origin = logical north-west
+X = east
+Y = south
orientation = 0 / 90 / 180 / 270
elevation = integer logical level
```

Native projection:

```swift
struct TownGridMetric: Sendable, Equatable {
    let tileWidth: CGFloat
    let tileHeight: CGFloat
    let elevationStep: CGFloat
}

func project(
    cellX: Int,
    cellY: Int,
    elevation: Int,
    metric: TownGridMetric
) -> CGPoint {
    CGPoint(
        x: CGFloat(cellX - cellY) * metric.tileWidth / 2,
        y: -CGFloat(cellX + cellY) * metric.tileHeight / 2
           + CGFloat(elevation) * metric.elevationStep
    )
}
```

SpriteKitのY軸方向へ合わせるため、Web projection式とscreen Y符号が異なってもよい。logical contractは変えない。

---

# 5. Deterministic sorting

Do not rely on insertion order.

Each render item receives a deterministic key:

```txt
layer rank
+ projected depth row
+ elevation
+ depth anchor
+ stable instance ID
```

Candidate:

```swift
struct TownSortKey: Comparable, Sendable {
    let layerRank: Int
    let depthRow: Int
    let elevation: Int
    let depthAnchorMilli: Int
    let stableID: String
}
```

`zPosition` is derived from the key and never persisted.

Transparent sprite bounds are not collision or depth authority.

---

# 6. Chunk model

The entire expanded town must not rebuild for one brush stroke.

```txt
semantic change
→ dirty region
→ affected chunk IDs
→ projection rebuild for those chunks
→ node tree swap
```

Candidate initial chunk size:

```txt
8×8 or 12×12 logical cells
```

Final size requires device benchmark.

Each chunk contains:

- terrain projection
- shoreline / riverbank derived sprites
- physical path projection
- vegetation clusters
- static ground decoration

Structures remain independent nodes when interaction, growth animation or relocation requires it.

Chunk replacement rules:

- build replacement off the visible node tree
- swap at frame boundary
- reuse textures
- do not mutate user semantic state
- cancellation safe by scene generation ID

---

# 7. Texture and atlas policy

```txt
semantic asset key
→ approved render variant
→ texture atlas frame
```

Persist semantic asset key, not atlas frame name.

Use atlases by family:

- terrain
- coast / water edge
- roads / bridges
- structures
- trees / vegetation
- seasonal overlays
- ambient particles

Avoid one unbounded atlas for the entire town.

Requirements:

- deterministic manifest
- dimensions and anchor validation
- maximum texture size validation
- nearest-neighbor filter for pixel-art profiles
- optional smooth filter for non-pixel water masks only when approved
- memory cost report per atlas

---

# 8. Camera

Use `SKCameraNode` or equivalent scene camera ownership.

Adopt:

- one-finger bounded pan
- central Home action
- authored landmark anchors
- weak release attraction candidate
- no free rotation
- no perspective tilt
- no long inertia
- no mandatory pinch zoom

Camera state is session state and is not Town Layout state.

Persist only optional user preference such as last district if explicitly adopted later; never persist raw camera pixels as map state.

Gesture arbitration:

```txt
touch down
→ movement threshold
→ tap or pan classification
→ semantic hit target only for tap
```

A drag must not activate a building when the finger is released.

---

# 9. Water rendering

Water is separated into semantic body and visual effect.

```txt
sea / river / canal / pond semantic state
→ geometry / mask projection
→ SpriteKit base surface
→ animated effect
```

Sea layers:

- base color / texture
- slow broad movement
- reflection band
- shoreline wave
- foam

River layers:

- directional flow
- smaller movement scale
- bridge occlusion contract
- bank highlight

Initial implementation should prefer:

- tiling texture movement
- small UV-like texture offset illusion
- limited overlay sprites
- low-resolution effect textures

Do not begin with full-screen custom Metal water.

Metal escalation requires evidence that SpriteKit cannot meet:

- frame pacing target
- memory budget
- visual quality target
- reduced-motion equivalence

Motion off:

- static water texture
- static reflection cue
- shoreline readable without animation

---

# 10. Sky and environment

Environment modes:

- morning
- day
- night
- midnight

Evening remains a visual transition, not a fifth persisted state.

Sky composition:

- gradient or authored backdrop
- distant cloud group
- near cloud group
- sun / moon
- stars
- horizon haze

Time transition:

```txt
palette interpolation
+ building light fade
+ water reflection change
+ sky asset transition
```

Do not bind actual GPS, weather or tide to the core environment.

---

# 11. Wind and vegetation

Use one unified wind input:

```swift
struct TownWindState: Sendable, Equatable {
    let direction: CGVector
    let strength: Double
    let phase: Double
}
```

Apply consistently to:

- tree crown
- grass overlay
- flowers
- clouds
- small flags
- water micro-detail

Do not animate every node independently with unsynchronized random actions.

Forest semantic regions project deterministic clusters from a seed.

Pinned trees remain individual object nodes and survive region edits.

---

# 12. Editor preview

Editing never writes canonical state continuously.

```txt
canonical layout revision
→ local Draft Town
→ command gesture
→ local semantic validation
→ preview scene snapshot
→ SpriteKit editorPreviewLayer
→ Apply or discard
```

Preview states:

- valid placement
- invalid collision
- protected region
- affected cells
- dirty chunks
- bridge candidate
- district socket compatibility

Color alone must not be the only validity cue.

Use shape, icon and SwiftUI text explanation as equivalents.

---

# 13. Accessibility

The town scene is never the only route to a feature.

SwiftUI must provide:

- list of districts
- list of buildings and destination
- Home action
- current selection description
- editor command summary
- validation issue list
- Undo / Redo / Apply / Discard

VoiceOver does not need to navigate every decorative tree or wave.

Semantic interactive objects only:

- feature building
- explicit personal display object
- editor-selected object
- district shortcut

Ambient and derived details remain hidden from accessibility tree.

---

# 14. Performance targets

Initial candidates, not release promises:

```txt
active visible interactive structures: <= 100
visible sprite nodes after chunking: target <= 2,000
ambient particles: adaptive
steady scene: 60 fps target
low-power mode: 30 fps acceptable candidate
memory warning: release non-visible atlases and rebuild safely
```

Final budgets require real-device evidence.

Required instrumentation:

- visible node count
- texture memory estimate
- chunk rebuild duration
- scene snapshot apply duration
- frame time percentile
- draw count where available
- thermal state
- memory warning recovery

Never optimize only against simulator performance.

---

# 15. Lifecycle

Scene lifecycle:

```txt
create generation N
→ apply snapshot
→ enter active
→ pause or background
→ cancel generation-bound tasks
→ release optional resources
→ resume or rebuild
```

Requirements:

- no orphan texture load callbacks
- no stale snapshot apply after account switch
- no renderer resurrection after account deletion
- background motion paused
- scene reconstruction from snapshot always possible

SpriteKit scene is disposable. Town semantic state is not.

---

# 16. Fallback

Fallback levels:

```txt
Full SpriteKit
→ Reduced-motion SpriteKit
→ Static rendered Town image
→ SwiftUI functional Town list
```

Capture, Search, Update and Export are identical across fallback levels.

Town failure must never block application launch.

---

# 17. Prototype gates

Before production authorization:

1. static native scene with central / river / harbor districts
2. bounded pan and tap classification
3. four time-mode environment swap
4. sea and river motion / off states
5. chunk rebuild after terrain edit
6. building relocation preview
7. district expansion preview
8. 10k-object synthetic semantic input projection test
9. oldest supported iPhone performance evidence
10. memory warning and background lifecycle test
11. SwiftUI accessibility equivalent route
12. no private Memory fields in scene snapshot

## Current status

```txt
native renderer decision:
LOCKED AT DESIGN LEVEL

SpriteKit prototype:
NOT CREATED

Metal requirement:
NOT PROVEN

production implementation:
NO-GO
```
