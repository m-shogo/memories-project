# Supplemental OPS learning — release baseline registry publisher concurrency (2026-10-29)

Append-only supplemental history only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, a release approval, environment generation, executable reviewed drill, typed eight-domain non-resurrection evidence, credentials, traffic, readiness, independent review or human promotion.

## Material failure / executable recurrence prevention

- **Symptom:** Release baseline source-negative CI pinned exact Git blobs, event/root/job/permission YAML, trigger topology, runtime and baseline authority, but did not independently assert publisher concurrency group/cancellation leaves. This is a static guard gap, not an observed release admission bypass.
- **Observed evidence:** Reviewed publisher workflow blob `e14c1c779228404a75ee03a2d0ec6d4a598764c5` declares `release-baseline-registry-${{ github.ref }}` and `cancel-in-progress: false`. Previous validator blob `c835e4a82dc1ff2c721fc6efaf1e403095dc8728` checked root `concurrency:` but lacked nested-leaf diagnostics.
- **Verified root cause:** Root-key and full Git blob checks reject changed bytes without independently classifying effective concurrency scope, cancellation or YAML-equivalent shadow leaves.
- **Failed approach:** Treating generic digest mismatch as complete semantic proof of noncancelling release baseline registry reconciliation.
- **Correction / recurrence guard:** [Commit `3fbd9376`](https://github.com/m-shogo/memories-project/commit/3fbd9376e3557796571bc920c357f41278e95098) adds exact reviewed concurrency-block validation and ten expected-diagnostic negatives for global group, enabled cancellation, duplicate/spaced/quoted group and cancellation, extra leaf and removed cancellation. All require `release baseline publisher concurrency scope drift`.
- **Retry condition:** Revisit only if the reviewed concurrency policy changes, a YAML semantic bypass is demonstrated or exact-source CI fails. Do not retry unchanged MinIO HTTP 401, canonical-learning transport, permission or human approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Release Baseline Registry #40809070478](https://github.com/m-shogo/memories-project/actions/runs/40809070478) completed **SUCCESS** at exact code `3fbd9376`. Logs confirm ten concurrency exact-diagnostic negatives, 16 YAML root/permission negatives, 36 job authority negatives, source/runtime negatives and release baseline contract/registry corruption/rollback tests.
- **Why safe:** Only the CI-reachable read-only Python validator changed. Reviewed workflows, release baseline registry, generation registry, recovery evidence, credentials, traffic, production status and human promotion were not edited.
- **Reusable mechanism:** Bind release publisher noncancellation independently of SHA and root/job authority. Source validation and learning do not approve releases or satisfy production-equivalent recovery/promotion gates.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` remains `productionDecision=NO_GO`; release baseline registry blob `700a466a32912ae0c7c2157f0ea2256fbe6ee0dd` unchanged; generation registry remains empty; autonomous learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` unchanged.
- **Canonical-learning limitation:** The 4.17 MB canonical learning authority returned empty text through the current read path. Existing unchanged transport blocker was not retried. This supplemental record cannot replace canonical learning or production evidence.
- **Next safe target:** Audit release compatibility pair publisher concurrency without modifying the approved release pair registry or human promotion authority.
