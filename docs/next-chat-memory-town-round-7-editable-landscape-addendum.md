# Next Chat Addendum — Memory Town Round 7 Editable Landscape

最終更新: 2026-07-14

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## Absolute conditions

- 実装はまだ開始しない
- 毎回commit / pushする
- Memory-first hierarchyを維持する
- landscapeを一枚絵の正本にしない
- final tile IDをuser layoutの正本にしない
- one-cell editingをmain UXにしない
- derived transitionでuser objectを削除・移動しない
- existing map origin / coordinatesを拡張時に変更しない
- free elevation sculptを先に実装しない
- Draft Town / atomic validation / rollbackを必須にする
- V0〜V4は同じsemantic townの編集前後として作る

## Read first

1. `docs/memory-town-current-authority-order-round-7-editable-landscape.md`
2. `docs/memory-town-editable-landscape-model-contract-round-7.md`
3. `docs/memory-town-landscape-editing-tools-and-phases-round-7.md`
4. `docs/memory-town-design-readiness-gate-round-7-editable-landscape.md`
5. `docs/memory-town-editable-landscape-structural-diagrams-e0-e9-round7.md`
6. `docs/memory-town-round7-targeted-schema-validation-report-2026-07-14.md`
7. `docs/memory-town-editable-landscape-research-round-7.md`
8. `docs/memory-town-current-authority-order-round-6-attachment-scenery.md`
9. `docs/memory-town-current-authority-order-round-5-memory-first.md`

## Core decision

```txt
Hierarchical Editable Diorama
```

```txt
World Frame
→ District / Expansion Graph
→ Semantic Terrain Regions
→ Road / River Linear Graphs
→ Parcels / Anchors
→ Houses / Trees / Objects
→ Derived Transitions and Micro-details
```

## Long-term editable features

- grass / soil / stone / forest floor
- coast and beach width
- small cove / cape
- river / stream / canal
- roads / footpaths / boardwalks
- forest / grove / flower region
- houses and feature-building parcel
- bridge at approved crossing
- district expansion

## Machine contracts created

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

Targeted JSON Schema Draft 2020-12 validation:

```txt
schemas: PASS
positive fixtures: PASS
issue-code extension: PASS
negative-case shape: PASS
```

Repository-wide resolver and semantic topology execution remain pending.

## Structural diagrams created

```txt
E0 exploded layers
E1 terrain brush
E2 coast reshape
E3 river + bridge
E4 road + junction
E5 forest + pinned tree
E6 building parcel move
E7 district socket expansion
E8 area reset / stored object
E9 same semantic town / different asset style
```

## V1 compatibility locked

```txt
forest_floor → grass
plaza → stone
shallow_water → water
marsh → water
promenade / boardwalk → footpath
validated road-river crossing → bridge
```

Do not persist:

```txt
connectionMask
coastlineMask
riverbankMask
derivedSpriteId
```

## Negative cases already defined

- terrain region overlap
- protected plaza edit
- coast topology hole
- missing river outlet
- dangling river segment reference
- road-river crossing without bridge anchor
- disconnected primary road
- district socket kind mismatch
- district profile mismatch
- occupied socket reuse
- expansion moves existing origin
- stale landscape revision
- pinned tree subtraction

## Next correct sequence

```txt
1. repository-integrated schema registry validation
2. semantic validator specification and implementation plan
3. isolated-water negative case
4. coast edit building-submersion negative case
5. river bank-clearance / building-crossing negative cases
6. derived-detail user-object mutation negative case
7. district socket compatibility matrix
8. positive district attach / detach fixture
9. positive bridge approach fixture
10. area-reset command schema
11. E0〜E9 mobile review and correction
12. V0〜V4 same-town image comparison
13. mobile gesture prototype
14. six viewport evidence
15. PixiJS chunk / memory / low-power budget
16. accessibility / emotional-safety / adversarial review
17. unresolved P0 correction
18. implementation authorization judgment
```

## Current status

```txt
external research:
completed

architecture decision:
completed

schemas and fixture shapes:
created and targeted validation PASS

repository-integrated validation:
pending

semantic topology validators:
pending

E0–E9 structural diagrams:
created, review pending

V0–V4 visual images:
not created by design

mobile interaction prototype:
not created

implementation:
NO-GO
```
