# Supplemental OPS learning — readonly recovery review source-order job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production evidence, backup/restore, RPO/RTO/skew, human review or promotion authority, recovery generation/objective/drill, typed eight-domain coverage, credentials, traffic or readiness.

## Material gap / executable recurrence prevention

- **Symptom:** The read-only review source-order workflow validator pinned exact YAML event/root/root-permission semantics and complete Git blob but did not independently reject duplicate job mappings or job-level permission shadows. This was a static guard gap, not an observed recovery or production incident.
- **Observed evidence:** Reviewed workflow Git blob `68f2d2f0b505a3322e30673afc14e3d11e9f5616` contains one `validate` job inheriting root `contents: read`, with `runs-on: ubuntu-latest`, `timeout-minutes: 10`, `steps`. Previous YAML negative inventory had nine cases.
- **Verified root cause / failed approach:** Root read-only permissions and complete source digest do not independently establish unique effective job mapping or absence of job-level write escalation; generic SHA rejection does not prove the intended semantic diagnostic.
- **Correction / recurrence guard:** [2cdb4ae9](https://github.com/m-shogo/memories-project/commit/2cdb4ae9d68e7031d16723d429b8359fdb58dfe7) pins the sole job mapping and allowed job-key inventory, adding six exact-diagnostic synthetic negatives for duplicate/spaced/quoted job IDs and plain/spaced/quoted job-level `contents: write` shadows. YAML negatives increase from nine to fifteen.
- **Retry condition:** Reassess only after reviewed job topology/permission changes or a demonstrated bypass. Do not retry unchanged canonical-learning transfer, supplemental workflow-write permission, MinIO 401 or human promotion blockers.

## Material success / protected authority

- **Outcome/evidence:** [Backup Restore Review Source Order Readonly #40771512370](https://github.com/m-shogo/memories-project/actions/runs/40771512370) completed SUCCESS for exact source `2cdb4ae9d68e7031d16723d429b8359fdb58dfe7`. CI log confirms fifteen YAML exact-diagnostic negatives, twenty semantic and two blob-only source negatives. Compare `9783bfdc` → `2cdb4ae9` changed only the CI-reachable validator (+34/-2).
- **Why safe:** Reviewed workflow, production status, registries, recovery evidence, credentials, traffic and human promotion were untouched; all negative fixtures are synthetic.
- **Reusable mechanism:** Bind exact job mapping and allowed job-key inventory independently from root YAML and whole-source SHA, with expected semantic diagnostics for nested permission escalation.
- **Protected-authority check:** Learning contract blob remains `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`; production status remains `NO_GO`, environment generations and recovery evidence remain empty, and no approved objective, executable reviewed drill, complete typed eight-domain record, final candidate or human promotion was admitted.
- **Next safe target:** Audit environment generation reconcile CI job mapping and permissions, preserving strict OPS-P0-007 gates.
