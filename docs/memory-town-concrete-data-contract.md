# Memory Town Concrete Data Contract

最終更新: 2026-07-13

## 目的

Memory Town の設計を文章だけで終わらせず、Feature Registry、Map Definition、Object Catalog、Layout Template、Scene Composition、Migration Fixture を、実装担当が解釈で変形できない具体的なdata contractへ落とす。

実装はまだ開始しない。

本書は以下のfixtureと一体で読む。

```txt
docs/fixtures/memory-town/
├─ feature-registry.v1.json
├─ map-definition.main-island.v1.json
├─ object-catalog.v1.json
├─ layout-template.main-island.v1.json
├─ scene-composition.non-shrinking.v1.json
└─ migration-three-way-merge.v1.json
```

---

# 1. Fixture status

fixtureには次の状態を持たせる。

```txt
contract_locked
prototype_candidate
asset_pending
superseded
invalid_negative_test
```

意味:

- `contract_locked`: ID、enum、責務分離など実装前に固定する契約
- `prototype_candidate`: 寸法や座標など、prototypeで検証後に確定する候補
- `asset_pending`: asset hash、hit polygonなどproduction asset待ち
- `superseded`: 後続versionへ置き換え済み。削除しない
- `invalid_negative_test`: validatorが拒否すべきfixture

Mapの28x28、parcel寸法、初期座標は`prototype_candidate`であり、visual approvalではない。

一方、以下は`contract_locked`である。

- semantic feature ID
- logical coordinate axes
- elevationはlogical integer
- screen pixelを永続化しない
- feature / layout / environment / renderの分離
- definition / instance / feature bindingの分離
- physical path / semantic connectionの分離
- path connection maskは導出
- user objectをmigrationで黙って削除しない

---

# 2. JSON Schema policy

JSON Schema Draft 2020-12相当の表現を使用する。

## 2.1 Closed objects

原則:

```json
{
  "additionalProperties": false
}
```

未知fieldを黙って保存しない。

forward compatibilityが必要な箇所だけ、明示的なextension bagを許可する。

```ts
interface TownExtensionBag {
  namespace: string;
  schemaVersion: string;
  data: Record<string, unknown>;
}
```

無制限な`metadata: any`は禁止。

## 2.2 Null policy

意味がない`null`を使わない。

- optional fieldは省略する
- `stored` objectのpositionだけは`position`自体を省略する
- `occupiedByInstanceId`が空なら省略する
- nullableを使う場合はschemaと意味を明示する

現在のfixtureに残る`null`はschema作成時に省略形式へ移行する。

## 2.3 Integer policy

以下はintegerのみ。

- cellX / cellY
- elevationLevel
- revision
- version
- stage
- count

NaN、Infinity、string numberを受け付けない。

## 2.4 Number policy

fractionを許すのはrender-only relative pointだけ。

例:

- depthAnchor
- visualAnchor
- hit polygon point

layout positionにはfractionを許さない。

---

# 3. Stable ID policy

## 3.1 ID format

```txt
^[a-z][a-z0-9]*(?:[._:-][a-z0-9]+)*$
```

最大128文字。

表示名、日本語名、asset file name、DB連番から生成しない。

## 3.2 Semantic IDs

```txt
featureId
mapDefinitionId
parcelId
definitionId
templateId
themeId
```

意味を表すstable ID。

同じIDを別の意味へ再利用しない。

## 3.3 Instance IDs

Template由来objectは、次からdeterministicに生成する。

```txt
namespace = memory-town-template-instance-v1
input = templateId + "|" + templateVersion + "|" + instanceIdSeed
```

出力形式:

```txt
townobj:tpl:<26-char-lowercase-base32>
```

実装言語が違っても同じ結果になるよう、UTF-8、区切り文字、hash、base32 alphabetを固定する。

推奨algorithm:

```txt
SHA-256
→ first 130 bits
→ RFC4648 base32 lowercase without padding
```

User作成object:

```txt
townobj:user:<uuidv7>
```

Migration作成object:

```txt
townobj:migration:<uuidv7>
```

ID生成失敗時にrandom fallbackを使わない。

## 3.4 Binding IDs

Template bindingは同様に、`bindingIdSeed`からdeterministic生成する。

```txt
townbinding:tpl:<26-char-lowercase-base32>
```

---

# 4. Version policy

以下を独立管理する。

```txt
spatialSchemaVersion
featureRegistryVersion
mapDefinitionVersion
layoutTemplateVersion
objectCatalogVersion
objectDefinitionVersion
growthRulesetVersion
growthEnvelopeVersion
projectionSchemaVersion
sceneSchemaVersion
assetManifestVersion
```

## 4.1 In-place mutation禁止

公開済みの以下は内容を直接書き換えない。

- Map Definition
- Layout Template
- Object Definition
- Object Catalog
- Growth Envelope
- Feature Registryのthreshold meaning

修正は新versionで行う。

誤字や説明文ではなく、validation・配置・成長結果が変わるならversionを上げる。

## 4.2 Compatibility result

```ts
interface TownCompatibilityResult {
  compatible: boolean;
  migrationRequired: boolean;
  unsupportedMajorVersion: boolean;
  issues: TownCompatibilityIssue[];
}
```

boolean一つで終わらせない。

---

# 5. Data dependency graph

```txt
Feature Registry
├─ featureId
├─ route
├─ aggregate key
├─ threshold
└─ default definition

Map Definition
├─ grid bounds
├─ terrain
├─ parcel
├─ expansion zone
└─ holding area policy

Object Catalog
├─ definition
├─ footprint
├─ placement rule
└─ render variant reference

Layout Template
├─ map definition reference
├─ object catalog reference
├─ object placement
├─ feature binding
├─ path cell
└─ decoration slot

Feature Projection
+ Feature Progress
+ Layout Snapshot
+ Environment
→ Scene Snapshot
```

参照先が存在しないfixtureをproduction fixtureとして承認しない。

---

# 6. Validation pipeline

順序を固定する。

```txt
1. byte / encoding limit
2. JSON parse
3. schema version dispatch
4. structural JSON Schema validation
5. stable ID syntax
6. duplicate ID detection
7. referential integrity
8. semantic enum compatibility
9. spatial validation
10. feature binding validation
11. growth envelope validation
12. privacy field denylist scan
13. deterministic composition
14. canonical serialization
15. fixture expected-result comparison
```

途中で例外終了せず、可能な範囲でissueを集約する。

## 6.1 Structural errors

```txt
INVALID_JSON
UNSUPPORTED_SCHEMA_VERSION
UNKNOWN_FIELD
MISSING_REQUIRED_FIELD
INVALID_TYPE
VALUE_OUT_OF_RANGE
ARRAY_TOO_LARGE
STRING_TOO_LONG
```

## 6.2 Referential errors

```txt
UNKNOWN_FEATURE_ID
UNKNOWN_MAP_DEFINITION
UNKNOWN_PARCEL_ID
UNKNOWN_DEFINITION
UNKNOWN_DEFINITION_VERSION
UNKNOWN_INSTANCE_REFERENCE
UNKNOWN_BINDING_REFERENCE
DUPLICATE_STABLE_ID
DUPLICATE_INSTANCE_ID
DUPLICATE_PATH_CELL
```

## 6.3 Spatial errors

```txt
OUT_OF_MAP_BOUNDS
PARCEL_CATEGORY_DENIED
PARCEL_BOUNDS_EXCEEDED
TERRAIN_KIND_DENIED
SOLID_COLLISION
CLEARANCE_COLLISION
GROWTH_ENVELOPE_RESERVED
ENTRANCE_BLOCKED
ORIENTATION_NOT_SUPPORTED
PLACEMENT_LAYER_CONFLICT
PATH_ON_NON_SURFACE_CELL
BRIDGE_CONNECTOR_INVALID
```

## 6.4 State errors

```txt
INVALID_PLACEMENT_STATE
STORED_OBJECT_HAS_POSITION
PLACED_OBJECT_MISSING_POSITION
LOCK_POLICY_DENIED
STALE_LAYOUT_REVISION
FEATURE_STAGE_REGRESSION_DENIED
FEATURE_BINDING_CONFLICT
PRIMARY_BINDING_MISSING
MULTIPLE_PRIMARY_BINDINGS
```

## 6.5 Privacy errors

```txt
RAW_MEMORY_FIELD_PRESENT
PRIVATE_TITLE_PRESENT
PERSON_NAME_PRESENT
PRIVATE_URL_PRESENT
PRECISE_LOCATION_PRESENT
UNSAFE_EXTENSION_NAMESPACE
```

---

# 7. Limits

初期hard limit候補。実装前にsecurity reviewで確定する。

```txt
max map width: 256 cells
max map height: 256 cells
max parcels: 256
max expansion zones: 64
max definitions per catalog: 10,000
max placed objects per layout: 5,000
max stored objects per layout: 5,000
max path cells: 65,536
max feature bindings: 1,000
max command batch commands: 500
max JSON document size: 10 MiB
max string ID length: 128
max issue count returned: 1,000
```

MVPの推奨量はこれより大幅に少ない。

上限超過をsilent truncateしない。

---

# 8. Feature Registry validation

必須:

- featureId unique
- routeはallowlisted internal route
- stage 0が存在
- stageは0から連続
- thresholdはstage順に単調増加
- minimumEligibleCountは非負整数
- default definitionがcatalogに存在
- primary bindingを持てる
- privacy aggregation policyが既知enum

禁止:

- 人生重要度
- 幸福度
- sensitive record量
- relationship評価
- private titleをaggregate keyに含める

---

# 9. Map Definition validation

必須:

- width / heightは正整数
- terrain overrideはmap bounds内
- parcelはmap bounds内
- parcelId unique
- expansion zone ID unique
- holding areaはmap magic coordinateを持たない
- active parcelとinactive expansion zoneの重なりを意図なく許可しない

parcel同士の重なりは原則禁止。

中央広場内のsub-zoneなど、必要な場合だけ明示的な`overlapGroupId`で許可する。

---

# 10. Object Catalog validation

必須:

- definitionId + definitionVersion unique
- pivotCellは常に0,0
- occupied / entrance / clearance / reserved cellに重複なし
- structureはoccupiedCellsを持つ
- reservedGrowthCellsは承認stageのenvelopeを包含
- supported orientationのrender variantが存在
- stage variantはFeature Registryの最大stageを覆う
- fallback texture keyを持つ
- categoryとplacement layerの組合せがallowlist内

禁止:

- sprite透明boundsをfootprintとして使用
- textureKeyをdefinitionIdとして再利用
- asset差し替え時のfootprint無断変更
- arbitrary executable asset

---

# 11. Layout Template validation

必須:

- map / catalog version一致
- instanceIdSeed unique
- bindingIdSeed unique
- object definition参照が有効
- placementがmap / parcel / terrain rule内
-全objectがcollision validatorを通る
- primary feature bindingが一つ
- path cell重複なし
- connectionMaskを保存しない
- decoration slotはgrowth envelope外、または明示的`slotMode: overlay`

## 11.1 Decoration slot mode

```ts
type TownDecorationSlotMode =
  | 'grid'
  | 'overlay';
```

`grid`:

- 実cellを占有する
- collision対象
- growth envelope内へ置けない

`overlay`:

- owner objectに追従
- layout cell collision対象外
- ownerのoverlay slot keyが必要
- owner削除時はstoredまたはowner replacementへ移行

現在の初期fixtureは、建物付属slotを`overlay`としてschema化する必要がある。

---

# 12. Scene composition validation

Scene Snapshotは次だけから作る。

```txt
Feature Projection
+ Feature Progress
+ Layout Snapshot
+ Feature Binding
+ Environment
+ Object Catalog / Asset Manifest
```

禁止:

- raw memory table query
- title / noteのscene埋め込み
- rendererでthreshold計算
- rendererでprivacy判定
- rendererでlayout修復

同じ入力version setから、同じobject順・variant・path maskを生成する。

---

# 13. Canonical serialization

Hash、fixture比較、snapshot比較のため、canonical JSONを定義する。

Rules:

1. UTF-8
2. object keyをUnicode code point順でsort
3. arrayは意味上orderedなものだけ入力順維持
4. set相当arrayはstable IDまたはcoordinate key順でsort
5. insignificant whitespaceなし
6. integerをdecimalで表現
7. negative zero禁止
8. timestampはUTC RFC3339、秒精度
9. optional fieldは未設定なら省略
10. nullの乱用禁止

Coordinate key:

```txt
elevationLevel + ":" + cellY + ":" + cellX
```

Path cell、terrain cellなどset相当arrayのsortへ使用する。

---

# 14. Determinism requirements

以下をproperty testする。

- input object array順を変えてもscene結果同一
- path cell順を変えてもderived mask同一
- footprintを4回rotateすると同一
- serialize / deserializeで同値
- same template seedから同一instance ID
- same migration inputから同一merge decision
- same invalid layoutからissue code集合が同一

Timestampやrandom IDをcomposition結果へ混ぜない。

必要なevent timeはcallerが明示的に渡す。

---

# 15. Negative fixtures

最低限作る。

```txt
invalid.duplicate-instance-id.json
invalid.unknown-definition.json
invalid.structure-out-of-parcel.json
invalid.solid-collision.json
invalid.growth-envelope-blocked.json
invalid.entrance-blocked.json
invalid.path-duplicate-cell.json
invalid.path-has-persisted-mask.json
invalid.multiple-primary-binding.json
invalid.stored-object-has-position.json
invalid.private-title-in-scene.json
invalid.stale-layout-revision.json
```

各fixtureに期待error codeを一つ以上固定する。

---

# 16. Fixture approval gate

fixtureを`contract_locked`へ進める条件:

```txt
[ ] JSON parse可能
[ ] schema validation成功
[ ] referential validation成功
[ ] spatial validation成功
[ ] privacy scan成功
[ ] canonical serialization snapshotあり
[ ] expected scene / migration resultあり
[ ] ID / version重複なし
[ ] prototype candidate値が明示されている
[ ] production asset未確定値を偽hashで埋めていない
[ ] superseded versionを削除していない
```

---

# 17. 現在の不足

今回のfixtureで具体化したが、まだ必要:

- actual JSON Schema files
- negative fixtures
- asset manifest fixture
- environment theme catalog fixture
- export package fixture
- reset command fixture
- editor command batch fixture
- RLS table contract
- deterministic ID test vector
- canonical JSON test vector
- map / parcel visual prototype結果

これらを埋めるまで、fixture layerも`strong_not_complete`とする。

---

# 結論

```txt
文章で方向を示すだけでは不十分。

stable ID
+ closed schema
+ concrete fixture
+ expected result
+ negative fixture
+ migration fixture
+ deterministic serialization

までを一つの設計契約として扱う。
```
