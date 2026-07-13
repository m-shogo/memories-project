# Next Chat Addendum — Memory Town Round 1 Hardening

最終更新: 2026-07-13

次チャットでは、以下を前提としてMemory Town設計を継続する。

## Repository

```txt
https://github.com/m-shogo/memories-project.git
branch: so
```

## 絶対条件

- 実装はまだ開始しない
- 毎回commit / pushする
- 古いv1 growth / scene / reset fixtureを実装へ使わない
- 文書量を完成の証明にしない
- 推測でPASSを作らない
- prototype値を正本へ昇格させない

## 最初に読む

1. `docs/memory-town-current-authority-order-round-1.md`
2. `docs/memory-town-adversarial-review-round-1.md`
3. `docs/memory-town-design-readiness-gate-round-1.md`
4. `docs/memory-town-feature-reset-and-unlock-race-contract.md`
5. `docs/memory-town-p0-runtime-accessibility-fallback-contract.md`
6. `docs/memory-town-worker-fencing-and-account-deletion-contract.md`
7. `docs/memory-town-access-connectivity-and-binding-recovery-contract.md`
8. `docs/memory-town-static-visual-prototype-spec.md`

Schema / fixture:

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/fixtures/memory-town/fixture-index.v2.json
docs/fixtures/memory-town/fixture-index.round1-extension.v1.json
```

## Round 1で見つけたP0

### 1. Resetが効かない

旧方式:

```txt
displayStage = max(current-count candidate, max unlocked)
```

では、現在件数が多いとReset直後にStageが戻る。

新方式:

```txt
currentEligibleItemCount
≠
growthEligibleContributionCount since growthOriginCursor
```

Reset時にcurrent projection cursorを新しい成長原点として保存する。

### 2. accessibility tree二重化

Production:

```txt
React / DOM = interaction / accessibility正本
Pixi canvas = aria-hidden visual renderer
Pixi accessibility plugin = disabled
```

### 3. fallback誤定義

```txt
Functional Fallback
Layered Visual Fallback
Cached Snapshot Fallback
```

へ分離。一枚画像をdynamic Townの正確な正本と呼ばない。

### 4. renderer async race

- exact Pixi version
- explicit WebGL
- private ticker
- autoStart false
- session generation
- AbortController
- stale async completion no-op

### 5. account deletion worker resurrection

- account lifecycle state
- deletionEpoch
- job expected epoch
- write-time fence
- deletion開始後enqueue禁止

### 6. access connectivity

```txt
entrance clearance
→ required access cell
→ physical path graph
→ enabled access root reachable
```

Semantic connectionはpathとして数えない。

## Active v2

```txt
feature-registry.v2.schema.json
feature-registry.v2.json
scene-composition-case.v2.schema.json
scene-composition.non-shrinking.v2.json
scene-composition.explicit-reset.v2.json
reset-case-set.v2.schema.json
reset-cases.v2.json
```

## Round 1 extension fixtures

```txt
issue-code-extension.round1.v1.json
worker-fence-cases.v1.json
access-connectivity-cases.v1.json
runtime-lifecycle-cases.v1.json
```

## Current status

```txt
P0 contracts: corrected
P0 fixtures: created
Schema Registry: updated
README: updated
Machine validation: not run
Visual assets: not created
Static prototype evidence: not created
Implementation: NO-GO
```

## 次の正しい順序

```txt
1. schema / fixture internal consistency review
2. machine validation runnerを作るかのauthorization確認
3. static prototype asset brief
4. Stage 0〜2 visual prototype
5. tile metric A/B/C比較
6. DOM accessibility / layered fallback evidence
7. external multidisciplinary review
8. unresolved P0修正
9. implementation authorization judgment
```

## 次回の最優先確認

- Schema Registryの全pathが存在するか
- base + extension issue codeに重複がないか
- active fixture依存にv1 growth fixtureが残っていないか
- `feature-registry.v2` threshold順序・stage連番
- scene v2 cursor / reset epoch整合
- worker fence expected issue code
- access graph fixtureの座標を最終map候補と混同していないか
- runtime lifecycle event transitionが一意か
- volatile fieldをscene content hashへ入れない契約

## 禁止

- v1へ戻す
- current countとgrowth contributionを再統合
- Pixi accessibilityとの二重DOM
- single static screenshot fallback
- route leaveでtickerだけ止めて完了扱い
- account cascade deleteだけで完了扱い
- access root検証省略
- visual objectが消えたらrouteも消す

この状態から続ける。
