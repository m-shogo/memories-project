# Memory Town Design Readiness Gate

最終更新: 2026-07-13

## Current verdict

```txt
design_contract_status:
strong_ready_for_external_review_not_prototype_validated

implementation_status:
no_go
```

「完璧」とは判定しない。

理由は、契約層は強くなったが、visual prototype、machine validation、実機、user testの証拠がまだないため。

---

# Gate D0: Product boundary

Status: PASS

```txt
[✓] Memory OS本体は棚・検索・Import・Export
[✓] Townは感情的menu
[✓] WebGL内にform / long text / security actionを置かない
[✓] game economyなし
[✓] streak / decay / guiltなし
[✓] AI importance scoringなし
[✓] free editorをMVPへ入れない
```

---

# Gate D1: State separation

Status: PASS

```txt
[✓] Memory Domain
[✓] Town Feature Progress
[✓] Town Layout
[✓] Town Environment
[✓] Town Render
```

```txt
[✓] Feature IDとvisual instance分離
[✓] non-shrinking progress
[✓] layoutとprojection分離
[✓] environmentとmemory分離
[✓] render state非永続
```

---

# Gate D2: Spatial contract

Status: CONTRACT PASS / DIMENSION PENDING

```txt
[✓] logical grid
[✓] coordinate axes
[✓] parcel
[✓] current footprint
[✓] Growth Envelope
[✓] entrance / clearance / access path分離
[✓] multi-cell completed building sprite
[✓] physical path / semantic overlay分離
[✓] overlay / grid decoration slot分離
[✓] holding area = stored without magic coordinate
```

Pending:

```txt
[ ] tile metric
[ ] map dimensions
[ ] parcel dimensions
[ ] concrete visual overflow
[ ] hit polygons
[ ] stage asset bounds
```

---

# Gate D3: Evolution / migration

Status: PASS

```txt
[✓] stable IDs
[✓] separate versions
[✓] deprecated definition preservation
[✓] three-way template merge
[✓] user changes preserved
[✓] invalid new object → stored
[✓] atomic apply
[✓] rollback snapshot
[✓] Reset scopes separated
[✓] Town Export / Re-import Preview
```

---

# Gate D4: Concurrency

Status: PASS

```txt
[✓] command batch
[✓] idempotent batch ID
[✓] same ID / different hash rejected
[✓] expected revision CAS
[✓] whole batch dry-run
[✓] whole batch rollback
[✓] no silent last-write-wins
```

---

# Gate D5: Privacy / security

Status: PASS AT CONTRACT LEVEL

```txt
[✓] raw memory excluded from scene
[✓] private title / person name / URL excluded
[✓] all user tables user_id
[✓] RLS fail closed
[✓] app role non-owner
[✓] composite ownership FK policy
[✓] support default denied
[✓] account deletion includes Town
[✓] safe issue messages
[✓] issue code registry
```

Pending implementation evidence:

```txt
[ ] actual RLS policy tests
[ ] actual account deletion integration
[ ] actual support ceremony
[ ] actual audit redaction
```

---

# Gate D6: Concrete contract assets

Status: PASS AT DESIGN LEVEL

```txt
[✓] closed JSON Schemas
[✓] Schema Registry
[✓] Fixture Index
[✓] positive fixtures
[✓] negative mutation fixtures
[✓] scene golden fixture
[✓] migration golden fixture
[✓] command golden fixture
[✓] reset fixture
[✓] export fixture
[✓] persistence matrix
[✓] RLS negative fixture
[✓] deterministic ID vectors
[✓] canonical JSON hash vector
[✓] validation harness plan
```

Pending:

```txt
[ ] machine validation runner
[ ] actual all-pass report
```

これは実装作業なので、現フェーズではNo-Goのまま残す。

---

# Gate D7: Assets

Status: PENDING

```txt
[✓] stable texture keys
[✓] fallback policy
[✓] provenance policy
[✓] no fake hash
[✓] atlas groups candidate
[ ] actual Stage 0〜2 sprites
[ ] dimensions
[ ] anchors
[ ] hit polygons
[ ] SHA-256
[ ] license records
[ ] stage family compatibility
```

---

# Gate D8: Prototype

Status: PENDING

Required:

```txt
[ ] A/B/C tile metric comparison
[ ] mobile 6 viewport
[ ] P0〜P6 prototype scenes
[ ] Stage 0〜2 silhouette comparison
[ ] Growth Envelope evidence
[ ] tap target overlap check
[ ] static fallback
[ ] reduced motion
[ ] high contrast
[ ] text zoom
```

---

# Gate D9: Device / performance

Status: PENDING

```txt
[ ] recent iPhone
[ ] older supported iPhone
[ ] mid-range Android
[ ] low-end supported Android
[ ] context loss / restore
[ ] background / foreground
[ ] texture memory
[ ] battery / heat
[ ] 30-minute idle leak
[ ] route enter / leave repetition
```

---

# Gate D10: User comprehension

Status: PENDING

```txt
[ ] cinema → movie shelf
[ ] story house → manga/anime
[ ] market → food
[ ] port → travel
[ ] warehouse → Inbox
[ ] square → reflection
[ ] labels ON / OFF
[ ] Stage 2 / current count 0 acceptance
[ ] decoration slot value
[ ] free editor demand
```

---

# Gate D11: External adversarial review

Status: PENDING

Required reviewers:

```txt
product / UX
frontend / PixiJS
backend / DB
security / privacy
accessibility
long-term migration
cost / operations
```

Review must search for:

- conflicting sources of truth
- hidden coupling
- irreversible migration
- cross-user leakage
- editor scope creep
- WebGL-only accessibility
- asset licensing gap
- performance assumptions
- inconsistent schema / fixture

---

# Implementation authorization

Memory Town implementation may begin only when:

```txt
D0〜D6 PASS
+ D7 minimum approved prototype assets
+ D8 minimum static prototype evidence
+ D11 critical findings resolved
```

PixiJS renderer implementation requires additional:

```txt
machine fixture validation pass
scene snapshot contract pass
static fallback pass
asset manifest approved subset
performance budget candidate
```

Free editor implementation requires:

```txt
slot personalization evidence
command / undo / reset implemented and tested
RLS integration pass
user demand evidence
Memory OS core not displaced
```

---

# Stop conditions

次が起きたら設計へ戻る。

```txt
schema変更なしでは新要件を表せない
user objectを黙って削除する必要が出る
Memory DomainとTown stateを混ぜたくなる
rendererへprivacy判定を入れたくなる
asset都合でstable entranceを動かす
map拡張で既存parcel IDの意味を変える
TownがImport基盤より優先される
editorがMemory OS本体より重くなる
```

---

# Final statement

```txt
契約層はかなり強い。

ただし、設計書が多いことは完成の証明ではない。

machine validation
visual prototype
実機
user test
外部レビュー

を通して初めて、実装開始を許可する。
```
