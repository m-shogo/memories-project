# Business Cost and Plan Sustainability

## 目的

この文書は、Memory OS を長期運用しても赤字で破綻しないための、料金・Quota・Cost Ledger・Abuse Limit・Plan設計を定義する。

Memory OS は人生文脈を扱うため、無料で無制限に見せるほど信頼されそうに見える。

しかし、raw、画像、LLM、Embedding、Export、Backup、API syncを無制限にすると、ユーザーが増えるほど破産する。

長く続けるためには、最初から「安全な制限」を設計する。

## 最上位原則

### 1. Sustainability is a safety requirement

赤字で止まるサービスは、ユーザーの人生文脈を預かるサービスとして危険。

### 2. Paid plan can increase capacity, not override safety

有料プランで増やせるもの:

- storage
- import frequency
- source count
- retention period
- export package size
- semantic search budget

有料プランでも越えられないもの:

- policy deny
- third-party raw restrictions
- impersonation denial
- deceased simulation denial
- Export re-auth
- deletion tombstone

### 3. Cost must be attributed

source、user、action、planごとにコストを記録する。

「なんとなく高い」ではなく、何が高いかを見える化する。

## Cost Drivers

```ts
type CostDriver =
  | 'raw_storage_bytes'
  | 'media_storage_bytes'
  | 'backup_storage_bytes'
  | 'search_document_count'
  | 'embedding_token_count'
  | 'llm_input_token_count'
  | 'llm_output_token_count'
  | 'api_sync_call_count'
  | 'export_package_bytes'
  | 'ocr_page_count'
  | 'thumbnail_generation_count'
  | 'support_ticket_count'
  | 'notification_count';
```

## Plan Dimensions

```ts
type PlanLimitDimension =
  | 'monthly_import_candidates'
  | 'monthly_saved_records'
  | 'connected_sources'
  | 'raw_storage_gb'
  | 'media_storage_gb'
  | 'raw_retention_days'
  | 'export_package_size_gb'
  | 'semantic_search_queries'
  | 'llm_reflection_requests'
  | 'api_sync_frequency'
  | 'backup_retention_days';
```

## Suggested Plan Shape

### Free / Trial

Purpose:

- product value確認。
- S-rank paste/manual体験。

Limits:

- small paste imports.
- preview-first.
- limited saved records.
- raw retention very short.
- no large media archive.
- no bulk Export except standard small export.
- no frequent API sync.

### Basic

Purpose:

- 個人の軽いMemory OS。

Limits:

- more saved records.
- manual/paste/CSV imports.
- limited media metadata.
- limited semantic search.

### Plus

Purpose:

- 複数サービス連携。

Limits:

- more sources.
- scheduled sync.
- larger export.
- longer retention.
- more semantic search.

### Pro / Lifetime-like caution

Do not promise unlimited forever.

Allowed:

- high monthly limits.
- priority export.
- longer backup retention.

Avoid:

- “永久無制限”
- “raw永続保存”
- “全履歴無制限AI分析”

## Cost Ledger

Every cost-producing action writes a ledger entry.

```ts
interface CostLedgerEntry {
  userId: string;
  sourceId?: string;
  importJobId?: string;
  action:
    | 'import_parse'
    | 'raw_store'
    | 'media_store'
    | 'thumbnail_generate'
    | 'ocr'
    | 'search_index'
    | 'embedding'
    | 'llm_summary'
    | 'api_sync'
    | 'export_build'
    | 'backup_store';
  units: number;
  unitType: string;
  estimatedCostMinorUnits?: number;
  planAtTime: string;
  createdAt: string;
}
```

Rules:

- no raw content in ledger.
- source/category only.
- aggregate dashboards allowed.

## Quota Enforcement Points

### Import Preview

Enforce:

- max input size.
- max candidate count.
- max file count.
- max archive uncompressed size.

If exceeded:

```txt
このImportは件数が多いため、範囲を絞って確認してください。
```

### Safe Commit

Enforce:

- monthly saved records.
- policy eligibility.
- plan source limits.

### Raw Storage

Enforce:

- raw retention days.
- raw storage bytes.
- sensitive raw off by default.

### Embedding / LLM

Enforce:

- budget per user/plan.
- no import-time all embedding.
- no private raw embedding.
- lazy/batch only.

### Export

Enforce:

- package size.
- TTL.
- re-auth.
- selected scopes.
- default exclusions.

## Abuse and Cost Attack Cases

1. Huge paste attack.
2. ZIP bomb.
3. millions of tiny bookmarks.
4. repeated Import Preview spam.
5. repeated Export package generation.
6. OCR abuse with screenshots.
7. embedding spam.
8. API sync loops.
9. support ticket spam.
10. image upload storage abuse.

Controls:

- per-user rate limits.
- per-IP/device risk limits where appropriate.
- import job cancellation.
- raw TTL cleanup.
- background job concurrency limits.
- source-level sync backoff.
- export generation cooldown.

## User-facing Limit Copy

Allowed:

```txt
安全に確認するため、まず一部だけPreviewします。
```

```txt
このImportは件数が多いため、範囲を選んでから保存できます。
```

```txt
画像やrawデータは容量が大きいため、保存期間を選べます。
```

Avoid:

```txt
容量が足りないので大切な思い出を失います。
```

```txt
今すぐ課金しないと記憶が消えます。
```

## Metrics

Track:

```txt
cost_per_active_user
cost_per_import_job
raw_storage_bytes_by_plan
embedding_cost_by_plan
llm_cost_by_feature
export_package_bytes_by_plan
api_sync_calls_by_provider
support_cost_by_issue_type
free_to_paid_conversion
quota_hit_rate
```

Do not track raw content.

## Plan Change Semantics

Upgrade:

- increase limits.
- do not auto-enable sensitive analysis.
- do not auto-export raw.

Downgrade:

- stop new cost-heavy operations.
- keep existing records unless retention policy expires.
- give clear grace period for raw/media overage.

Cancel:

- read/export grace period.
- raw retention follows cancellation policy.
- safe account deletion path.

## P0 Tests

1. Free plan cannot import huge archive into saved records.
2. Plan increase does not override policy deny.
3. Private raw cannot be embedded even on paid plan.
4. Export package without TTL denied.
5. Repeated export generation rate-limited.
6. Raw expiration job reduces stored bytes.
7. Cost ledger contains no raw/private title.
8. API sync stops at plan/source limit.
9. Downgrade does not silently delete active memories.
10. Lifetime/unlimited copy is not used.

## 結論

Memory OSを長く続けるには、コスト設計は安全設計である。

無料/有料の違いは容量・頻度・保持期間であり、Policyを越える権利ではない。

raw、media、LLM、embedding、Export、API syncはすべてCost LedgerとQuotaで制御する。
