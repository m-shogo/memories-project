# Supplemental OPS learning — live-load gofmt YAML root/job/permission authority (2026-10-29)

Append-only supplemental learning; not the canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` authority and never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, promotion or human-review evidence.

## Material failure / recurrence prevention

- **Symptom:** The read-only gofmt source-negative validator pinned publisher and independent Git blobs and exact event topology but did not independently diagnose YAML root shadows, duplicate job mappings or permission-leaf shadows. The initial new guard run also failed because its hard-coded fixture total was incorrect.
- **Observed evidence:** Existing `gofmt_validate_trigger_matrix` checked PR/push/dispatch and reviewed Git blobs, but not semantic job or permission shadow mutations. [First gofmt CI #40753258795](https://github.com/m-shogo/memories-project/actions/runs/40753258795) failed with `live-load-gofmt YAML negative population drift: 28` when the source expected 26.
- **Verified root cause:** Byte-level identity alone does not independently explain effective YAML mapping semantics. The fixture accounting mistake was arithmetic: publisher has 16 negatives (six root, two root-permission, four per job across two jobs), independent has 12 (six root, two root-permission, four for one job), totaling 28.
- **Failed approach:** Trusting a manually entered fixture total of 26; relying solely on complete-source Git SHA for effective YAML root/job/permission authority.
- **Correction:** [Guard commit b24143a4](https://github.com/m-shogo/memories-project/commit/b24143a4d3c046251535ca896c715611591309c9) adds independent root/job/permission mapping checks and exact-diagnostic in-memory mutations. [Count correction 3d536d5a](https://github.com/m-shogo/memories-project/commit/3d536d5aa70aff6d8357dda2f45d6995dd38f4fa) fixes the expected fixture count to 28 without weakening diagnostics.
- **Executable recurrence guard:** `gofmt_validate_yaml_authority` enforces exact root and job identities, root `contents: read`, publisher PR job `contents: read`, publisher format job `contents: write`, and independent CI job `contents: read`. `gofmt_yaml_authority_negatives` verifies 28 exact-diagnostic root, job and permission shadow mutations; the population check rejects fixture loss or accidental addition.
- **Retry condition:** Revisit only if reviewed YAML topology, job authority, or permission semantics change, or a new demonstrable bypass is found. Do not retry unchanged canonical-learning transport, MinIO 401, workflow-write permission or human-approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Live Load Formatting Source Negative #40753282597](https://github.com/m-shogo/memories-project/actions/runs/40753282597) completed **SUCCESS** on exact code `3d536d5aa70aff6d8357dda2f45d6995dd38f4fa`; the initial failure above is retained as failure evidence, not hidden. Existing event matrix, source integrity and executable shell/CAS checks remain in the same validator.
- **Why safe:** Only the CI-reachable read-only Python validator was modified. No reviewed workflow, production authority, registry, credential, traffic, readiness or promotion data was written.
- **Reusable mechanism:** Check the effective YAML authority of each workflow role independently, including job-level permission leaves, and require the specific semantic diagnostic rather than generic SHA mismatch.
- **Protected-authority check:** After both code writes, a protected superset of 127 contract/backup-evidence/canonical-learning blobs was compared with the initial Git tree; no protected blob drift was found. `productionDecision=NO_GO` remains mandatory; no production-equivalent generation, recovery objective, executable reviewed request, typed eight-domain evidence or human promotion approval was manufactured or inferred from this learning.
- **Next safe target:** Audit remaining source-negative validators without independent job/root permission diagnostics, then verify exact-source CI before recording each result.
