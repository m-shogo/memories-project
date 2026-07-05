# Compatibility Policy

## 目的

Compatibility Policy は、Memory OS のデータ・Export・API・Adapter・Policy が、将来のバージョン変更後も読める・移せる・削除できる状態を保つためのルールである。

Memory OS は短命なAIアプリではなく、人生文脈を長期で扱う。

したがって、今日保存した記憶が、5年後・10年後にも意味を保つ必要がある。

## Compatibility の対象

```ts
type CompatibilitySurface =
  | 'schema'
  | 'export_format'
  | 'adapter_output'
  | 'policy_decision'
  | 'memory_query_language'
  | 'backup_package'
  | 'api'
  | 'event_schema'
  | 'embedding_metadata';
```

## Versioning Principles

### 1. Version everything that leaves a boundary

境界を越えるものはversionを持つ。

- schemaVersion
- policyVersion
- exportSpecVersion
- adapterVersion
- eventSchemaVersion
- apiVersion

### 2. Additive before breaking

まずoptional field追加で進める。

破壊的変更はRFC/ADRが必要。

### 3. Old exports remain readable

古いExport packageは、少なくともREADMEとschemaVersionから読み方が分かる必要がある。

### 4. Deleted remains deleted across versions

schema migrationやbackup restoreで削除済みが復活してはいけない。

### 5. Policy decisions are versioned

過去のPolicyDecisionは、その時点のpolicyVersionを持つ。

## Semantic Versioning

Use semantic-ish versioning:

```txt
MAJOR.MINOR.PATCH
```

- PATCH: typo, docs, non-behavioral change
- MINOR: additive field, new safe enum, backward compatible behavior
- MAJOR: breaking schema/export/API behavior

## Schema Compatibility

### Compatible changes

- optional field追加
- new table追加
- enum追加 if unknown-safe
- new riskClass if default deny/safe

### Breaking changes

- field rename/remove
- field meaning change
- enum value behavior change
- default raw storage change
- lifecycle meaning change

## Export Compatibility

Export package must include:

- manifest.json
- schemaVersion
- exportSpecVersion
- policyVersion
- README.md
- checksums

Old export readers should ignore unknown fields.

New export writers must not omit required old safety metadata without MAJOR version.

## Adapter Compatibility

Adapter output must include:

- adapterId
- adapterVersion
- parserVersion
- sourceType
- extractionMode

If parser logic changes meaningfully:

- bump adapterVersion
- keep old outputs readable
- avoid silently reinterpreting old data

## Policy Compatibility

Policy can become stricter in MINOR version.

Example:

- third_party_private export from summary_only to deny can be MINOR if safer.

Policy becoming looser requires RFC and likely MAJOR/explicit migration.

Example:

- corporate raw export deny -> allow is breaking and dangerous.

## API Compatibility

MVP API rules:

- version routes or request headers before public use
- stable error codes
- idempotency keys for mutation where retryable
- cursor pagination for large lists
- explicit deprecation windows later

## Event Compatibility

Domain events must include schemaVersion.

Rules:

- consumers ignore unknown payload fields
- event type removal is breaking
- payload must not add raw content in any version
- event old versions remain processable during migrations

## Backup Compatibility

Backup package must remain understandable without service.

Include:

- README
- schema docs reference
- version files
- manifest
- open formats

Do not require:

- one specific LLM vendor
- proprietary embedding store only
- hidden application state

## Deprecation Policy

Before removing a format/field/API:

1. mark deprecated
2. provide migration path
3. keep reading old format
4. document end date if public
5. ensure export still works
6. ensure deletion/tombstone unaffected

## Compatibility Test Matrix

Required tests:

- v1 export can be read by v1.1 reader
- unknown fields ignored
- old tombstone prevents new import resurrection
- old policy decisions still explainable
- adapter v1 output still normalizable
- backup package with old schema still opens
- migration does not change lifecycle visibility

## Breaking Change Checklist

Before MAJOR change:

1. Does it affect deletion?
2. Does it affect SourceRef?
3. Does it affect Export readability?
4. Does it loosen privacy/security?
5. Does it require user notice?
6. Does it break local backups?
7. Does it require migration tests?
8. Does it need RFC and ADR?

## Acceptance Criteria

- all boundary formats have versions
- additive changes preferred
- breaking changes require RFC/ADR
- old exports/backups remain readable
- deleted/tombstoned semantics survive migrations
- policy loosening requires explicit review

## 結論

Compatibility Policy は、Memory OS が長期で信頼されるための時間軸の設計である。

今動くだけでは足りない。

未来の自分とユーザーが、過去の記憶を読めて、消せて、持ち出せることを保証する。
