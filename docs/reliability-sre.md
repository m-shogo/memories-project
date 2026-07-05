# Reliability / SRE Guide

## 目的

Reliability / SRE Guide は、Memory OS を安定して運用するための信頼性目標・障害時の期待値・復旧方針を定義する。

Memory OS は人生文脈を扱うため、単なる uptime だけでなく、削除・Export・Privacy・Policy の信頼性が重要である。

## SREを一言で言うと

```txt
サービスを壊れないようにするだけでなく、壊れた時にどれくらい許容し、どう復旧するかを決める運用設計。
```

## Reliability Domains

```ts
type ReliabilityDomain =
  | 'capture'
  | 'search'
  | 'delete'
  | 'export'
  | 'import'
  | 'policy'
  | 'auth'
  | 'storage'
  | 'llm_optional'
  | 'backup_restore';
```

## Core Reliability Principle

### 1. Safety over availability

危険な時は止める。

例:

- Policyが壊れたらLLM/Exportを止める。
- Search lifecycle filterが壊れたら検索を止める。
- Export redactionが壊れたらExportを止める。

### 2. Capture should degrade gracefully

AIやembeddingが落ちても、小さな記録保存はできるべき。

### 3. Delete must be highly reliable

削除・封印・非表示は最優先で信頼性を確保する。

### 4. LLM is optional

LLM停止でMemory OS全体が止まってはいけない。

## SLO Drafts

### Capture SLO

- 99.9% of low-risk manual captures complete without LLM.
- failure must not lose user input silently.

### Search SLO

- 99.5% of basic search requests succeed.
- hidden/sealed/deleted leak rate target: 0.

### Delete SLO

- 99.99% of delete requests set pending_deletion within 1s.
- deleted content surfaced target: 0.

### Export SLO

- 99% of safe small exports complete within 30s.
- unsafe export leakage target: 0.

### Policy SLO

- Policy evaluator availability target: effectively local/in-process.
- policy bypass target: 0.

## Error Budgets

For ordinary availability, small error budget is acceptable.

For safety invariants, error budget is zero.

Zero-budget failures:

- deleted memory shown
- secret exported
- corporate raw sent to LLM
- third-party raw shared/exported
- admin raw access without break-glass

## Degradation Modes

| Dependency failed | Degrade to |
|---|---|
| LLM vendor down | no AI summary; save/search still works |
| Vector index down | keyword search only |
| Object storage down | metadata-only capture; raw upload disabled |
| Export worker down | queue export; no unsafe fallback |
| Policy engine broken | block dangerous actions |
| Search index stale | query DB with lifecycle filter or disable search |
| Cost service down | block medium+ jobs |

## Reliability Tests

Required tests:

1. LLM down does not block manual capture.
2. Vector down falls back to keyword search.
3. Policy failure blocks LLM/Export.
4. Export worker failure does not expose partial package.
5. Delete sets pending_deletion even if object deletion fails.
6. Search checks lifecycle even if index stale.
7. Cost estimate unavailable blocks large import.

## Disaster Recovery

Recovery priorities:

1. stop unsafe surfaces
2. restore auth/session safety
3. restore deletion/search lifecycle correctness
4. restore capture
5. restore export
6. restore optional LLM/embedding

## Backup Restore Reliability

Restore procedure must:

- restore relational core
- replay tombstones
- rebuild search index only for active eligible data
- rebuild vector only for eligible data
- verify export packages not restored as downloadable

## Operational Runbooks

Minimum runbooks:

- LLM vendor outage
- DB outage
- object storage outage
- export worker stuck
- search index stale
- deletion propagation lag
- policy deny spike
- cost attack spike

## Acceptance Criteria

- safety-over-availability principle documented
- core SLOs drafted
- zero-budget safety failures listed
- degradation modes defined
- DR restore order defined
- reliability tests listed

## 結論

Memory OS の信頼性は、単に落ちないことではない。

落ちた時に、危険なことをしないこと。

特に削除・Policy・Export・Search lifecycle は、普通の機能より強い信頼性が必要である。
