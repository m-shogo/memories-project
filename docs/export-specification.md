# Export Specification

## 目的

Export Specification は、Memory OS に保存された人生文脈を、ユーザーが安全に持ち出すための仕様である。

このサービスはベンダーロックインを目的にしない。

ユーザーは、自分の記憶をサービス外へ移せる必要がある。ただし、Export は単純な全データダンプではない。第三者情報、会社情報、未成年情報、故人関連、秘密情報を無警告で外に出すと、ユーザー本人だけでなく周囲の人を傷つける。

したがって Export は、**持ち出す権利** と **他人をデータ化しない義務** を同時に満たす必要がある。

## 最上位原則

### 1. User-owned portability

ユーザー本人の記憶・メモ・ライフイベント・嗜好・未来意図は、可能な限り持ち出せるようにする。

### 2. Not a raw leak tool

Export は、LINE / Gmail / Slack / Discord / 写真 / AIチャットログの raw 全文を漏らすための機能ではない。

### 3. Provenance preserved

持ち出したデータでも、どの出典・日時・根拠から生成されたかを追える必要がある。

### 4. Deletion respected

削除済み、封印済み、非表示、LLM除外、Export除外の設定を Export は尊重する。

### 5. Policy-gated export

Export は、Policy Engine の `export_memory` 判定を必ず通す。

## Export Modes

```ts
type ExportMode =
  | 'personal_archive'
  | 'migration_package'
  | 'readable_markdown'
  | 'source_index_only'
  | 'safe_family_share'
  | 'legal_or_support_limited'
  | 'emergency_backup';
```

### personal_archive

本人用の長期保管。

- 自分の記憶中心
- 第三者情報は要約または除外
- secrets は常に除外
- raw は safe raw のみ opt-in

### migration_package

他システムへ移るための構造化 export。

- JSONL / JSON manifest
- schemaVersion / policyVersion を保持
- SourceRef / Evidence を保持
- deleted tombstone を含めるか選択可能
- raw は原則含めない

### readable_markdown

人間が読める形。

- 年月別 / life phase 別
- 出典リンクまたは SourceRef ID
- 危険引用は出さない
- 重要度ランキングは禁止

### source_index_only

出典索引だけを持ち出す。

- SourceRef
- import job
- counts
- date ranges
- raw保存有無
- risk class summary

本文を出さずに、バックアップや監査に使える。

### safe_family_share

家族共有用。

- explicit opt-in の記憶のみ
- 第三者の秘密は除外
- 未成年情報は原則除外
- 故人の再現素材化は禁止
- grief/loss は warning 必須

### legal_or_support_limited

サポート・法的確認など限定用途。

- 本文最小化
- audit log 優先
- admin access と同等に厳格
- 目的外利用を防ぐ scope が必要

### emergency_backup

サービス終了・障害・アカウント移行に備える export。

- source index
- user-created memory
- safe summaries
- tombstones
- raw は別鍵・別同意

## Export Package Layout

```txt
memory-export-<userId>-<timestamp>/
  manifest.json
  README.md
  memories.jsonl
  interpretations.jsonl
  evidence.jsonl
  source_refs.jsonl
  import_jobs.jsonl
  people_relationships.jsonl
  visibility.jsonl
  tombstones.jsonl
  policy_decisions.jsonl
  attachments/
    README.md
  raw/
    README.md
```

Default package does not include `raw/` content.

`raw/` は explicit opt-in かつ Policy allow の場合だけ生成する。

## Manifest

```ts
type ExportManifest = {
  exportId: string;
  userId: string;
  createdAt: string;
  exportMode: ExportMode;
  schemaVersion: string;
  policyVersion: string;
  exportSpecVersion: string;
  appVersion?: string;
  timezone?: string;
  locale?: string;
  range?: DateRange;
  counts: ExportCounts;
  filters: ExportFilters;
  safetySummary: ExportSafetySummary;
  files: ExportFileEntry[];
  checksum: ExportChecksum;
};
```

```ts
type ExportCounts = {
  memories: number;
  interpretations: number;
  evidence: number;
  sourceRefs: number;
  importJobs: number;
  peopleRelationships: number;
  tombstones: number;
  excluded: number;
  redacted: number;
};
```

## Export Filters

```ts
type ExportFilters = {
  dateRange?: DateRange;
  memoryKinds?: MemoryKind[];
  sourceTypes?: SourceType[];
  includeHidden: boolean;
  includeSealed: boolean;
  includeDeletedTombstones: boolean;
  includeRaw: boolean;
  includeThirdPartySummaries: boolean;
  includeMinorData: boolean;
  includeCorporateData: boolean;
  includeLegacyData: boolean;
  includePolicyAudit: boolean;
};
```

Default:

- includeHidden: false
- includeSealed: false
- includeDeletedTombstones: true for migration, false for readable markdown
- includeRaw: false
- includeThirdPartySummaries: true
- includeMinorData: false
- includeCorporateData: false
- includeLegacyData: warning + opt-in
- includePolicyAudit: true for migration, false for family share

## Export Record Envelope

Every exported row must be wrapped.

```ts
type ExportEnvelope<T> = {
  exportId: string;
  entityType: ExportEntityType;
  entityId: string;
  schemaVersion: string;
  policyVersion: string;
  exportedAt: string;
  data: T;
  provenance: ExportProvenance;
  redactions: ExportRedaction[];
};
```

```ts
type ExportEntityType =
  | 'memory'
  | 'interpretation'
  | 'evidence'
  | 'source_ref'
  | 'import_job'
  | 'person_relationship'
  | 'visibility'
  | 'tombstone'
  | 'policy_decision';
```

## Redaction

```ts
type ExportRedaction = {
  fieldPath: string;
  reason:
    | 'secret_or_credential'
    | 'third_party_private'
    | 'corporate_confidential'
    | 'minor_sensitive'
    | 'medical_or_mental'
    | 'self_harm_or_crisis'
    | 'grief_or_death'
    | 'raw_not_exportable'
    | 'user_visibility_setting'
    | 'policy_denied';
  replacement: '[REDACTED]' | '[SUMMARY_ONLY]' | '[EXCLUDED]' | '[HIDDEN_BY_USER]';
  policyDecisionId?: string;
};
```

Redaction must be explicit. Silent omission is allowed only when showing human-readable markdown, and even then README must state that exclusions were applied.

## Policy Matrix

| Data | personal_archive | migration_package | readable_markdown | safe_family_share |
|---|---|---|---|---|
| User-created low-risk memory | allow | allow | allow | opt-in |
| User preference / routine | allow | allow | allow | opt-in |
| Third-party private data | summary/exclude | summary/exclude | summary only | exclude |
| LINE / DM raw | deny default | deny default | deny | deny |
| Gmail raw | deny default | deny default | deny | deny |
| Slack / company data | deny | deny | deny | deny |
| Secrets / credentials | deny | deny | deny | deny |
| Minor data | exclude default | exclude default | exclude default | deny default |
| Grief / deceased memories | warning + opt-in | warning + opt-in | warning | safe summary only |
| Self-harm/crisis raw | deny | deny | deny | deny |
| AI companion / roleplay logs | summary only | summary only | summary only | deny default |

## Export Pipeline

```txt
requestExport
-> validateUserAuth
-> collectScope
-> estimateExportSize
-> showSafetyPreview
-> requireUserConfirmation
-> queryEntities
-> evaluatePolicyPerEntity
-> redactOrExclude
-> writePackage
-> computeChecksums
-> createExportAuditLog
-> deliverDownload
-> expireDownload
```

## Safety Preview UI

Before export, user must see:

- export mode
- date range
- estimated files / records / size
- included source types
- excluded source types
- third-party handling
- raw handling
- hidden / sealed handling
- deletion tombstone handling
- warnings

Example warning:

```txt
このExportには、あなた以外の人が関係する記憶が含まれる可能性があります。相手の秘密や原文会話は除外または要約されます。LINE/DM/Gmailの原文は既定では含めません。
```

## Format Requirements

### JSONL

- One entity per line.
- UTF-8.
- No trailing commas.
- Large export friendly.
- Each line must be independently parseable.

### Markdown

```txt
/YYYY/
  2026.md
  2027.md
/by-source/
  chatgpt.md
  manual.md
  calendar.md
README.md
```

Markdown must avoid ranking language.

Forbidden headings:

- Top Memories
- Most Important People
- Best / Worst Years
- Personality Analysis
- Life Score

Allowed headings:

- 2026年の記録
- 旅行に関する記録
- 食事に関する記録
- 仕事の転機に関する記録
- 出典別索引

## Encryption and Delivery

Export package should be encrypted at rest while being prepared.

Download requirements:

- short-lived signed URL
- expiration timestamp
- one-time or limited download count preferred
- audit log created
- no email attachment for full export
- user can delete export package immediately

For high-risk export:

- re-authentication required
- delayed generation allowed
- explicit warning required
- raw export requires separate confirmation

## Audit Log

```ts
type ExportAuditLog = {
  id: string;
  userId: string;
  exportId: string;
  exportMode: ExportMode;
  requestedAt: string;
  completedAt?: string;
  downloadedAt?: string;
  expiredAt?: string;
  deletedAt?: string;
  filters: ExportFilters;
  counts: ExportCounts;
  safetySummary: ExportSafetySummary;
  actor: 'user' | 'system' | 'admin';
};
```

Audit log must not include raw memory text.

## Deletion Interaction

Export must respect deletion state.

Rules:

- deleted Memory is not exported.
- tombstone may be exported for migration if user opts in.
- sealed Memory is excluded unless explicit includeSealed.
- hidden Memory is excluded from readable markdown by default.
- raw deleted by retention policy cannot be reconstructed.
- if SourceRef remains but raw is deleted, export SourceRef with `rawStored: false`.

## Backup Interaction

Backup is not the same as export.

Backup can be operational and encrypted for recovery.

Export is user-readable or migration-oriented.

However, emergency backup should use the same redaction and manifest rules when it leaves the service boundary.

## Anti-abuse Rules

Export must not support:

- partner surveillance bundle
- coworker evidence package
- child profile bundle
- deceased person reconstruction pack
- password dump
- company knowledge dump
- raw DM archive as a shareable package

If requestIntent suggests these, Policy Engine returns deny or summary-only.

## Acceptance Criteria

Export Specification is ready when:

- Export modes are implemented as explicit enum values.
- Every exported entity has ExportEnvelope.
- manifest.json includes schemaVersion / policyVersion / exportSpecVersion.
- Export runs Policy Engine per entity.
- Redactions are recorded.
- Secrets are never exported.
- Company data is denied by default.
- Third-party private data is summary-only or excluded.
- LINE / Gmail / Slack raw is denied by default.
- Hidden / sealed / deleted states are respected.
- Download is short-lived and auditable.
- Markdown export avoids ranking and personality analysis.

## Non-goals

- Full raw export of every connected service.
- Legal discovery tooling.
- Relationship evidence generation.
- Company search / archive replacement.
- Character or deceased-person reconstruction dataset.

## 結論

Export は、ユーザーが自分の人生文脈を持ち出すための権利である。

しかし Memory OS が扱う記録には、他人・会社・未成年・故人・秘密が混ざる。

だから Export は「全部出す」ではなく、**本人の持ち出し可能性を守りながら、他人を巻き込まない安全な境界**として設計する。
