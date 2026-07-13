# Next Chat Addendum — Memory Town Round 2 Environment

最終更新: 2026-07-13

次チャットでは、以下を前提としてMemory Townの設計を継続する。

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## 絶対条件

- 実装はまだ開始しない
- 毎回commit / pushする
- Environment v1を実装へ使わない
- 4時間帯を勝手に5時間帯へ増やさない
- 16枚の完成背景を正本にしない
- Memory Treeへ重要度・感情・streak・課金を混ぜない
- 冬を罰・死・放置として描かない
- real weather / tide / astronomyと誤認させない
- prototype候補値を証拠なしで承認しない

## 最初に読む

1. `docs/memory-town-current-authority-order-round-2-environment.md`
2. `docs/memory-town-environment-and-seasonal-life-contract.md`
3. `docs/memory-town-environment-asset-brief.md`
4. `docs/memory-town-static-visual-prototype-environment-addendum.md`
5. `docs/memory-town-design-readiness-gate-round-2-environment.md`
6. `docs/memory-town-current-authority-order-round-1.md`

Schema / fixture:

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/fixtures/memory-town/fixture-index.v2.json
docs/fixtures/memory-town/fixture-index.round1-extension.v1.json
docs/fixtures/memory-town/fixture-index.round2-environment-extension.v1.json
```

## Active Environment

```txt
docs/schemas/memory-town/environment-theme-catalog.v2.schema.json
docs/fixtures/memory-town/environment-theme-catalog.v2.json
```

Legacy / implementation禁止:

```txt
docs/schemas/memory-town/environment-theme-catalog.v1.schema.json
docs/fixtures/memory-town/environment-theme-catalog.v1.json
```

## Active Memory Tree

```txt
docs/schemas/memory-town/memory-tree-catalog.v1.schema.json
docs/fixtures/memory-town/memory-tree-catalog.v1.json
```

## Canonical time modes

```txt
morning
05:00–10:59 candidate

day
11:00–16:59 candidate

night
17:00–22:59 candidate

midnight
23:00–04:59 candidate
```

`evening`はnightへのvisual transitionであり、第5modeではない。

## Initial environment inclusion

- current device local time
- manual time / season preview
- four sky profiles
- cloud motion
- sun / moon non-astronomical movement
- stars
- four building-light profiles
- beach / coast / water terrain
- distant water / reflection / shore foam
- Memory Tree 3 stages
- spring sakura motif
- summer deep green
- autumn momiji motif
- winter warm dormant motif
- seasonal ground cues
- unified wind field
- motion off / reduced / full / low power
- layered fallback
- optional sound foundation, default OFF

## Not initial

- real weather API
- GPS
- real tide API
- astronomical position
- collecting / fishing / crafting
- moon phase accuracy
- rare sky events
- generic citizens

## Round 2 issue code extension

```txt
docs/fixtures/memory-town/issue-code-extension.round2-environment.v1.json
```

主要code:

```txt
ENVIRONMENT_V1_ACTIVE_DEPENDENCY
TIME_MODE_SET_MISMATCH
TIME_MODE_RANGE_OVERLAP
TIME_MODE_RANGE_GAP
MEMORY_TREE_THRESHOLD_NON_MONOTONIC
MEMORY_TREE_STAGE_SEQUENCE_INVALID
MEMORY_TREE_EXACT_COUNT_EXPOSED
MEMORY_TREE_WINTER_PUNITIVE_VISUAL
MOTION_OFF_STATE_MISSING
LAYERED_FALLBACK_ENVIRONMENT_MISMATCH
BEACH_BAKED_BACKGROUND_ONLY
SEASON_REQUIRES_PARTICLE_FOR_RECOGNITION
```

## Current status

```txt
Round 2 environment contract:
completed

Environment v2 schema / fixture:
created

Memory Tree schema / fixture:
created

Schema Registry:
updated

README:
updated

machine validation:
not run

visual assets:
not created

static visual evidence:
not created

implementation:
NO-GO
```

## 次の正しい順序

```txt
1. Environment v2 / Memory Tree JSON internal consistency review
2. machine validation authorization
3. time ranges 24-hour coverage validation
4. Tree stage / threshold monotonicity validation
5. beach A/B/C placement rough
6. Memory Tree T-A/T-B/T-C placement rough
7. four time-mode palette roughs
8. Tree Stage 0〜2 × four-season silhouette roughs
9. layered fallback environment mock
10. six mobile viewport comparison
11. accessibility / emotional-safety review
12. external multidisciplinary review
13. unresolved P0 correction
14. implementation authorization judgment
```

## Prototype scenes

```txt
E0 spring morning / Tree Stage 0
E1 summer day / Tree Stage 1
E2 autumn night / Tree Stage 2
E3 winter midnight / Tree Stage 2
E4 four time modes
E5 four seasons
E6 motion profiles
E7 layered fallback
E8 200% text zoom midnight
E9 low power
E10 Tree privacy reset
```

## 最優先確認

- Environment v2 rangesが24時間を重複なく覆うか
- `morning / day / night / midnight`の順序とschema constが一致するか
- Tree stageが0 / 1 / 2連番か
- Tree thresholdが単調増加か
- Tree exact countがUIへ漏れないか
- Winter asset briefがpunitive visualを誘発しないか
- Beachがmap terrainとして扱われているか
- Fallbackが同じtime / season / Tree stageを表現できるか
- motion offで四季と時間を認識できるか
- Environment v1へのactive dependencyが残っていないか

この状態から続ける。
