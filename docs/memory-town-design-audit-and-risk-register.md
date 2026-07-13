# Memory Town Design Audit and Risk Register

最終更新: 2026-07-13

## Verdict

```txt
status: strong_design_not_complete
```

Memory Townは、MVPの固定表示だけに最適化された設計から、将来の編集可能な箱庭へ拡張できる基盤へ進んだ。

ただし、実装・prototype・実機検証前に「完璧」とは判断しない。

---

# 1. 現時点で強い点

## Product boundary

- 町はMemory OS本体ではなく感情的なmenu
- 棚、検索、Import、ExportはDOM UI
- game economy、streak、建築待ち時間を入れない
- AIが人生の重要度を判定しない

## Spatial foundation

- screen pixel座標を正本にしない
- logical grid / parcel / footprint
- structureはmulti-cell完成sprite
- path / terrain / small objectの粒度分離
- versioned layout template
- future editorを見据えたvalidator

## Data safety

- raw memoryをrendererへ渡さない
- layoutとmemoryを分離
- hidden / sealed / restricted exclusion
- static fallback
- migration snapshot

## Long-term evolution

- object definition / instance分離
- stable IDs
- deprecated object preservation
- map expansion zone
- chunk化可能なscene model

---

# 2. 今回修正した重大リスク

## RISK-MT-001 Feature / visual identity coupling

### Before

映画棚の成長がcinema instanceへ直結していた。

### Failure

skin差し替え、建物移動、instance migrationで成長状態が消える。

### Resolution

- TownFeatureId
- feature binding
- definitionId / instanceIdとの分離

### Status

```txt
contract_fixed
```

---

## RISK-MT-002 Building shrink contradiction

### Before

- 建物は縮まない
- stageは現在件数から再計算

が矛盾していた。

### Failure

削除やImport取り消しで町が罰のように退化する。

### Resolution

- candidate stage
- max unlocked stage
- explicit feature reset
- privacy erasure option

### Status

```txt
contract_fixed
```

---

## RISK-MT-003 Environment mixed into projection

### Before

season / time / weatherがTownProjectionに含まれていた。

### Failure

Memory由来状態と端末・設定由来状態が混線する。

### Resolution

Town Environment Stateを独立。

### Status

```txt
contract_fixed
```

---

## RISK-MT-004 Template overwrite

### Before

新template適用時にuser layoutを守るmerge契約が弱かった。

### Failure

新建物追加やmap改善でユーザー配置が消える。

### Resolution

old baseline / current layout / new templateのthree-way merge。

### Status

```txt
contract_fixed
```

---

## RISK-MT-005 Path mask inconsistency

### Before

connectionMaskをpath stateへ持たせる設計だった。

### Failure

隣接path削除時にmaskが古くなる。

### Resolution

path typeだけ保存し、maskは導出。

### Status

```txt
contract_fixed
```

---

## RISK-MT-006 Non-atomic editor writes

### Before

command単位の考えはあったが、draft/save transactionが未固定。

### Failure

道路paintや複数object移動が途中状態で保存される。

### Resolution

local draft + atomic command batch + server revalidation + CAS。

### Status

```txt
contract_fixed
```

---

## RISK-MT-007 Magic holding coordinates

### Before

safe holding areaの表現が未固定。

### Failure

`(-999,-999)`などのoff-map配置が将来のbounds拡張と衝突する。

### Resolution

`placementState: stored`。

### Status

```txt
contract_fixed
```

---

## RISK-MT-008 Event sourcing ambiguity

### Before

layout eventとcurrent layoutのどちらが正本か曖昧だった。

### Failure

復旧、migration、問い合わせ対応が複雑化する。

### Resolution

current-state tablesを正本、eventは監査・復旧補助。

### Status

```txt
contract_fixed
```

---

## RISK-MT-009 Cross-user layout mutation

### Before

town tableのRLS / user ownershipが空間文書で弱かった。

### Failure

別userのinstance ID参照、layout mutation。

### Resolution

user_id、RLS fail closed、server validation、negative tests。

### Status

```txt
contract_fixed
```

---

## RISK-MT-010 Town portability gap

### Before

Memory Exportは強いが、町のlayout / growth / preferenceの持ち出しが未固定。

### Failure

Memoryは持ち出せても、長年作った町だけ失う。

### Resolution

Town export sectionとImport Preview。

### Status

```txt
contract_fixed
```

---

# 3. 未解決だが、文書だけでは決めない項目

## RISK-MT-P1-001 Tile metric

未決定:

- tile width
- tile height
- elevation step
- source sprite scale

必要:

- 6 viewport比較
- hit target検証
- art asset試作

Status:

```txt
prototype_required
```

---

## RISK-MT-P1-002 Initial map dimensions

未決定:

- grid width / height
- parcel size
- road width
- central square size
- expansion zone size

固定が早すぎると、建物追加で窮屈になる。

Status:

```txt
prototype_required
```

---

## RISK-MT-P1-003 Growth envelope dimensions

現在は概念契約のみ。

必要:

- Stage 0〜2の実asset
- Later stage想定
- entrance / shadow / signage余白

Status:

```txt
asset_prototype_required
```

---

## RISK-MT-P1-004 Mobile performance

未検証:

- low-end Android
- older iPhone
- WebGL context loss
- texture memory
- battery / heat

Status:

```txt
device_test_required
```

---

## RISK-MT-P1-005 Town comprehension

未検証:

- 映画館が映画棚に見えるか
- 倉庫がInboxに見えるか
- 中央広場が振り返りに見えるか
- labelsが必要か

Status:

```txt
user_test_required
```

---

## RISK-MT-P1-006 Non-shrinking visual mismatch

例:

```txt
Stage 2 cinema
current movie count 0
```

が自然に感じるか未検証。

候補copy:

```txt
これまでに育った映画館
現在の映画棚 0件
```

必要:

- user interview
- reset discoverability
- deletion expectation確認

Status:

```txt
user_test_required
```

---

## RISK-MT-P1-007 Editor scope creep

自由配置が楽しくても、Memory OS本体より重くなる可能性。

Gate:

- decoration slotで価値を検証
- free editor前にretention / return reason確認
- editor利用率だけを成功指標にしない

Status:

```txt
product_validation_required
```

---

## RISK-MT-P1-008 Asset production cost

建物stage、orientation、season、skinを掛け合わせるとasset数が急増する。

対策:

- fixed camera
- initial orientation固定
- season overlay分離
- building stage本体を共通化
- skinは後続

Status:

```txt
production_budget_required
```

---

# 4. 将来リスク

## RISK-MT-P2-001 Catalog entitlement drift

将来theme / skin販売をする場合、entitlementとlayout参照を分離する。

購入失効や提供終了でinstanceを削除しない。

## RISK-MT-P2-002 Custom uploaded asset safety

user画像を町assetへ使う場合:

- image decode safety
- metadata stripping
- copyright
- inappropriate content
- export rights

が必要。

初期No-Go。

## RISK-MT-P2-003 Large map navigation

地区拡張後、全体overviewだけではtap不能になる。

- district preset
- minimapの必要性
- accessibility list

を検証する。

## RISK-MT-P2-004 Resident pathfinding complexity

自由道路と住人移動を連動すると、行き止まりや孤立parcelが増える。

初期はfixed route。

将来はwalkability graphを別Projectorで作る。

## RISK-MT-P2-005 Screenshot privacy

町だけでも、建物stageやbadgeが趣味・利用量を示す可能性。

共有機能を作る前に:

- private mode
- count hide
- badge hide
- generic building mode

を設計する。

---

# 5. 破綻防止の設計原則

```txt
意味と見た目を分ける
解除と現在値を分ける
配置と記憶を分ける
環境とProjectionを分ける
current stateとauditを分ける
physical pathとsemantic relationを分ける
MVPのUI制限と内部schema制限を混同しない
```

---

# 6. Current Confidence

| Area | Confidence | Reason |
|---|---:|---|
| Product role | High | 町と棚の責務が明確 |
| Ethical boundary | High | guilt / dependency / importance scoring禁止 |
| Spatial data model | High | grid / parcel / footprint / versioning |
| Long-term layout evolution | Medium-High | merge / migration契約あり、fixture未作成 |
| Editor concurrency | Medium-High | atomic batch / CAS契約あり、API未検証 |
| Visual style | Medium | prototype比較前 |
| Mobile performance | Low-Medium | 実機未検証 |
| Asset production cost | Medium | stage / season量産前 |
| User comprehension | Medium | usability test前 |
| Free editor product value | Low-Medium | slot式検証前 |

---

# 7. Verdict Rule

現時点では:

```txt
設計思想: 強い
長期構造: 強い
実装着手契約: まだ整合確認中
数値・見た目・実機: 未検証
```

次の状態になった時、初めて`implementation_ready`へ変更する。

```txt
P0 hardening exit gate完了
+ docs contradiction audit完了
+ first map fixture完成
+ first object catalog fixture完成
+ migration golden fixtures定義
+ visual prototype比較計画固定
+ mobile performance test plan固定
```

「完璧」ではなく、破綻条件を把握し、検証可能な状態を目標とする。
