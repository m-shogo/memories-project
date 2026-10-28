# Supplemental OPS learning — admission linkage readonly job authority (2026-10-29)

Append-only supplemental learning only; never canonical learning, production-equivalent generation or recovery evidence, backup/restore, RPO/RTO/skew, reviewed drill, credential, traffic, readiness or human promotion authority.

## Material guard gap / failure learning
- **Symptom:** Admission Authority Linkage Readonly source validator independently pinned event/root/root-permission YAML but lacked semantic job-mapping and job-level permission shadow checks. This is a discovered static CI admission gap, not an observed production bypass.
- **Observed evidence:** Reviewed `.github/workflows/admission-authority-linkage-readonly.yml` has one `prove-readonly` job with `runs-on: ubuntu-latest`, `timeout-minutes: 6`, `steps` and inherited root `contents: read`; earlier YAML negative inventory was nine.
- **Verified root cause:** Root read-only permission and source digest alone cannot independently establish unique effective YAML job identity and nested permission/execution authority.
- **Failed approach:** Treating complete Git blob mismatch as the only protection for job-level YAML shadow mutations.
- **Correction / executable recurrence guard:** [b57731a5](https://github.com/m-shogo/memories-project/commit/b57731a5d4e39c8bb4f5263a1b7c4e9fceeb3c4d) adds exact job mapping and job-key inventory plus nine in-memory exact-diagnostic negatives for duplicate/spaced/quoted jobs, plain/spaced/quoted job write permissions, false job condition, spaced timeout and continuation overrides; YAML total rises to 18.
- **Retry condition:** Revisit only when reviewed workflow topology/permission changes or an actual bypass is demonstrated; do not retry unchanged canonical learning transport, workflow write permission, MinIO 401 or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Admission Authority Linkage Readonly #40774631833](https://github.com/m-shogo/memories-project/actions/runs/40774631833) completed SUCCESS on exact source `b57731a5d4e39c8bb4f5263a1b7c4e9fceeb3c4d`. Job log confirms 18 exact-diagnostic YAML negatives, 32 PR/push path removal negatives, six runtime branch cases, 20 semantic and two blob-only source negatives.
- **Why safe:** Only the existing read-only, PR/push CI-reachable Python validator changed (+39/-2); no workflow, production/evidence/registry, credential, traffic, readiness or promotion authority changed.
- **Reusable mechanism:** Bind nested YAML job identity and top-level job-key inventory to reviewed source semantics; mutate each boundary in memory and assert the exact rejection diagnostic before the existing blob check.
- **Protected-authority check:** Compare shows only validator changed. Production status blob `3956bb805ee124ca7baf594ba05bcb0d986783b4` remains `productionDecision=NO_GO`, learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged; empty recovery/drill/typed non-resurrection registries were not modified. Learning cannot promote production readiness.
- **Next safe target:** Audit other existing source-negative validators for genuinely unguarded job mapping and permission semantics; verify full-chain status separately.
