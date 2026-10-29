# Supplemental OPS learning — independent environment review publisher concurrency (2026-10-29)

Append-only supplemental history only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, an environment generation, approved recovery objective, executable reviewed drill request, typed eight-domain non-resurrection evidence, credentials, traffic, readiness, independent human review or promotion.

## Material failure / executable recurrence prevention

- **Symptom:** Review-independence source-negative CI pinned full reviewed Git blob, event/root/job/permission YAML, exact trigger inventory, branch runtime and diagnostic redaction, but did not independently classify the publisher's concurrency group or cancellation leaves. Static guard gap only; no observed review bypass.
- **Observed evidence:** Publisher workflow blob `56d15ffd78c816ccecd0ff27c9e159f78c913bf4` declares PR/so-scoped `production-equivalent-environment-review-independence-${{ github.event.pull_request.number || 'so' }}` and `cancel-in-progress: false`. Previous validator blob `f007251d72dcf8b58c6e0c2e207a9c45e2486635` checked root `concurrency:` but did not assert the two effective leaves.
- **Verified root cause:** A Git blob digest and a root-key check reject unreviewed changes without a dedicated exact diagnostic for group/cancellation changes or YAML-equivalent shadow keys.
- **Failed approach:** Relying on generic digest mismatch to prove review-independence publisher noncancellation semantics.
- **Correction / recurrence guard:** [Commit `03d04ac2`](https://github.com/m-shogo/memories-project/commit/03d04ac2fe662762ba46c5616157908e681976c0) adds exact concurrency-block validation and ten exact-diagnostic negatives: global group, cancellation enabled, duplicate/spaced/quoted group and cancellation, extra leaf and missing cancellation. Each must reject with `review independence CI concurrency scope drift`.
- **Retry condition:** Revisit only on reviewed concurrency-policy changes, a demonstrated YAML bypass or a failing exact-source CI; do not retry unchanged canonical-learning transfer, MinIO 401, workflow permissions or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Production Equivalent Environment Review Independence #40808645770](https://github.com/m-shogo/memories-project/actions/runs/40808645770) completed **SUCCESS** at exact code `03d04ac2`. Job log explicitly confirms ten concurrency exact-diagnostic negatives, 29 existing YAML event/root/job/permission negatives, 41 trigger negatives, six branch-runtime cases and diagnostic redaction.
- **Why safe:** Only the CI-reachable read-only validator changed. Reviewed workflow, review evidence, generation registry, objective approval, executable drill request, typed eight-domain non-resurrection evidence, credentials, traffic and human promotion authority were not modified.
- **Reusable mechanism:** Preserve independent review execution noncancellation independently of Git blob and YAML root/job guards. An automated source CI success is not an independent review, a recovery candidate or a promotion decision.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; environment generation registry blob `bfd1b04561a257d1a288bd127572bdad762bfae5` remains empty; autonomous learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged. Human promotion remains separate and unperformed.
- **Canonical-learning limitation:** The 4.17 MB canonical learning authority returned empty text through the current read path. The unchanged transfer blocker was not retried. This supplemental record does not replace canonical learning or satisfy any readiness gate.
- **Next safe target:** Audit migration evidence registry source-negative publisher concurrency and its CI trigger overlap before modifying only an independently executable validator.
