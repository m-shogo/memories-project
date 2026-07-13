# Memory Town Fixture Validation Harness Plan

最終更新: 2026-07-13

## 目的

Memory TownのJSON Schemaとfixtureを、読むだけの参考資料ではなく、実装前後に同じ結果を保証する検証資産として運用する。

本書は検証ハーネスの設計であり、コード実装はまだ開始しない。

---

# 1. Inputs

```txt
docs/schemas/memory-town/schema-registry.v1.json
docs/schemas/memory-town/*.schema.json
docs/fixtures/memory-town/fixture-index.v1.json
docs/fixtures/memory-town/*.json
```

Schema IDはnetworkから取得しない。

```txt
logical schema ID
→ schema registry
→ repository local path
```

remote fetch fallbackは禁止。

---

# 2. Harness layers

```txt
H0 Repository file integrity
H1 JSON parse
H2 Schema registry resolution
H3 JSON Schema validation
H4 Cross-fixture reference validation
H5 Semantic contract validation
H6 Spatial validation
H7 Privacy denylist validation
H8 Deterministic composition
H9 Negative mutation runner
H10 Golden behavior runner
H11 Canonical serialization / hash
H12 Report and readiness gate
```

各layerの責務を混ぜない。

---

# 3. H0 Repository file integrity

確認:

- fixture index記載pathが存在
- schema registry記載pathが存在
- schema ID重複なし
- fixture ID重複なし
- path traversalなし
- symlink経由でrepo外へ出ない
- file size上限
- UTF-8のみ
- BOM policy統一

Error:

```txt
FILE_NOT_FOUND
DUPLICATE_SCHEMA_ID
DUPLICATE_FIXTURE_ID
UNSAFE_REPOSITORY_PATH
FILE_TOO_LARGE
INVALID_ENCODING
```

---

# 4. H1 JSON parse

Rules:

- duplicate object keyを拒否
- trailing garbageを拒否
- commentsを許可しない
- NaN / Infinityを許可しない
- numberを暗黙string変換しない

標準JSON parserがduplicate keyを検知できない場合、pre-parserまたはtoken-level checkを入れる。

---

# 5. H2 Schema registry resolution

```txt
fixture.$schema
→ exact schema ID lookup
→ local file
→ schema.$id exact match
```

禁止:

- URLへ実際にHTTP access
-末尾file名だけで曖昧match
- unknown schemaをskip
- latest schemaへ自動置換

Error:

```txt
SCHEMA_ID_NOT_REGISTERED
SCHEMA_ID_PATH_MISMATCH
SCHEMA_FILE_ID_MISMATCH
REMOTE_SCHEMA_FETCH_ATTEMPTED
```

---

# 6. H3 JSON Schema validation

Draft 2020-12相当を使う。

検証実装を選ぶ時は、実装時点の公式documentationで対応状況を確認する。

必須機能:

- `$ref`
- boolean schema
- `if / then / else`
- `oneOf`
- `const`
- `not`
- `additionalProperties: false`
- format validation for UUID / date-time

formatをannotationだけにせず、strict validationを有効にする。

Output:

```ts
interface SchemaValidationIssue {
  fixtureId: string;
  schemaId: string;
  instancePath: string;
  schemaPath: string;
  keyword: string;
  code: string;
}
```

raw private valueをreportへ出さない。

---

# 7. H4 Cross-fixture reference validation

確認:

## Feature Registry

- default definition exists
- stage threshold最大値をstructure stage variantsが覆う

## Object Catalog

- growthEnvelopeId exists
- textureKey exists in Asset Manifest
- fallbackTextureKey exists
- overlay slot key exists in Growth Envelope

## Layout Template

- map version exists
- catalog version exists
- definition version exists
- parcel exists
- feature exists
- object seed exists before binding
- owner object exists before decoration slot
- ownerOverlaySlotKey is supported by owner definition / envelope

## Scene fixture

- referenced fixture names exist
- feature projection and progress feature IDs exist
- expected variant is available

## Export fixture

- dependency versions exist
- section IDs unique
- required continuity sections present

Error:

```txt
REFERENCE_NOT_FOUND
REFERENCE_VERSION_NOT_FOUND
FEATURE_STAGE_VARIANT_MISSING
GROWTH_ENVELOPE_NOT_FOUND
TEXTURE_KEY_NOT_FOUND
FALLBACK_TEXTURE_NOT_FOUND
OVERLAY_SLOT_NOT_SUPPORTED
PRIMARY_BINDING_TARGET_NOT_FOUND
```

---

# 8. H5 Semantic contract validation

JSON Schemaだけでは難しい規則を検証する。

## Stable IDs

- unique by scoped namespace
- deprecated ID再利用なし
- display labelから生成した形跡を自動断定しないがreview issue可能

## Feature thresholds

- stage 0 exists
- stages contiguous
- count monotonically increases
- duplicate thresholdなし

## Stage variants

- stage unique
- stages required by Feature Registry are present
- unsupported stageをsceneが要求しない

## Placement state

```txt
placed → position required
stored / retired → position absent
```

## Feature binding

- one primary per feature / layout
- primary target is placed
- target definition compatible with feature

---

# 9. H6 Spatial validation

入力:

```txt
Map Definition
+ Object Catalog
+ Growth Envelope
+ Layout Template / Layout Snapshot
```

順序:

```txt
map bounds
→ parcel bounds
→ terrain compatibility
→ footprint rotation
→ solid collision
→ placement layer coexistence
→ growth envelope
→ entrance clearance
→ access path connectivity
→ decoration slot
→ visual overflow warning
```

## Rotation

- pivot 0,0
- integer relative cells
- rotate 4回で元へ戻る
- normalizeしない

## Collision

sprite boundsを使わない。

```txt
logical occupied cells
+ placement layers
+ coexistence matrix
```

## Growth

- `reservedGrowthCells == maxSolidOccupiedCells`
- entrance / required pathはreserved solidへ含めない
- current occupiedはmax solid内

## Path

- duplicate cell拒否
- connection maskは周囲から導出
- primary entranceからpublic networkへの到達性

---

# 10. H7 Privacy denylist

Scene、audit fixture、export metadataへ以下が入らないことをkey / semantic pathで確認する。

```txt
title
privateTitle
personName
rawNote
chatBody
privateUrl
preciseLocation
imageUrl
messageText
memoryBody
```

単純substringだけでなくallowlist DTO validationを主とする。

Extension bag:

- namespace allowlist
- schema registered
- private content prohibited

Outputに検出valueを出さない。

```txt
path + issue code
```

だけを返す。

---

# 11. H8 Deterministic composition

同じ入力から同じ結果を検証する。

Property runs:

- input array順shuffle
- object key順shuffle
- path cell順shuffle
- repeated run
- different process
- supported runtime間

比較:

```txt
instance IDs
binding IDs
display stages
unlock events
path masks
render object order
canonical JSON hash
migration decisions
```

current time / random / locale / timezoneをimplicit inputにしない。

---

# 12. H9 Negative mutation runner

`negative-validation-cases.v1.json`を読む。

Flow:

```txt
load immutable base fixture
→ deep clone
→ apply listed RFC6901 mutations
→ validate
→ collect issue codes
→ compare expected subset
```

Rules:

- base fixture hash before / afterが同一
- mutation failure自体もtest failure
- expected issue以外が出ても記録
- expected issueが一つでも欠ければfailure
- scene生成禁止caseでscene composerを呼ばない、または拒否assertion

`duplicate` operationはtest harness専用拡張であり、production APIではない。

---

# 13. H10 Golden behavior runner

対象:

```txt
scene composition
three-way migration
command batch
reset
export / re-import preview
RLS negative case plan
```

## Scene

candidate stage / max unlocked / display stageを比較。

## Migration

- merge decision
- stored fallback
- user edit preservation
- resulting revision
- issue codes

## Command

- atomicity
- replay
- stale revision
- lock rejection

## Reset

- Memory Domain unchanged
- user object disposition
- snapshot
- reset epoch

RLS fixtureはDB実装前はplan validation、DB実装後はintegration testへ昇格する。

---

# 14. H11 Canonical serialization

Rulesは`memory-town-concrete-data-contract.md`に従う。

検証:

- known vector canonical string
- known SHA-256
- negative zeroなし
- optional absent fieldをnullへ変換しない
- set相当arrayのsort rule

Canonical serializerをExport用pretty printerと共用しない。

---

# 15. H12 Report

生成候補:

```txt
reports/memory-town-fixture-validation.json
reports/memory-town-fixture-validation.md
```

Reportに含める:

```txt
run timestamp
validator build version
schema registry version
fixture index version
fixture count
pass / fail / warning
issue code
safe path
prototype candidate summary
```

含めない:

- private memory
- fixture内の将来的なprivate extension value
- auth token
- local absolute path

---

# 16. Severity

```txt
error
warning
prototype_pending
info
```

## error

- schema invalid
- missing reference
- collision
- privacy field
- deterministic mismatch
- negative expected issue missing

## warning

- visual overflow候補
- deprecated definition
- optional fallback使用

## prototype_pending

- map寸法未承認
- asset hash未確定
- hit polygon未確定
- performance未測定

Prototype pendingをerror扱いして設計fixture自体を使えなくしない。

Production approval時はpendingを0にする。

---

# 17. Execution modes

```txt
contract
prototype
production
```

## contract

- schema
- reference
- semantic
- deterministic
- negative fixtures

## prototype

contract +

- spatial candidate
- placeholder assets許可
- pending report

## production

prototype +

- approved asset hashes
- no prototype_pending
- device metrics
- visual approval
- migration compatibility

---

# 18. Future CI integration

実装開始後の候補:

```txt
fixture:lint
fixture:validate
fixture:negative
fixture:determinism
fixture:migration
fixture:report
```

CI名やpackage manager commandはrepo実装構成確定後に決める。

現段階で架空commandをREADMEの必須実行として書かない。

---

# 19. Harness implementation gate

コードを書く前に:

```txt
[ ] Schema Registry確定
[ ] Fixture Index確定
[ ] issue code registry確定
[ ] duplicate key policy確定
[ ] canonical JSON algorithm確定
[ ] mutation semantics確定
[ ] spatial coexistence matrix確定
[ ] report privacy policy確定
[ ] execution modes確定
[ ] implementation-time validator official docs確認
```

---

# 20. Harness acceptance

```txt
[ ] 全schemaをlocal解決
[ ] 全positive fixtureがexpected modeでpass
[ ] 全negative fixtureが期待issueを返す
[ ] base fixture immutable
[ ] deterministic vectors一致
[ ] scene composition一致
[ ] migration golden一致
[ ] command atomicity一致
[ ] reset Memory Domain不変
[ ] privacy denylist leakなし
[ ] reportにraw valueなし
```

---

# 結論

```txt
fixtureを置くだけでは設計は守られない。

schema
+ cross-reference
+ semantic validator
+ spatial validator
+ negative mutation
+ deterministic golden
+ safe report

を一つの検証系として扱う。
```
