# Supplemental OPS learning — human promotion readonly job mapping (2026-10-29)

Append-only supplemental learning only, never canonical learning, human promotion approval, production/recovery evidence, RPO/RTO/skew, drill, credentials, traffic or readiness.

## Material gap / recurrence prevention

- **Symptom:** Promotion-review readonly workflow had exact event/root permission semantics and a reviewed complete Git blob, but no mutation-specific diagnostic for a duplicate `validate` job mapping or a new job-scoped write permission. Static CI-source coverage gap; no observed promotion bypass.
- **Observed evidence:** The reviewed workflow has one `validate` job with `runs-on`, `timeout-minutes`, `steps`, no job-level `permissions`, and root `contents: read`. The existing validator checked nine event/root/permission YAML negatives, but no job-level shadows.
- **Verified root cause:** Root-level read-only permissions do not independently prove the absence of job-level overrides, and byte-identity failures are not mutation-specific semantic evidence.
- **Failed approach:** Depending solely on Git blob identity and root-level `contents: read` for effective job authority.
- **Correction / executable recurrence guard:** [Code commit 46965538](https://github.com/m-shogo/memories-project/commit/46965538c3e534ea3d50413a944a4c3081d29046) adds exact single-job mapping and allowed job metadata checks; five exact-diagnostic negatives reject spaced/quoted job shadows and plain/spaced/quoted job write-permission overrides. The YAML negative population rises from nine to fourteen.
- **Retry condition:** Reassess only after reviewed readonly job topology/permission changes or a demonstrated new bypass. Do not retry unchanged canonical learning transport, MinIO 401, workflow-write permission or human promotion blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Backup Restore Promotion Review Readonly #40753631871](https://github.com/m-shogo/memories-project/actions/runs/40753631871) completed **SUCCESS** on exact source `46965538c3e534ea3d50413a944a4c3081d29046`. Job logs confirm fourteen exact-diagnostic YAML negatives, 44 trigger removals, eight additions, one shortened inventory, six runtime branch checks, 21 semantic and two blob-only source negatives; the promotion validators also ran read-only.
- **Why safe:** Only the existing CI-reachable Python validator changed. The human promotion contract/registry, production decision, recovery evidence and GitHub workflows remain unchanged.
- **Reusable mechanism:** Bind inherited root read permission by prohibiting any unreviewed job-scoped permission override, including YAML spelling variants; require a specific negative diagnostic.
- **Protected-authority check:** Git tree comparison after code commit found no changes across a 127-file contract/backup-evidence/canonical-learning protected superset. `productionDecision=NO_GO`; human promotion remains separate and non-automatic. No learning record can satisfy generation, objective, reviewed drill, typed eight-domain, independent review or promotion gates.
- **Next safe target:** Audit other high-risk publisher and independent CI job metadata/permission shadows and verify current Full Admission Chain independently.
