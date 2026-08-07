# Human Incident Tabletop Evidence

This directory is the append-only evidence ledger for completed **human-led** Memory OS incident tabletop exercises.

Rules:

- One accepted completion per required scenario: `IR-DRILL-001.json` through `IR-DRILL-006.json`.
- Use `scripts/register-memory-os-incident-human-tabletop.py`; do not overwrite an accepted scenario record.
- Planned records and automated control exercises are not human attendance evidence.
- The completed record must preserve the canonical planned severity, objective, scope, injects, assumptions, and safety constraints.
- Operational participants use pseudonymous `actor_*` references. Required command roles and severity-specific closure approvals must be explicit.
- Every planned inject must have an observed response; severity, containment, and recovery decisions plus independent verification remain mandatory under the canonical tabletop contract.
- Human tabletop evidence is not a production recovery drill, paging configuration, external contact ownership, or production readiness.
