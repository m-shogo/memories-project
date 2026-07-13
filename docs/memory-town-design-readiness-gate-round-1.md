# Memory Town Design Readiness Gate — Round 1

最終更新: 2026-07-13

## Verdict

```txt
Round 1 adversarial review:
completed

Round 1 P0 contract correction:
completed

Round 1 schemas / fixtures:
created, not machine validated

Static visual prototype:
specification completed, evidence pending

Implementation:
NO-GO
```

---

# R1-0 Authority and legacy isolation

Status: PASS AT CONTRACT LEVEL

- [✓] Round 1 authority order
- [✓] Feature Registry v2 active
- [✓] Scene Composition v2 active
- [✓] Reset v2 active
- [✓] v1 growth/reset fixtures marked legacy
- [✓] implementation shortcut prohibition
- [ ] machine check that no active dependency resolves to legacy v1

---

# R1-1 Effective visual reset

Status: CONTRACT + FIXTURE PASS / MACHINE PENDING

- [✓] current count and growth contribution split
- [✓] opaque projection cursor
- [✓] growthOriginCursor
- [✓] resetEpoch fence
- [✓] unlock proposal fence
- [✓] explicit reset fixture with current 100 / Stage 0
- [✓] reset cases v2
- [ ] machine schema validation
- [ ] reset/unlock race executable golden test

---

# R1-2 Renderer lifecycle

Status: CONTRACT + FIXTURE PASS / RUNTIME PENDING

- [✓] exact Pixi version policy
- [✓] explicit WebGL preference
- [✓] WebGPU separate gate
- [✓] private ticker
- [✓] autoStart false
- [✓] session generation
- [✓] AbortController
- [✓] stale completion no-op
- [✓] context loss degraded mode
- [✓] runtime lifecycle fixture
- [ ] actual Pixi runtime evidence
- [ ] 100 mount/unmount test
- [ ] context loss browser test

---

# R1-3 Accessibility

Status: CONTRACT PASS / PROTOTYPE PENDING

- [✓] one authoritative React / DOM tree
- [✓] Canvas aria-hidden
- [✓] Pixi accessibility production disabled
- [✓] overlay / list focus isolation
- [✓] DOM editor is keyboard/screen-reader authority
- [✓] duplicate target issue code
- [ ] static overlay evidence
- [ ] 200% text zoom
- [ ] keyboard-only route test
- [ ] screen reader test
- [ ] tab order user test

---

# R1-4 Fallback

Status: CONTRACT PASS / VISUAL PENDING

- [✓] Functional Fallback mandatory
- [✓] Layered Visual Fallback candidate
- [✓] Cached Snapshot non-authoritative
- [✓] single static image promise removed
- [ ] layered fallback mock
- [ ] stage-aware fallback evidence
- [ ] missing asset evidence
- [ ] stale cached snapshot copy

---

# R1-5 Worker and deletion fencing

Status: CONTRACT + FIXTURE PASS / DB INTEGRATION PENDING

- [✓] account lifecycle state
- [✓] deletionEpoch
- [✓] no job enqueue after deletion request
- [✓] write-time fence
- [✓] no resurrection rule
- [✓] layout mutation modes
- [✓] migration/reset/repair lock
- [✓] worker fence cases
- [ ] actual DB constraints
- [ ] actual queue cancellation
- [ ] account deletion integration test
- [ ] object storage purge test

---

# R1-6 Access graph and binding recovery

Status: CONTRACT + FIXTURE PASS / COORDINATE PENDING

- [✓] entrance / access / path graph separation
- [✓] access roots
- [✓] physical path only
- [✓] semantic overlay not path
- [✓] path edit disconnection rejected
- [✓] primary → portal → secondary → DOM-only fallback
- [✓] feature route independent from visual object
- [✓] access connectivity fixture
- [ ] initial map exact access-root coordinates approved
- [ ] all six structures validated against final path fixture
- [ ] path editor property tests

---

# R1-7 Schema and fixture registry

Status: DESIGN PASS / MACHINE PENDING

- [✓] v2 schemas registered
- [✓] Round 1 extension schemas registered
- [✓] Fixture Index v2
- [✓] Round 1 extension index
- [✓] Issue code extension
- [ ] parse all JSON
- [ ] resolve all local `$ref`
- [ ] validate all positive fixtures
- [ ] validate all negative expectations
- [ ] duplicate issue code check across base + extension
- [ ] active dependency graph contains no cycle

---

# R1-8 Static visual prototype

Status: SPEC PASS / EVIDENCE PENDING

- [✓] viewport matrix
- [✓] tile metric candidates A/B/C
- [✓] P0〜P10 scene matrix
- [✓] target-size policy
- [✓] accessibility evidence format
- [✓] layered fallback mock requirements
- [✓] evaluation JSON shape
- [ ] Stage 0〜2 assets
- [ ] actual 6 mobile viewport images
- [ ] actual hit target measurements
- [ ] Growth Envelope visual evidence
- [ ] user comprehension evidence

---

# Implementation authorization

Memory Town domain implementation remains prohibited until:

```txt
1. Round 1 schema / fixture machine validation passes
2. active fixture graph has no legacy dependency
3. Stage 0〜2 minimum asset prototype exists
4. Static prototype passes VP-1 / VP-3 / VP-4
5. External review finds no unresolved P0
```

PixiJS renderer implementation additionally requires:

```txt
1. exact PixiJS version selected
2. lifecycle prototype verifies abort / generation behavior
3. DOM accessibility tree prototype passes
4. layered visual fallback exists
5. context loss test plan executable
6. performance budget candidate selected
```

---

# Stop conditions

次の場合は実装へ進まず設計へ戻る。

- current countをcandidate stageへ再結合したくなる
- growthOriginCursorなしでResetを実装したくなる
- Pixi accessibilityをproductionで同時利用したくなる
- single screenshot fallbackへ戻したくなる
- account deletion fenceをqueue retryで回避したくなる
- path connectivityを見た目で判定したくなる
- visual object消失でrouteも消したくなる
- v1 fixtureへ依存する

---

# Decision

```txt
Round 1で重大な設計欠陥を発見し、v2契約へ修正した。

修正は文章だけでなくschema / fixtureへ落とした。
ただしmachine validationとvisual evidenceは未完了。

現状は「実装してよい」ではなく、
「次の検証へ進める設計」まで到達した状態。
```
