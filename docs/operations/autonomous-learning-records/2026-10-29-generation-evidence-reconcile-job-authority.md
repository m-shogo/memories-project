# Supplemental OPS learning — generation evidence reconcile job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production evidence, generation-bound recovery proof, backup/restore, RPO/RTO/skew, reviewed drill, typed eight-domain evidence, credentials, traffic, readiness or human promotion.

## Material gap / recurrence prevention

- **Symptom:** Generation-evidence reconcile-negative CI source validator pinned reviewed event/root/root-permission YAML and complete Git blob but did not independently reject duplicate job mappings or job-level write permissions. Static validator gap, not observed production or restore failure.
- **Observed evidence:** Reviewed workflow has one `negative` job inheriting root `contents: read`, with `runs-on: ubuntu-latest`, `timeout-minutes: 5`, `steps`. Previous nine YAML negatives covered event/root/root-permission shadows only.
- **Verified root cause:** Root read-only permission and complete source identity do not independently prove effective job-level permission absence or job mapping uniqueness.
- **Failed approach:** Relying on whole-source blob mismatch or root permission as a specific job-scope semantic guard.
- **Correction / executable guard:** [2c7b99be](https://github.com/m-shogo/memories-project/commit/2c7b99beb5af0cf834e6e00b54492df8e18016d4) pins the sole job identity and allowed job-key inventory; six in-memory exact-diagnostic negatives cover duplicate/spaced/quoted job mappings and plain/spaced/quoted job-level write permissions. YAML negative count increased from nine to fifteen.
- **Retry condition:** Revisit only after reviewed job topology/permission changes or a demonstrated bypass; do not retry unchanged MinIO HTTP 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Generation Evidence Reconcile Negative #40763212475](https://github.com/m-shogo/memories-project/actions/runs/40763212475) completed **SUCCESS** on exact source `2c7b99beb5af0cf834e6e00b54492df8e18016d4`. Job log confirms fifteen exact-diagnostic YAML negatives, 54 trigger removals, eight additions, one shortened inventory, six branch-runtime cases, seventeen semantic source negatives and two complete-source/terminator negatives.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed; reviewed workflow, generation/objective, drill, evidence registries, credentials, traffic and human promotion were untouched.
- **Reusable mechanism:** Pin job mapping and all top-level job keys for inherited root read-only workflows; inject job and permission shadows and require their exact semantic failure diagnostics.
- **Protected-authority check:** Git tree comparison `567b3c31` → `2c7b99be` found only this validator changed and zero contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; source-negative CI never satisfies recovery evidence, readiness or promotion gates.
- **Next safe target:** Audit generation independent-review CI for job-level permission shadows, while keeping Full Admission Chain and human promotion separate.
