# Next Chat Memory Town Hardening Addendum

最終更新: 2026-07-13

## Repository

- Repo: `m-shogo/memories-project`
- Branch: `so`
- Rule: 作業したらcommit / push

## Current Verdict

```txt
strong_design_not_complete
```

実装はまだ開始しない。

現在はMemory Townの長期空間設計と破綻防止契約を詰めるフェーズ。

---

## Read First

1. `docs/memory-town-architecture-hardening-contract.md`
2. `docs/memory-town-design-audit-and-risk-register.md`
3. `docs/current-product-direction.md`
4. `docs/memory-town-long-term-spatial-model.md`
5. `docs/memory-town-webgl-architecture.md`
6. `docs/memory-town-visual-design-direction.md`
7. `docs/memory-town-hardening-tickets.md`
8. `docs/memory-town-spatial-foundation-tickets.md`
9. `docs/memory-town-implementation-roadmap.md`

既存文書と矛盾する場合、`memory-town-architecture-hardening-contract.md`を優先する。

---

## Product Direction

```txt
どうぶつの森のように、自分の場所へ愛着を持てる箱庭。
ただし、特定作品を複製しない。
```

- 固定視点2.5D
- MVPは固定layout
- 内部はlogical grid
- terrain / path / small object / structureを適切な粒度で分離
- 将来はdecoration、道、植栽、建物移動、district expansion
- Minecraft型の1block建築ではない

---

## Five-state Model

```txt
Memory Domain
Town Feature Progress
Town Layout
Town Environment
Town Render
```

古い4-state設計へ戻さない。

### Important

- Featureの意味とvisualを分離
- `TownFeatureId`をstableにする
- building skin / definition / instance IDへ意味を直結しない
- max unlocked stageをFeature Progressへ保持
- record削除で罰のように縮小しない
- current countは正確に表示
- explicit reset / privacy erasureを提供
- season / time / cameraをFeature Projectionへ混ぜない

---

## Spatial Rules

```txt
origin = logical north-west
+X = east
+Y = south
0° = north
90° = east
180° = south
270° = west
```

- elevationはlogical level
- footprintはpivot中心
- rotation後normalizeしない
- screen x/yを保存しない
- physical path maskは導出
- semantic connectionは別overlay
- major buildingはgrowth envelopeを持つ
- envelope外stageはmigration必須

---

## Object State

```txt
origin:
template / user / migration / system_unlock

placement:
placed / stored / retired

lock policy:
system_fixed / decor_editable / relocatable_later / user_owned
```

禁止:

- `source='projection'`
- `(-999,-999)` holding area
- boolean lockedだけの権限

---

## Template Evolution

```txt
old baseline
+ current user layout
+ new template
→ three-way merge
```

New templateで町を丸ごと再生成しない。

User変更を上書きしない。

---

## Future Editor

```txt
load revision
→ local draft
→ undo / redo
→ atomic command batch
→ server revalidation
→ compare-and-swap
```

- silent last-write-wins禁止
- CRDT初期採用なし
- batch all-or-nothing
- server authoritative validation

---

## Security / Portability

- all town user tables carry user_id
- RLS fail closed
- cross-user ID negative tests
- account deletionでTown全state削除
- Town layout / progress / preferenceをExport可能にする
- Re-importはPreview必須
- unsupported objectはstoredへ

---

## P0 Before Renderer

Rendererより前に固定する。

```txt
Feature registry
Feature binding
Feature progress
Coordinate convention
Footprint pivot
Terrain
Parcel
Growth envelope
Object catalog
Layout template
Three-way merge
Validator
Path state
Persistence source of truth
RLS
Export / reset / recovery
Scene composition
Static fallback
```

PixiJSを先に作らない。

---

## Still Open — Prototype Required

- tile metric
- initial map dimensions
- parcel dimensions
- growth envelope dimensions
- art style
- mobile touch comprehension
- low-end device performance
- atlas / texture memory
- non-shrinking copy
- decoration slot product value
- free editor product value

文書だけで数値を決めない。

---

## Next Design Work

候補順:

1. docs contradiction audit
2. initial Feature Registry fixture
3. initial Map Definition fixture
4. initial Object Catalog fixture
5. initial Layout Template fixture
6. growth envelope draft
7. migration golden fixture definitions
8. RLS negative test matrix for Town
9. Town export / reset UX wire contract
10. visual prototype comparison plan
11. mobile performance test plan

実装コードはまだ書かない。
