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
- 新しい完成景観画像はE0〜E9後に作る

## Read first

1. `docs/memory-town-current-authority-order-round-7-editable-landscape.md`
2. `docs/memory-town-editable-landscape-model-contract-round-7.md`
3. `docs/memory-town-landscape-editing-tools-and-phases-round-7.md`
4. `docs/memory-town-design-readiness-gate-round-7-editable-landscape.md`
5. `docs/memory-town-editable-landscape-research-round-7.md`
6. `docs/memory-town-current-authority-order-round-6-attachment-scenery.md`
7. `docs/memory-town-current-authority-order-round-5-memory-first.md`

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

## Water boundary

```txt
Distant sea / horizon:
World Frame

Near sea / coast / beach:
Editable

River / stream / canal:
Graph / spline-like semantic route
```

## Expansion

```txt
existing map
+ expansion socket
+ new district
```

District socket kinds:

- land
- road
- river
- coast
- harbor
- view

## Editing phases

```txt
0 authored town
1 style / safe slots
2 vegetation / ground
3 paths / minor water
4 coast / river reshape
5 building relocation
6 district expansion
7 terrace bands research
```

## Next correct sequence

```txt
1. terrain-region schema v1
2. linear-feature graph schema v1
3. district / expansion-socket schema v1
4. landscape command schema v1
5. synthetic valid fixture
6. coast topology negative fixtures
7. river continuity negative fixtures
8. expansion compatibility fixtures
9. v1 cell projection compatibility fixture
10. E0 exploded layer diagram
11. E1 ground brush diagram
12. E2 coast edit diagram
13. E3 river / bridge diagram
14. E4 road / junction diagram
15. E5 forest / pinned tree diagram
16. E6 building parcel move diagram
17. E7 district expansion diagram
18. E8 reset / stored object diagram
19. E9 asset style swap diagram
20. V0〜V4 landscape image comparison
21. mobile gesture prototype
22. performance / accessibility / adversarial review
23. unresolved P0 correction
24. implementation authorization judgment
```

## Current status

```txt
external research:
completed

architecture decision:
completed

Git contracts:
committed and pushed

schemas / fixtures:
not created

structural diagrams:
not created

new visual images:
not created by design

implementation:
NO-GO
```
