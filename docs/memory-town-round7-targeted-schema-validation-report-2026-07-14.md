# Memory Town Round 7 Targeted Schema Validation Report

検証日: 2026-07-14

## Verdict

```txt
Round 7 JSON syntax:
PASS

Round 7 JSON Schema definitions:
PASS

Round 7 positive fixtures against their schemas:
PASS

Round 7 issue-code extension against extension schema:
PASS

Round 7 negative case set against negative-case schema:
PASS

Repository-wide integrated resolver validation:
PENDING

Semantic topology validator execution:
PENDING
```

## Validated schemas

`Draft202012Validator.check_schema`で次を確認した。

```txt
docs/schemas/memory-town/terrain-region-state.v1.schema.json
docs/schemas/memory-town/linear-feature-graph.v1.schema.json
docs/schemas/memory-town/district-expansion-state.v1.schema.json
docs/schemas/memory-town/landscape-command-batch.v1.schema.json
```

Result:

```txt
4 / 4 PASS
```

## Validated positive fixtures

```txt
terrain-region-state.round7.valid.v1.json
→ terrain-region-state.v1.schema.json
→ PASS

linear-feature-graph.round7.valid.v1.json
→ linear-feature-graph.v1.schema.json
→ PASS

district-expansion-state.round7.valid.v1.json
→ district-expansion-state.v1.schema.json
→ PASS

landscape-command-batch.round7.valid.v1.json
→ landscape-command-batch.v1.schema.json
→ PASS
```

## Validated supporting fixtures

```txt
issue-code-extension.round7-editable-landscape.v1.json
→ issue-code-extension.v1.schema.json
→ PASS

negative-validation-cases.round7-editable-landscape.v1.json
→ negative-case-set.v1.schema.json
→ PASS
```

## Validation method

- Python `jsonschema`
- JSON Schema Draft 2020-12
- format checker enabled
- local reference store
- `core.v1.schema.json`からRound 7で参照する定義を同一制約で使用
  - `StableId`
  - `PositiveInteger`
  - `NonNegativeInteger`
  - `UtcTimestamp`
  - `TownGridPosition`
  - `TownOrientation`

Validated behavior includes:

- Stable ID format
- required fields
- unknown-field rejection
- cell coordinate limits
- orientation values
- UTC timestamp format
- command discriminator shapes
- issue-code shape
- negative-case mutation shape

## Important limitation

このPASSは、**Round 7のschema形状とfixture形状が参照可能で矛盾していないこと**を示す。

次はまだ示していない。

- repository内の全schema pathが存在すること
- schema registry全体を実際のrepository file resolverで巡回できること
- 既存Round 1 / 2 fixtureとの全参照整合
- ID重複のrepository-wide検出
- 川がsourceからoutletへ到達すること
- segment参照先が実在すること
- terrain regionが重ならないこと
- coast topologyが閉じていること
- road access rootが維持されること
- socket kind / profile compatibility
- pinned treeが編集で消えないこと
- stale layout revisionのatomic rejection

上記はJSON Schemaだけでなく、semantic validatorが必要。

## Environment limitation

実行環境からGitHub hostを名前解決できず、repository cloneによる統合validationは実施できなかった。

```txt
git ls-remote:
failed because github.com could not be resolved
```

この制約を理由に統合PASSとは記録しない。

## Current interpretation

```txt
schema and fixture shape:
validated

Round 7 machine-contract foundation:
usable for next design work

repository-integrated validation:
pending

semantic topology validation:
pending

implementation:
NO-GO
```

## Next validation work

```txt
1. repository file resolver validation script
2. schema registry path existence scan
3. schema ID uniqueness scan
4. fixture index dependency resolution
5. terrain overlap validator
6. coast topology validator
7. river graph continuity validator
8. road access connectivity validator
9. district socket compatibility validator
10. command revision / atomicity validator
11. negative cases must emit exact expected codes
12. deterministic projection compatibility test
```
