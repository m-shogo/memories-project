# Supplemental OPS learning — typed non-resurrection reconcile job authority (2026-10-29)

Append-only supplemental learning only. Never canonical learning authority, production evidence, typed eight-domain recovery proof, generation/objective, reviewed drill, backup/restore, RPO/RTO/skew, credentials, traffic, readiness or human promotion.

## Material semantic gap / recurrence prevention

- **Symptom:** Typed non-resurrection reconcile-negative workflow source validation pinned reviewed event/root/permission YAML and Git blob identity but did not independently reject a duplicate job mapping or job-scoped write permission. Static validator gap, not observed production failure.
- **Observed evidence:** Reviewed workflow has one `negative` job inheriting root `contents: read`, with `runs-on: ubuntu-latest`, `timeout-minutes: 5`, and `steps`. Previous nine exact-diagnostic YAML negatives covered event/root/root-permission shadows.
- **Verified root cause:** Root-level read-only permission and complete source identity do not independently prove job-level permission absence or job ID uniqueness.
- **Failed approach:** Relying on root permission and digest mismatch as a job-scope semantic diagnostic.
- **Correction / executable guard:** [c060a21f](https://github.com/m-shogo/memories-project/commit/c060a21f0519d4a31d107b53588b0487a5fbe5cc) adds exact job header/key inventory checks and six in-memory exact-diagnostic negatives: duplicate/spaced/quoted jobs and normal/spaced/quoted job-level write permissions. YAML semantic negative inventory increased from nine to fifteen without relaxing existing source/branch/trigger/rollback guards.
- **Retry condition:** Revisit after reviewed job topology or permission semantics change, or a new verified bypass. Do not retry unchanged MinIO HTTP 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Non-Resurrection Reconcile Negative #40761661392](https://github.com/m-shogo/memories-project/actions/runs/40761661392) completed **SUCCESS** on exact source `c060a21f0519d4a31d107b53588b0487a5fbe5cc`. Job log confirms fifteen exact-diagnostic YAML negatives, 54 trigger removals, eight additions, one shortened inventory, six branch-runtime cases, seventeen semantic source negatives, two complete-source/terminator negatives, and private error suppression checks.
- **Why safe:** Only the CI-reachable read-only Python validator changed; workflow, production, recovery evidence, registries, promotion authority and credentials were untouched.
- **Reusable mechanism:** For read-only inherited-permission workflows, enforce exact job mapping and allowed top-level job keys, then prove job permission escalation/duplicate job shadows are rejected for the intended diagnostic.
- **Protected-authority check:** Git tree comparison `5abcff0e` → `c060a21f` found only the validator changed and zero protected contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; source-negative CI never satisfies generation, objective, typed eight-domain evidence, readiness or human promotion gates.
- **Next safe target:** Audit typed non-resurrection readonly job mapping and permission inheritance; check Full Admission Chain separately rather than treating source-negative success as full production admission.
