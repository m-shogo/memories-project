# Supplemental OPS learning — preflight job/permission YAML shadows (2026-10-29)

Append-only supplemental learning only, not the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` authority. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness or promotion evidence.

## Material gap / recurrence prevention

- **Symptom:** OPS-P0-007 preflight publisher and independent source-negative CI had exact reviewed Git blobs, event topology, root mapping and root permission checks, but no mutation-specific check for job identity shadowing or job-scoped `contents` permission overrides. This was a static coverage gap, not observed production bypass.
- **Observed evidence:** `validate_yaml_authority` checked root `contents: read`, events and roots. The reviewed publisher defines `validate-pr` with `contents: read` and `validate-and-publish` with `contents: write`; independent `source-admission` has `contents: read`. Existing 18 YAML negatives did not exercise job shadows.
- **Verified root cause:** Root-level mapping validation and Git blob identity do not independently diagnose the effective YAML job mapping or job-scoped permissions.
- **Failed approach:** Treating root permission checks as sufficient to explain job-level authority; treating all jobs as read-only would incorrectly reject the reviewed publisher.
- **Correction / executable recurrence guard:** [Code commit 72faa0b5](https://github.com/m-shogo/memories-project/commit/72faa0b541d8fdcb81f2210f00f705cd4d409521) binds exact job names and role-specific permissions and adds twelve exact-diagnostic job-shadow fixtures, raising the YAML negative population from 18 to 30. No workflow or OPS-P0-007 gate was edited.
- **Retry condition:** Revisit only if a reviewed preflight job topology or job permission changes, or a demonstrated semantic bypass appears. Do not retry unchanged MinIO 401, canonical-learning transport, workflow-write permission or human-approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Backup Restore Drill Preflight Source Negative #40753483810](https://github.com/m-shogo/memories-project/actions/runs/40753483810) completed **SUCCESS** on exact code `72faa0b541d8fdcb81f2210f00f705cd4d409521`. Job logs confirm 30 exact-diagnostic YAML negatives, six trigger removals, eight additions, one shortened inventory negative, twelve branch cases, four publisher event cases, 24 SHA cases, four CAS cases, five diagnostic/atomic cases, 42+3 publisher and 19+4 independent source negatives.
- **Why safe:** Only the CI-reachable read-only preflight source-negative validator changed; reviewed publisher/independent workflows, evidence, registry, objective, generation and promotion authority remain untouched.
- **Reusable mechanism:** Check job identity and scoped permissions independently of root mapping and Git blob identity; mutate job keys and leaves in memory, and demand the intended semantic diagnostic.
- **Protected-authority check:** The code change was followed by a Git tree comparison covering 127 contract/backup-evidence/canonical-learning blobs with no drift. `productionDecision=NO_GO` remains mandatory; registered versus semantically eligible generations, approved current recovery objective, executable reviewed drill request, typed eight-domain non-resurrection and independent review requirements are unchanged. Learning never satisfies any of these gates; human promotion remains separate/non-automatic.
- **Next safe target:** Audit independent promotion-review CI for job-level shadow diagnostics; distinguish source-negative CI success from Full Admission Chain outcomes.
