# Memory OS Production Operability Audit

Date: 2026-07-24
Status: AUTHORITATIVE SUPPLEMENT — PRODUCTION REMAINS NO-GO
Scope: `so` branch through the Apple code-exchange checkpoint

This document prevents implementation-level fault handling from being mistaken for production operability. It audits ten areas: migration rollback, incident recovery, observability, metrics, tracing, rate limiting, load testing, chaos testing, backup restore, and version compatibility.

Conflict rule: this document may narrow an older readiness claim, but it may not promote a capability beyond evidence. A later document may supersede it only by naming executable evidence and the exact commit that produced it.

## Executive verdict

| Area | Current state | Evidence that exists | Missing production evidence | Gate |
|---|---|---|---|---|
| Migration rollback | PARTIAL, NOT PRODUCTION-READY | Atomic transaction rollback; conflicting retry/full rollback tests; spool seal rollback boundary | Migration policy, backward-compatible rollout sequence, down/forward-fix decision rules, rehearsal against production-shaped data | P0 |
| Incident recovery procedure | PARTIAL FOUNDATIONS ONLY | Startup reconciliation; TTL cleanup; deletion worker lease/resume; fail-closed paths | Incident classification, command-level runbooks, ownership/escalation, communication, recovery verification, post-incident evidence | P0 |
| Observability | MINIMAL | Selected security-safe logs; deletion backlog count-only alert line | Structured event schema, correlation IDs, redaction contract, log retention/access, dashboards and alert routing | P0 |
| Metrics | NOT IMPLEMENTED AS AN OPERATING SYSTEM | Test assertions and status documents are not runtime metrics | SLI/SLO metrics, bounded-cardinality labels, queue/latency/error/saturation metrics, alert thresholds | P0 |
| Distributed tracing | NOT IMPLEMENTED | No trace propagation evidence | W3C trace context, request/job correlation across HTTP/DB/object storage/parser worker, sampling/redaction policy | P1 before multi-service production |
| Rate limiting | EXPLICITLY INCOMPLETE | Strict validation/authentication fail closed | Per-principal and per-IP limits, endpoint budgets, Retry-After behavior, storage-backed distributed policy, abuse tests | P0 |
| Load testing | NOT IMPLEMENTED | Unit, race, fuzz-smoke and live integration tests do not establish capacity | Workload model, sustained/burst tests, saturation limits, latency percentiles, leak/queue growth checks, capacity report | P0 |
| Chaos testing | COMPONENT FAULT INJECTION ONLY | Crash/checksum/drift/short-write/ENOSPC/cancellation/retry tests | System-level dependency loss, restart, network delay/reset, DB failover, object-store outage and recovery invariants | P1; selected failure drills are P0 |
| Backup restore | NOT IMPLEMENTED / NOT PROVEN | Versioned object-store behavior in MinIO is not a backup | PostgreSQL backup/PITR design, object version retention, encrypted backup handling, restore rehearsal, RPO/RTO evidence, deletion semantics | P0 |
| Version compatibility | PARTIAL PINNING, NO POLICY | Go 1.23 and PostgreSQL 16 test baselines; digest-pinned worker; schema/checksum validation | Supported-version matrix, API/schema compatibility rules, rolling upgrade order, downgrade behavior, client skew tests | P0 before external clients |

Overall operability verdict: **NO-GO**. The security vertical slice is increasingly strong, but production operability is not yet demonstrated.

## 1. Migration rollback

### What is already strong

- Database writes use atomic transactions and have live rollback evidence for conflicting or failed operations.
- Apply rejection is performed before destructive mutation and is live-proven to leave rows unchanged.
- Spool publication has an explicit rollback/durability-uncertain boundary.

### What this does not prove

These are operation rollback properties, not a production schema-migration lifecycle. There is no evidence yet for:

- whether migrations are strictly forward-only or support selected down migrations;
- expand/contract deployment for mixed application versions;
- lock-time and table-rewrite assessment;
- pre-deploy backup checkpoint and restore trigger;
- rollback versus forward-fix decision authority;
- migration rehearsal using production-shaped volume;
- failed-migration recovery after partial deployment.

### Binding requirement

Adopt forward-compatible expand/contract migrations by default. A migration is releasable only when it declares:

1. compatibility window;
2. expected locks and maximum tolerated lock duration;
3. data backfill strategy and resumability;
4. application rollout order;
5. rollback or forward-fix procedure;
6. backup/restore checkpoint;
7. executable rehearsal evidence.

Destructive contract steps must occur only after old readers/writers are proven absent.

## 2. Incident recovery procedure

Existing reconciliation and resumable workers are useful recovery mechanisms, but there is no operator-facing incident system.

Required runbooks:

- authentication or replay-store incident;
- PostgreSQL unavailable/corrupt/slow;
- object storage unavailable, version mismatch or checksum mismatch;
- parser worker crash, compromise suspicion or quarantine growth;
- deletion backlog stuck;
- migration failure;
- accidental release or compatibility regression;
- credential/key compromise.

Every runbook must contain detection signal, severity, immediate containment, safe commands, data-loss risk, recovery steps, verification queries, customer-impact decision, escalation owner and evidence location. Runbooks must never advise bypassing RLS, disabling integrity checks or deleting unexplained quarantine residue to make an alert disappear.

## 3. Observability

Current logs are insufficient for production diagnosis. Introduce a structured, privacy-minimizing event contract.

Mandatory fields where applicable:

- timestamp, service, version, environment;
- event name and severity;
- request ID, trace ID, job ID as opaque non-secret identifiers;
- account-scoped identifiers only as keyed digests or internal opaque IDs where operationally necessary;
- result class, stable error code and retryability;
- duration and bounded counts.

Forbidden fields:

- raw Apple authorization codes, nonce, client secrets or private keys;
- bearer/session tokens or token digests usable as authenticators;
- raw imported memory content;
- object credentials or signed URLs;
- unbounded parser payloads;
- email as an identity key.

A redaction test must fail CI when known secret-shaped fields are logged.

### Implementation status (2026-07-25)

Implemented and machine-verified, keeping OPS-P0-003 at PARTIAL rather than
READY:

- a structured, privacy-first event logger (`services/import-api/internal/obslog`)
  whose event type has no free-form message, error or map field, so a secret has
  no field to occupy; enums are closed and every string is length-bounded;
- request and correlation identifiers (`services/import-api/internal/reqid`) that
  reject or replace an untrusted inbound request ID and never reuse an account or
  Apple subject for correlation;
- an HTTP middleware emitting one request event per request with a
  low-cardinality route template, plus panic recovery and lifecycle events;
- redaction canary tests over the real server output, HTTP error responses and
  panic recovery;
- a machine-readable event contract, valid and negative fixtures, and a
  validator that fails on forbidden fields, secret-shaped names, unbounded
  fields, code drift between the contract and the Go implementation, and any
  attempt to mark OPS-P0-003 READY without retention and alert routing.

Still missing before READY, and the reason the gate stays PARTIAL: a configured
log retention and access policy, and real alert routing that carries the
structured events to an operator alerting system. Structured emission is not
alert delivery, and a logger is not a retention policy.

## 4. Metrics and SLOs

Tests are not runtime metrics. Define bounded-cardinality metrics before production.

Minimum metrics:

- HTTP request count, latency and response class by stable route template;
- authentication exchange success/rejection/retryable failure;
- upload issue/complete/revoke outcomes;
- import job age, queue depth, running count and terminal outcomes;
- parser duration, killed workers, output-limit and protocol failures;
- spool reconciliation classifications and quarantine count;
- PostgreSQL pool saturation, transaction duration and error class;
- object-store operation latency/error class;
- apply idempotent replay/conflict/rejection counts;
- deletion backlog age/count and completion latency.

Do not label metrics with account ID, job UUID, filename, URL, raw error text or adapter options.

Before launch, define measurable availability, latency and durability objectives plus alert thresholds and an error-budget policy. Values must be derived from observed load evidence, not guessed into this document.

## 5. Tracing

Tracing may be deferred while the system is a single-process development slice, but it becomes mandatory before production spans HTTP, PostgreSQL, object storage and parser workers.

Requirements:

- W3C Trace Context at HTTP boundaries;
- explicit trace/job correlation across worker frames without serializing memory content;
- spans for DB/object-store calls using operation names, never raw SQL/object keys containing user data;
- parent linkage for background deletion/import work;
- sampling and retention rules;
- proof that secrets and imported content do not enter attributes or events.

## 6. Rate limiting

Rate limiting is a P0 security and reliability gate, especially for Apple exchange, signed-upload issuance, upload completion, import creation, preview reads, apply and account deletion.

Required behavior:

- separate per-principal and coarse per-network controls;
- stricter unauthenticated authentication-exchange budget;
- endpoint-specific burst and sustained budgets;
- bounded request body before expensive work;
- stable 429 response with `Retry-After`;
- fail-safe behavior when the limiter store is degraded, documented per endpoint;
- no account-existence oracle through different limits or errors;
- tests for concurrency, clock boundaries, distributed instances and limiter bypass attempts.

Exact numeric limits remain deployment configuration and must be calibrated by load tests.

### Implementation status (2026-07-28)

Implemented and machine-verified, keeping OPS-P0-005 at PARTIAL rather than
READY:

- a token-bucket limiter (`services/import-api/internal/ratelimit`) with bounded
  memory, a key-cardinality cap, clock-rollback safety and concurrency-safe
  atomic consume;
- a whole-route global guard plus a per-network guard, keyed by an HMAC digest
  of the normalized client network (IPv4 /32, IPv6 /64) with an explicit
  trusted-proxy boundary — no raw IP is stored or logged, and an arbitrary
  X-Forwarded-For is never trusted;
- per-route-class failure modes: the public pre-auth Apple exchange fails closed
  with a strict local emergency fallback, other public routes fail closed, and
  health is exempt so readiness is not coupled to the limiter store;
- a stable `429 SEC_RATE_LIMITED` with a bounded `Retry-After` and no policy,
  key, network or bucket detail; a live-DB test proves a 429 creates no account,
  session, Apple identity or replay row;
- structured rate-limit observability events carrying no raw key or address;
- a machine-readable policy contract, negative fixtures and a validator that
  fails on forbidden key dimensions, unbounded capacity, missing failure modes,
  public fail-open, and Go/contract drift.

Still missing before READY, and the reason the gate stays PARTIAL: a
production-equivalent distributed (shared atomic) store — the in-memory store
protects one instance only — plus per-deployment trusted-proxy configuration,
load-calibrated limits, and a disable/rollback runbook. An in-memory limiter is
not distributed production enforcement.

## 7. Load testing

A green race/fuzz/integration suite does not establish capacity.

The load plan must cover:

- normal and burst Apple login exchange;
- signed upload issue/complete flow;
- concurrent imports with realistic candidate/rejection distributions;
- parser CPU/memory/output caps;
- preview read and apply replay/conflict behavior;
- account deletion while other work is in flight;
- large but contract-valid inputs near limits.

Report throughput, p50/p95/p99 latency, error rate, pool/CPU/memory/file-descriptor saturation, queue growth, recovery after burst and data-integrity assertions. A test is invalid if it bypasses runtime roles, RLS, real transaction boundaries or object-store verification used in production.

## 8. Chaos and failure drills

The repository already contains strong component-level adversarial tests. Call them fault-injection tests, not production chaos evidence.

Required drills before launch:

- kill API during an in-flight transaction;
- kill parser worker at every protocol phase;
- restart during spool publication/reconciliation;
- object-store timeout, checksum mismatch and version disappearance;
- PostgreSQL connection loss and primary restart/failover simulation;
- delayed/duplicated worker delivery and lease expiry;
- limiter/metrics/tracing backend degradation;
- partial deployment with old and new application versions.

Every drill must assert no unauthorized cross-account access, no silent mutation, no duplicate durable apply, no lost deletion fence and deterministic recovery or quarantine.

## 9. Backup restore

Versioning is not a backup and a backup is not proven until restored.

Required design and evidence:

- encrypted PostgreSQL backups with PITR/WAL retention;
- encrypted object-store version retention independent of application credentials;
- configuration and migration metadata required to interpret restored data;
- documented RPO/RTO targets approved before production;
- restore into an isolated environment;
- integrity checks for row ownership/epoch, preview completeness, object version/checksum bindings and session/replay safety;
- proof that account deletion obligations are preserved across backup retention and restore workflows;
- periodic restore rehearsal with timestamped evidence.

Restored sessions, authorization codes and replay records must not silently become valid beyond their intended lifetime.

## 10. Version compatibility

Current pinning protects reproducibility but does not define upgrade compatibility.

Create a compatibility matrix covering:

- Go toolchain and module baseline;
- PostgreSQL major/minor versions and extensions;
- object-store S3 behavior relied upon, including versioning/checksum semantics;
- parser-worker protocol version and digest transition;
- database schema version;
- HTTP API version and error-code stability;
- future iOS app versions versus server versions;
- import adapter/record schema versions.

Binding rules:

1. readers must reject unknown incompatible major versions;
2. additive minor fields require unknown-field policy to be explicit per boundary;
3. rolling deployment must support at least the declared old/new version window;
4. downgrade behavior must be documented and tested or explicitly prohibited;
5. migration contract steps wait until compatibility telemetry proves old clients/writers are outside the support window.

## Mandatory production-operability gates

Production remains NO-GO until all P0 rows below have executable evidence.

| Gate ID | Requirement | Required evidence |
|---|---|---|
| OPS-P0-001 | Migration lifecycle | expand/contract policy, migration linter/checklist, production-shaped rehearsal, recovery proof |
| OPS-P0-002 | Incident runbooks | reviewed command-level runbooks plus at least one tabletop/drill record |
| OPS-P0-003 | Structured observability | event/redaction contract, runtime implementation, secret-leak tests, real alert routing |
| OPS-P0-004 | Metrics/SLO | bounded metrics, dashboards, thresholds, SLO/error-budget document |
| OPS-P0-005 | Rate limiting | runtime limiter, distributed/concurrency/bypass tests, calibrated configuration |
| OPS-P0-006 | Load/capacity | repeatable harness and signed capacity report against production-shaped stack |
| OPS-P0-007 | Backup restore | backup configuration and successful isolated restore rehearsal with RPO/RTO evidence |
| OPS-P0-008 | Compatibility | supported-version matrix, mixed-version tests and upgrade/rollback order |
| OPS-P0-009 | Critical failure drills | DB/object-store/parser/API interruption drills with invariant verification |

Tracing is OPS-P1 only while deployment remains a single process, but becomes P0 before production uses independently deployed services or asynchronous hops that cannot be diagnosed with request/job correlation alone.

## Correct implementation order

1. Define stable error taxonomy, structured log schema and redaction tests.
2. Add bounded runtime metrics and request/job correlation IDs.
3. Implement endpoint-specific distributed rate limiting.
4. Write migration and incident runbooks before adding more production migrations.
5. Create production-shaped load harness and establish initial safe limits.
6. Implement backup/PITR/object-retention configuration and complete an isolated restore rehearsal.
7. Publish the version compatibility matrix and mixed-version tests.
8. Run critical failure drills; add tracing before service boundaries require it.
9. Re-audit this matrix from executable evidence. Only then may any operability row move to READY.

## Review conclusion

The repository is not careless: it already has unusually strong fail-closed contracts, live PostgreSQL/MinIO/HTTP proofs, transaction rollback tests, crash-residue reconciliation and resumable deletion behavior. The gap is that these component guarantees have not yet been assembled into an operator-controlled production system.

Therefore:

- do not reduce the existing security work;
- do not call current fault-injection tests “chaos complete”;
- do not call object versioning “backup complete”;
- do not call local/CI green “production observed”;
- do not call transaction rollback “migration rollback complete”;
- keep production at **NO-GO** until OPS-P0-001 through OPS-P0-009 have executable evidence.
