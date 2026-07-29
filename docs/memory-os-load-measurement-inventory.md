# Memory OS — Load-Test Measurement Inventory (OPS-P0-006 Phase 1)

This inventory records, before load testing begins, which metrics are actually
**emitted from a real call site** versus only **defined in the registry**. A
metric that is defined but never emitted cannot be measured; treating it as
observable would be a measurement blind spot. The load-test scenarios in this
checkpoint (`contracts/operations/load-test-scenario-contract.v1.json`) drive
only the boundaries classified `DEFINED_AND_EMITTED` below.

As of commit that adds Apple/DB dependency instrumentation.

## Classification

| Metric | Component | Classification | Emitting call site |
|---|---|---|---|
| `memory_os_http_requests_total` | http | DEFINED_AND_EMITTED | `internal/httpserver/observability.go` |
| `memory_os_http_request_duration_seconds` | http | DEFINED_AND_EMITTED | `internal/httpserver/observability.go` |
| `memory_os_http_in_flight` | http | DEFINED_AND_EMITTED | `internal/httpserver/observability.go` |
| `memory_os_http_panics_total` | http | DEFINED_AND_EMITTED | `internal/httpserver/observability.go` |
| `memory_os_http_request_body_rejected_total` | http | DEFINED_NOT_EMITTED | no call site yet (body-limit path records via 4xx status only) |
| `memory_os_rate_limit_decisions_total` | rate_limit | DEFINED_AND_EMITTED | `internal/httpserver/ratelimit.go` |
| `memory_os_rate_limit_decision_duration_seconds` | rate_limit | DEFINED_AND_EMITTED | `internal/httpserver/ratelimit.go` |
| `memory_os_rate_limit_store_failures_total` | rate_limit | DEFINED_AND_EMITTED | `internal/httpserver/ratelimit.go` |
| `memory_os_rate_limit_active_keys` | rate_limit | DEFINED_NOT_EMITTED | limiter exposes no active-key count yet; not required for this checkpoint |
| `memory_os_apple_exchange_total` | apple_auth | DEFINED_AND_EMITTED | `internal/appleauth/metered.go` (MeteredLoginService) |
| `memory_os_apple_exchange_duration_seconds` | apple_auth | DEFINED_AND_EMITTED | `internal/appleauth/metered.go` |
| `memory_os_apple_replay_rejections_total` | apple_auth | DEFINED_AND_EMITTED | `internal/appleauth/metered.go` |
| `memory_os_session_issuance_total` | apple_auth | DEFINED_AND_EMITTED | `internal/appleauth/metered.go` |
| `memory_os_db_operations_total` | db | DEFINED_AND_EMITTED (Apple + request seams) | `internal/appleauth/metered.go` — `apple_identity_upsert`, `apple_replay_consume`, `session_insert`; `internal/servicemetrics/servicemetrics.go` — `preview_read`, `apply_transaction` |
| `memory_os_db_operation_duration_seconds` | db | DEFINED_AND_EMITTED (Apple + request seams) | same |
| `memory_os_db_failures_total` | db | DEFINED_AND_EMITTED (Apple + request seams) | same |
| DB ops `resolve_session`, `begin_deletion`, `sweep`, `provision_identity` | db | DEFINED_NOT_EMITTED | not on the load-critical paths exercised here |
| `memory_os_object_store_operations_total` (+ duration, failures) | object_store | DEFINED_NOT_EMITTED → NOT_REQUIRED_FOR_THIS_LOAD_CHECKPOINT | object-store paths (presign/head/erase) are not in the steady/burst Apple + rate-limit scenarios |
| `memory_os_import_operations_total` (+ duration, items, failures) | import | DEFINED_NOT_EMITTED → NOT_REQUIRED_FOR_THIS_LOAD_CHECKPOINT | the import/parse path is not driven by this checkpoint's scenarios |
| `memory_os_deletion_jobs_total` (+ duration) | deletion_worker | DEFINED_AND_EMITTED | `cmd/import-api-server/main.go` (deletion runtime) |
| `memory_os_deletion_backlog` | deletion_worker | DEFINED_AND_EMITTED | same |
| `memory_os_deletion_retries_total` | deletion_worker | DEFINED_AND_EMITTED | same |
| `memory_os_deletion_terminal_failures_total` | deletion_worker | DEFINED_AND_EMITTED | same |

## Consequences for this checkpoint

- Apple sign-in (HTTP + Apple exchange + session issuance + replay + the three
  Apple database seams), the authenticated preview-read and apply request
  boundaries, and rate limiting are observable and are the load targets driven
  here.
- Object storage and import remain `DEFINED_NOT_EMITTED` and are **not** claimed
  as load-measured. Preview read and apply are now emitted, but only exercised
  under **MOCK** load (a fixed session resolver and fake DB-backed services); a
  live-PostgreSQL/object-store load run against real queries is still missing,
  which is one reason `OPS-P0-004` and `OPS-P0-006` stay `PARTIAL`.
- Every number produced by this checkpoint comes from an in-process server over
  **mocked** Apple and **in-memory** stores (`dependencyMode: MOCK`). These are
  local, non-production figures. No production capacity is claimed.
