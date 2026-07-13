# Memory Town Design Readiness Gate — Round 2 Environment

最終更新: 2026-07-13

## Verdict

```txt
Environment direction:
locked at contract level

Environment v2 / Memory Tree:
created, machine validation pending

Visual prototype:
specification complete, evidence pending

Implementation:
NO-GO
```

---

# E2-0 Authority and legacy isolation

Status: PASS AT CONTRACT LEVEL

- [✓] Round 2 environment authority order
- [✓] Environment v2 active
- [✓] Environment v1 marked legacy for implementation
- [✓] canonical modes = morning / day / night / midnight
- [✓] `evening` not added as fifth canonical mode
- [ ] machine check for active Environment v1 dependency

---

# E2-1 Time model

Status: CONTRACT + FIXTURE PASS / MACHINE AND VISUAL PENDING

- [✓] device local time
- [✓] no precise location
- [✓] manual fixed mode
- [✓] non-persistent preview mode
- [✓] four candidate ranges
- [✓] crossfade candidate
- [✓] sun / moon movement is non-astronomical
- [ ] 24-hour no-gap / no-overlap machine validation
- [ ] four palette roughs
- [ ] four boundary transition mocks
- [ ] night / midnight comprehension evidence

---

# E2-2 Sky and lighting

Status: CONTRACT PASS / ASSET PENDING

- [✓] layered sky
- [✓] reusable cloud sprites
- [✓] sun / moon separation
- [✓] star visibility profiles
- [✓] four building-light profiles
- [✓] four shadow presets
- [✓] no dynamic 3D shadow requirement
- [ ] palette tokens
- [ ] building Stage 2 light masks
- [ ] midnight contrast evidence

---

# E2-3 Beach and waves

Status: CONTRACT PASS / MAP AND ASSET PENDING

- [✓] beach included in initial map direction
- [✓] terrain = water / coast / sand
- [✓] beach not baked into single background
- [✓] three shoreline layers
- [✓] no real tide claim
- [✓] motion off support
- [✓] no collecting / fishing scope
- [ ] beach position comparison A/B/C
- [ ] port access compatibility
- [ ] wave loop seam evidence
- [ ] low-power still frame

---

# E2-4 Memory Tree

Status: CONTRACT + FIXTURE PASS / THRESHOLD, ASSET AND SPATIAL PENDING

- [✓] fictional seasonal species
- [✓] three growth stages
- [✓] spring sakura motif
- [✓] summer deep-green motif
- [✓] autumn momiji motif
- [✓] winter warm dormant motif
- [✓] information quantity only
- [✓] no importance / emotion / streak / payment
- [✓] hidden / sealed / restricted / deleted excluded
- [✓] non-shrinking normal deletion
- [✓] reset / hide / privacy reset
- [✓] exact count not exposed
- [ ] threshold monotonicity machine validation
- [ ] threshold product approval
- [ ] 12 principal sprites
- [ ] maximum silhouette
- [ ] Tree Growth Envelope
- [ ] central-square placement comparison
- [ ] winter emotional-safety evidence

---

# E2-5 Seasons beyond the tree

Status: CONTRACT PASS / VISUAL PENDING

- [✓] seasonal ground cues
- [✓] particles not required for recognition
- [✓] spring flower patch
- [✓] summer ground / shore cue
- [✓] autumn leaf patch
- [✓] winter snow cap / warm light cue
- [ ] particle-off four-season comparison
- [ ] building readability in all seasons
- [ ] winter non-punitive user test

---

# E2-6 Motion and power

Status: CONTRACT PASS / RUNTIME PENDING

- [✓] unified wind field
- [✓] off / reduced / full / low-power profiles
- [✓] priority order for motion
- [✓] hidden tab pause
- [✓] route leave pause
- [✓] stale async completion fenced by Round 1 contract
- [ ] static motion-off evidence
- [ ] reduced-motion user test
- [ ] low-power visual evidence
- [ ] actual battery / heat test

---

# E2-7 Sound

Status: FOUNDATION ONLY

- [✓] default OFF
- [✓] autoplay prohibited
- [✓] user gesture required
- [✓] route / tab lifecycle
- [✓] no information loss when disabled
- [ ] sound assets
- [ ] user preference study

Sound is not an implementation blocker for the first static visual prototype.

---

# E2-8 Accessibility and fallback

Status: CONTRACT PASS / EVIDENCE PENDING

- [✓] React / DOM interaction authority
- [✓] Canvas aria-hidden
- [✓] environment motion not focusable
- [✓] layered fallback includes Tree and beach
- [✓] time / season not conveyed by motion alone
- [✓] motion off
- [ ] 200% zoom midnight scene
- [ ] focus-ring contrast
- [ ] layered fallback environment state match
- [ ] keyboard / screen-reader route evidence

---

# E2-9 Schema and fixture

Status: DESIGN PASS / MACHINE PENDING

- [✓] Environment v2 schema
- [✓] Environment v2 fixture
- [✓] Memory Tree schema
- [✓] Memory Tree fixture
- [✓] schema registry entries
- [✓] Round 2 fixture index
- [✓] Round 2 issue code extension
- [ ] parse all JSON
- [ ] resolve all `$ref`
- [ ] validate positive fixtures
- [ ] duplicate issue code scan
- [ ] time-range coverage test
- [ ] stage sequence test
- [ ] threshold monotonicity test
- [ ] active graph legacy-dependency test

---

# E2-10 Static visual prototype

Status: SPEC PASS / EVIDENCE PENDING

Required:

```txt
E0 spring morning / Tree Stage 0
E1 summer day / Tree Stage 1
E2 autumn night / Tree Stage 2
E3 winter midnight / Tree Stage 2
E4 four time modes
E5 four seasons
E6 motion profiles
E7 layered fallback
E8 200% zoom midnight
E9 low power
E10 Tree privacy reset
```

- [ ] tile A/B/C comparison with beach and Tree included
- [ ] six mobile viewport composites
- [ ] beach A/B/C placement
- [ ] Tree T-A/T-B/T-C placement
- [ ] Stage 0〜2 silhouette
- [ ] building target overlap evidence
- [ ] comprehension test

---

# Implementation authorization

Environment domain implementation remains prohibited until:

```txt
1. Environment v2 / Memory Tree machine validation passes
2. active dependency graph contains no Environment v1
3. time ranges cover 24 hours exactly once
4. four time-mode palette roughs exist
5. Memory Tree 3 stages × four seasons roughs exist
6. beach and Tree placement candidate is approved
7. E2-8 accessibility minimum evidence passes
8. layered fallback matches effective environment state
9. no unresolved P0 from review
```

PixiJS ambient animation additionally requires:

```txt
1. motion off / reduced / low-power states proven
2. route / hidden-tab lifecycle prototype
3. wave and cloud loop memory budget candidate
4. current-time re-resolve on resume
5. no duplicate accessibility tree
```

---

# Stop conditions

次の場合は設計へ戻る。

- 4時間帯を背景16枚で実現しようとする
- Treeを情報の価値scoreへ接続する
- 冬を枯死や放置の罰にする
- motion particleがないと季節を判別できない
- real weather / tide / astronomyと誤認させる
- beachをlogical map外の背景へ固定する
- midnightで機能targetが見えなくなる
- Environment v1をactive dependencyへ戻す
- soundを自動再生する
- Tree Stageから正確な件数を示す

---

# Final statement

```txt
Round 2で環境の方向性は固定した。

ただし、空・海・四季樹は魅力が大きい分、
map寸法、asset数、暗所contrast、motion、privacy推測を同時に壊し得る。

machine validationと静止visual evidenceが揃うまで実装しない。
```
