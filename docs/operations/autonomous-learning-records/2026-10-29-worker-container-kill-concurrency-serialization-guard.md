# Supplemental OPS learning — worker container-kill recovery concurrency serialization (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production or backup/restore/RPO/RTO/skew evidence, a generation, approved objective, executable reviewed drill, typed eight-domain non-resurrection evidence, credentials, traffic, readiness, independent recovery review or human promotion.

## Material failure / executable recurrence prevention
- **Symptom:** Worker container-kill recovery source-negative CI pinned reviewed Git blobs, inherited publisher write authority, job permissions and runtime identity but lacked an independent semantic diagnostic for publisher concurrency cancellation/grouping. Static coverage gap, not observed production cancellation.
- **Observed evidence:** Publisher blob `fd01bf06241cdb476cc592e507339914346038e8` declares `group: deletion-worker-container-kill-recovery-so` and `cancel-in-progress: false`. Previous validator blob `fe30275cb409d761f083d3b60c83b34bf90e8790` checked root `concurrency:` but not nested cancellation leaves.
- **Verified root cause:** Full-source SHA and root-key checks reject changed bytes but do not independently classify effective cancellation semantics or YAML shadows.
- **Failed approach:** Treating reviewed Git blob identity and root YAML mapping as sufficient standalone proof of writer noncancellation.
- **Correction / executable recurrence guard:** [`1ea3d0e5`](https://github.com/m-shogo/memories-project/commit/1ea3d0e59ec3fe3da25be41d992b26625d5f0617) adds an exact reviewed static-group/noncancellation guard and ten exact-diagnostic negatives for global group, enabled cancellation, duplicate/spaced/quoted leaves, unreviewed leaf and missing cancellation.
- **Retry condition:** Revisit only on reviewed concurrency-policy change or demonstrated effective YAML shadow bypass; do not retry unchanged MinIO HTTP 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Deletion Worker Container Kill Recovery Diagnostic Source Negative #40806488717](https://github.com/m-shogo/memories-project/actions/runs/40806488717) completed **SUCCESS** at exact code `1ea3d0e5`; log confirms ten concurrency negatives, 24 existing nested-job negatives and `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the existing CI-reachable read-only validator changed (+48 lines, no deletions). Publisher/independent workflows, production status, registries, evidence, credentials, traffic and human promotion authority were not changed.
- **Reusable mechanism:** Bind reviewed static writer serialization and noncancellation independently of source SHA/root YAML, proving mutation-specific in-memory negatives.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No registered generation, approved objective, executable reviewed request, generation evidence, complete typed eight-domain record, final candidate or human promotion.
- **Next safe target:** Audit deletion-worker saturation publisher reviewed cancellation policy and cross-workflow trigger coupling without modifying protected authorities.
