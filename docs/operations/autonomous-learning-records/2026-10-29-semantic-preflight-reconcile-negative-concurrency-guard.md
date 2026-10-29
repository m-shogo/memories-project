# Supplemental OPS learning — semantic preflight reconcile-negative concurrency (2026-10-29)

Append-only supplemental learning, not canonical authority or production/backup/restore/RPO/RTO/skew/drill/credential/traffic/readiness/promotion evidence. Never count this record as an environment generation, recovery objective, executable reviewed drill, typed eight-domain coverage or independent review.

## Material failure and executable recurrence prevention
- **Symptom:** Semantic preflight reconcile-negative source CI pinned workflow root `concurrency:` and complete Git blob but lacked a distinct group/cancellation semantic diagnostic. This was a static negative-test coverage gap, not observed production promotion.
- **Observed evidence:** Reviewed publisher workflow blob `2ee5dd443a19a4a8f01113bdbc5ced4fbd4bdc60` has PR/so-scoped `backup-restore-drill-preflight-reconcile-negative` group and `cancel-in-progress: false`; previous validator blob `7b98bb758c8321c6a1f518cffa76b8257327ca49` lacked nested concurrency classification.
- **Verified root cause:** Whole-source digest and root-key checks do not independently prove noncancelling serialization or distinguish YAML-equivalent group/cancellation shadow leaves.
- **Failed approach:** Relying on digest mismatch alone to reject effective YAML concurrency changes.
- **Correction / executable recurrence guard:** [Commit `07b09cc8`](https://github.com/m-shogo/memories-project/commit/07b09cc88cca0eec5c84abee99373750f64dca4f) pins the reviewed concurrency block and ten exact-diagnostic in-memory negatives: global group, cancellation enabled, duplicate/spaced/quoted group and cancellation leaves, unreviewed leaf, and removed cancellation.
- **Retry condition:** Revisit only on reviewed concurrency policy change, proven bypass or exact-source CI regression. Do not retry unchanged MinIO 401, canonical learning transfer, workflow-write permission or human approval blockers.

## Material success, safe reuse and authority
- **Observed outcome/evidence:** [Preflight Reconcile Source Negative #40816934216](https://github.com/m-shogo/memories-project/actions/runs/40816934216) completed **SUCCESS** on exact code `07b09cc8`. Job log confirms ten new concurrency exact-diagnostic negatives and 55 existing publisher YAML negatives plus a shortened inventory case. The distinct publisher workflow and Full Admission Chain were not inferred successful from this source-negative result.
- **Why safe:** Only the existing CI-reachable read-only Python validator changed (+51 lines, zero deletions). No reviewed publisher/independent workflow, production evidence, generation/objective/drill/typed-domain/promotion registry, credentials or traffic changed.
- **Reusable mechanism:** Pin noncancelling publisher concurrency separately from root mapping and Git blob while retaining exact PR/push reachability, branch/SHA and fail-closed gates. Semantically eligible unsuperseded generations from distinct environments and explicitly human-approved current recovery objective remain separate from registration; executable reviewed request, complete typed eight-domain evidence, independent review and human promotion remain separate gates.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. CI and supplemental learning cannot promote readiness.
- **Canonical learning limitation:** Canonical learning file content remained unavailable via the known large-file connector read; unchanged blocker was not retried.
- **Next safe target:** Audit admission authority linkage readonly workflow concurrency semantics and existing CI guard coverage.
