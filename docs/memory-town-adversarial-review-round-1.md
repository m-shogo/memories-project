# Memory Town Adversarial Review Round 1

最終更新: 2026-07-13

## Verdict

```txt
status: not_ready
implementation: no_go
```

契約層は強いが、実装前に修正必須のP0が残っている。

本レビューは実装を行わず、既存の正本、schema、fixture、PixiJS v8公式仕様を突き合わせた結果である。

---

# P0 Findings

## MT-AR1-P0-001 Feature reset is visually ineffective

対象:

- `memory-town-architecture-hardening-contract.md`
- `memory-town-webgl-architecture.md`
- `reset-cases.v1.json`
- `scene-composition.non-shrinking.v1.json`

現状:

```txt
displayStage = max(candidateStage, maxUnlockedStage)
```

`reset_feature_progress`が`maxUnlockedStage = 0`にしても、現在のeligible countがStage 2閾値以上なら`candidateStage = 2`となり、その場でStage 2へ戻る。

Failure scenario:

```txt
映画100件
→ Stage 2
→ user_requested_visual_reset
→ maxUnlockedStage = 0
→ candidateStage = 2
→ 表示はStage 2のまま
```

Correction:

- current eligible countとgrowth candidate countを分離する
- Feature Progressへopaqueな`growthOriginCursor`を持つ
- reset時に現在projection cursorをoriginとして保存する
- candidate stageはorigin以降のeligible contributionから計算する
- current count表示は引き続き全現在件数を使う
- unlock workerは`expectedResetEpoch`と`expectedGrowthOriginCursor`を照合する

Required fixtures:

- explicit visual reset with current count retained
- reset and unlock race
- stale projection cursor rejection

---

## MT-AR1-P0-002 Duplicate accessibility trees

対象:

- `memory-town-webgl-architecture.md`
- `memory-town-design-readiness-gate.md`

PixiJS v8 accessibilityはCanvas上のaccessible objectに対応するDOM overlayを生成する。

既存設計は別途DOM feature buttons / object list alternativeを持つため、両方を同時に有効化すると同じ建物が二重にTab移動・読み上げされる可能性がある。

Correction:

- productionのauthoritative interaction treeはReact / DOMの一つに固定
- canvasは視覚表現として`aria-hidden="true"`
- building interactionも同じSceneSnapshotから生成したDOM button overlayを使用
- Pixi accessibility pluginはproductionでは無効
- pluginはdebug比較時のみ使用可能
- overlay modeとlist modeを同時にfocusableにしない
- future editorもDOM object list / toolbarをkeyboard・screen reader正本とする

Required tests:

- duplicate focus target 0件
- tab order deterministic
- 200% text zoom
- screen reader route activation
- static fallbackと同一semantic IDs

---

## MT-AR1-P0-003 Static fallback promises an impossible exact image

対象:

- `memory-town-webgl-architecture.md`
- `memory-town-design-readiness-gate.md`

現状の`static town image + DOM feature buttons`では、次を一枚画像で正確に再現できない。

- building stage
- skin
- season
- future user layout
- stored / migrated object
- map expansion

Correction:

Fallbackを三段階へ分離する。

```txt
Functional fallback
= DOM feature buttons / list。常に必須。

Layered visual fallback
= base map + per-object imageをDOM/CSSで配置。MVP fixed layoutで対応。

Cached snapshot fallback
= 過去に生成したthumbnail。任意。正本ではない。
```

一枚のprecomposed imageを正確なcurrent townとして扱わない。

---

## MT-AR1-P0-004 Async renderer lifecycle race

対象:

- `memory-town-webgl-architecture.md`

`ticker停止`だけでは、route leave後に完了する以下を防げない。

- `Application.init()`
- asset manifest load
- texture load
- SceneSnapshot generation
- context restore

Failure scenario:

```txt
Town route enter
→ init / asset load開始
→ userが棚へ移動
→ renderer disposed
→ 古いload完了
→ stale callbackが破棄済みrendererへ書き込む
```

Correction:

- renderer lifecycle state machine
- monotonically increasing `rendererSessionGeneration`
- all async completion checks generation
- AbortControllerでfetch / composition taskを取消
- destroy後callback no-op
- private ticker only
- `autoStart: false`
- assets and snapshot ready後のみstart
- visibility / motion policyによりrender-on-demandへ切替

---

## MT-AR1-P0-005 Account deletion worker resurrection

対象:

- `memory-town-persistence-rls-and-recovery-contract.md`

Cascade deleteだけでは、削除開始前にqueueされたprojection / snapshot / migration workerが削除後にTown rowを再作成する可能性がある。

Correction:

- accountに`accountState`と`deletionEpoch`
- async jobへexpected deletion epochを封入
- write直前にactive stateとepochを再確認
- deletion開始後はnew Town jobs enqueue禁止
- stale jobは成功扱いにせず`ACCOUNT_DELETION_FENCE_REJECTED`
- account deletion完了条件にTown queue drain / stale job rejection確認を含める

---

## MT-AR1-P0-006 Access connectivity is not in the canonical validation order

対象:

- `memory-town-webgl-architecture.md`
- `memory-town-growth-envelope-and-access-contract.md`

`entrance clearance`だけでは、入口前が空いていても中央access networkから孤立できる。

Correction:

```txt
entrance clearance
→ required access cells
→ path graph connectivity
→ primary access root到達
```

Future path editorは、primary feature bindingを持つstructureの最後のaccess routeを切断できない。

---

# P1 Findings

## MT-AR1-P1-001 Volatile fields and deterministic snapshot hashing

`generatedAt`を含むSceneSnapshot全体をhashすると同じsceneでもhashが変わる。

Correction:

- `sceneContentHash`対象からgeneratedAt / trace IDを除外
- fixtureではclock injection
- renderer diffはcontent payloadのみを見る

## MT-AR1-P1-002 PixiJS renderer selection drift

PixiJS v8はWebGL / WebGPUをasync initで選択できる。

Correction:

- exact PixiJS versionをlock
- `preference: 'webgl'`を明示
- WebGPUは別Gateまで禁止
- major / minor upgrade時にruntime compatibility review

## MT-AR1-P1-003 Shared ticker and start semantics

PixiJS公式仕様では`autoStart: false`だけではshared ticker自体を止めない。

Correction:

- `sharedTicker: false`
- private ticker
- explicit start / stop lifecycle

## MT-AR1-P1-004 Asset cache lifecycle

Asset alias、bundle、unload、manifest versionの契約が不足。

Correction:

- stable alias = textureKey
- application init後にAssets init / load
- core / seasonal / district bundles分離
- asset manifest version changeでalias collision検査
- optional bundle unload policy
- fallback bundleは常駐

## MT-AR1-P1-005 Primary binding target becomes stored

Primary feature objectがstoredになった時、Town route入口が消える。

Correction:

- feature routeはDOM navigationから常に利用可能
- scene composerはprimary binding unavailable時にportal fallbackを解決
- visual fallbackがなくても機能を失わせない

## MT-AR1-P1-006 Stored object accumulation

Migrationやresetでstored objectが増え続ける可能性。

Correction:

- stored reason / source revision / storedAt必須
- recovery tray
- automatic silent deletion禁止
- quota超過はwarningのみ
- explicit export / restore / delete

---

# Official PixiJS facts used in this review

2026-07-13時点のPixiJS v8公式documentationで確認した事項:

- `Application`はconstruct後に`await app.init(...)`する
- renderer preferenceは`webgl`または`webgpu`
- default preferenceはWebGL
- private tickerは`sharedTicker: false`
- `app.start()` / `app.stop()`でlifecycle制御可能
- Accessibilityはopt-inで、DOM overlayを生成する
- AssetsはPromise-based / cache-aware
- Application init後にasset loadする
- manifest bundlesが推奨される
- `Assets.unload()`でcacheから解放できる

---

# Final Gate Recommendation

順序:

```txt
1. P0 reset model v2
2. Runtime / accessibility / fallback contract
3. Worker fencing / access connectivity
4. schema / fixture v2
5. internal consistency review
6. static visual prototype specification
7. asset prototype
8. machine validation runner
9. external multi-discipline review
10. implementation authorization judgment
```

Round 1 findingsを解消するまで、Memory Town実装は開始しない。
