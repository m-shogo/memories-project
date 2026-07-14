# Memory Town Design Readiness Gate — Round 7 Editable Landscape

最終更新: 2026-07-14

## Verdict

```txt
research:
completed

architecture direction:
locked at design level

schemas / fixtures:
not created

interaction prototype:
not created

visual comparison:
not created

implementation:
NO-GO
```

---

# R7-1 Hierarchical landscape model

Status: DESIGN ADOPTED / MACHINE CONTRACT PENDING

- [x] world frame separated
- [x] district graph defined
- [x] terrain regions defined
- [x] linear path / water features defined
- [x] parcel / object separation retained
- [x] derived detail excluded from source of truth
- [ ] schema
- [ ] synthetic fixtures
- [ ] compatibility projection fixture

# R7-2 Terrain brush

Status: PRODUCT ADOPTED / PROTOTYPE PENDING

- [x] semantic terrain kinds
- [x] automatic edge transition
- [x] one stroke = one command
- [x] building non-destruction
- [ ] brush size candidates
- [ ] touch precision prototype
- [ ] transition atlas estimate
- [ ] undo / redo evidence

# R7-3 Coast and beach editing

Status: LONG-TERM ADOPTED / TOPOLOGY PENDING

- [x] distant sea / near coast separation
- [x] beach width editable candidate
- [x] cove / cape control-handle direction
- [x] harbor anchor preservation
- [ ] coastline topology validator
- [ ] coast profile catalog
- [ ] sand buffer rule
- [ ] mobile before / after prototype

# R7-4 River and stream editing

Status: LONG-TERM ADOPTED / GRAPH CONTRACT PENDING

- [x] source / outlet model
- [x] segment and control-point direction
- [x] width profile direction
- [x] bridge crossing candidate
- [ ] river graph schema
- [ ] cross-district socket fixture
- [ ] isolated-water negative test
- [ ] bank clearance test

# R7-5 Road and path editing

Status: LONG-TERM ADOPTED / ACCESSIBILITY TEST PENDING

- [x] graph / spline direction
- [x] automatic junction projection
- [x] physical / semantic separation
- [x] access root validation retained
- [ ] path graph schema v2
- [ ] building entrance reconnection fixture
- [ ] bridge approach fixture
- [ ] DOM equivalent

# R7-6 Forest and vegetation regions

Status: LONG-TERM ADOPTED / ASSET AND DENSITY PENDING

- [x] region + density model
- [x] deterministic cluster
- [x] pinned tree protection
- [x] seasonal profile
- [ ] density metric
- [ ] silhouette / sightline test
- [ ] asset family estimate
- [ ] reduced-motion / static equivalence

# R7-7 Building relocation

Status: EXISTING DIRECTION HARDENED / PARCEL FIXTURE PENDING

- [x] parcel-based move
- [x] instance / feature binding preservation
- [x] growth envelope preservation
- [x] no free pixel placement
- [ ] parcel candidate fixture
- [ ] entrance reconnect fixture
- [ ] invalid move recovery
- [ ] cross-device conflict test

# R7-8 District expansion

Status: LONG-TERM ADOPTED / SOCKET CONTRACT PENDING

- [x] expansion socket concept
- [x] existing coordinate preservation
- [x] road / river / coast compatibility
- [x] rollback snapshot requirement
- [ ] district definition schema
- [ ] socket compatibility matrix
- [ ] attach / detach commands
- [ ] stored-object recovery
- [ ] map bound / camera update fixture

# R7-9 Area reset and cleanup

Status: ADOPTED / UX PENDING

- [x] area reset instead of one-by-one cleanup
- [x] user object stored, not deleted
- [x] template baseline reset candidate
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

# Required evidence before landscape image generation

```txt
1. exploded layer diagram
2. semantic source vs derived projection diagram
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
4. Round 7 schemas and fixtures
5. E0〜E9 structural prototypes
6. V0〜V4 visual edit comparison
7. six mobile viewport evidence
8. accessibility review
9. performance budget
10. adversarial review
11. unresolved P0 zero
```
