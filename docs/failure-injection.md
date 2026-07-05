# Failure Injection Plan

## 目的

Failure Injection Plan は、Memory OS の重要な依存や処理を意図的に壊し、安全に劣化・停止できるかを検証するための設計である。

これは Chaos Engineering の考え方を、Memory OS の安全境界に合わせて小さく適用する。

## 一言で言うと

```txt
本番で事故る前に、壊れ方をテストする。
```

## 最上位原則

### 1. Never inject raw data

failure test に本物の個人情報や秘密を使わない。

### 2. Safety failures are more important than uptime failures

単なる500より、deletedが検索に出る方が重大。

### 3. Fail closed for dangerous actions

Policy/Cost/Redactionが不安なら、LLM/Export/Embeddingを止める。

## Failure Scenarios

## 1. LLM Vendor Down

Inject:

- LlmPort throws timeout/error.

Expected:

- manual capture still works.
- search still works.
- LLM summary unavailable message.
- no retry storm.
- no raw fallback to another vendor without policy.

## 2. Vector Index Down

Inject:

- vector search unavailable.

Expected:

- keyword search fallback.
- no unsafe vector cache exposure.
- user sees limited search notice if needed.

## 3. Object Storage Down

Inject:

- raw upload/delete fails.

Expected:

- metadata-only capture allowed if safe.
- raw storage disabled.
- delete access block still immediate.
- physical delete retried async.

## 4. Policy Engine Error

Inject:

- PolicyEvaluator throws.

Expected:

- dangerous actions deny.
- safe manual capture may fail closed or use minimal policy depending action.
- LLM/export/embedding blocked.

## 5. Export Redactor Error

Inject:

- redaction step fails.

Expected:

- export fails closed.
- no package downloadable.
- export audit records failure without raw.

## 6. Search Index Stale

Inject:

- search index returns deleted memory id.

Expected:

- final lifecycle check filters it.
- alert critical if stale unsafe result attempted.

## 7. Backup Restore Before Tombstone

Inject:

- restore snapshot with deleted data.

Expected:

- tombstones replayed before search/export enabled.
- deleted memory not visible.

## 8. Cost Estimator Down

Inject:

- cost estimate unavailable.

Expected:

- medium+ jobs blocked.
- small manual capture allowed if configured safe.
- no full history processing.

## 9. Outbox Worker Retry

Inject:

- event handler fails halfway.

Expected:

- retry idempotent.
- no duplicate tombstones.
- no duplicate export packages.

## 10. Admin Tool Misconfiguration

Inject:

- support_admin requests read_raw.

Expected:

- denied.
- break-glass required.
- audit no raw.

## Test Environment

MVP failure injection can run in tests, not production.

Use:

- fake ports
- throwing repositories
- fake storage
- fake LLM
- fake search index
- fake clock

## Failure Injection Matrix

| Failure | Must preserve |
|---|---|
| LLM down | capture/search/delete |
| vector down | keyword search |
| object storage down | lifecycle delete block |
| policy error | dangerous actions blocked |
| export redactor error | no downloadable package |
| stale search | lifecycle final filter |
| backup restore issue | tombstone replay |
| cost error | no large job |
| outbox retry | idempotency |
| admin misconfig | no raw access |

## Acceptance Criteria

- failure tests exist for P0 safety surfaces.
- dangerous dependency failure fails closed.
- delete access block survives storage failure.
- search final filter catches stale index.
- export redaction failure never produces package.
- LLM outage does not break core memory capture.

## Non-goals

- Full production chaos engineering in MVP.
- Random failure in live user data.
- Vendor-level chaos at first release.

## 結論

Failure Injection は、Memory OS が壊れた時に思想も壊れないかを見る訓練である。

特に、Policy・Export・Deletion・Search lifecycle は、依存が落ちたら安全側に倒れる必要がある。
