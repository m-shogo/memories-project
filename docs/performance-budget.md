# Performance Budget

## 目的

Performance Budget は、Memory OS の主要操作がどれくらいの時間・容量・コストで動くべきかを定義する。

性能目標は、速さのためだけではない。

遅い処理は、ユーザー体験を悪化させるだけでなく、コスト攻撃・タイムアウト・重複実行・削除遅延・Export事故につながる。

## 最上位原則

### 1. Small capture must be instant

小さな記録を残す体験は軽い必要がある。

### 2. Large import must be staged

大きなimportは即時処理しない。inspect -> scope -> estimate -> job。

### 3. Delete access block is immediate

物理削除が非同期でも、検索/LLM/Exportからの遮断は即時。

### 4. Export can be async

安全なExportは時間がかかってもよいが、進捗と期限を明示する。

## MVP Latency Targets

| Operation | Target | Hard limit | Notes |
|---|---:|---:|---|
| Manual capture save | < 300ms | 1s | no LLM |
| Share text capture | < 500ms | 2s | small text |
| Policy evaluation | < 20ms | 100ms | pure function preferred |
| Secret scan small text | < 50ms | 200ms | regex/local |
| Basic search | < 300ms | 1s | keyword/date/source |
| Hide/seal | < 200ms | 1s | lifecycle update |
| Delete access block | < 200ms | 1s | pending_deletion |
| Raw object physical delete | async | 24h | access blocked immediately |
| Import inspect small file | < 1s | 5s | no LLM |
| Export small markdown | < 5s | 30s | can be job |

## Batch Limits MVP

| Job | Soft limit | Hard limit | Behavior |
|---|---:|---:|---|
| manual paste chars | 20k | 100k | require confirmation/partial |
| share text chars | 10k | 50k | partial or reject |
| import files | 100 | 1,000 | inspect only/partial |
| extracted records | 1,000 | 10,000 | scope required |
| embedding writes | 0 default | selected only | post-MVP |
| export records | 10,000 | 100,000 | async |

## Cost Budget

MVP default:

- LLM calls: zero in core capture/search/delete/export path
- Embedding: zero default
- Raw storage: optional, low-risk only
- Inspect: cheap/local

Cost red flags:

- LLM call during inspect
- embedding during save by default
- full history import sync
- image analysis at import
- export with raw media default

## Deletion Performance

P0 target:

```txt
User requests delete
-> pending_deletion set within 200ms target
-> all surfaces check lifecycle immediately
```

Physical cleanup can be async, but access cannot wait.

## Search Performance

MVP:

- keyword/date/source search
- relational or FTS
- no vector required

Post-MVP:

- vector search only for safe eligible records
- vector query must still filter lifecycle/policy

## Export Performance

Export jobs should report:

- status
- counts
- redactions
- expiresAt

Do not block UI for large exports.

## Performance Tests

Required tests:

1. Policy evaluator fast unit test.
2. Delete sets pending_deletion quickly.
3. Search excludes pending_deletion even if index stale.
4. Import inspect does not call LLM.
5. Large input returns partial/scope required.
6. Export job can be async.

## Acceptance Criteria

- performance targets documented
- large jobs staged
- LLM not on MVP hot path
- delete access block immediate
- search target defined
- cost red flags listed

## 結論

Performance Budget は、速さよりも安全な運用のために必要である。

特にMemory OSでは、重い処理を勝手に走らせないことが、コスト・プライバシー・思想を守ることにつながる。
