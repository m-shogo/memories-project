# Memory Town Editable Landscape Structural Diagrams E0–E9 — Round 7

最終更新: 2026-07-14

## Status

```txt
structural diagram specification:
created

GitHub Mermaid rendering:
available

mobile interaction prototype:
not created

final visual assets:
not created

implementation:
NO-GO
```

本書は完成景観を描く前に、同じ町が地形編集・建物移動・地区増築・asset差し替えへ耐えられるかを確認する構造図である。

---

# E0 — Exploded landscape layers

```mermaid
flowchart TB
  A[Memory Domain<br/>record / shelf / progress] -->|privacy-safe projection only| B[Town Feature Projection]

  W[World Frame<br/>sky / horizon / distant sea] --> R
  D[District Graph<br/>central / river / coast / harbor] --> R
  T[Semantic Terrain Regions<br/>grass / sand / plaza / shallow water] --> R
  L[Linear Feature Graphs<br/>river / road / path] --> R
  P[Parcels and Anchors<br/>building / bridge / pier] --> R
  O[User Objects<br/>houses / pinned trees / furniture] --> R
  B --> R[Spatial Scene Projector]

  R --> X[Derived Projection<br/>shore edge / riverbank / junction / shadow / shrubs]
  X --> S[TownSceneSnapshot]
  S --> G[PixiJS / WebGL layers]

  G --> G1[terrain]
  G --> G2[water]
  G --> G3[path and bridge]
  G --> G4[structures]
  G --> G5[vegetation]
  G --> G6[light and ambient motion]
```

Binding decisions:

- Memory Domainは町の座標を持たない
- final sprite IDはcanonical stateではない
- World Frameと近景の編集可能地形を分離する
- derived projectionは再生成可能
- PixiJSは描画担当で、地形ルールの正本ではない

---

# E1 — Ground brush and protected areas

```mermaid
flowchart LR
  A[Load canonical revision R] --> B[Open Draft Town]
  B --> C[Brush stroke<br/>grass / soil / sand / stone]
  C --> D[Create one PaintTerrainCommand]
  D --> E{Protected boundary or object collision?}
  E -->|yes| F[Reject affected cells<br/>show safe warning]
  E -->|no| G[Update semantic terrain region]
  G --> H[Mark dirty chunks]
  H --> I[Rebuild edge transitions]
  I --> J[Before / After preview]
  J --> K{Apply?}
  K -->|discard| L[Canonical revision unchanged]
  K -->|apply| M[Server revalidate + CAS R]
  M --> N[Atomic revision R+1]
```

Required UX:

- one gesture = one undo unit
- brush does not silently move or delete a house
- locked plaza and landmark corridor stay protected
- invalid cells may be explained, but destructive automatic fixing is prohibited

---

# E2 — Coast and beach editing

```mermaid
flowchart TB
  H[Fixed World Frame<br/>horizon / distant sea] --> V[Visible composition]

  C[Editable near-coast region] --> C1[coast control boundary]
  C1 --> S[sand buffer region]
  S --> W[shallow-water region]
  W --> V

  C1 --> Q{Topology validation}
  Q -->|closed shoreline| P[Generate coast edge]
  Q -->|hole / self-cross / submerged building| X[Block Apply]

  P --> F[foam and wet-sand projection]
  F --> V

  A[Pier / harbor approved anchors] --> V
```

Editable:

- beach width
- small cove
- small cape
- rock cluster
- coast vegetation
- pier at an approved anchor

Not freely editable initially:

- horizon
- distant island silhouette
- entire open sea
- land beneath occupied structure footprints

---

# E3 — River, road crossing and bridge

```mermaid
flowchart LR
  RS[River source node] --> R1[River segment]
  R1 --> RC[Crossing node]
  RC --> R2[River segment]
  R2 --> RO[Outlet / pond / sea]

  PW[Road west node] --> P1[Road segment]
  P1 --> PC[Road crossing node]
  PC --> P2[Road segment]
  P2 --> PE[Harbor / entrance node]

  RC -.same logical crossing position.-> PC
  RC --> B{Approved bridge or culvert anchor?}
  PC --> B
  B -->|yes| BP[Derived bridge projection]
  B -->|no| X[BRIDGE_ANCHOR_REQUIRED]
```

River validation:

- source and outlet exist
- every segment references existing nodes
- graph is connected in the intended direction
- district boundary uses a compatible river socket
- building footprint and riverbank clearance are respected

Bridge is not persisted as a random path tile. It is projected from a validated crossing contract and an approved bridge anchor.

---

# E4 — Road drawing and automatic junctions

```mermaid
flowchart TB
  A[User draws road line] --> B[Normalize control points]
  B --> C[Path nodes and segments]
  C --> D[Rasterize only for projection]
  D --> E[Derive adjacency masks]
  E --> F[straight / curve / T / cross / dead end]
  F --> G{All primary entrances reach access root?}
  G -->|yes| H[Preview road and junction sprites]
  G -->|no| X[ROAD_ACCESS_ROOT_DISCONNECTED]
```

Canonical state:

```txt
path kind
+ nodes
+ segments
+ surface profile
+ accessibility profile
```

Derived only:

```txt
connection mask
corner sprite
junction sprite
bridge approach sprite
path-side flowers and signs
```

---

# E5 — Forest region and pinned trees

```mermaid
flowchart LR
  A[Vegetation region<br/>cells + density + species + seed] --> B[Deterministic tree cluster]
  B --> C[Generated tree A]
  B --> D[Generated tree B]
  B --> E[Generated tree C]

  D -->|user selects Keep this tree| P[Pinned user-owned tree object]

  A -->|region later shrinks| R[Reproject cluster]
  R --> C2[Generated trees may change]
  R --> E2[Generated trees may change]
  P --> K[Pinned tree remains]
```

Rules:

- forest is not stored as thousands of mandatory tree rows
- region edit avoids roads, rivers, entrances and structure clearance
- pinned trees survive forest density or boundary changes
- season changes sprite variants, not canonical species identity

---

# E6 — Building relocation without losing memory binding

```mermaid
flowchart TB
  A[Select building instance] --> B[Show approved parcel candidates]
  B --> C[Place translucent preview]
  C --> D{Validation}

  D --> D1[footprint]
  D --> D2[growth envelope]
  D --> D3[entrance connection]
  D --> D4[scenic corridor]
  D --> D5[access root]

  D -->|invalid| X[Keep canonical building unchanged]
  D -->|valid| E[MoveObjectCommand]
  E --> F[Atomic Apply]

  F --> G[Same featureId]
  F --> H[Same instanceId]
  F --> I[Same shelf route]
  F --> J[Same growth progress]
```

Moving a cinema changes its place, not the movie records or the meaning of the feature.

---

# E7 — District expansion through sockets

```mermaid
flowchart LR
  A[Existing district A] --> SA[Available expansion socket]
  N[New district B preview] --> SB[Compatible socket]

  SA --> C{kind + profile + direction compatible?}
  SB --> C

  C -->|no| X[Reject without changing map]
  C -->|yes| V[Validate overlap / road / river / scenic view]
  V -->|pass| AP[AttachDistrictCommand]
  AP --> R[Revision R+1]

  A --> K[Existing origin and coordinates stay unchanged]
  R --> CAM[Camera bounds expand]
```

Socket kinds:

- land
- road
- river
- coast
- harbor
- view

Expansion does not regenerate the existing town and does not move its origin.

---

# E8 — Area reset, stored objects and rollback

```mermaid
flowchart TB
  A[Select editable area] --> B[Choose reset scope]
  B --> B1[terrain only]
  B --> B2[paths only]
  B --> B3[vegetation only]
  B --> B4[all visual layout in area]

  B --> C[Compare current state with template baseline]
  C --> D[System-generated details discarded]
  C --> E[User-owned objects detected]
  E --> F{Safe position remains?}
  F -->|yes| G[Keep object]
  F -->|no| H[Move to stored state<br/>no map coordinate]

  D --> I[Reset preview]
  G --> I
  H --> I
  I --> J{Apply or discard}
  J -->|apply| K[Snapshot + atomic revision]
  J -->|discard| L[No canonical change]
  K --> M[Rollback available]
```

No reset flow may delete a user-owned object without an explicit separate deletion action.

---

# E9 — Same semantic town, different asset style

```mermaid
flowchart TB
  S[Same semantic town state] --> P[Scene projector]

  P --> A[Style profile A<br/>storybook pixel coast]
  P --> B[Style profile B<br/>quiet paper harbor]

  A --> RA[Sprite atlas A]
  B --> RB[Sprite atlas B]

  RA --> VA[Visual scene A]
  RB --> VB[Visual scene B]

  S --> C[Canonical IDs / coordinates / routes unchanged]
  VA --> C
  VB --> C
```

Must remain identical across style swap:

- terrain region IDs
- river and road graph IDs
- building instance IDs
- feature bindings
- district sockets
- memory records
- accessibility DOM routes

Allowed to change:

- sprite atlas
- palette
- texture
- wave and leaf animation profile
- derived edge and micro-detail visuals

---

# Cross-diagram invariants

```txt
Memory is the product.
Landscape is semantic state.
Final art is projection.
Preview is not canonical.
User objects are never silently destroyed.
Existing coordinates do not move during expansion.
The town remains usable without WebGL.
```

# Evidence still missing

- diagrams rendered and reviewed on mobile
- touch editing prototype
- actual coast topology validator
- river continuity validator
- positive bridge asset prototype
- building footprint / parcel fixtures
- area reset command schema
- V0–V4 same-town visual image sequence
- performance and accessibility review
