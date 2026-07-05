# Observability Model for Memory OS

## 目的

Observability Model は、Memory OS を安全に運用するために、何を計測し、何をログに残し、何をアラートにするかを定義する。

Memory OSでは、普通のSaaSのように「ログを見れば原因が分かる」設計は危険である。

人生文脈・第三者情報・秘密情報・会社情報を扱うため、**ユーザー内容を覗かずに、システムの安全性と健全性を観測する**必要がある。

## Observabilityを一言で言うと

```txt
システムの中で何が起きているかを、危険な本文を見ずに分かるようにする仕組み。
```

## 3 Pillars

業界ではObservabilityはよく3つに分けられる。

| Pillar | Meaning | Memory OSでの注意 |
|---|---|---|
| Logs | 何が起きたか | raw text禁止 |
| Metrics | 数値の傾向 | risk class / count中心 |
| Traces | 1リクエストの流れ | payload本文を載せない |

## 最上位原則

### 1. No raw content in observability

ログ・メトリクス・トレースにraw memory textを入れない。

### 2. Observe safety boundaries

性能だけでなく、Policy deny、Export redaction、Deletion propagation、LLM blockも観測する。

### 3. Alert on dangerous success

失敗だけでなく、「成功してはいけないものが成功した」時にアラートする。

### 4. User trust over debugging convenience

デバッグしやすさより、ユーザーの人生文脈を覗かないことを優先する。

## What to Log

Allowed log fields:

```ts
type SafeLogFields = {
  requestId?: string;
  userIdHash?: string;
  actorType?: ActorType;
  action?: string;
  entityType?: string;
  entityId?: string;
  sourceType?: SourceType;
  riskClasses?: RiskClass[];
  policyMode?: string;
  costClass?: CostClass;
  count?: number;
  durationMs?: number;
  errorCode?: string;
  adapterId?: string;
  schemaVersion?: string;
  policyVersion?: string;
};
```

Forbidden log fields:

- raw memory text
- raw third-party messages
- secret values
- full prompts
- LLM full responses
- export package contents
- precise location unless explicitly safe
- filenames if they contain sensitive text

## Metrics

### Safety Metrics

```txt
policy_denied_total{action,riskClass,sourceType}
secret_detected_total{sourceType,adapterId}
third_party_raw_blocked_total{sourceType}
corporate_data_blocked_total{sourceType}
minor_data_blocked_total{sourceType}
llm_send_denied_total{riskClass}
export_redacted_total{reason}
```

### Deletion Metrics

```txt
memory_delete_requested_total
raw_delete_requested_total
tombstone_created_total
search_index_delete_lag_ms
vector_disable_lag_ms
backup_tombstone_replay_total
reimport_tombstone_skipped_total
```

### Import Metrics

```txt
import_inspected_total{sourceType,adapterId}
import_blocked_total{reason}
import_partial_total{sourceType}
import_records_extracted_total{sourceType}
unknown_source_inspect_only_total
```

### Export Metrics

```txt
export_requested_total{mode}
export_completed_total{mode}
export_failed_total{reason}
export_expired_total
export_url_revoked_total
export_raw_requested_total
export_raw_denied_total{reason}
```

### Cost Metrics

```txt
cost_estimate_total{costClass,action}
cost_hard_stop_total{reason}
llm_tokens_estimated_total
embedding_writes_total
large_job_confirmation_required_total
```

### Reliability Metrics

```txt
request_latency_ms{route}
job_duration_ms{jobType}
job_failed_total{jobType,errorCode}
outbox_pending_count
outbox_retry_total
```

## Tracing

Trace spans should show flow, not content.

Example trace:

```txt
ImportInspectRequest
  AdapterDetect
  SecretScan
  CostEstimate
  PolicyPrecheck
  InspectionPreviewCreated
```

Span attributes allowed:

- sourceType
- adapterId
- count
- riskClasses
- policyMode
- durationMs

Span attributes forbidden:

- raw text
- prompt
- LLM response
- secret
- full filename if sensitive

## Alerts

### Critical Alerts

Alert immediately:

- secret stored after scan
- export package includes raw when includeRaw=false
- LLM send executed with policyMode=deny
- hidden/sealed/deleted returned in search
- vector result for deleted target
- export URL accessed after expiry
- admin raw access without break-glass

### High Alerts

- unusual spike in policy deny
- repeated huge imports
- export failures with redaction errors
- deletion propagation lag too high
- outbox backlog for deletion events
- secret scan positives spike

### Medium Alerts

- adapter parse failure spike
- cost estimate mismatch spike
- unknown source increase
- partial import increase

## Dashboards

### Safety Dashboard

- policy denies by action
- secret detections
- LLM denied sends
- export redactions
- unsafe raw blocks

### Deletion Dashboard

- delete requests
- tombstones created
- search/vector propagation lag
- re-import skips

### Import Dashboard

- source types
- adapter success/failure
- partial imports
- blocked imports

### Cost Dashboard

- cost class distribution
- LLM/embedding usage
- hard stops
- large job confirmations

### Incident Dashboard

- open incidents
- severity
- affected users estimate
- containment status

## Privacy-preserving User IDs

Use hash or internal ID in logs.

Do not log email/name by default.

```ts
type ObservabilityUserRef = {
  userIdHash: string;
  region?: string;
  plan?: string;
};
```

## Sampling

For high-volume logs:

- sample low-risk success logs
- never sample critical security failures
- keep metrics aggregated
- keep audit logs complete for sensitive actions

## Debug Mode

Debug mode must not dump raw content.

Bad:

```txt
DEBUG prompt=<full memory text>
```

Good:

```txt
DEBUG llm_input_bytes=1200 riskClasses=[owner_private] redactions=3
```

## Observability + Incident Response

Metrics should trigger incident playbooks.

Examples:

- `llm_send_denied_total` spike -> investigate prompt injection/source issue
- `export_raw_denied_total` spike -> check UI copy pushing raw export
- `reimport_tombstone_skipped_total` spike -> user repeatedly importing deleted source
- `hidden_search_result_total > 0` -> critical incident

## Tests

Required tests:

1. logger redacts raw text field.
2. logger rejects secret values.
3. LLM span has no prompt body.
4. export metric has counts only.
5. policy denial event has reason codes only.
6. critical alert fires on denied LLM send success.
7. search test fires alert when sealed result returned.
8. debug mode contains no raw.
9. audit log and observability log are distinct.
10. user email not logged by default.

## MVP Implementation

MVP can start simple:

- structured logger
- safe fields allowlist
- policy deny metrics
- deletion propagation metrics
- export redaction counts
- test that logs do not contain raw

Do not need immediately:

- full distributed tracing
- Prometheus/Grafana setup
- complex anomaly detection

## Acceptance Criteria

- Observability fields allowlist exists.
- raw content never logged.
- key safety metrics defined.
- critical alert conditions documented.
- incident playbook links to metrics.
- tests prevent prompt/raw/secret logging.
- audit logs are separated from operational logs.

## 結論

Observability は、Memory OS を安全に運用するための目である。

ただしその目は、ユーザーの人生の中身を覗いてはいけない。

内容ではなく、状態・件数・risk・policy・lifecycleを観測することで、信頼を守りながら運用する。
