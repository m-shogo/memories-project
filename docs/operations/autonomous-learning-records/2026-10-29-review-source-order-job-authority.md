# Supplemental OPS learning — recovery review source-order job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, human review approval, production evidence, backup/restore, RPO/RTO/skew, recovery generation/objective/drill authority, typed eight-domain coverage, credentials, traffic, readiness or promotion.

## Material gap / recurrence prevention

- **Symptom:** The human recovery review source-order CI source validator checked exact event/root/root-permission YAML and reviewed Git blob but did not independently reject duplicate job mappings or job-scoped write permission shadows. Static coverage gap, not an observed review or production failure.
- **Observed evidence:** Reviewed workflow blob `ac458bffc479d890505dfa6a82bd0c799f50e4bc` has one `validate` job inheriting root `contents: read`, with `runs-on: ubuntu-latest`, `timeout-minutes: 8`, `steps`. Previous YAML negative inventory had nine cases.
- **Verified root cause / failed approach:** Root read-only permission and complete source identity do not independently prove effective nested job identity or absence of job-level privilege escalation. Generic blob rejection does not provide a precise semantic diagnostic.
- **Correction / executable guard:** [9dcb82f2](https://github.com/m-shogo/memories-project/commit/9dcb82f2cf5bf2d71d6e86ac2e09e7ce672eb3a4) pins the sole job mapping and allowed job-key inventory. Six new in-memory exact-diagnostic negatives reject duplicate/spaced/quoted job mappings and plain/spaced/quoted job-level `contents: write` shadows; YAML negatives rise from nine to fifteen.
- **Retry condition:** Reassess only after independently reviewed job topology/permission changes or a demonstrated bypass; do not retry unchanged canonical learning transfer, supplemental workflow-write permission, MinIO 401 or human approval blockers.

## Material success / protected authority

- **Outcome/evidence:** [Backup Restore Review Source Order #40771290641](https://github.com/m-shogo/memories-project/actions/runs/40771290641) completed SUCCESS on exact source `9dcb82f2cf5bf2d71d6e86ac2e09e7ce672eb3a4`. Job log confirms fifteen YAML exact-diagnostic negatives. Compare `0c221513` → `9dcb82f2` changed only the existing CI-reachable validator (+34/-2).
- **Why safe:** Reviewed workflow, generation/objective/drill/evidence authorities, credentials, traffic, readiness and separate human promotion were untouched; mutation probes are synthetic.
- **Reusable mechanism:** Bind unique job ID and complete job-key inventory independently of root YAML and Git blob; assert intended rejection diagnostics for job/permission shadows.
- **Protected-authority check:** Learning contract Git blob remains `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`. Production status remains `NO_GO`; no registered or semantically eligible generation, approved objective, executable reviewed drill, complete typed eight-domain record, final candidate or human promotion was created.
- **Next safe target:** Audit read-only recovery review source-order CI for job mapping/permission shadows, keeping human review authority separate from automatic CI.
