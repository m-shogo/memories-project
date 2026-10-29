# Supplemental OPS learning — worker saturation reviewed concurrency policy (2026-10-29)

Append-only supplemental learning only. Not canonical learning, production or backup/restore/RPO/RTO/skew evidence, a generation, approved recovery objective, executable reviewed drill, typed eight-domain non-resurrection evidence, credentials, traffic, readiness, independent recovery review or human promotion.

## Material failure / executable recurrence prevention
- **Symptom:** Worker saturation source-negative CI pinned reviewed Git blobs, inherited publisher write authority and nested job permissions but lacked an independent semantic diagnostic for publisher concurrency grouping/cancellation. Static coverage gap, not observed production bypass.
- **Observed evidence:** Reviewed publisher blob `a671ebaddffe34d27b9b152044e2f510befe3f61` declares `group: deletion-worker-saturation-so` and `cancel-in-progress: true`. Previous validator blob `9ab9e5415293bab7f93cf6e4b223f934e9f398f0` checked only root `concurrency:`.
- **Verified root cause:** Whole-file SHA and root YAML checks reject changed bytes without separately proving effective nested cancellation or group semantics.
- **Failed approach:** Blindly reusing the noncancellation expectation from worker recovery workflows would contradict the reviewed saturation workflow; generic digest mismatch alone lacks semantic diagnostics.
- **Correction / executable recurrence guard:** [`da3edc91`](https://github.com/m-shogo/memories-project/commit/da3edc9157ea028cc725b60111e900eb25bc1b7f) pins the reviewed static group and `cancel-in-progress: true` with ten exact-diagnostic negatives for global grouping, disabled cancellation, duplicate/spaced/quoted leaves, unreviewed leaf and missing cancellation.
- **Retry condition:** Revisit only on reviewed concurrency-policy change or demonstrated effective YAML shadow bypass; do not retry unchanged MinIO 401, canonical-learning transport, workflow-write permission or human approval blockers.

## Material success / protected authority
- **Observed outcome/evidence:** [Deletion Worker Saturation Diagnostic Source Negative #40806596056](https://github.com/m-shogo/memories-project/actions/runs/40806596056) completed **SUCCESS** at exact code `da3edc91`; log confirms ten new concurrency negatives, 24 nested-job negatives and `production evidence generated: false; production decision changed: false`.
- **Why safe:** Only the CI-reachable read-only validator changed (+48 lines, no deletions). Reviewed publisher/independent workflows, production status, registries, evidence, credentials, traffic and human promotion authority were unchanged.
- **Reusable mechanism:** Verify reviewed `cancel-in-progress` value before copying guard patterns; bind static grouping and the actual cancellation policy independently of SHA/root YAML with mutation-specific negatives.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. No registered generation, approved objective, executable reviewed request, generation evidence, complete typed eight-domain record, final candidate or human promotion.
- **Next safe target:** Audit deletion pre-fence diagnostic publishers' concurrency semantics and avoid changing production evidence or triggering known external blockers.
