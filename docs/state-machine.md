# State Machine Specification

## 目的

State Machine Specification は、Memory OS の重要な状態遷移を明確に定義する。

状態遷移を曖昧にすると、削除済み記憶が検索に出る、封印記憶がLLMに送られる、Export packageが期限切れ後も残る、Importがinspect前にextractするなどの事故が起きる。

## State Machine の考え方

State Machine は、あるentityが今どの状態で、次にどの状態へ移れるかを定義する。

```txt
状態 + イベント -> 次の状態
```

許可されていない遷移はバグとして扱う。

## Memory Lifecycle State

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

## Memory State Transitions

| From | Event | To | Allowed? | Notes |
|---|---|---|---|---|
| active | hide | hidden | yes | search hidden default |
| active | seal | sealed | yes | stronger than hidden |
| active | archive | archived | yes | low proactive surfacing |
| active | delete | pending_deletion | yes | immediate access block |
| hidden | unhide | active | yes | user action |
| hidden | seal | sealed | yes | stronger restriction |
| hidden | delete | pending_deletion | yes |  |
| sealed | unlock | active | yes with reauth | explicit unlock only |
| sealed | delete | pending_deletion | yes |  |
| archived | restore | active | yes | user action |
| archived | hide | hidden | yes |  |
| archived | delete | pending_deletion | yes |  |
| pending_deletion | complete_delete | deleted | yes | async physical delete may follow |
| pending_deletion | create_tombstone | tombstoned | yes | when resurrection guard needed |
| deleted | restore | active | restricted | only explicit restore, if allowed |
| tombstoned | reimport | active | no/default | must skip by default |

Forbidden:

- deleted -> active without explicit restore
- tombstoned -> active by normal import
- sealed -> LLM/search/export visible without unlock
- pending_deletion -> search/export/LLM visible

## Surface Eligibility by State

| State | Search | Tip | LLM | Export | Share | Raw Quote |
|---|---|---|---|---|---|---|
| active | policy | policy | policy | policy | policy | policy |
| hidden | no/default | no | explicit only | no/default | no/default | no/default |
| sealed | no | no | no/default | no/default | no | no |
| archived | explicit | no/default | explicit | selected | no/default | policy |
| pending_deletion | no | no | no | no | no | no |
| deleted | no | no | no | no | no | no |
| tombstoned | no content | no | no | marker only | no | no |

## RawRecord State

```ts
type RawRecordState =
  | 'not_stored'
  | 'stored'
  | 'masked'
  | 'pending_delete'
  | 'deleted';
```

Transitions:

| From | Event | To |
|---|---|---|
| not_stored | store_safe_raw | stored |
| stored | mask | masked |
| stored | delete_raw | pending_delete |
| masked | delete_raw | pending_delete |
| pending_delete | complete_delete | deleted |

Forbidden:

- deleted -> stored by system regeneration
- masked -> stored with original value unless raw object still exists and user explicitly restores

## ImportJob State

```ts
type ImportJobState =
  | 'received'
  | 'detected'
  | 'inspected'
  | 'scope_required'
  | 'planned'
  | 'extracting'
  | 'normalizing'
  | 'policy_evaluating'
  | 'indexing'
  | 'completed'
  | 'partial'
  | 'blocked'
  | 'failed'
  | 'deleted';
```

Happy path:

```txt
received
-> detected
-> inspected
-> scope_required
-> planned
-> extracting
-> normalizing
-> policy_evaluating
-> indexing
-> completed
```

Forbidden:

- received -> extracting
- detected unknown -> extracting full
- inspected high cost -> extracting without confirmation
- policy denied -> indexing

## ExportJob State

```ts
type ExportJobState =
  | 'requested'
  | 'policy_evaluating'
  | 'redacting'
  | 'packaging'
  | 'completed'
  | 'downloaded'
  | 'expired'
  | 'revoked'
  | 'failed'
  | 'deleted';
```

Rules:

- completed must have expiresAt.
- expired/revoked/deleted package cannot be downloaded.
- failed package must not remain downloadable.
- downloaded may still expire/delete after download.

Forbidden:

- requested -> packaging without policy_evaluating
- completed without manifest
- completed without redaction report for redacted fields
- expired -> downloaded

## Embedding State

```ts
type EmbeddingLifecycle =
  | 'active'
  | 'disabled_by_visibility'
  | 'pending_delete'
  | 'deleted';
```

Transitions:

| From | Event | To |
|---|---|---|
| active | memory_hidden | disabled_by_visibility |
| active | memory_sealed | disabled_by_visibility |
| active | memory_delete | pending_delete |
| disabled_by_visibility | memory_unhidden | active |
| pending_delete | vector_deleted | deleted |

Forbidden:

- deleted -> active without recompute after explicit restore
- active when Memory is sealed/deleted/pending_deletion

## PolicyDecision State

PolicyDecision is immutable.

If context changes, create a new PolicyDecisionRecord.

Forbidden:

- editing old policy decision in place
- deleting policy decision to hide history
- storing raw content inside policy decision

## State Transition Enforcement

Use helpers:

```ts
canTransitionMemory(from, event): boolean
transitionMemory(state, event): MemoryLifecycleState
assertSurfaceEligibility(memory, surface): void
```

Use in:

- search
- export
- LLM send
- deletion
- embedding
- share
- tip

## State Machine Tests

P0 tests:

1. pending_deletion cannot search.
2. pending_deletion cannot export.
3. pending_deletion cannot LLM.
4. sealed cannot search/export/LLM default.
5. deleted cannot restore by import.
6. tombstoned cannot restore by import.
7. Import cannot extract before inspect.
8. Unknown import cannot full extract.
9. Export cannot package before policy.
10. Expired export cannot download.
11. Active embedding disabled when memory sealed.
12. Raw deleted cannot be regenerated.

## UX Mapping

UI labels:

| Internal State | User label |
|---|---|
| active | 表示中 |
| hidden | 非表示 |
| sealed | 封印中 |
| archived | アーカイブ |
| pending_deletion | 削除処理中 |
| deleted | 削除済み |
| tombstoned | 削除済み記録あり |

Avoid:

- 大切な記憶を削除
- 価値の低い記憶
- AIが重要と判断

## Acceptance Criteria

- All state transitions are explicit.
- Forbidden transitions are tested.
- Lifecycle is checked at every surface.
- Import has no extract-before-inspect path.
- Export has no package-before-policy path.
- Embedding lifecycle follows Memory lifecycle.
- UI copy maps states without guilt or value judgment.

## 結論

State Machine は、Memory OS の安全境界を状態で守る設計である。

「削除したのに出る」「封印したのにAIに送る」「Export期限切れなのに落とせる」を防ぐには、状態遷移を明示してテストする必要がある。
