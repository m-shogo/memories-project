# Supplemental OPS learning — generation evidence readonly job authority (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production evidence, generation-bound recovery proof, backup/restore, RPO/RTO/skew, reviewed drill, typed eight-domain evidence, credentials, traffic, readiness or human promotion.

## Material gap / recurrence prevention

- **Symptom:** Generation-evidence readonly CI source validator pinned reviewed event/root/root-permission YAML and complete Git blob, but lacked independent rejection of duplicate job mapping or newly introduced job-level write permissions. This is a static semantic coverage gap, not an observed production bypass.
- **Observed evidence:** Reviewed workflow has one `prove-readonly` job inheriting root `contents: read`, with `runs-on: ubuntu-latest` and `steps`; prior nine YAML negatives covered event/root/root-permission shadows.
- **Verified root cause:** Root read-only permission and complete source identity do not independently prove absence of job-scoped write authority or duplicate job mappings.
- **Failed approach:** Treating blob mismatch and root-level permission as sufficient job-scope semantic validation.
- **Correction / executable guard:** [5d60f8e1](https://github.com/m-shogo/memories-project/commit/5d60f8e193ea29a52697503a63e400bf458a5071) pins the single job ID and allowed job-key inventory and adds six in-memory exact-diagnostic negatives (duplicate/spaced/quoted job, plain/spaced/quoted job permission override), increasing YAML negatives from nine to fifteen.
- **Retry condition:** Revisit after reviewed job/permission topology changes or demonstrated new bypass, not on unchanged MinIO 401, canonical learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Generation Evidence Readonly #40762044479](https://github.com/m-shogo/memories-project/actions/runs/40762044479) completed **SUCCESS** on exact code `5d60f8e193ea29a52697503a63e400bf458a5071`. Job log confirms fifteen exact-diagnostic YAML negatives, 34 trigger removals, eight additions, one shortened inventory, six branch-runtime cases and 19 semantic plus two blob-only source negatives.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed; no production workflow, generation/objective, reviewed drill, typed eight-domain evidence, credentials, traffic or human promotion was modified.
- **Reusable mechanism:** For single-job CI inheriting root read-only authority, require exact job ID and allowed job-level keys, then inject duplicate jobs and job-level write permissions and assert their intended semantic diagnostic.
- **Protected-authority check:** Git tree comparison `acedcf21` → `5d60f8e1` showed only the validator changed and zero contract/backup-evidence/canonical-learning blob drift. `productionDecision=NO_GO`; learning/CI success is not production recovery evidence, readiness or promotion.
- **Next safe target:** Inspect remaining generation-evidence and preflight source-negative workflows for post-`runs-on` permission shadows and job-level YAML mapping overrides.
