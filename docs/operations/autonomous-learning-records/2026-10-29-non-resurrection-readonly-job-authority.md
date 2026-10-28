# Supplemental OPS learning — typed non-resurrection readonly job authority (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore evidence, typed eight-domain proof, generation/objective, reviewed drill, RPO/RTO/skew, credentials, traffic, readiness or human promotion.

## Material gap / recurrence prevention

- **Symptom:** Typed non-resurrection readonly source validator pinned reviewed event/root/root-permission YAML and complete Git blob identity but did not independently reject duplicate job mapping or job-scoped write permission. Static validator gap, not observed production failure.
- **Observed evidence:** Reviewed workflow has exactly one `readonly` job inheriting root `contents: read`, with `runs-on: ubuntu-latest`, `timeout-minutes: 8`, and `steps`. Nine prior YAML negatives covered event/root/root-permission shadows.
- **Verified root cause:** Root read-only permission and full Git blob equality do not provide a specific semantic diagnostic for job-scoped permission override or duplicate job mapping.
- **Failed approach:** Treating root permission and blob mismatch as independent job-level authority validation.
- **Correction / executable guard:** [1aed71b3](https://github.com/m-shogo/memories-project/commit/1aed71b3461409973169da3e3e93aeb28b298bf1) pins exact job identity and allowed top-level job keys; six in-memory exact-diagnostic negatives reject duplicate/spaced/quoted job mappings and normal/spaced/quoted job-level write permissions. YAML negative count increased from nine to fifteen without weakening trigger/source/branch/runtime checks.
- **Retry condition:** Revisit only after reviewed job topology or permission semantics change, or a demonstrated new bypass. Do not retry unchanged MinIO HTTP 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Non-Resurrection Readonly #40761853657](https://github.com/m-shogo/memories-project/actions/runs/40761853657) completed **SUCCESS** on exact source `1aed71b3461409973169da3e3e93aeb28b298bf1`. Job log confirms fifteen exact-diagnostic YAML negatives, thirty trigger removals, eight additions, one shortened inventory, six branch-runtime cases, twenty semantic and two blob-only source negatives, plus private error suppression tests.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed. Actual workflow, production/evidence contracts, generation/objective/drill/typed registries, credentials, traffic and human promotion remained untouched.
- **Reusable mechanism:** Pin single job identity and job-key inventory for inherited root read-only authority, and require exact diagnostics for duplicate job or newly introduced job-level permission shadows.
- **Protected-authority check:** Git tree comparison `1557e2db` → `1aed71b3` showed only this validator changed and zero protected contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; successful CI cannot satisfy production or typed recovery gates.
- **Next safe target:** Audit additional source-negative workflows for role-specific job permissions and verify the Full Admission Chain independently of these source-negative successes.
