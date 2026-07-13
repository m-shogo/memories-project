# Memory Town Current Authority Order — Round 1

最終更新: 2026-07-13

## 目的

Adversarial Review Round 1で修正した契約と、以前のv1設計が同時に存在するため、実装担当が古い式・fixture・fallback・accessibility方針を採用しないよう、現在の優先順位とsupersessionを固定する。

実装はまだ開始しない。

---

# 1. Current verdict

```txt
contract_status:
round1_p0_resolved_at_contract_and_fixture_level

machine_validation:
pending

visual_prototype:
pending

implementation:
no_go
```

---

# 2. Authority order

矛盾する場合、上を優先する。

```txt
1. memory-town-current-authority-order-round-1.md
2. memory-town-adversarial-review-round-1.md
3. memory-town-feature-reset-and-unlock-race-contract.md
4. memory-town-p0-runtime-accessibility-fallback-contract.md
5. memory-town-worker-fencing-and-account-deletion-contract.md
6. memory-town-access-connectivity-and-binding-recovery-contract.md
7. memory-town-architecture-hardening-contract.md
8. current-product-direction.md
9. memory-town-long-term-spatial-model.md
10. memory-town-webgl-architecture.md
11. concrete data / persistence / visual / roadmap documents
12. legacy fixture and schema documents
```

同順位の文書が矛盾する場合、後日付だから自動的に正しいとは扱わず、明示的なADRまたは本書更新を必要とする。

---

# 3. Active schemas and fixtures

## Feature Registry

Active:

```txt
docs/schemas/memory-town/feature-registry.v2.schema.json
docs/fixtures/memory-town/feature-registry.v2.json
```

Legacy / implementation禁止:

```txt
feature-registry.v1.schema.json
feature-registry.v1.json
```

理由:

v1はcurrent eligible countを成長candidateへ直接使用し、明示Resetが実質的に効かない。

## Scene Composition

Active:

```txt
scene-composition-case.v2.schema.json
scene-composition.non-shrinking.v2.json
scene-composition.explicit-reset.v2.json
```

Legacy / implementation禁止:

```txt
scene-composition-case.v1.schema.json
scene-composition.non-shrinking.v1.json
```

## Reset

Active:

```txt
reset-case-set.v2.schema.json
reset-cases.v2.json
```

Legacy / implementation禁止:

```txt
reset-case-set.v1.schema.json
reset-cases.v1.json
```

## Round 1 extension fixtures

Active:

```txt
issue-code-extension.round1.v1.json
worker-fence-cases.v1.json
access-connectivity-cases.v1.json
runtime-lifecycle-cases.v1.json
```

Index:

```txt
fixture-index.v2.json
+ fixture-index.round1-extension.v1.json
```

---

# 4. Superseded formulas and statements

## 4.1 Candidate stage

Superseded:

```txt
candidateStage = resolveStage(currentEligibleItemCount)
```

Active:

```txt
candidateStage = resolveStage(
  growthEligibleContributionCountSinceOrigin
)
```

Current countはUI表示用であり、Reset後のcandidate計算へ直接使用しない。

## 4.2 Feature progress

Superseded:

```ts
interface TownFeatureProgress {
  maxUnlockedStage: number;
  resetEpoch: number;
}
```

Active concept:

```ts
interface TownFeatureProgressV2 {
  maxUnlockedStage: number;
  resetEpoch: number;
  growthOriginCursor: string;
}
```

## 4.3 Accessibility

Superseded / prohibited production combination:

```txt
Pixi accessibility DOM overlay
+ independent React DOM overlay
```

Active:

```txt
React / DOM = authoritative interaction and accessibility tree
Pixi Canvas = aria-hidden visual renderer
Pixi accessibility plugin = production disabled
```

## 4.4 Fallback

Superseded:

```txt
single static image = exact current Town fallback
```

Active:

```txt
Functional Fallback = DOM routes / list
Layered Visual Fallback = base + object images
Cached Snapshot = optional stale preview only
```

## 4.5 Runtime lifecycle

Superseded:

```txt
route leave → ticker stop only
```

Active:

```txt
AbortController
+ rendererSessionGeneration
+ private ticker
+ explicit lifecycle state machine
+ stale async completion no-op
```

## 4.6 Access validation

Superseded:

```txt
entrance clear = accessible
```

Active:

```txt
entrance clear
+ required access cell valid
+ physical path graph
+ enabled access root reachable
```

Semantic connection overlayはphysical pathとして数えない。

## 4.7 Account deletion

Superseded:

```txt
cascade deleteだけで完了
```

Active:

```txt
account lifecycle state
+ deletionEpoch
+ background job fence
+ stale write rejection
+ cache / thumbnail invalidation
```

---

# 5. PixiJS MVP decisions

Current contract:

```txt
PixiJS v8 exact version pin
renderer preference = webgl
WebGPU = separate future gate
sharedTicker = false
autoStart = false
Application.init before Assets load
Assets manifest / bundle lifecycle
```

具体version番号はpackage selection時にofficial release / compatibility確認後固定する。

---

# 6. Static prototype decisions

正本:

```txt
memory-town-static-visual-prototype-spec.md
```

比較候補であり未確定:

- tile metric A / B / C
- map dimensions
- parcel dimensions
- building asset bounds
- hit polygon
- target rectangles
- bottom sheet height
- reduced motion frame policy

これらを既存fixtureへ確定値として書き戻すのはprototype evidence後。

---

# 7. Prohibited implementation shortcuts

- v1 Feature Registryを使う
- current countだけでReset後candidateを計算する
- Pixi accessibilityとReact overlayを同時focusableにする
- single static imageをdynamic Town正本にする
- shared tickerへ依存する
- route leave後のasync completionを無条件適用する
- cascade deleteだけでworker resurrectionを防げると扱う
- entrance clearanceだけでaccessibility PASSにする
- physical pathとsemantic connectionを混ぜる
- primary binding visualが消えたらfeature routeも消す
- volatile generatedAtをscene content hashへ含める

---

# 8. Required next sequence

```txt
1. Round 1 schema / fixture machine validation
2. cross-document contradiction scan
3. static visual prototype asset brief
4. Stage 0〜2 prototype images
5. A/B/C metric comparison
6. accessibility / fallback static evidence
7. external multidisciplinary review
8. critical findings correction
9. implementation authorization judgment
```

---

# Decision

```txt
Round 1で見つかったP0は、契約とfixtureのv2へ修正した。
ただし、machine validationとvisual evidenceはまだない。

古いv1を実装へ使わない。
実装は引き続きNo-Go。
```
