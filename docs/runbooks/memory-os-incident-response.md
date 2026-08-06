# Memory OS Incident Response and Recovery Runbook

Status: **FOUNDATION — NOT PRODUCTION-PROVEN**  
Authority: `contracts/operations/incident-response-contract.v1.json`  
Production decision remains: **NO_GO**

## Purpose

This runbook controls response to security, privacy, integrity, availability and recovery incidents affecting Memory OS. Its first priority is protecting user data, tenant isolation and deletion semantics. Restoring a green health check is not sufficient when the trustworthiness of stored memory, authentication authority or object bindings is uncertain.

The operating sequence is:

```text
DETECT AND DECLARE
→ TRIAGE AND SCOPE
→ CONTAIN
→ PRESERVE AND DIAGNOSE
→ RECOVER
→ VERIFY
→ CLOSE AND FOLLOW UP
```

A transaction rollback, process restart, queue retry or component recovery does **not** prove full incident recovery. Closure requires independent verification of the affected security and integrity invariants.

## Immediate rules

- Prefer fail-closed or read-only behavior when tenant authority, data integrity or exact object identity is uncertain.
- Freeze destructive automation for credible SEV0 or SEV1 integrity events.
- Do not delete ambiguous database, object, spool or parser state to clear an alert.
- Preserve evidence before applying a mutation that could change the diagnosis.
- Record exact source commit, deployment version, migration state and dependency identity without copying secrets into notes.
- Separate confirmed facts, known prior conditions, hypotheses and opinion.
- Use incident command for tradeoffs. Individual operators do not improvise destructive recovery.
- Do not promise recovery, root cause or affected scope before evidence supports the claim.

## Severity model

### SEV0 — Critical security or integrity

Use SEV0 for confirmed or credible:

- cross-tenant visibility;
- unauthorized account/session authority;
- destructive or unaccounted memory mutation;
- deleted data or expired/revoked sessions reappearing after restore;
- credential, signing-key or superuser compromise;
- evidence that production data cannot currently be trusted.

Required posture:

- acknowledge target: 5 minutes;
- assign incident commander and security/privacy lead;
- freeze relevant changes and destructive workers;
- fail closed or isolate affected surfaces;
- assess user communication and privacy/legal escalation;
- closure approval by incident commander, security/privacy lead and system owner.

### SEV1 — Major availability or data risk

Use SEV1 for:

- widespread Import API, PostgreSQL or object-store outage;
- bad migration/backfill with possible integrity impact;
- unbounded queue or resource exhaustion;
- material account deletion/export unavailability;
- repeated internal failure where partial state is possible.

Required posture:

- acknowledge target: 15 minutes;
- assign incident commander;
- stop affected writes when partial mutation cannot be excluded;
- preserve reads only when safe;
- assess user communication;
- closure approval by incident commander and system owner.

### SEV2 — Degraded or limited scope

Use SEV2 for bounded partial degradation without a confirmed integrity or security boundary violation. Acknowledge target: 60 minutes. Limit scope, observe and repair.

Escalate to SEV1 or SEV0 immediately if impact expands or data trust becomes uncertain.

### SEV3 — Minor or internal only

Use SEV3 for non-user-facing defects, documentation/test failures or isolated transients with no integrity/security concern. Acknowledge target: 240 minutes.

A failed CI check is SEV3 unless it exposes an untested production risk or indicates deployed impact.

## Roles

### Incident commander

- declares severity and scope;
- assigns roles;
- approves containment/recovery phase transitions;
- owns one decision log;
- escalates uncertainty;
- approves closure after verification.

### Operations lead

- executes approved actions;
- records exact commands, targets and results;
- stops on unclassified state;
- never places credentials or raw personal data in the record.

### Security/privacy lead

- assesses confidentiality, unauthorized authority and evidence-preservation needs;
- owns credential rotation/access restriction decisions;
- engages legal/privacy review when the confirmed facts require it.

### System owner

- states expected invariants and dependency boundaries;
- defines integrity checks and safe recovery choices;
- accepts remediation work.

### Communications lead

- prepares fact-only internal/user updates;
- records timestamp and next review point;
- avoids unsupported scope, root-cause or recovery claims.

### Scribe

- maintains the append-only timeline and decision/evidence index;
- separates facts, prior-known conditions, inference and opinion;
- excludes secrets, bearer tokens and unnecessary personal content.

For a small non-production event, one person may hold multiple roles. SEV0 and production SEV1 require an explicit incident commander; SEV0 also requires a distinct security/privacy decision owner.

## Mandatory stop conditions

Stop the proposed operation and escalate when:

- the target environment or database identity is ambiguous;
- exact source commit/deployment version is unknown;
- the action requires an unreviewed destructive mutation;
- cross-tenant visibility or authentication authority is uncertain;
- the action would delete or overwrite incident evidence;
- a restore/rollback could violate deletion or expired-session semantics;
- required incident-command/security roles are unassigned;
- the command or note would expose a secret or unrestricted personal content.

## Phase 1 — Detect and declare

Create an incident record immediately. Do not wait for root cause.

Minimum declaration:

```json
{
  "incidentId": "inc_...",
  "declaredAt": "RFC3339",
  "detectedBy": "privacy-safe source",
  "severity": "SEV0|SEV1|SEV2|SEV3",
  "incidentCommander": "named role or UNASSIGNED",
  "affectedSurfaces": ["unknown-or-known"],
  "confirmedFacts": ["first observed symptom"],
  "knownPriorConditions": [],
  "hypotheses": [],
  "openRisks": []
}
```

Immediate declaration checks:

- Is tenant isolation uncertain?
- Is authentication/session authority uncertain?
- Could a write, migration, worker or deletion job worsen the event?
- Is evidence about to expire or be overwritten?
- Is this a restored system where deletion/session non-resurrection must be checked?

For credible SEV0/SEV1 integrity events, pause affected writes, migrations, backfills and cleanup workers through reviewed reversible controls.

## Phase 2 — Triage and scope

Record separately:

### Confirmed facts

Facts directly supported by logs, metrics, database/object metadata, exact responses or reproducible tests.

### Known prior conditions

Issues or limitations that existed before this event. Do not present them as newly caused impact.

### Hypotheses

Possible explanations and what evidence would confirm/refute each.

### Opinion or recommendation

Operational judgment based on the facts and uncertainty.

Scope dimensions:

- first/last known affected timestamp;
- endpoint, worker, migration, parser or dependency;
- tenant/account count without exposing identities unnecessarily;
- confidentiality, integrity, availability, authentication, deletion and export impact;
- deployed source SHA and configuration generation;
- PostgreSQL migration sequence;
- object-store bucket/version state;
- session/replay/account-control state;
- queues, leases and in-progress work.

Do not use absence of a log line as proof of no impact unless the logging boundary is independently known to be complete.

## Phase 3 — Contain

Choose the smallest reversible containment that protects invariants.

### Authority or cross-tenant concern

- fail closed on affected authenticated surfaces;
- revoke or fence affected sessions/accounts where justified;
- preserve account/session/replay rows before cleanup;
- verify runtime role and `FORCE RLS` state;
- do not substitute a privileged connection for normal runtime traffic.

### Database concern

- stop affected writes/backfills/migrations;
- preserve read-only access only if it cannot expose inconsistent/cross-tenant state;
- inspect locks, failed transactions, replication/recovery state;
- use the migration recovery runbook for committed schema changes;
- do not treat transaction rollback as service/data recovery.

### Object-store concern

- refuse parsing/apply when exact version, checksum or metadata cannot be verified;
- preserve ambiguous versions and authorization rows;
- stop lifecycle/cleanup actions that could erase evidence;
- never accept “latest object” as a substitute for the bound version.

### Parser concern

- stop the affected worker artifact/digest;
- quarantine source object and spool state;
- verify the worker had no credentials/network authority;
- assess host/process-group/resource impact before restart.

### Deletion/restore concern

- fence affected account access;
- stop cleanup that could obscure what reappeared;
- verify account epoch, deletion state, sessions, memory items, previews and object versions;
- keep restored environment isolated until non-resurrection checks pass.

Containment verification:

- active impact stopped or bounded;
- no new 2xx mutations on the affected path if fail-closed was intended;
- RLS/authority boundary still intact;
- evidence preserved;
- containment did not create a broader outage or irreversible cleanup.

## Phase 4 — Preserve and diagnose

Evidence index should reference, not copy unnecessarily:

- exact Git commit/deployment identifier;
- migration sequence and checksums;
- privacy-safe structured event ranges;
- bounded-cardinality metric snapshots;
- PostgreSQL identity and metadata queries;
- object key/version/checksum metadata;
- request/correlation IDs;
- spool/manifest hashes;
- parser artifact digest and limits;
- approved screenshots or exported logs with secret/PII review.

Evidence protections:

- append-only incident timeline;
- no password, bearer token, private key, raw database URL or unrestricted personal content;
- record who captured evidence and when;
- preserve original timestamps;
- do not edit past decisions; append correction entries.

Diagnosis requires at least one independent check of the leading hypothesis. A convenient story is not root cause.

## Phase 5 — Recover

State the recovery decision explicitly:

- application rollback against a compatible expanded schema;
- forward-fix;
- idempotent replay/resume;
- isolated restore;
- compensating action for external side effects;
- credential rotation;
- dependency failover;
- controlled worker restart.

Recovery rules:

- smallest reversible step first;
- restoration of service and destructive cleanup are separate;
- database rollback does not reverse object writes, notifications or credentials;
- exact idempotency/accounting must be checked before replay;
- destructive down migration is never assumed safe;
- restore remains isolated until deletion/session non-resurrection passes;
- do not “repair” canonical records in place through unsupported update paths.

Record before execution:

- target/source identifiers;
- expected result;
- abort condition;
- rollback/forward-fix path;
- owner and reviewer;
- evidence that will prove success.

## Phase 6 — Verify

Verification is independent from the person who made the recovery change when practical.

Required checks selected by incident type:

### Tenant and authority

- runtime deployment role, `NOBYPASSRLS`/`NOINHERIT` expectations;
- cross-tenant negative read/write tests;
- bearer-session expiry/revocation;
- Apple issuer+subject binding and replay rules;
- no raw token/identity leakage in evidence.

### Preview and Apply

- exact Preview hash binding;
- accepted/rejected counts;
- one complete Apply accounting result;
- idempotent replay returns original result;
- no destructive `update_safe_fields` path;
- no partial memory materialization.

### Upload and object store

- exact object key/version/checksum/content metadata;
- no unverified object enters parsing;
- authorization state and scan enqueue accounting;
- retained evidence versions remain accessible where required.

### Deletion and restore

- account remains fenced/deleted as intended;
- deleted memory/previews/sessions do not reappear;
- expired/revoked sessions remain unusable;
- object erasure/retention semantics are understood;
- isolated restored environment cannot serve normal users.

### Availability and capacity

- error/status classes;
- p50/p95/p99 latency where measured;
- queue/lease/backlog trend;
- goroutine/heap/RSS trend;
- dependency health;
- no new incident-specific alert.

The initiating failure must have a negative test or reproducible verification. “Looks normal” is not closure evidence.

## Phase 7 — Communicate

SEV0 and SEV1 updates include:

- timestamp;
- current confirmed impact;
- what is contained/not contained;
- what remains unknown;
- actions underway;
- next review/update point.

Do not say:

- “no data was affected” without evidence;
- “fully recovered” before verification;
- “root cause fixed” when only the symptom stopped;
- “all users” or “only one user” without supported scope;
- marketing reassurance that obscures risk.

No pager, status page, external contact tree or user-notification channel is configured by this repository yet. Channel ownership remains deployment work.

## Phase 8 — Close and follow up

Closure requires:

- final severity and supported impact scope;
- supported root cause, or explicit statement that root cause remains unknown;
- containment/recovery decisions recorded;
- independent verification passed;
- no unresolved critical safety condition;
- required approvals for the severity;
- remediation owners and target dates;
- append-only evidence/timeline preserved.

SEV0 and SEV1 require a blameless review. The review must identify system/control changes, not merely operator reminders.

Possible remediation classes:

- code/test fix;
- fail-closed validator;
- runbook correction;
- access/credential control;
- observability/alert routing;
- capacity or timeout correction;
- migration/backfill design;
- restore/non-resurrection proof;
- mixed-version compatibility proof;
- dependency isolation.

## Tabletop scenarios

The required plan covers:

1. cross-tenant Preview visibility or forged authority;
2. PostgreSQL unavailable during Preview/Apply;
3. MinIO/object-store outage or exact-version mismatch;
4. bad migration or mixed-version incompatibility;
5. restore causes deleted data or expired sessions to reappear;
6. parser resource escape/untrusted payload compromise.

A completed tabletop record must include participants, timestamps, decisions, missing information, elapsed response milestones, verification plan and remediation items. This runbook defines the plan but does not claim that a tabletop or production drill has been completed.

## Current limitations

The repository still lacks:

- configured pager/alert routing and on-call ownership;
- external legal/privacy/user communication contact tree;
- a completed tabletop record;
- production-shaped recovery drill evidence;
- isolated restore rehearsal linked to this response process;
- independent review of all incident controls.

Therefore `OPS-P0-002` remains `PARTIAL` and production remains `NO_GO`.
