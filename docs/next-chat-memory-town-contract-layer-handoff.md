# Next Chat — Memory Town Contract Layer Handoff

最終更新: 2026-07-13

## Repository

- Repo: `https://github.com/m-shogo/memories-project.git`
- Branch: `so`
- Rule: 作業後は毎回commit / push

## Current instruction

```txt
Memory Townの実装はまだ開始しない。
```

現在は設計契約を詰め、prototype・machine validation・外部reviewの準備を完了させる段階。

## Current verdict

```txt
design contract:
strong_ready_for_external_review_not_prototype_validated

implementation:
no-go
```

## Highest-priority docs

1. `docs/memory-town-architecture-hardening-contract.md`
2. `docs/current-product-direction.md`
3. `docs/memory-town-long-term-spatial-model.md`
4. `docs/memory-town-webgl-architecture.md`
5. `docs/memory-town-concrete-data-contract.md`
6. `docs/memory-town-growth-envelope-and-access-contract.md`
7. `docs/memory-town-persistence-rls-and-recovery-contract.md`
8. `docs/memory-town-fixture-validation-harness-plan.md`
9. `docs/memory-town-prototype-metric-matrix.md`
10. `docs/memory-town-design-readiness-gate.md`
11. `docs/memory-town-design-audit-and-risk-register.md`
12. `docs/memory-town-final-adversarial-review-prompt.md`

Machine-readable contracts:

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/schemas/memory-town/
docs/fixtures/memory-town/fixture-index.v1.json
docs/fixtures/memory-town/
```

## Architecture fixed

```txt
Memory Domain State
Town Feature Progress State
Town Layout State
Town Environment State
Town Render State
```

- feature semantic IDとvisual objectを分離
- building stageはmax unlockedで通常縮まない
- privacy resetは明示command
- fixed-view 2.5D
- logical isometric grid
- parcel / footprint / Growth Envelope
- buildingはmulti-cell completed sprite
- path / terrainはtile
- tree / furnitureはobject
- Physical PathとSemantic Connectionは別model
- DOMが実用UI、PixiJSはrenderer

## Concrete contracts added

- closed JSON Schemas
- local Schema Registry
- Fixture Index
- Feature Registry
- Map Definition
- Growth Envelope Catalog
- Object Catalog
- Layout Template
- non-shrinking Scene case
- three-way Migration case
- negative mutation cases
- atomic Command Batch cases
- Asset Manifest
- Environment Theme Catalog
- deterministic ID / canonical JSON vectors
- Reset cases
- Export package
- Persistence table matrix
- RLS negative cases
- Issue Code Registry

## Important refinements

### Overlay / grid slot

```txt
overlay slot
= ownerへ追従、map cell collisionなし

grid slot
= logical cellを占有、spatial validation対象
```

### Null

Fixture / API JSONでは未設定fieldを省略する。

- stored objectはpositionなし
- seasonMode autoはmanualSeasonなし

### Growth Envelope

```txt
max solid occupied
persistent entrance
protected clearance
required access path
visual overflow
overlay slot
```

を分離。

`reservedGrowthCells`はmax solid occupiedだけを表す。

### Deterministic ID

```txt
namespace + NUL + templateId + NUL + decimalTemplateVersion + NUL + seed
→ SHA-256
→ first 130 bits
→ lowercase RFC4648 Base32 no padding
```

### Persistence

- global definitionsとuser state分離
- user state全tableにuser_id
- RLS fail closed
- app runtime非owner
- composite ownership FK
- command batch atomic
- revision CAS
- account deletion対象

## Current prototype candidate values

固定してはいけない:

- 28x28 map
- parcel dimensions
- tile metric
- Stage footprints
- Growth Envelope cell coordinates
- visual overflow
- path shape
- initial decoration positions
- stage thresholds
- season / time ranges

Contract shapeとstable IDsは固定。

数値はprototype evidence後にversioned fixtureへ反映する。

## Remaining before implementation

```txt
1. machine schema / fixture validation
2. positive fixture all-pass report
3. negative expected-code report
4. Stage 0〜2 visual prototype
5. A/B/C tile metric comparison
6. mobile 6 viewport evidence
7. Growth Envelope screenshot evidence
8. static fallback prototype
9. accessibility prototype
10. device performance baseline
11. user comprehension test
12. final adversarial review
13. P0 findings resolution
```

## Do not do next

- PixiJS implementation
- WebGL renderer code
- DB migration
- Town RLS implementation
- free placement editor
- production asset mass generation
- TownをImport基盤より先行

## Next recommended task

```txt
設計レビューのみ:

1. schema / fixture referenceを再点検
2. final adversarial review promptをFable等へ渡す
3. P0指摘をdocs / schema / fixtureへ反映
4.その後、static visual prototypeの仕様を作る
```

## Final rule

```txt
内部構造を長期対応にする。
しかし、設計書の量だけで実装許可を出さない。

machine validation
visual evidence
実機
user test
external review

が揃うまでNo-Go。
```
