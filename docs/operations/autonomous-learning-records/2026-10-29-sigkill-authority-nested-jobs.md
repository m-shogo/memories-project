# Supplemental OPS learning — deletion SIGKILL authority nested jobs (2026-10-29)

Append-only supplemental learning only, not canonical learning, production deletion/recovery evidence, backup/restore, RPO/RTO/skew, reviewed drill, credentials, traffic, readiness or human promotion.

## Material static gap / executable recurrence prevention

- **Symptom:** SIGKILL authority diagnostic source-negative CI pinned reviewed Git blobs, exact triggers, root permissions and redacted runtime diagnostics but lacked independent nested job mapping/permission-shadow proof. Static CI-admission gap only, not observed unauthorized production SIGKILL evidence.
- **Observed evidence:** Publisher blob `0906a248b52297e836738d0c6ff00daaf49fed7d` has `validate-pr` (PR base so, read, timeout 10) and `reconcile` (push/dispatch so, write, timeout 10); independent blob `18e047a7bbc8f5e7335eefa5f8931610f8522306` has `source-negative` (read, timeout 5).
- **Verified root cause:** Root permissions and full Git blob SHA do not independently prove unique nested job identity, PR base restriction, publisher write isolation or fail-closed YAML shadow handling.
- **Failed approach:** Relying on root permission and whole-source digest alone for nested job semantic evidence, or reusing a mismatched job schema.
- **Correction / executable recurrence guard:** [Code `d6fe0451`](https://github.com/m-shogo/memories-project/commit/d6fe0451590128455ff4c8fbe6a6a98a56ae0c2d) reuses the CI-proven three-job guard after verifying the reviewed PR-base and publisher/independent job topology. Adds **36 exact-diagnostic in-memory negatives** for duplicate/quoted/spaced mappings, condition/permission/runner/timeout/steps shadows, continuation override and direct/spaced/quoted permission mutations.
- **Retry condition:** Revisit only if reviewed job topology, permissions, PR base scope or a demonstrated bypass changes. Do not retry unchanged PostgreSQL client-major, MinIO HTTP 401, canonical-learning transport or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Deletion SIGKILL Diagnostic Source Negative #40794466082](https://github.com/m-shogo/memories-project/actions/runs/40794466082) completed **SUCCESS** on exact source `d6fe0451`. Logs confirm 36 new nested job negatives, 12 YAML root/permission negatives, 26 trigger omissions, 16 additions, four shortened inventories, three event topology negatives, 12 runtime identity cases, 24 source mutations and seven diagnostic-writer cases passing. Output states `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed; mutations were in-memory. Reviewed workflows, production contracts, registries, evidence, credentials, traffic, readiness and human promotion were untouched.
- **Reusable mechanism:** Pin exact reviewed PR-read, publisher-write and independent-read jobs and require expected semantic diagnostics before relying on Git blob equality.
- **Protected-authority check:** Production status blob `3ab8092c7e3fec2b48d62fb2728f024151f610c5` remains `productionDecision=NO_GO`; canonical learning blob `b809c69dda5d788245abd2a79b34c6e8c1d6c628` and learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No production-equivalent generation, approved objective, executable reviewed drill, complete typed eight-domain non-resurrection evidence, independent final review or human promotion is asserted.
- **Next safe target:** Audit remaining deletion authority source-negative jobs for distinct inherited versus explicit permissions, without altering OPS-P0-007 or retrying unchanged external blockers.
