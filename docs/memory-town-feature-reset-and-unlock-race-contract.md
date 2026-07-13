# Memory Town Feature Reset and Unlock Race Contract

最終更新: 2026-07-13

## 目的

「一度育った建物は通常削除で縮ませない」と「ユーザーが明示的に成長をResetできる」を両立する。

既存の単純な次式だけではResetが成立しない。

```txt
displayStage = max(candidateStage, maxUnlockedStage)
```

現在件数が閾値以上ならReset直後にcandidateStageが元へ戻るためである。

この文書はFeature Progress、candidate stage、reset、unlock persistence、race処理の正本とする。

実装はまだ開始しない。

---

# 1. Current count and growth contribution are different

Feature Projectionは二種類のcountを持つ。

```ts
interface TownFeatureProjectionItemV2 {
  featureId: TownFeatureId;

  // UIへ表示する現在の安全な件数
  currentEligibleItemCount: number;

  // growthOriginCursor以降に成立した成長寄与数
  growthEligibleContributionCount: number;

  // projection snapshotのopaque cursor
  projectionCursor: string;

  candidateStage: number;
  recentDelta: number;
  route: string;
  badges: TownFeatureBadge[];
}
```

Rules:

- current countは棚の現在状態
- growth contribution countは町の成長計算用
- candidateStageはgrowth contribution countから計算する
- current countをcandidateStageへ直接使わない
- title、item ID、人名をTown Projectionへ入れない

---

# 2. Opaque projection cursor

`projectionCursor`はMemory Domain aggregateの順序を表すopaque valueとする。

要求:

- 同一user / feature内で単調に前進する
- 時刻だけに依存しない
- clientが生成しない
- rendererが解釈しない
- cursorからMemory内容を推測できない
- user間で比較可能である必要はない

例は仕様上の説明であり、形式は実装前にDB基盤と整合させる。

```txt
featurecursor:01J...
```

Townはcursorの内部構造を知らない。

---

# 3. Feature Progress v2

```ts
interface TownFeatureProgressV2 {
  featureId: TownFeatureId;
  maxUnlockedStage: number;
  unlockedAtByStage: Record<number, string>;
  growthRulesetVersion: string;

  resetEpoch: number;
  growthOriginCursor: string;

  updatedAt: string;
}
```

Initial state:

```txt
maxUnlockedStage = 0
resetEpoch = 0
growthOriginCursor = feature origin cursor
```

`growthOriginCursor`以前のeligible itemsはcurrent countには含むが、Reset後のgrowth contributionには含めない。

---

# 4. Candidate and display stage

```ts
candidateStage = resolveStage(
  featureProjection.growthEligibleContributionCount,
  growthRulesetVersion,
);

displayStage = Math.max(
  candidateStage,
  featureProgress.maxUnlockedStage,
);
```

重要:

- explicit reset後はmaxUnlockedStage = 0
- growthOriginCursorが現在cursorへ移る
- 既存itemはgrowth contribution 0になる
- current countはそのまま表示できる
- 新しいeligible contributionによって再び育つ

例:

```txt
現在の映画棚: 100件
町の成長をReset
→ 映画棚表示: 100件
→ 映画館stage: 0
→ Reset後の新しいeligible contribution: 0
```

その後5件追加:

```txt
現在の映画棚: 105件
Reset後のgrowth contribution: 5
→ thresholdに応じてstageを再解除
```

---

# 5. What counts as a contribution

Growth contributionは単純なrequest回数ではない。

対象候補:

- Safe Commitで新たにeligibleとなったunique item
- restricted / sealed解除後にpolicy上eligibleとなったitem
- duplicate統合後も一つだけ

非対象:

- 同じImport再送
- Previewのみ
- rollbackされたcommit
- duplicateとして統合された二重item
- hidden / sealed / restricted / deleted
- title編集だけ
- source metadataだけの変更

Contribution identityはMemory Domain側でdeduplicateする。

Town Feature Progressへitem ID一覧を保存しない。

---

# 6. Explicit visual reset transaction

Command:

```ts
interface ResetFeatureProgressCommandV2 {
  commandId: string;
  featureId: TownFeatureId;
  expectedResetEpoch: number;
  expectedProjectionCursor: string;
  reason:
    | 'user_requested_visual_reset'
    | 'privacy_reset';
}
```

Atomic flow:

```txt
load current feature progress
→ load current safe feature projection cursor
→ expected resetEpoch確認
→ expected projectionCursor確認
→ reset preview snapshot確認
→ maxUnlockedStage = 0
→ unlockedAtByStage = {}
→ resetEpoch + 1
→ growthOriginCursor = current projectionCursor
→ reset audit event
→ commit
```

Memory Domainは変更しない。

---

# 7. Unlock transaction

Unlock proposal:

```ts
interface TownFeatureUnlockProposal {
  proposalId: string;
  featureId: TownFeatureId;
  candidateStage: number;
  expectedResetEpoch: number;
  expectedGrowthOriginCursor: string;
  projectionCursor: string;
  growthRulesetVersion: string;
}
```

Apply条件:

```txt
account active
AND feature exists
AND resetEpoch一致
AND growthOriginCursor一致
AND projection cursor not older
AND candidateStage > maxUnlockedStage
AND stage supported by active feature registry / growth envelope / asset compatibility
```

一つでも不一致ならunlock persistenceしない。

Rendererへunlock write権限を与えない。

---

# 8. Reset / unlock race scenarios

## Scenario A: Reset wins

```txt
worker reads candidate Stage 2 at resetEpoch 0
user reset commits resetEpoch 1
worker attempts unlock with expected resetEpoch 0
→ reject STALE_FEATURE_RESET_EPOCH
```

## Scenario B: Unlock wins before reset

```txt
unlock Stage 2 commits at resetEpoch 0
user reset confirms preview and commits resetEpoch 1
→ final stage 0
```

Resetは明示操作なので、直前unlockより後に適用された場合はResetを優先する。

## Scenario C: Projection changes during Reset preview

```txt
Preview cursor C10
new import commits cursor C11
user confirms with expected cursor C10
→ reject STALE_FEATURE_PROJECTION_CURSOR
→ Preview再生成
```

Silent rebaseしない。

## Scenario D: Same command replay

同じcommand ID / same request hash:

```txt
return previous result
```

同じcommand ID / different request hash:

```txt
reject IDEMPOTENCY_PAYLOAD_MISMATCH
```

---

# 9. Privacy reset

Privacy resetは次を同一transactionまたは整合したworkflowで行う。

- Feature Progress reset
- feature badge除去
- semantic overlay除去
- cached scene / cached thumbnail invalidation
- safe telemetryのみ

Primary feature bindingはdefaultで維持する。

理由:

route入口まで消すとMemory OSの機能が見つからなくなるため。

Feature binding除去は別Previewを必要とする。

---

# 10. Growth ruleset changes

Ruleset変更で既存stageを縮ませない。

```txt
maxUnlockedStageは維持
candidateStageはactive rulesetで再計算
```

ただしReset後は、Reset時に固定した`growthOriginCursor`を維持する。

Ruleset migrationでcursorを勝手に初期化しない。

Stage削除は禁止。

必要な場合:

```txt
old stage
→ explicit compatibility mapping
→ replacement visual stage
```

一度解除されたstageに対応するvisual fallbackを保持する。

---

# 11. Required issue codes

```txt
STALE_FEATURE_RESET_EPOCH
STALE_FEATURE_PROJECTION_CURSOR
FEATURE_UNLOCK_ORIGIN_MISMATCH
FEATURE_UNLOCK_STAGE_UNSUPPORTED
FEATURE_GROWTH_RULESET_MISMATCH
FEATURE_RESET_PREVIEW_REQUIRED
```

Errorへcurrent count、title、item IDを含めない。

---

# 12. Required v2 fixtures

- non-shrinking normal deletion
- visual reset with 100 current items
- post-reset new contributions
- reset wins against stale unlock worker
- unlock then reset
- stale projection cursor
- privacy reset cache invalidation
- ruleset change preserving max stage
- unsupported old stage visual fallback

---

# Decision

```txt
現在件数と成長寄与数を分離する。
Resetはopaque cursorを成長原点にする。
Unlockはreset epochとorigin cursorでfenceする。

これにより、
現在件数を正確に見せながら、
明示Resetを本当に効かせ、
古いworkerによる再成長を防ぐ。
```
