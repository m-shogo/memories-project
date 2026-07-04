# RFC-0005: Deletion / Backup Semantics

## Status

`accepted_with_limits`

## Summary

Deletion / Backup Semantics は、Memory OS における削除・非表示・封印・raw削除・tombstone・バックアップ復元・再インポートの関係を定義する。

Memory OS は忘れないための索引だが、ユーザーには忘れる権利がある。

このRFCは `docs/deletion-backup-semantics.md` を採用仕様として扱う。

## Motivation

長期記憶サービスでは、削除が弱いと信頼が壊れる。

以下の事故を防ぐ必要がある。

- 削除済み記憶が検索に出る
- 削除済み記憶がTipに出る
- 削除済み記憶がLLMに送られる
- バックアップ復元で消した記憶が戻る
- 再インポートで消した記録が復活する
- raw削除したのに要約からrawを再生成する
- deletion UIが罪悪感を煽る

## Non-goals

- 削除を心理的に難しくすること
- rawを永続保存すること
- バックアップを隠れた保持手段にすること
- 管理者が削除済みmemoryを簡単に復元すること
- 削除済みrawをAIで再構築すること

## Constitution Check

| Question | Answer |
|---|---|
| ChatGPT代替にならないか | Yes. deletion semanticsは会話機能ではない。 |
| Character.AI化しないか | Yes. 削除済みpersona素材の復活を防ぐ。 |
| 本人・家族・故人を演じないか | Yes. raw削除/封印でsimulation素材化を防ぐ。 |
| 人格診断にならないか | Yes. 削除/封印は分析対象から外す。 |
| 人生ランキングにならないか | Yes. 削除UIで大切さを押し付けない。 |
| 保存時に分析しすぎないか | Yes. raw-only deleteを許す。 |
| 小さな記録を捨てないか | Yes. rawなしSourceRef/safe summaryを残せる。 |
| 大きなイベントを押し付けないか | Yes. grief/deceased削除を罪悪感化しない。 |
| 出典・日付・検索性を守るか | Yes. raw削除後もsafe SourceRefを保持可能。 |
| 削除・非表示・Exportを尊重するか | Yes. このRFCの中心。 |

## User Value

- 消したものが戻らない安心。
- 原文だけ消して文脈は残せる。
- 見たくない記憶を封印できる。
- バックアップや再インポートでも削除が尊重される。

## Data Model Impact

追加:

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

## Policy Impact

| Action | Default decision | Reason |
|---|---|---|
| import_inspect | check tombstone | deleted imports not silently restored. |
| extract_raw | check tombstone | re-import guard. |
| store_raw | deny if tombstoned | resurrection防止。 |
| create_memory | deny if tombstoned |  |
| create_embedding | deny if hidden/sealed/deleted | search exposure防止。 |
| send_to_llm | deny if pending/hidden/sealed/deleted |  |
| show_in_search | deny if hidden/sealed/deleted default |  |
| show_raw_quote | deny if raw_deleted |  |
| generate_tip | deny if hidden/sealed/deleted |  |
| share_memory | deny if hidden/sealed/deleted default |  |
| export_memory | deny if deleted/pending; default exclude hidden/sealed |  |
| delete_memory | allow | user right. |
| admin_access | metadata_only | deleted rawを見ない。 |

## Privacy Impact

Deletion strengthens privacy.

Special handling:

- family/grief deletion UI must not guilt-frame.
- minor raw deletion should be easy.
- third-party raw deletion can preserve user relationship summary if safe.

## Security Impact

- pending_deletion must block derived access immediately.
- embeddings disabled/deleted.
- backup restore must replay tombstones.
- audit logs no raw.
- raw delete irreversible.

## Third-party Impact

If third-party private data is found later, raw-only delete or memory delete must be possible.

Export/share must respect deletion.

## Minor / Family Impact

- minor raw delete recommended.
- family conflict can be sealed.
- deletion UI must avoid “大切な思い出” guilt copy.

## Legacy / Deceased Impact

- grief records can be sealed/deleted without guilt.
- deceased simulation素材を削除/封印できる。
- no “故人が悲しむ” style copy.

## Corporate Data Impact

Corporate data discovered after import should support:

- raw delete
- import job delete
- source delete
- tombstone to prevent re-import

## Cost Impact

- Expected input size: all user data operations.
- LLM calls: none.
- Embedding writes: delete/disable operations.
- Storage growth: tombstones/audit minimal.
- Worst-case abuse: repeated delete/restore/re-import.
- Free plan behavior: deletion never blocked by plan.
- Paid plan behavior: same.
- Hard stop: restore of policy violation/account deletion.
- User-visible estimate: show affected records, not price.

## UX Impact

Good deletion copy:

```txt
この記録を削除できます。削除後は検索・Tip・Exportに表示されません。
```

Bad:

```txt
本当にこの大切な思い出を消しますか？
```

UI actions:

- hide
- seal
- delete
- raw-only delete
- exclude from AI
- exclude from Tip
- exclude from Export

## Explainability Impact

Deletion state should explain:

- what is hidden vs sealed vs deleted
- raw only deleted or whole memory deleted
- what remains
- whether tombstone prevents re-import
- whether export includes marker

## Deletion / Export Impact

Core rules:

- pending_deletion blocks immediately.
- deleted content excluded.
- tombstone optional in migration package only.
- sealed excluded default.
- rawStored=false after raw delete.

## Failure Modes

- search index not updated after delete.
- vector row still active.
- backup restore ignores tombstone.
- re-import recreates contentHash.
- export includes pending_deletion.
- AI uses old interpretation derived from deleted raw.

## Abuse Cases

1. 削除したパートナーDMを再インポートで戻す。
2. 家族を責めるためにsealed recordを検索する。
3. 故人ログを削除後backupから再現する。
4. AI恋人ログをraw delete後summaryから再構築する。
5. 子ども情報を削除してもExportに残る。
6. 会社情報を削除後vector searchで出す。
7. APIキーをraw delete後embeddingで検索する。
8. 巨大削除でサービスを詰まらせる。
9. pending_deletion中にLLMへ送る。
10. tombstoneにraw contentを保存してしまう。

## Alternatives Considered

### Physical delete only, no tombstone

却下。再インポート復活を防げない。

### Hide as delete

却下。ユーザー権利として不十分。

### Backup restore before deletion replay

却下。削除権を壊す。

## Acceptance Criteria

- pending_deletion blocks search/tip/LLM/export immediately.
- tombstone prevents re-import resurrection.
- raw-only delete works.
- rawStored=false reflected in SourceRef.
- embedding disabled/deleted.
- backup restore replays tombstones.
- deletion audit has no raw.
- deleted content excluded from export.
- deletion UI copy is non-guilt-inducing.

## Rollout Plan

1. hide/delete memory
2. pending_deletion lifecycle
3. raw-only delete
4. tombstone
5. search/vector exclusion
6. export exclusion
7. backup restore replay
8. explicit restore flow

## Open Questions

- tombstone retention period for account deletion。
- local export tombstone portability。
- irreversible raw delete confirmation UX。

## Decision

`accepted_with_limits`

制限:

- deletion cannot be plan-gated.
- restore must be explicit.
- tombstones must never store raw text.
