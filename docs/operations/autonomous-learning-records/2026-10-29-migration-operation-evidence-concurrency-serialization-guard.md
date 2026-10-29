# Supplemental OPS learning — migration operation evidence publisher concurrency (2026-10-29)

Append-only supplemental history only. Not canonical learning, production/backup/restore/RPO/RTO/skew evidence, environment generation, approved recovery objective, executable reviewed drill request, typed eight-domain non-resurrection record, credentials, traffic, readiness, independent review or human promotion.

## Material failure / executable recurrence prevention

- **Symptom:** Existing migration-operation evidence source-negative CI pinned complete Git blobs, event/root/job/permission YAML, branch/SHA runtime and trigger paths, but had no independent exact diagnostic for publisher concurrency serialization or cancellation. This is a static coverage gap, not an observed production bypass.
- **Observed evidence:** Reviewed publisher workflow blob `fae2ea025d19fa8fce0b319a6392d67f368247fa` has `migration-operation-evidence-${{ github.event.pull_request.number || 'so' }}` with `cancel-in-progress: false`. Previous validator blob `00671d0d0b7dbab4fa499d7bc9396cee7feef643` did not implement a dedicated concurrency validator or negative fixtures.
- **Verified root cause:** A complete Git blob guard rejects altered bytes but cannot independently classify YAML-equivalent group/cancellation shadows or unreviewed concurrency scope changes.
- **Failed approach:** Treating complete source digest and root-key presence as sufficient semantic noncancellation proof.
- **Correction / executable recurrence guard:** [Commit `affd9e5e`](https://github.com/m-shogo/memories-project/commit/affd9e5e51090b59868d69a7129853abc2d90070) adds exact reviewed concurrency-block validation and ten expected-diagnostic negative fixtures: global group, enabled cancellation, duplicate/spaced/quoted group and cancellation, unreviewed leaf and removed cancellation. Each requires `migration operation publisher concurrency scope drift`.
- **Retry condition:** Revisit only for an explicitly reviewed concurrency-policy change, demonstrated bypass, or exact-source CI failure; do not repeat unchanged MinIO HTTP 401, canonical learning transfer, permissions or human-approval blockers.

## Material success / protected authority

- **Observed outcome/evidence:** [Migration Operation Evidence Source Negative #40811178707](https://github.com/m-shogo/memories-project/actions/runs/40811178707) completed **SUCCESS** on exact code `affd9e5e`. Job log confirms 10 concurrency negatives, 48 YAML authority negatives, 40 trigger removals, 16 trigger additions, 2 shortened inventory negatives, 20 source negatives and 18 runtime cases. [Migration Operation Evidence #40811176904](https://github.com/m-shogo/memories-project/actions/runs/40811176904) also completed **SUCCESS** on that code.
- **Why safe:** Only the CI-reachable read-only Python source-negative validator was changed. Reviewed workflows, production status, recovery objectives, generation registries, typed non-resurrection evidence, credentials, traffic and human promotion authority were not modified by the code commit.
- **Reusable mechanism:** Pin publisher serialization and noncancellation independently of full Git blob and root/job authority; require exact diagnostics for shadowed YAML leaves, and confirm both source-negative and publisher CI.
- **Protected-authority check:** Production status blob `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` still has `productionDecision=NO_GO`. Autonomous learning contract blob `87712ea9c0e1d25dea1565f34b1c21a2b2d276db` is unchanged. This record is supplemental history and cannot satisfy any OPS-P0-007, readiness or promotion gate.
- **Canonical-learning limitation:** The canonical 4.17 MB learning file returned empty content through the existing read path; the unchanged transport blocker was not retried.
- **Next safe target:** Audit migration production-shaped admission publisher concurrency and other CI-reachable read-only validators without changing evidence or promotion authority.
