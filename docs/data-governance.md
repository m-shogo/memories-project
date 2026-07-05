# Data Governance Policy

## 目的

Data Governance Policy は、Memory OS のデータ定義・変更・保持・削除・移行・権限・品質を管理するためのルールである。

Memory OS は人生文脈を長期で扱うため、データをその場の実装都合で変えると、将来の検索・Export・削除・証拠性・互換性が壊れる。

## Data Governance とは

```txt
データを誰が、どのルールで、どう変更し、どう守り、どう捨てるかを決める運営ルール。
```

## 最上位原則

### 1. User context is durable

ユーザーの人生文脈は短期的なUI都合で壊さない。

### 2. Schema changes require migration thinking

schema変更は必ず既存データへの影響を見る。

### 3. Raw is minimized

rawデータは保存すればするほどgovernance負債になる。

### 4. Deletion is governance

削除・封印・tombstone・backup replay はデータ運営の中心である。

### 5. Provenance is mandatory

出典を失った記憶は、AI生成の幻覚と区別しにくくなる。

## Governed Data Domains

```ts
type GovernedDataDomain =
  | 'identity'
  | 'source'
  | 'raw'
  | 'normalized'
  | 'memory'
  | 'interpretation'
  | 'evidence'
  | 'policy'
  | 'privacy'
  | 'deletion'
  | 'export'
  | 'backup'
  | 'embedding'
  | 'audit'
  | 'cost';
```

## Data Owners

```ts
type DataStewardRole =
  | 'product_owner'
  | 'security_owner'
  | 'privacy_owner'
  | 'schema_owner'
  | 'infra_owner'
  | 'support_owner';
```

MVPでは個人開発でも、役割として分けて考える。

| Domain | Required reviewer |
|---|---|
| Raw / Security | security_owner |
| Privacy / Third-party | privacy_owner |
| Schema / Migration | schema_owner |
| Export / Backup | privacy_owner + schema_owner |
| Admin access | security_owner |
| Cost / LLM | product_owner + security_owner |

## Data Classification

| Class | Examples | Default |
|---|---|---|
| low_risk_context | food, hobby, routine | store/search/export allowed |
| user_sensitive | health, mental, grief | summary/warning |
| third_party_private | DM raw, other secrets | no raw default |
| minor_sensitive | child data | strict exclude/default |
| corporate_confidential | Slack, customer, code | deny/default |
| secret_or_credential | password, API key | deny |
| sealed | user sealed memory | no surface default |

## Schema Change Rules

### Additive changes

Allowed with lighter review:

- optional field
- new table/entity
- new enum value if default safe
- new audit metadata field without raw

### Breaking changes

Require RFC or ADR:

- renaming existing field
- removing field
- changing meaning
- changing default visibility
- changing export format
- changing deletion semantics
- changing policy decision meaning

### Forbidden changes without explicit RFC

- adding importanceScore/lifeScore/personalityScore
- making raw default on for risky sources
- removing SourceRef requirement
- allowing admin raw by default
- exporting third-party raw by default

## Data Quality Rules

Memory data quality means:

- source known
- dates separated
- evidence linked
- privacy classified
- lifecycle valid
- deletion state respected
- rawStored accurate

It does not mean:

- AI judged important
- perfect emotional analysis
- personality insight
- life ranking

## Retention Rules

| Data | Default retention |
|---|---|
| SourceRef | long-term unless source deleted |
| RawRecord | source/risk dependent, optional |
| NormalizedRecord | long-term if safe |
| Memory | user controlled |
| Interpretation | user controlled, lower confidence if evidence deleted |
| Tombstone | retain enough to prevent resurrection |
| Export package | short-lived |
| Audit log | no raw, retained for safety |
| Cost ledger | no raw, retained for abuse/cost analysis |

## Data Lineage

Every Memory should be traceable:

```txt
Memory
-> Evidence
-> NormalizedRecord
-> RawRecord optional
-> SourceRef
-> ImportJob
-> AdapterMetadata
```

Lineage can skip RawRecord if raw was not stored, but SourceRef must remain.

## Data Access Governance

Rules:

- owner can access own safe summary subject to policy.
- owner cannot bypass third-party raw export deny.
- admin metadata-only default.
- ai_worker scoped and policy-gated.
- support never uses raw for convenience.

## Data Change Review Checklist

Before changing data model:

1. Does SourceRef remain intact?
2. Does deletion still work?
3. Does Export remain compatible?
4. Does privacy classification survive?
5. Does search exclude hidden/sealed/deleted?
6. Does vector lifecycle survive?
7. Does rawStored remain accurate?
8. Does migration affect tombstones?
9. Does schema change introduce ranking/diagnosis language?
10. Does audit/cost log avoid raw?

## Migration Governance

Every migration must define:

- old shape
- new shape
- backfill strategy
- rollback or forward-only reason
- safety validation
- export compatibility
- deletion/tombstone impact

## Data Governance Tests

Required tests:

- migration preserves SourceRef
- migration preserves tombstone
- migration does not make hidden visible
- migration does not make rawStored true incorrectly
- migration does not add forbidden fields
- export old data still works

## Acceptance Criteria

- data domains listed
- data classification exists
- schema change rules defined
- retention rules defined
- lineage required
- migration checklist defined
- governance tests defined

## 結論

Data Governance は、Memory OS を長期運用するためのデータの憲法である。

機能を増やす前に、データの意味・保持・変更・削除・移行を管理するルールを持つことで、10年後も読める記憶体に近づく。
