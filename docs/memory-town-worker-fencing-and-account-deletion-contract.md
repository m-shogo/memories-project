# Memory Town Worker Fencing and Account Deletion Contract

最終更新: 2026-07-13

## 目的

Projection、snapshot、migration、asset manifest refreshなどの非同期workerが、account deletion後やlayout migration中に古い状態を書き戻すことを防ぐ。

DBのcascade deleteだけでは、削除前にqueueされたjobによるrow再作成を防げない。

実装はまだ開始しない。

---

# 1. Account lifecycle fence

```ts
type AccountLifecycleState =
  | 'active'
  | 'deletion_requested'
  | 'deleting'
  | 'deleted';

interface AccountWriteFence {
  accountState: AccountLifecycleState;
  deletionEpoch: number;
}
```

Rules:

- account作成時`deletionEpoch = 0`
- deletion request受理時にepochをincrement
- `deletion_requested`以降は新しいTown background jobをenqueueしない
- 全Town writeは`accountState = active`を必要とする
- jobはenqueue時のexpectedDeletionEpochを持つ
- write直前にcurrent epochを再確認する
- mismatch時はwrite禁止

---

# 2. Fenced background job envelope

```ts
interface TownBackgroundJobEnvelope<TPayload> {
  jobId: string;
  jobType:
    | 'feature_projection'
    | 'feature_unlock'
    | 'scene_snapshot'
    | 'layout_migration'
    | 'thumbnail_generation'
    | 'asset_manifest_refresh';
  userId: string;
  expectedDeletionEpoch: number;
  expectedAccountState: 'active';
  enqueuedAt: string;
  payload: TPayload;
}
```

Job payloadへMemory title、note、人名を入れない。

---

# 3. Write precondition

全worker write直前にserver authoritative checkを行う。

```txt
account exists
AND accountState = active
AND deletionEpoch = expectedDeletionEpoch
AND RLS / ownership valid
AND target version / revision still valid
```

Failure:

```txt
ACCOUNT_DELETION_FENCE_REJECTED
```

stale jobをretry loopへ戻さない。

---

# 4. Account deletion workflow

```txt
explicit confirmation
→ accountState = deletion_requested
→ deletionEpoch + 1
→ new jobs enqueue停止
→ active Town jobsへcancellation signal
→ accountState = deleting
→ Town export / snapshot generation停止
→ Town user rows削除
→ Memory OS user rows削除
→ object storage削除queue
→ stale job write rejection確認
→ deletion completion audit
→ accountState = deleted or account row removal
```

Deletion完了条件:

- user-owned Town table row = 0
- pending Town job = 0またはfence reject可能
- thumbnail / cached scene無効化
- export temp object削除queue作成
- support access session revoke
- auditにprivate contentなし

---

# 5. No resurrection rule

禁止:

- deleted user IDでlayout auto-create
- missing layoutを理由にdefault Town生成
- stale snapshot workerによるupsert
- deleted accountのasset preference再作成
- deletion完了後のretry

Default Town作成は、active accountのexplicit onboarding transaction内だけ許可する。

---

# 6. Layout mutation mode

Migrationとuser editの同時実行を防ぐ。

```ts
type TownLayoutMutationMode =
  | 'normal'
  | 'user_edit_session'
  | 'migration_locked'
  | 'reset_locked'
  | 'repair_locked';
```

`town_layout`は次を持つ。

```ts
interface TownLayoutMutationFence {
  mode: TownLayoutMutationMode;
  fenceToken: string;
  fenceRevision: number;
  expiresAt?: string;
}
```

Rules:

- migration開始時にCASで`migration_locked`
- user saveは`normal`または自身の`user_edit_session`のみ
- migration中のcommand batchは拒否
- reset中のmigration開始は禁止
- stale fence tokenでunlock禁止
- timeoutだけで自動commitしない

Issue codes:

```txt
LAYOUT_MIGRATION_IN_PROGRESS
LAYOUT_RESET_IN_PROGRESS
LAYOUT_REPAIR_IN_PROGRESS
LAYOUT_FENCE_TOKEN_MISMATCH
```

---

# 7. Projection / unlock fencing

Feature unlock jobはaccount fenceに加えて次を確認する。

- expectedResetEpoch
- expectedGrowthOriginCursor
- projection cursor
- active growth ruleset

Layout migration jobは次を確認する。

- expected layout revision
- baseline template version
- expected object catalog version
- expected growth envelope version

---

# 8. Snapshot and thumbnail rules

Snapshot / thumbnailは正本ではない。

Write前:

```txt
account fence
→ current layout revision
→ current scene content hash
→ visibility / privacy policy
```

Account deletion開始後:

- 新規生成禁止
- existing cached URL revoke
- CDN purge best effort
- fallback UIへdeleted snapshotを表示しない

Thumbnail jobが遅れて完了しても、fence mismatchならobject storage publishしない。

---

# 9. Retry policy

Retry可能:

- transient network
- temporary object storage failure
- recoverable renderer-independent thumbnail worker error

Retry不可:

- account deletion fence mismatch
- stale reset epoch
- stale layout revision
- migration token mismatch
- ownership failure
- unknown definition

Retry回数・backoffは運用設計で固定する。

---

# 10. Required negative tests

1. deletion request後にprojection worker write
2. deletion中にsnapshot worker publish
3. deleted userへdefault layout auto-create
4. stale deletion epoch job replay
5. migration中にuser command batch
6. reset中にmigration開始
7. expired fence tokenでmigration commit
8. support session revoke後のread
9. account deleteとexport生成同時
10. object storage upload完了直前にdeletion epoch change

---

# Decision

```txt
Cascade deleteだけに依存しない。
全非同期writeをaccount epochでfenceする。
Migration / Reset / Repairはlayout mutation modeで直列化する。
削除後にTownが復活する経路を残さない。
```
