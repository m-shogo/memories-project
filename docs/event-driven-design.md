# Event-driven Design for Memory OS

## 目的

このドキュメントは、Event-driven Design を Memory OS にどう適用するかを説明する。

Event-driven Design は、重要な出来事をイベントとして記録し、検索・Export・削除・監査・バックアップ・通知などを安全に連動させる設計である。

Memory OSでは、特に削除・Policy拒否・Export・Import・LLM送信・Embedding無効化が重要なイベントになる。

## 一言で言うと

```txt
何か重要なことが起きたら、それを「出来事」として残し、別の処理が安全に追従できるようにする設計。
```

## なぜ必要か

例えばユーザーが記憶を削除した時、やることは1つではない。

```txt
Memoryをpending_deletionにする
Search indexから消す
Vector indexを無効化する
Raw objectを削除する
Export対象から外す
Tombstoneを作る
Audit logを書く
Backup restore用markerを作る
```

これを全部1つの関数にベタ書きすると壊れやすい。

Eventとして扱うと、以下のように分離できる。

```txt
MemoryDeleted event
-> SearchProjection disables result
-> VectorProjection disables embedding
-> TombstoneHandler creates tombstone
-> AuditHandler writes audit log
```

## Domain Event vs Audit Log

混ぜてはいけない。

| Type | Purpose | Example |
|---|---|---|
| Domain Event | システム内部の状態変化 | MemoryDeleted |
| Audit Log | 誰が何をしたかの監査 | user deleted memory at time |
| Incident Log | 事故対応 | wrong export revoked |

Domain Event は処理連動のため。

Audit Log は説明責任のため。

## MVP Events

```ts
type DomainEventType =
  | 'ImportInspected'
  | 'ImportPlanned'
  | 'ImportExtracted'
  | 'MemoryCreated'
  | 'PolicyDenied'
  | 'MemoryHidden'
  | 'MemorySealed'
  | 'MemoryDeleted'
  | 'RawDeleted'
  | 'TombstoneCreated'
  | 'SearchIndexUpdated'
  | 'EmbeddingDisabled'
  | 'ExportRequested'
  | 'ExportCreated'
  | 'ExportExpired'
  | 'LlmSendDenied';
```

## Event Shape

```ts
type DomainEvent = {
  id: string;
  type: DomainEventType;
  userId: string;
  aggregateType: string;
  aggregateId: string;
  occurredAt: string;
  schemaVersion: string;
  policyVersion?: string;
  payload: Record<string, unknown>;
  containsRawContent: false;
};
```

Rule:

- event payload must not include raw memory text.
- event payload must not include secret values.
- event payload should include IDs, counts, risk classes, policy modes.

## Example Events

### MemoryCreated

```ts
{
  type: 'MemoryCreated',
  userId: 'user_123',
  aggregateType: 'memory',
  aggregateId: 'mem_001',
  payload: {
    sourceRefIds: ['src_001'],
    evidenceIds: ['ev_001'],
    riskClasses: [],
    lifecycle: 'active'
  },
  containsRawContent: false
}
```

### PolicyDenied

```ts
{
  type: 'PolicyDenied',
  userId: 'user_123',
  aggregateType: 'policy_decision',
  aggregateId: 'pol_001',
  payload: {
    action: 'send_to_llm',
    targetType: 'raw_record',
    targetId: 'raw_001',
    reasons: ['corporate_confidential'],
    mode: 'deny'
  },
  containsRawContent: false
}
```

### RawDeleted

```ts
{
  type: 'RawDeleted',
  userId: 'user_123',
  aggregateType: 'raw_record',
  aggregateId: 'raw_001',
  payload: {
    sourceRefId: 'src_001',
    rawStored: false,
    deletionScope: 'raw_only'
  },
  containsRawContent: false
}
```

## Event Consumers

```ts
type EventConsumer =
  | 'search_projection'
  | 'vector_projection'
  | 'audit_writer'
  | 'cost_ledger_writer'
  | 'export_status_updater'
  | 'backup_marker_writer'
  | 'incident_monitor'
  | 'notification_service';
```

## Projections

Projection は、イベントから作る読み取り用のビュー。

Examples:

- Search index
- Vector lifecycle table
- Export status view
- Import progress view
- Admin metadata dashboard

Projectionは原本ではない。

原本は relational core / SourceRef / Memory / Tombstone。

## Event Sourcingについて

Event Sourcing は、現在状態をすべてイベントから復元する高度な設計である。

Memory OS MVPでは、完全なEvent Sourcingは不要。

理由:

- 複雑になる。
- 削除権とイベント保持が衝突しやすい。
- rawをイベントに入れない制約が強い。

MVPでは以下で十分。

```txt
State stored in DB
+ important domain events for side effects/audit/projections
```

## Outbox Pattern

DB更新とイベント発行のズレを防ぐ業界パターン。

Problem:

```txt
DB更新成功
Event発行失敗
```

Solution:

```txt
same DB transaction:
  update memory
  insert outbox event
worker:
  publish/process event
  mark processed
```

MVPでもDeletion/ExportはOutbox推奨。

## Idempotency

イベント処理は重複実行される前提にする。

Examples:

- EmbeddingDisabledを2回受けてもOK。
- ExportExpiredを2回受けてもOK。
- TombstoneCreatedを2回受けても重複しない。

```ts
type IdempotencyKey = string;
```

Recommended key:

```txt
<eventType>:<aggregateId>:<occurredAt or version>
```

## Event Safety Rules

1. No raw text.
2. No secret values.
3. No full third-party content.
4. No company raw.
5. Use IDs and counts.
6. Use risk classes instead of content.
7. PolicyDenied events can include reason codes only.
8. Deleted data events must not include deleted content.

## Event Use Cases

### Delete propagation

```txt
MemoryDeleted
-> search_projection removes
-> vector_projection disables
-> backup_marker_writer records
-> audit_writer writes
```

### Export lifecycle

```txt
ExportRequested
-> export worker creates package
-> ExportCreated
-> download available
-> ExportExpired
-> package deleted
```

### Policy monitoring

```txt
PolicyDenied(send_to_llm)
-> incident_monitor increments metric
-> if spike, alert
```

### Cost monitoring

```txt
ImportExtracted(count=10000)
-> cost_ledger_writer records units
-> if budget exceeded, pause jobs
```

## Failure Modes

- event includes raw content.
- event processing duplicated and creates duplicate tombstone.
- DB update succeeds but event lost.
- event order wrong: ExportCreated after ExportExpired.
- deleted memory event not consumed by vector index.
- audit and domain event confused.

## Tests

Required tests:

1. DomainEvent payload rejects raw content field.
2. MemoryDeleted emits outbox event.
3. Search projection handles MemoryDeleted.
4. Vector projection handles MemoryDeleted.
5. ExportExpired deletes package idempotently.
6. TombstoneCreated idempotent.
7. PolicyDenied has no raw text.
8. Outbox worker retries safely.
9. Event ordering handles stale events.
10. Incident monitor catches LLM deny spike.

## MVP Recommendation

Implement events for:

- MemoryDeleted
- RawDeleted
- TombstoneCreated
- ExportCreated
- ExportExpired
- PolicyDenied
- EmbeddingDisabled

Defer:

- full event sourcing
- cross-service message broker
- Kafka/PubSub
- complex saga orchestration

MVP can use:

- DB outbox table
- worker loop
- in-process event dispatch in tests

## Acceptance Criteria

- Important state changes emit raw-free events.
- Deletion propagation uses events or equivalent hooks.
- Event handlers are idempotent.
- Outbox prevents lost side effects.
- Events do not become hidden raw logs.
- Event tests cover deletion/export/policy deny.

## 結論

Event-driven Design は、Memory OS の削除・Export・Policy・検索index更新を安全に連動させるための設計である。

完全なEvent SourcingはMVPでは不要。

まずは raw-free Domain Events と Outbox Pattern で、事故りやすい副作用を確実に処理する。
