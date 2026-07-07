# Schema, API, and Export Version Governance

## 目的

この文書は、Memory OS を長期運用する上で、DB schema、Import parser、Source Adapter、Export format、API、Policy versionの変更を安全に管理するためのgovernanceを定義する。

長く続けるほど、変更は必ず起きる。

変更管理がないと、古いExportが読めない、古いImportが再処理できない、AI解釈が変わる、削除済みが復活する、という事故が起きる。

## Versioned Things

```ts
type VersionedSurface =
  | 'db_schema'
  | 'import_parser'
  | 'source_adapter'
  | 'policy_engine'
  | 'export_format'
  | 'public_api'
  | 'mobile_app'
  | 'web_app'
  | 'llm_prompt_contract'
  | 'embedding_model'
  | 'search_projection';
```

## Version Fields

Every durable derived or external-facing object should carry version fields.

Examples:

- source_item.parser_id
- source_item.parser_version
- source_item.adapter_id
- source_item.adapter_version
- policy_decision.policy_version
- export_manifest.export_version
- export_manifest.schema_version
- embedding_record.model_version
- search_document.projection_version
- ai_interpretation.prompt_contract_version

## Compatibility Rules

### Backward compatibility

New system can read old data/exports when feasible.

Required for:

- Memory OS standard export.
- import_preview snapshots.
- source_item parser metadata.
- policy_decision reason codes.

### Forward compatibility

Old system may not read new exports.

Therefore:

- manifest must state minReaderVersion.
- unknown fields ignored where safe.
- unknown packageClass requires preview-only.

## Change Types

```ts
type ChangeType =
  | 'additive'
  | 'behavior_change'
  | 'breaking_schema_change'
  | 'policy_tightening'
  | 'policy_relaxation'
  | 'export_format_change'
  | 'parser_reinterpretation'
  | 'adapter_terms_change'
  | 'model_change';
```

## Governance by Change Type

### Additive

Examples:

- new optional field.
- new parser warning.
- new source adapter.

Allowed with tests.

### Behavior change

Examples:

- title normalization changes.
- dedupe confidence changes.
- privacy default changes.

Requires:

- migration note.
- before/after fixture snapshots.
- rollback plan.

### Breaking schema change

Requires:

- RFC.
- migration safety checklist.
- export compatibility check.
- backfill plan.
- rollback/irreversible flag.

### Policy tightening

Example:

- Export default now excludes a class previously included.

Allowed but requires:

- user-visible explanation where relevant.
- migration of derived search/export eligibility.

### Policy relaxation

Example:

- allowing a sensitive class previously denied.

High risk.

Requires:

- safety review.
- red-team cases.
- explicit user opt-in.
- no automatic retroactive exposure.

### Parser reinterpretation

Example:

- old Netflix parser treated date differently.

Requires:

- parser_version bump.
- affected rows query.
- optional reprocess job.
- preserve original source facts.

### Model change

Example:

- LLM provider/model changes.
- embedding model changes.

Requires:

- model_version bump.
- no silent reinterpretation.
- derived records invalidated or marked old.
- user-facing AI inference labels preserved.

## Export Format Versioning

Export format must be stable.

```ts
interface ExportVersionInfo {
  exportVersion: string;
  schemaVersion: string;
  minReaderVersion?: string;
  policyVersion: string;
  createdAt: string;
}
```

Rules:

- standard export must remain readable by future Memory OS versions.
- raw archive export can be stricter and versioned separately.
- persona/media flags cannot be removed silently.
- manifest unknown packageClass = preview_only.

## Public API Governance

If Memory OS ever has public API:

- versioned path: `/v1/...`
- stable error codes.
- no raw by default.
- explicit scopes.
- rate limits.
- deprecation policy.
- changelog.

Do not expose API before:

- Export safety.
- token scope model.
- abuse limits.
- third-party data restrictions.

## Deprecation Policy

For external-facing formats/API:

- announce deprecation.
- keep read support for old exports as long as feasible.
- never deprecate delete/export path without replacement.
- security fixes may be immediate.

## Compatibility Test Corpus

Maintain fixtures for:

- old export manifests.
- old parser outputs.
- old policy decisions.
- old schema snapshots.

CI should test:

- current reader reads old standard export.
- old tombstones still block re-import.
- old sealed/private flags remain excluded.
- old persona/media flags do not activate.

## Decision Records

Every breaking or policy-affecting change needs ADR/RFC.

Must include:

- reason.
- affected users/data.
- migration plan.
- rollback plan.
- user communication.
- safety review.

## P0 Tests

1. export v1 manifest can be read by current importer.
2. unknown export package class goes preview_only.
3. parser version bump preserves old parsed data.
4. policy relaxation cannot expose old sensitive records automatically.
5. policy tightening invalidates derived search/export eligibility.
6. embedding model change does not overwrite old embedding metadata silently.
7. API breaking change requires version bump.
8. deletion tombstones survive schema migration.
9. persona/media flags survive export/import roundtrip.
10. compatibility fixtures are not deleted without replacement.

## 結論

Memory OSの長期信頼は、変更をしないことではなく、変更しても過去の記録・Export・Policy・削除・安全境界を壊さないことにある。

DB、Import、Export、API、AI model、Policyのすべてにversion governanceを持たせる。
