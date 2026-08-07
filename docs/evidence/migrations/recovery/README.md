# Migration recovery artifact evidence

This directory contains append-only, privacy-safe **local/non-production** result documents for exact migration recovery-artifact rehearsals.

A result may be referenced by a migration rehearsal record only when all of the following are true:

- the file name matches the migration rehearsal run ID;
- the document schema is `memory-os-local-migration-recovery-artifact.v1`;
- the recorded recovery artifact is identified only by SHA-256 digest and byte count;
- that exact artifact was restored into a separate local PostgreSQL database;
- the pre-migration surface was observed after restore;
- the migration under test was reapplied successfully;
- the canonical SQL integration suite passed after recovery;
- `productionTraffic`, `productionCredentials`, and `productionEvidence` are all `false`.

Raw database URLs, hostnames, credentials, dump bytes, account/session identifiers, and user data must never be committed here.

These files do **not** prove PITR, physical backup, production-equivalent restore, destructive rollback safety, RPO/RTO, or Production readiness.
