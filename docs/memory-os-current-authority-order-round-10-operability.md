# Memory OS Current Authority Order — Round 10 Operability

最終更新: 2026-07-25

Status: CURRENT PRODUCTION-READINESS AUTHORITY

## Current verdict

```txt
product direction:
Capture / Import first

security vertical slice:
STRONG BUT PARTIAL

production operability:
NOT PROVEN

production decision:
NO_GO

priority:
correctness, recovery, observability, capacity, compatibility and restore evidence
before additional product breadth
```

The repository must not claim production readiness from design quality, local tests, CI health or component-level recovery alone. A capability moves to READY only when executable evidence exists at a named repository path and the operability validator accepts it.

## Two kinds of authority

Do not mix implementation truth with readiness judgement.

- **Implementation truth:** current code, migrations, executable tests and exact-HEAD runtime evidence decide what exists.
- **Readiness judgement:** this Round 10 authority, the machine-readable operability status and the audit decide whether that implementation is sufficient for production.

A checkpoint is historical evidence. It can explain a change, but it cannot override newer code or tests.

## Authority order

Conflicts are resolved from top to bottom:

1. `docs/memory-os-current-authority-order-round-10-operability.md` for production-readiness judgement;
2. `contracts/operations/production-operability-status.json` for machine-readable gate state;
3. `docs/memory-os-production-operability-audit-2026-07-24.md` for detailed gate interpretation;
4. current code, migrations and executable tests for implementation facts;
5. exact-HEAD local/runtime/remote evidence whose scope is explicitly recorded;
6. `docs/memory-os-current-authority-order-round-9-security.md` for subordinate security architecture decisions;
7. current roadmap and newest applicable implementation checkpoint;
8. historical progress and handoff documents.

Historical documents never override newer code or a newer narrower verdict. A green workflow at an older commit never proves a newer HEAD.

## Binding distinctions

- transaction rollback is not migration rollback
- object versioning is not backup
- fault injection is not chaos completion
- CI green is not production observability
- authentication is not rate limiting
- race and fuzz tests are not load tests
- a restartable worker is not an incident-recovery procedure
- version pinning is not a compatibility policy
- documentation without executable evidence is not completion
- a checkpoint statement is not stronger than current code and tests
- a fake external dependency proves integration behavior, not production credentials or provider behavior

## Mandatory production gates

| Gate | Area | Release condition |
|---|---|---|
| OPS-P0-001 | Migration rollback | Expand/contract policy, production-shaped rehearsal, recovery decision procedure and mixed-version proof |
| OPS-P0-002 | Incident recovery | Reviewed runbooks, severity/ownership model and completed recovery drill |
| OPS-P0-003 | Observability | Structured event contract, correlation identifiers, privacy checks, retention and real alert routing |
| OPS-P0-004 | Metrics | Bounded runtime metrics, SLI/SLO, dashboards, thresholds and error-budget policy |
| OPS-P0-005 | Rate limiting | Endpoint-specific controls, stable 429 contract, concurrency/bypass tests and load calibration |
| OPS-P0-006 | Load testing | Production-shaped sustained/burst harness, percentile and saturation report, integrity checks and post-burst recovery proof |
| OPS-P0-007 | Backup restore | PostgreSQL backup/PITR, independent object retention, RPO/RTO and successful isolated restore rehearsal |
| OPS-P0-008 | Version compatibility | Supported-version matrix, API/schema rules, old/new mixed-version tests and upgrade/downgrade order |
| OPS-P0-009 | Critical failure drills | API, database, object-store and parser interruption drills proving security and durability invariants |

`OPS-P1-001` covers tracing. It remains P1 only while the deployable backend is diagnostically one process. It becomes P0 before independently deployed services or opaque asynchronous boundaries are introduced.

## Existing strengths

- FORCE RLS and scoped runtime roles;
- exact-hash idempotency and fail-closed duplicate handling;
- destructive update path removed and live-proven to change no row;
- Apple issuer/subject binding and replay controls;
- bounded digest-pinned parser supervision;
- checksum, drift and malformed-record rejection;
- durable spool publication and startup reconciliation;
- resumable leased deletion worker;
- live PostgreSQL, MinIO and HTTP integration evidence;
- explicit production `NO_GO`.

These are foundations. They do not close the production gates by themselves.

## Implementation priority

1. repair contradictions, stale status and validators;
2. introduce structured error/event contracts and privacy tests;
3. add request/job correlation and bounded metrics;
4. implement endpoint-specific rate limiting;
5. define migration and incident procedures before further schema expansion;
6. establish repeatable production-shaped load evidence;
7. configure and rehearse backup/restore;
8. publish compatibility policy and mixed-version tests;
9. execute critical failure drills;
10. re-audit every READY claim from repository evidence.

Feature work may proceed only when it does not bypass a higher-priority safety gate. New surfaces must add operating requirements to this same gate system rather than creating a parallel roadmap.

## Machine enforcement

Machine-readable source:

`contracts/operations/production-operability-status.json`

Detailed audit:

`docs/memory-os-production-operability-audit-2026-07-24.md`

CI validators:

- `scripts/validate-memory-os-operability.py`
- `scripts/validate-memory-os-entry-docs.py`

The validators must fail when:

- a mandatory gate disappears;
- a P0 stops being blocking;
- READY retains missing evidence;
- READY lacks repository evidence references;
- a referenced evidence file does not exist;
- production is marked GO while a P0 is incomplete;
- authority documents disagree;
- a binding distinction is removed;
- root entry documents point to an obsolete authority or repeat a known stale implementation claim.

## Completion rule

Production may change from `NO_GO` to `GO` only in a dedicated reviewed checkpoint that moves every OPS-P0 gate to READY, removes every missing-evidence entry, provides repository evidence paths, passes all validators and integration suites, records remote workflow results for the same HEAD, and includes independent review of rollback, restore, limiting, privacy-safe telemetry and failure recovery.

Until then, the target is to make every remaining weakness explicit, executable, reviewable and impossible to silently regress.
