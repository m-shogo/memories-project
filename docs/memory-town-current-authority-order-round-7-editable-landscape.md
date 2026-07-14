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

Round 7 schemas / positive fixtures / negative fixture shapes:
targeted validation PASS

repository-wide registry validation:
pending

semantic topology validator execution:
pending

E0–E9 structural diagrams:
created, review pending

V0–V4 same-town visual comparison:
not created

implementation:
NO-GO
```

## Authority order

矛盾時は上を優先する。

1. `memory-town-current-authority-order-round-7-editable-landscape.md`
2. `memory-town-editable-landscape-model-contract-round-7.md`
3. `memory-town-landscape-editing-tools-and-phases-round-7.md`
4. `memory-town-design-readiness-gate-round-7-editable-landscape.md`
5. `memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`
6. `memory-town-round7-targeted-schema-validation-report-2026-07-14.md`
7. `memory-town-editable-landscape-research-round-7.md`
8. `memory-town-current-authority-order-round-6-attachment-scenery.md`
9. `memory-town-attachment-first-scenic-design-principles-round-6.md`
10. `memory-town-bounded-pan-camera-and-scenic-navigation-contract-round-6.md`
11. `memory-town-current-authority-order-round-5-memory-first.md`
12. `memory-first-capture-motivation-contract-round-5.md`
13. `memory-town-full-pattern-adoption-and-permanent-non-goals-round-4.md`
14. `memory-town-long-term-spatial-model.md`
15. prior Memory Town contracts and fixtures

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

## Active Round 7 machine contracts

Schemas:

```txt
terrain-region-state.v1.schema.json
linear-feature-graph.v1.schema.json
district-expansion-state.v1.schema.json
landscape-command-batch.v1.schema.json
landscape-v1-projection-case.v1.schema.json
```

Fixtures:

```txt
terrain-region-state.round7.valid.v1.json
linear-feature-graph.round7.valid.v1.json
district-expansion-state.round7.valid.v1.json
landscape-command-batch.round7.valid.v1.json
landscape-v1-projection.round7.valid.v1.json
issue-code-extension.round7-editable-landscape.v1.json
negative-validation-cases.round7-editable-landscape.v1.json
fixture-index.round7-editable-landscape-extension.v1.json
```

Targeted Draft 2020-12 validation passed for the new schema and fixture shapes. This is not repository-wide semantic validation.

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

## Structural diagrams

E0–E9 were added as GitHub Mermaid diagrams:

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
E9 same semantic layout / different asset style
```

These are structural evidence, not final art evidence. Mobile readability and design review remain pending.

## V1 compatibility

New semantic state must project deterministically to the current cell-oriented renderer while it remains in use.

Locked mappings include:

```txt
forest_floor → grass
plaza → stone
shallow_water → water
marsh → water
promenade / boardwalk → footpath
validated road-river crossing → bridge
```

Never persist as canonical user state:

```txt
connectionMask
coastlineMask
riverbankMask
derivedSpriteId
```

## Image-generation hold

V0–V4 final comparison images are still held until the following are complete:

- E0–E9 review
- repository-integrated schema registry validation
- semantic validator specification for coast / river / access / sockets
- missing high-risk negative cases

Then generate the same semantic town as:

```txt
V0 initial
V1 coast edit
V2 forest edit
V3 building move
V4 district expansion
```

Do not generate five unrelated attractive towns.

## Remaining high-risk negative evidence

- sea or coast edit submerges a building
- isolated water region saved as a river
- river violates bank clearance or crosses a structure
- derived projection moves or deletes a user object
- district removal exceeds stored-object capacity
- camera bounds fail after district attach

## Implementation prohibition

Round 7を理由にrendererやeditor実装を開始しない。

開始前に必要:

- repository-integrated schema / fixture validation
- semantic topology validators and exact expected issue codes
- structural diagram review
- visual comparisons V0–V4
- mobile interaction evidence
- accessibility equivalence
- performance budget
- external review
- unresolved P0 zero
