# Supplemental OPS learning — typed non-resurrection path job authority (2026-10-29)

Append-only supplemental learning, not canonical learning, production evidence, typed eight-domain non-resurrection evidence, generation/objective, reviewed drill, backup/restore, RPO/RTO/skew, credentials, traffic, readiness or human promotion.

## Material gap / recurrence prevention

- **Symptom:** Typed non-resurrection path-negative workflow source validator pinned exact events, root mapping, root `contents: read` and reviewed Git blob, but had no independent semantic rejection of duplicate job IDs or a newly inserted job-scoped write permission. This is a static validator gap, not an observed production incident.
- **Observed evidence:** Reviewed workflow has exactly one `validate` job, inheriting root read-only permissions, with `runs-on: ubuntu-latest`, `timeout-minutes: 4`, and `steps`. Previous nine YAML negatives covered event/root/root-permission shadows only.
- **Verified root cause:** Root read-only permission does not prove that a job cannot introduce its own `permissions` mapping, and blob mismatch is not an independently specific job-mapping diagnostic.
- **Failed approach:** Assuming root-level read-only authority and source SHA alone establish effective job-level read-only semantics.
- **Correction / executable guard:** [5abcff0e](https://github.com/m-shogo/memories-project/commit/5abcff0ec6cddcf6046f4cfd0fbd236abd5d446c) pins the single job header and its top-level job-key inventory; six in-memory exact-diagnostic negatives cover duplicate/spaced/quoted job mappings and normal/spaced/quoted job-level write permissions, increasing YAML negatives from nine to fifteen.
- **Retry condition:** Reassess only after a reviewed job topology/permission change or demonstrated bypass; do not retry unchanged MinIO 401, canonical learning transfer, workflow write-permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Non-Resurrection Path Negative #40761595056](https://github.com/m-shogo/memories-project/actions/runs/40761595056) completed **SUCCESS** on exact code `5abcff0ec6cddcf6046f4cfd0fbd236abd5d446c`. Job log confirms fifteen exact-diagnostic YAML negatives, twenty trigger removals, eight additions and one shortened-inventory negative, plus existing private path/ref safety checks.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed; workflow and all production/evidence/review authorities were untouched.
- **Reusable mechanism:** For read-only workflows inheriting root permissions, pin both the sole job ID and the allowed job-key sequence; reject any job-scoped permission mapping and duplicate YAML job with exact diagnostics.
- **Protected-authority check:** Before/after Git tree comparison `993395ad` → `5abcff0e` found only this validator changed; no contract, backup evidence or canonical learning blob drift. `productionDecision=NO_GO`; CI proof is not recovery evidence, readiness or human promotion.
- **Next safe target:** Apply the same bounded read-only job-key audit to typed non-resurrection reconcile/readonly workflows, after checking each reviewed job's actual topology.
