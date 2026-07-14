# Memory Town Design Readiness Gate — Round 7 Editable Landscape

最終更新: 2026-07-14

## Verdict

```txt
research:
completed

architecture direction:
locked at design level

schemas / synthetic fixtures:
created and registered

JSON syntax check:
completed locally

cross-file machine validation:
pending

interaction prototype:
not created

structural diagrams / visual comparison:
not created

implementation:
NO-GO
```

---

# R7-1 Hierarchical landscape model

Status: MACHINE CONTRACT CREATED / VALIDATION PENDING

- [x] world frame separated
- [x] district graph defined
- [x] terrain regions defined
- [x] linear path / water features defined
- [x] parcel / object separation retained
- [x] derived detail excluded from source of truth
- [x] terrain-region schema v1
- [x] linear-feature graph schema v1
- [x] district-expansion state schema v1
- [x] landscape command-batch schema v1
- [x] synthetic connected fixtures
- [ ] cross-file machine validation
- [ ] v1 cell projection compatibility fixture

# R7-2 Terrain brush

Status: PRODUCT ADOPTED / COMMAND SHAPE CREATED / PROTOTYPE PENDING

- [x] semantic terrain kinds
- [x] automatic edge transition direction
- [x] one stroke = one command
- [x] building non-destruction rule
- [x] protected-boundary negative case
- [x] overlap negative case
- [ ] brush size candidates
- [ ] touch precision prototype
- [ ] transition atlas estimate
- [ ] undo / redo evidence

# R7-3 Coast and beach editing

Status: LONG-TERM ADOPTED / NEGATIVE CONTRACT CREATED / VALIDATOR PENDING

- [x] distant sea / near coast separation
- [x] beach width editable candidate
- [x] cove / cape control-handle direction
- [x] harbor anchor preservation
- [x] coast-topology-hole negative case
- [ ] coastline topology validator implementation plan
- [ ] building-submersion negative fixture
- [ ] coast profile catalog
- [ ] sand buffer rule
- [ ] mobile before / after prototype

# R7-4 River and stream editing

Status: GRAPH SCHEMA AND CONNECTED FIXTURE CREATED / SEMANTIC VALIDATION PENDING

- [x] source / outlet model
- [x] segment and control-point direction
- [x] width profile direction
- [x] bridge crossing candidate
- [x] river graph schema
- [x] cross-district river socket fixture
- [x] missing outlet negative case
- [x] dangling segment reference negative case
- [x] missing crossing anchor negative case
- [ ] isolated-water negative test
- [ ] bank clearance test
- [ ] building-crossing negative fixture

# R7-5 Road and path editing

Status: GRAPH SCHEMA CREATED / ACCESSIBILITY TEST PENDING

- [x] graph / spline direction
- [x] automatic junction projection direction
- [x] physical / semantic separation
- [x] access root validation retained
- [x] path graph schema
- [x] primary-road disconnected negative case
- [x] bridge-anchor negative case
- [ ] building entrance reconnection fixture
- [ ] positive bridge approach fixture
- [ ] DOM equivalent

# R7-6 Forest and vegetation regions

Status: COMMAND SHAPE AND PIN PROTECTION CASE CREATED / ASSET AND DENSITY PENDING

- [x] region + density model
- [x] deterministic cluster
- [x] pinned tree protection
- [x] seasonal profile
- [x] pinned-tree subtraction negative case
- [ ] density metric
- [ ] silhouette / sightline test
- [ ] asset family estimate
- [ ] reduced-motion / static equivalence

# R7-7 Building relocation

Status: EXISTING DIRECTION HARDENED / COMMAND SHAPE CREATED / PARCEL FIXTURE PENDING

- [x] parcel-based move
- [x] instance / feature binding preservation
- [x] growth envelope preservation
- [x] no free pixel placement
- [x] move-object command shape
- [ ] parcel candidate fixture
- [ ] entrance reconnect fixture
- [ ] invalid move recovery
- [ ] cross-device conflict test

# R7-8 District expansion

Status: STATE AND COMMAND SCHEMAS CREATED / COMPATIBILITY VALIDATION PENDING

- [x] expansion socket concept
- [x] existing coordinate preservation
- [x] road / river / coast compatibility direction
- [x] rollback snapshot requirement
- [x] district / socket / connection state schema
- [x] attach and remove command shapes
- [x] socket-kind mismatch negative case
- [x] connection-profile mismatch negative case
- [x] occupied-socket reuse negative case
- [x] existing-origin relocation negative case
- [ ] district definition catalog schema
- [ ] socket compatibility matrix fixture
- [ ] positive attach / detach fixture
- [ ] stored-object recovery
- [ ] map bound / camera update fixture

# R7-9 Area reset and cleanup

Status: ADOPTED / UX AND COMMAND CONTRACT PENDING

- [x] area reset instead of one-by-one cleanup
- [x] user object stored, not deleted
- [x] template baseline reset candidate
- [ ] area-reset command schema
- [ ] selection UX
- [ ] mixed-origin object behavior
- [ ] undo after reset
- [ ] storage overflow behavior

# R7-10 Performance and rendering

Status: DIRECTION SET / BUDGET PENDING

- [x] chunked reprojection
- [x] dirty-region update
- [x] derived cache replaceable
- [x] final sprite not canonical
- [ ] target chunk metric
- [ ] maximum edited-region benchmark
- [ ] low-power mode
- [ ] asset memory budget
- [ ] PixiJS batching prototype

---

# Machine contract files created

Schemas:

```txt
docs/schemas/memory-town/terrain-region-state.v1.schema.json
docs/schemas/memory-town/linear-feature-graph.v1.schema.json
docs/schemas/memory-town/district-expansion-state.v1.schema.json
docs/schemas/memory-town/landscape-command-batch.v1.schema.json
```

Fixtures:

```txt
docs/fixtures/memory-town/terrain-region-state.round7.valid.v1.json
docs/fixtures/memory-town/linear-feature-graph.round7.valid.v1.json
docs/fixtures/memory-town/district-expansion-state.round7.valid.v1.json
docs/fixtures/memory-town/landscape-command-batch.round7.valid.v1.json
docs/fixtures/memory-town/issue-code-extension.round7-editable-landscape.v1.json
docs/fixtures/memory-town/negative-validation-cases.round7-editable-landscape.v1.json
docs/fixtures/memory-town/fixture-index.round7-editable-landscape-extension.v1.json
```

JSONとしての構文確認は行った。repository全体のresolver、既存fixtureとの参照整合、semantic validator実行はまだ行っていない。

---

# Hard stop conditions

実装へ進まず設計へ戻る。

- final tile IDをuser landscape正本として固定する
- one-cell manual correctionがmain editing loopになる
- terrain editがuser objectをsilent deleteする
- coast editがworld horizonを壊す
- riverがsource / outletなしで保存できる
- district attachで既存座標を移動する
- expansionがrecord count報酬になる
- forestを木instance数千件としてのみ保存する
- WFC結果を説明不能なままcanonical saveする
- free elevation sculptを先に実装する
- Draft Town / atomic validationを迂回する
- Town editorがCapture / Search / Exportより優先される

---

# Next required sequence

```txt
1. repository resolverでRound 7 schema / fixtureをmachine validate
2. v1 cell terrain / path projection compatibility fixture
3. isolated water negative fixture
4. coast edit building-submersion negative fixture
5. river bank-clearance / building-crossing negative fixtures
6. district socket compatibility matrix
7. E0 exploded layer diagram
8. E1 ground brush diagram
9. E2 coast edit diagram
10. E3 river / bridge diagram
11. E4 road / junction diagram
12. E5 forest / pinned tree diagram
13. E6 building parcel move diagram
14. E7 district expansion diagram
15. E8 reset / stored object diagram
16. E9 same semantic state / different asset style diagram
17. V0〜V4 same-town visual edit comparison
18. mobile gesture prototype
19. six mobile viewport evidence
20. performance / accessibility / adversarial review
21. unresolved P0 zero
22. implementation authorization judgment
```

# Required evidence before landscape image generation

```txt
1. E0〜E9 structural diagrams
2. semantic source vs derived projection distinction
3. coast / river / road topology examples
4. district socket examples
5. edit-command and undo boundaries
6. same semantic layout with two asset styles
```

# Required evidence before implementation authorization

```txt
1. Round 1 / 2 machine validation
2. Round 5 Memory-first evidence
3. Round 6 scenic composition evidence
4. Round 7 machine validation
5. E0〜E9 structural prototypes
6. V0〜V4 visual edit comparison
7. six mobile viewport evidence
8. accessibility review
9. performance budget
10. adversarial review
11. unresolved P0 zero
```
