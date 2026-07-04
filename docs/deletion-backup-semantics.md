# Deletion / Backup Semantics

## 目的

Deletion / Backup Semantics は、Memory OS における削除・非表示・封印・Export除外・バックアップ・再インポートの関係を定義する。

Memory OS は「忘れない」ためのサービスだが、ユーザーには忘れる権利がある。

したがって、記憶を守る設計と、消す・隠す・薄める設計は同じくらい重要である。

## 最上位原則

### 1. Delete means do not resurrect

ユーザーが削除した記録は、再インポート・バックアップ復元・再解析で勝手に復活させない。

### 2. Hide is not delete

非表示は通常表示・検索・Tipから隠すが、データを消すとは限らない。

### 3. Seal is stronger than hide

封印は、ユーザーが明示的に解除するまで検索・Tip・分析・Exportから除外する。

### 4. Backup is not a loophole

バックアップは復旧のためのもの。削除権を迂回してよい理由にはならない。

### 5. Raw deletion is irreversible

raw原文を削除したら、後からAIで再生成しない。

## Lifecycle States

```ts
type MemoryLifecycleState =
  | 'active'
  | 'hidden'
  | 'sealed'
  | 'archived'
  | 'pending_deletion'
  | 'deleted'
  | 'tombstoned';
```

| State | Search | Tip | LLM | Export | Backup restore |
|---|---|---|---|---|---|
| active | yes | policy | policy | policy | yes |
| hidden | no/default | no | explicit only | no/default | yes hidden |
| sealed | no | no | no/default | no/default | yes sealed |
| archived | search if asked | no/default | explicit only | yes if selected | yes archived |
| pending_deletion | no | no | no | no | no new restore |
| deleted | no | no | no | no | no |
| tombstoned | no content | no | no | migration opt-in | marker only |

## Deletion Types

```ts
type DeletionScope =
  | 'memory_only'
  | 'interpretations_only'
  | 'raw_only'
  | 'normalized_only'
  | 'source_import_job'
  | 'entire_source'
  | 'account_all';
```

### memory_only

Memory entity is deleted. SourceRef / RawRecord may remain if user chooses.

### raw_only

RawRecord text or file is deleted. Safe summary and SourceRef may remain.

### source_import_job

Everything created by one import job is deleted or tombstoned.

### entire_source

All data from a sourceType or connected source is deleted or tombstoned.

### account_all

All user data scheduled for deletion according to retention and legal constraints.

## Tombstones

Tombstone prevents silent resurrection.

```ts
type DeletionTombstone = {
  id: string;
  userId: string;
  entityType: 'raw_record' | 'normalized_record' | 'memory' | 'source_ref' | 'import_job' | 'source';
  entityId?: string;
  sourceType?: SourceType;
  externalId?: string;
  contentHash?: string;
  importJobId?: string;
  deletedAt: string;
  deletionScope: DeletionScope;
  reason?: 'user_request' | 'policy_violation' | 'retention_expired' | 'account_deletion';
  retainUntil?: string;
};
```

Rules:

- Tombstone contains no raw content.
- Tombstone may contain hashes and external IDs.
- Re-import checks tombstones before creating records.
- Tombstones may be included in migration export if user opts in.
- Account deletion may eventually remove tombstones after retention window, but then re-import should still not happen unless user provides data again explicitly.

## User Controls

Every memory should support:

- hide
- seal
- delete
- delete raw only
- exclude from AI
- exclude from tips
- exclude from export
- correct
- show source

High-risk memories should make delete/hide easier, not harder.

## Delete Flow

```txt
user requests delete
-> show affected entities
-> explain reversible/irreversible parts
-> require confirmation for destructive delete
-> mark pending_deletion
-> stop search/tip/LLM/export immediately
-> delete or detach linked data
-> create tombstone
-> update indexes
-> write audit log
-> confirm completion
```

Search/Tip/LLM/Export must stop at `pending_deletion`, not only after physical deletion.

## Raw-only Delete Flow

Raw-only deletion preserves safe index without preserving raw text.

```txt
user requests raw delete
-> identify raw records and attached files
-> show what remains: source/date/safe summary/search metadata
-> delete rawStoragePath content
-> set rawStored=false
-> update rawRetentionPolicy
-> keep SourceRef
-> keep Memory if policy allows
-> create raw tombstone
```

This supports the right to keep life context without keeping risky original text.

## Backup Semantics

```ts
type BackupSnapshot = {
  id: string;
  userId: string;
  createdAt: string;
  backupType: 'operational' | 'user_emergency' | 'migration_staging';
  encrypted: boolean;
  includesRaw: boolean;
  includesTombstones: boolean;
  retentionUntil: string;
  policyVersion: string;
  schemaVersion: string;
};
```

Operational backup:

- encrypted
- access minimized
- not user-facing by default
- deletion propagation required

User emergency backup:

- follows Export Specification
- redacted by policy
- user downloadable

Migration staging:

- short-lived
- created during export/import transfer
- expires automatically

## Backup Deletion Propagation

When user deletes data:

1. Active DB stops using it immediately.
2. Search / Tip / LLM / Export indexes remove it immediately.
3. Backup delete marker is written.
4. Operational backups age out according to retention.
5. Restore process replays delete markers after restoring snapshot.

Restore must never restore data without replaying deletion tombstones.

## Re-import Semantics

```txt
new import
-> detect source
-> extract candidate externalId/contentHash
-> check deletion tombstone
-> if tombstoned: skip or ask user only if explicit restore is allowed
-> if duplicate active: dedupe
-> if changed: create new version
```

Default for tombstoned records:

- do not restore
- do not show raw content
- optionally show count: `削除済みの記録と一致したため取り込みませんでした`

## Explicit Restore

Explicit restore is allowed only when:

- user asks to restore
- data is still available
- policy allows restoration
- high-risk warning is shown
- tombstone reason is not policy violation or account deletion

Restored record must keep history:

```ts
type RestoreEvent = {
  id: string;
  userId: string;
  tombstoneId: string;
  restoredEntityId: string;
  restoredAt: string;
  source: 'user_explicit_restore';
};
```

## Deletion and Export

Export must respect deletion:

- deleted content excluded
- pending_deletion excluded
- tombstones optional in migration_package
- tombstones excluded from readable_markdown by default
- sealed excluded unless explicit
- hidden excluded from readable_markdown default

## Deletion and AI

Deleted / pending / sealed records must not be sent to LLM.

If a previous AI interpretation was derived from deleted raw:

- if interpretation depends entirely on deleted raw, delete it
- if interpretation has other evidence, mark evidence removed and lower confidence
- never regenerate deleted raw from summary

## Deletion and Embeddings

Embeddings are derived data and must be deleted or disabled.

```ts
type EmbeddingLifecycle =
  | 'active'
  | 'disabled_by_visibility'
  | 'pending_delete'
  | 'deleted';
```

On delete:

- remove vector row or mark inaccessible immediately
- purge asynchronously if vendor/index requires batch
- search filter must block pending_delete embeddings

## Family / Minor / Legacy Special Cases

### Family

Family memories may include third-party data.

Delete options should allow:

- remove raw quotes
- keep shared event summary
- hide from family share
- seal relationship record

### Minor

Minor data defaults stricter.

- raw delete recommended
- no tips
- no share default
- export exclude default

### Legacy / Deceased

Deleting grief/deceased records must not be guilt-framed.

Bad UI:

```txt
本当にこの大切な思い出を消しますか？
```

Good UI:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

## Audit Log

```ts
type DeletionAuditLog = {
  id: string;
  userId: string;
  action: 'hide' | 'seal' | 'delete' | 'delete_raw' | 'restore' | 'backup_purge';
  entityType: string;
  entityId?: string;
  scope: DeletionScope;
  requestedAt: string;
  completedAt?: string;
  actor: 'user' | 'system' | 'admin';
  policyVersion: string;
};
```

Audit log must not include raw memory text.

## Acceptance Criteria

Deletion / Backup is ready when:

- pending_deletion blocks search/tip/LLM/export immediately.
- deleted records cannot be restored by normal backup restore.
- re-import checks tombstones.
- raw-only deletion is supported.
- embeddings are deleted or disabled.
- SourceRef can remain without raw.
- sealed is stronger than hidden.
- export respects lifecycle state.
- restore is explicit and audited.
- deletion UI avoids guilt or importance language.

## Non-goals

- Making deletion emotionally harder.
- Keeping raw forever for product convenience.
- Using backup as hidden retention.
- Rebuilding deleted raw from summaries.
- Letting admins restore user-deleted memory casually.

## 結論

Memory OS は忘れないための索引だが、忘れる権利を弱くしてはいけない。

削除・封印・非表示・raw削除・tombstone・backup復元を明確に分けることで、長く持てる記憶体になる。
