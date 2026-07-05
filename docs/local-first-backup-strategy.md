# Local-first Backup Strategy

## 目的

Local-first Backup Strategy は、Memory OS が長期的にユーザーの人生文脈を守るために、クラウド依存を減らし、ユーザーが自分の記憶を手元に残せる設計を定義する。

Memory OS の価値は「半永久的に文脈を持ち続ける」ことにある。

したがって、サービス終了・アカウント停止・価格変更・AIベンダー変更・クラウド障害が起きても、ユーザーが自分の記憶を失わない必要がある。

## 最上位原則

### 1. User keeps context

ユーザーの人生文脈はサービス会社の所有物ではない。

### 2. Export is not enough

Exportは単発持ち出し。Backupは継続的な保全。

両方が必要である。

### 3. Safe by default

ローカルやDriveに出す時も、第三者情報・会社情報・秘密情報を無警告で含めない。

### 4. Raw is optional

ローカルバックアップでも raw は既定OFF。

### 5. Open formats first

JSONL / Markdown / SQLite / ZIP manifest など、将来読み出せる形式を優先する。

## Backup Modes

```ts
type UserBackupMode =
  | 'manual_export'
  | 'scheduled_safe_archive'
  | 'local_sqlite_snapshot'
  | 'markdown_archive'
  | 'drive_sync_package'
  | 'emergency_exit_package';
```

### manual_export

ユーザーが任意で出力する。

- MVP対象
- JSONL / Markdown
- raw default off
- redaction report included

### scheduled_safe_archive

定期的に安全なアーカイブを生成する。

- post-MVP
- user opt-in
- no raw default
- encrypted preferred

### local_sqlite_snapshot

ローカルで検索可能なSQLite snapshot。

- post-MVP
- schemaVersion included
- tombstones included optional
- raw excluded default

### markdown_archive

人間が読める長期保存。

- year/month/source folders
- no ranking headings
- safe summaries
- SourceRef references

### drive_sync_package

Google Drive / iCloud Drive / Dropbox などに保存する将来案。

- user-controlled
- encrypted package preferred
- third-party raw excluded default

### emergency_exit_package

サービス終了や重大変更時の脱出用。

- source index
- safe memories
- evidence
- tombstones
- schema docs
- README
- no raw default

## Package Layout

```txt
memory-os-backup-<timestamp>/
  README.md
  manifest.json
  schema/
    memory-schema-version.txt
    export-spec-version.txt
  data/
    memories.jsonl
    evidence.jsonl
    source_refs.jsonl
    interpretations.jsonl
    policy_decisions.jsonl
    tombstones.jsonl
  markdown/
    2026.md
    by-source.md
  redactions.jsonl
  checksums.txt
```

Optional raw package:

```txt
raw/
  README.md
  objects/
```

Raw package requires separate confirmation.

## Manifest

```ts
type BackupManifest = {
  backupId: string;
  userId: string;
  createdAt: string;
  backupMode: UserBackupMode;
  schemaVersion: string;
  policyVersion: string;
  exportSpecVersion: string;
  includesRaw: boolean;
  includesTombstones: boolean;
  encrypted: boolean;
  counts: BackupCounts;
  redactionSummary: RedactionSummary;
  checksum: string;
};
```

## Safety Defaults

| Data | Backup default |
|---|---|
| user low-risk memory | include |
| SourceRef | include |
| Evidence safe metadata | include |
| Interpretations | include if safe |
| Tombstones | include for migration/local snapshot |
| Secrets | exclude |
| Corporate data | exclude |
| Third-party raw | exclude |
| Minor data | exclude/default |
| Sealed data | exclude/default |
| Hidden data | exclude/default |
| Raw files | exclude/default |

## Local-first Search

Long-term goal:

- user can open local SQLite/Markdown archive without service.
- source/date/search text preserved.
- no LLM required.
- no vendor API required.

MVP:

- safe Markdown + JSONL export.

Post-MVP:

- SQLite snapshot with FTS.

## Encryption

Backup encryption options:

```ts
type BackupEncryptionMode =
  | 'none_user_visible_warning'
  | 'app_generated_passphrase'
  | 'user_passphrase'
  | 'platform_keychain'
  | 'external_key_file';
```

MVP can start with unencrypted manual download only if user warning is explicit.

Preferred post-MVP:

- user passphrase or platform keychain
- never store passphrase server-side
- recovery warning clear

## Deletion Interaction

Backups must not become deletion loopholes.

Rules:

- generated after deletion excludes deleted content.
- local old backups cannot be remotely erased; user must be warned.
- tombstones included in migration package to prevent resurrection.
- service restore replays tombstones.

User copy:

```txt
過去にダウンロードしたバックアップ内のデータは、このサービスからは削除できません。新しいバックアップには削除済み記録を含めません。
```

## Service Exit Plan

If service shuts down:

Must provide:

- emergency_exit_package
- schema docs
- README explaining formats
- export window
- no new AI analysis required
- raw optional and policy-gated

Do not provide:

- unsafe full raw dump by default
- third-party raw package
- company data package

## AI Vendor Independence

Backup package must not require one LLM vendor.

Store:

- summaries
- evidence
- confidence
- source refs
- policy versions

Do not store as required:

- vendor-specific conversation state
- hidden prompt format
- proprietary embedding-only representation

## Cost Considerations

- Scheduled backup can be expensive if raw included.
- Markdown/JSONL safe backup is cheap.
- SQLite snapshot medium.
- Raw object backup high.

Default:

- safe archive only
- raw opt-in
- no media copy in MVP

## Failure Modes

- user thinks backup includes raw but it does not.
- user thinks backup is encrypted but it is not.
- third-party raw leaks to Drive.
- deleted data appears in new backup.
- old local backup conflicts with deletion expectations.
- schema not included, future unreadable.
- only embeddings exported, no readable content.

## Acceptance Criteria

- Manual safe export supports backup use.
- Backup manifest states raw/encryption/tombstone status.
- Open formats used.
- Deleted content excluded from new backups.
- Tombstones included for migration/local snapshot when selected.
- Third-party/corporate/secret raw excluded default.
- README explains limitations.
- No LLM/vendor dependency required to read backup.

## Non-goals

- Perfect remote deletion of downloaded files.
- Password manager backup.
- Full company archive backup.
- Raw photo library replacement.
- Cloud-drive integration in MVP.

## 結論

Memory OS は、サービス内に閉じた記憶では弱い。

ユーザーが自分の人生文脈を手元に持てるように、safe export / local archive / emergency exit を設計の中心に置く。
