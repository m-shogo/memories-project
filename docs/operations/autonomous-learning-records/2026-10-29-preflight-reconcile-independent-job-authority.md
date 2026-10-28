# Supplemental OPS learning — preflight reconcile independent job authority (2026-10-29)

Append-only supplemental learning only; not canonical learning, production evidence, generation/objective approval, reviewed drill, backup/restore, RPO/RTO/skew, typed eight-domain evidence, credentials, traffic, readiness or human promotion.

## Material semantic gap / recurrence prevention

- **Symptom:** The independent preflight reconcile source-negative validator checked exact YAML events/root/root-permission mapping and full reviewed Git blob, but did not independently validate job identity, job permission leaves or late permission shadow mappings. This was a static validator gap, not an observed production or preflight bypass.
- **Observed evidence:** Reviewed independent workflow has one `source-admission` job with explicit `contents: read`, `runs-on: ubuntu-latest`, `timeout-minutes: 5`, `steps` and a PR/push branch-scoped `if`. Prior nine YAML negatives covered event/root/root-permission shadows only.
- **Verified root cause:** A root read-only token and Git blob pin do not independently establish effective job mapping uniqueness or absence of late job-scoped permission overrides.
- **Failed approach:** Treating source digest mismatch or root permission as a specific job-level semantic diagnostic.
- **Correction / executable guard:** [4b5cf36d](https://github.com/m-shogo/memories-project/commit/4b5cf36dabce83f207fc2ba452f95df7335457a7) pins job header, allowed top-level job keys and explicit read-only permission leaf; eight exact-diagnostic in-memory negatives cover duplicate/spaced/quoted job mappings, spaced/quoted job permission leaves and plain/spaced/quoted late job permission overrides. YAML negative inventory increased from nine to seventeen.
- **Retry condition:** Reassess after reviewed job topology/permission changes or a new verified bypass; do not retry unchanged canonical-learning transfer, workflow-write permission, MinIO HTTP 401 or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Preflight Reconcile Source Negative #40762851004](https://github.com/m-shogo/memories-project/actions/runs/40762851004) completed **SUCCESS** on exact source `4b5cf36dabce83f207fc2ba452f95df7335457a7`. Job log confirms seventeen exact-diagnostic YAML negatives, six trigger removals, eight additions, one shortened inventory, PR/push branch and SHA runtime cases, fifteen semantic and two blob-only independent source negatives, and seventeen semantic plus three complete-source/terminator reconcile negatives.
- **Why safe:** Only an already CI-reachable read-only Python source-negative validator changed; no reviewed workflow, production registry, recovery evidence, credentials, traffic or human approval authority was modified.
- **Reusable mechanism:** Enumerate the full job-level key inventory, require explicit read-only leaves and inject late permission shadows after `runs-on` with exact diagnostic assertions.
- **Protected-authority check:** Git tree comparison `bc656f53` → `4b5cf36d` found only the validator changed and zero contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; source-negative CI does not establish recovery readiness or promotion.
- **Next safe target:** Audit other preflight/OPS-P0-007 independent source-negative workflows for late job-scoped YAML overrides and separately check Full Admission Chain status.
