# Platform Continuity, Sunset, and Portability

## 目的

この文書は、Memory OS が長期運用でサービス終了・買収・料金変更・障害・移行・Export互換性に直面しても、ユーザーが人生文脈を失わないための設計である。

Memory OS は「消えたら終わり」のサービスにしてはいけない。

## 最上位原則

### 1. User memory must be portable

ユーザーの人生文脈は、Memory OS内に閉じ込めない。

### 2. Exit is a core feature

退会、Export、移行、read-only mode、sunsetは、後付けではなくcore機能。

### 3. Export must be safe and usable

Exportは危険でもある。

だから、raw/sealed/third-party/persona/mediaを分け、versioned manifest付きで安全に出す。

## Continuity Scenarios

```ts
type ContinuityScenario =
  | 'planned_sunset'
  | 'company_acquisition'
  | 'pricing_shutdown_for_free_plan'
  | 'major_provider_loss'
  | 'data_center_failure'
  | 'security_incident'
  | 'legal_region_exit'
  | 'founder_bus_factor'
  | 'open_source_migration'
  | 'read_only_archive_mode';
```

## Planned Sunset Requirements

If Memory OS shuts down:

- announce with sufficient notice.
- freeze risky new imports.
- keep read-only access during grace period.
- allow standard export.
- allow sensitive export with safety ceremony.
- keep deletion available.
- provide export verification tools.
- provide migration guide.

Do not:

- delete user data without notice except legally/security required.
- force raw export without review.
- make export paid-only during sunset.
- hide shutdown until last moment.

## Read-only Archive Mode

Read-only mode allows:

- search existing eligible records.
- export.
- delete.
- download manifest.
- view source provenance.

Disallows:

- new imports.
- API sync.
- new LLM analysis.
- new embeddings.
- persona activation.

## Export Format Classes

```ts
type PortabilityExportClass =
  | 'standard_json_export'
  | 'standard_csv_export'
  | 'markdown_bundle'
  | 'media_manifest_only'
  | 'sensitive_summary_bundle'
  | 'raw_archive_reauth_required';
```

Minimum standard export:

- JSONL/JSON manifest.
- CSV for simple timeline/activity data.
- Markdown for user-readable memories.
- sourceRef/provenance.
- policy flags.
- redaction summary.
- version info.

## Export Manifest Requirements

```ts
interface PortabilityManifest {
  exportVersion: string;
  createdAt: string;
  appVersion?: string;
  policyVersion: string;
  schemaVersion: string;
  packageClass: string;
  recordCounts: Record<string, number>;
  containsRaw: boolean;
  containsMedia: boolean;
  containsSealed: boolean;
  containsThirdPartyRaw: boolean;
  containsPersonaLikeData: boolean;
  containsMinorData: boolean;
  redactionSummary: Record<string, number>;
  compatibilityNotes: string[];
}
```

Manifest must not contain raw private titles or chat text.

## User-owned Backup Strategy

Long term options:

1. manual export.
2. scheduled encrypted export to user storage.
3. local-first archive later.
4. open format reader later.

MVP:

- manual standard export.
- documented export schema.
- no one-click raw full export.

## Buyer / Acquisition Protection

If company is acquired:

- user notification.
- privacy policy change notice.
- export/delete grace period.
- no silent policy weakening.
- no automatic AI training use expansion.
- no persona/impersonation feature added by policy drift.

## Data Center / Infra Failure

Requirements:

- backups.
- restore drills.
- deletion tombstone replay.
- derived search/embedding rebuild.
- raw object restore verification.
- export package recreation where possible.

## Founder / Bus Factor

Even if one developer disappears:

- handoff docs exist.
- architecture docs exist.
- runbooks exist.
- backup/restore documented.
- export schema documented.
- admin credentials not single-person only.

## Local Reader / Open Format Later

Potential future:

- offline read-only viewer for exported memories.
- static HTML export.
- local search over JSON/Markdown.

Important:

- local reader must not activate persona.
- local export must preserve policy flags.

## Migration to Another Memory OS

Export should include enough to import elsewhere:

- stable IDs.
- source provenance.
- timestamps with precision.
- lifecycle states.
- user corrections.
- redaction reasons.

But must not include by default:

- secrets.
- third-party raw.
- sealed raw.
- raw persona clone bundles.

## P0 Tests

1. standard export includes manifest version.
2. standard export excludes sealed/raw/third-party by default.
3. sunset mode keeps export/delete available.
4. re-import of Memory OS export checks tombstones.
5. export manifest contains no raw private titles.
6. backup restore replays tombstones.
7. read-only mode disables new API sync/import.
8. acquisition policy change requires user notice/export grace.
9. raw archive export requires re-auth.
10. local/static export does not activate persona.

## 結論

Memory OSが長く信頼されるには、サービスが続くことだけでなく、終わる時にもユーザーの人生文脈を失わせない設計が必要である。

Exit、Export、read-only mode、sunset、migration、backup restoreは、長期信頼の中核である。
