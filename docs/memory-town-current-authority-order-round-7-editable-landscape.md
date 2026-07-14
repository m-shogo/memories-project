# Memory Town Current Authority Order — Round 7 Editable Landscape

最終更新: 2026-07-14

## Current verdict

```txt
Memory-first hierarchy:
locked

attachment-first scenery:
locked at design level

editable landscape architecture:
locked at design level

terrain / graph schemas:
pending

structural prototypes:
pending

new landscape images:
blocked until structural prototypes

implementation:
NO-GO
```

## Authority order

矛盾時は上を優先する。

1. `memory-town-current-authority-order-round-7-editable-landscape.md`
2. `memory-town-editable-landscape-model-contract-round-7.md`
3. `memory-town-landscape-editing-tools-and-phases-round-7.md`
4. `memory-town-design-readiness-gate-round-7-editable-landscape.md`
5. `memory-town-editable-landscape-research-round-7.md`
6. `memory-town-current-authority-order-round-6-attachment-scenery.md`
7. `memory-town-attachment-first-scenic-design-principles-round-6.md`
8. `memory-town-bounded-pan-camera-and-scenic-navigation-contract-round-6.md`
9. `memory-town-current-authority-order-round-5-memory-first.md`
10. `memory-first-capture-motivation-contract-round-5.md`
11. `memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md`
12. `memory-town-long-term-spatial-model.md`
13. prior Memory Town contracts and fixtures

## Binding decision

```txt
Memory Town landscape
=
Hierarchical Editable Diorama
```

Not:

- one giant background
- final tile IDs as user source of truth
- unrestricted height sculpt
- one-cell-at-a-time editing as primary UX

Adopt:

```txt
World Frame
+ District Graph
+ Semantic Terrain Regions
+ Road / River Linear Graphs
+ Parcels / Anchors
+ Object Instances
+ Derived Transition / Micro-detail Projection
```

## Editable target

Long-term users can change:

- grass / soil / stone / forest floor
- near-shore coastline
- sand / beach width
- river / stream / canal route within validation
- roads / footpaths / boardwalks
- forest / grove / flower regions
- houses / feature-building parcels
- bridge style and approved crossing
- new districts / harbor extension / forest edge / upstream

## Source-of-truth decision

Persist semantic intent:

- terrain region
- water body and route
- path graph
- vegetation region
- district and socket
- parcel
- object instance

Derive:

- shoreline edge
- foam
- riverbank
- road corner / junction
- bridge approach
- forest edge detail
- fence join
- contact shadow
- decorative micro-detail

## Water decision

```txt
Distant sea / horizon:
World Frame

Near sea / coast / beach:
Editable Landscape

River / stream / canal:
Linear graph + width profile
```

Water-first composition order:

```txt
coast / water
→ roads / bridges
→ parcels / buildings
→ vegetation
→ derived detail
```

## Expansion decision

```txt
existing map
+ approved expansion socket
+ new district instance
```

Rules:

- existing origin不変
- existing cell coordinates不変
- compatible road / river / coast socket
- before / after preview
- atomic apply
- rollback snapshot
- user object loss禁止

## Editor phase decision

```txt
Phase 0 authored landscape
Phase 1 style / safe decoration slots
Phase 2 vegetation / ground
Phase 3 paths / minor water
Phase 4 coast / river reshape
Phase 5 building relocation
Phase 6 district expansion
Phase 7 terrace bands research
```

## Image-generation hold

新しい完成景観画像は、次ができるまで正本判断へ使わない。

```txt
E0 exploded layers
E1 terrain brush
E2 coast reshape
E3 river + bridge
E4 road + junction
E5 forest + pinned tree
E6 building parcel move
E7 district socket expansion
E8 area reset
E9 same layout / different asset style
```

その後:

```txt
V0 initial
V1 coast edit
V2 forest edit
V3 building move
V4 district expansion
```

を同一semantic townとして生成・比較する。

## Compatibility

Round 7は`memory-town-long-term-spatial-model.md`の以下を将来authoring向けに拡張する。

- cell-only terrain source
- cell-only path source

Retain:

- logical grid
- feature / visual separation
- stable IDs
- parcels
- growth envelope
- command batch
- revision / CAS
- Draft Town
- three-way merge
- recovery / export / RLS

## Implementation prohibition

Round 7を理由にrendererやeditor実装を開始しない。

開始前に必要:

- machine schemas / fixtures
- topology negative tests
- structural diagrams E0〜E9
- visual comparisons V0〜V4
- mobile interaction evidence
- accessibility equivalence
- performance budget
- external review
- unresolved P0 zero
