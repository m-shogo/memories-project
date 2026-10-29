# Supplemental OPS learning — Upload Route critical shell and writer CAS body guard (2026-10-30)

Append-only supplemental history only. Canonical authority is `docs/operations/AUTONOMOUS-OPS-LEARNING.md`; mandatory policy is `contracts/operations/autonomous-learning-system.json`. This record is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review or human promotion evidence.

## Material failure — prospective shell-body bypass

- **Symptom:** The reviewed Upload Route workflows could change MinIO readiness polling, source-integrity shell checks, Publisher's source-SHA compare-and-swap/exit-75 writer boundary, or PR whole-worktree verification without changing step names, action identities or the ten direct Python/Go command strings.
- **Observed evidence:** Read-only inspection found Publisher's `git fetch origin so`, strict `origin/so == SOURCE_SHA` comparison, `exit 75` on stale source and `git push origin HEAD:so`, plus PR `git diff --check`, `git diff --exit-code` and clean-worktree check. MinIO health polling is local and bounded. Existing command/step/permission guards did not pin these complete shell bodies. This is prospective drift, not an observed production failure.
- **Verified root cause:** Direct Python/Go command identity and ordered step names do not bind adjacent shell commands, including CAS and failure handling.
- **Failed approach:** Treating an unchanged step graph and direct command list as proof of the complete shell execution body.
- **Correction / executable recurrence guard:** [`1e511c3d`](https://github.com/m-shogo/memories-project/commit/1e511c3d072bf74300d1bfff0ededcc3d4f5a802) pins SHA-256 of three critical step blocks per workflow: local MinIO startup/readiness, exact clean-source verification and Publisher writer CAS or PR whole-worktree verification. It adds ten in-memory mutation negatives across both workflows, with real-source positive controls. Only the CI-reachable read-only negative validator changed (+70 lines).
- **Retry condition:** Any legitimate change to MinIO readiness, source SHA checks, writer CAS, PR diff checks or shell body requires explicit review of failure/authority semantics, deterministic digest update, exact-source CI and protected-authority verification. Do not retry unchanged Quay MinIO 401 or promote any learning record to recovery evidence.

## Prewrite failures prevented before repository write

- **Symptom/evidence 1:** A local candidate copied the shared MinIO SHA-256 incorrectly into the PR entry (62 rather than 64 hex characters), causing the positive control to reject the PR block.
- **Verified root cause / failed approach:** Manual duplication of a reviewed digest into two separate literals introduced a transcription error.
- **Correction / recurrence guard:** Use one shared `REVIEWED_UPLOAD_ROUTE_MINIO_STEP_SHA256` constant for both events and test positive extraction for both Publisher and PR. The committed version uses that shared constant.
- **Retry condition:** Reuse a digest only after checking its full length, identical source bytes and both event positive controls.
- **Symptom/evidence 2:** An early synthetic negative attempted to mutate `--health-retries 30` inside the MinIO step; the anchor occurred zero times because it belongs to the PostgreSQL service health block.
- **Verified root cause / failed approach:** Confusing adjacent service health settings with MinIO's own `for attempt in $(seq 1 60)` polling loop.
- **Correction / recurrence guard:** Replace the negative with a unique MinIO polling-loop mutation and assert one occurrence of every negative anchor in the actual reviewed workflow. All ten corrected local negatives passed before commit.
- **Retry condition:** Re-read the exact named step block and require unique within-workflow anchors before any future test mutation. Neither prewrite failure created a GitHub commit.

## Material success

- **Observed outcome/evidence:** [Autonomous Learning Guard #40947542385](https://github.com/m-shogo/memories-project/actions/runs/40947542385) **SUCCESS** on exact source `1e511c3d072bf74300d1bfff0ededcc3d4f5a802`. Logs confirm append-only and contract PASS, 201 printed canonical negatives, 74 fanout synthetic, entry-document PASS, 1,186 helper-ancestor negative mutations and read-only completion. The ten nested shell-body negatives are additional to the printed 201.
- **Why safe:** No workflow YAML, production service, credentials, traffic, readiness, generation/objective, drill, recovery evidence, typed eight-domain records, independent review or human promotion was changed.
- **Reusable mechanism:** Hash complete critical named step bodies and enforce unique extraction, rather than relying solely on action refs, direct commands or step order.
- **Protected-authority check:** The code commit changed only `scripts/validate-autonomous-learning-system-negative.py`. Canonical learning `b809c69dda5d788245abd2a79b34c6e8c1d6c628`, contract `87712ea9c0e1d25dea1565f34b1c21a2b2d276db`, production status `2c6b196a54fafcbb6e02db65116e6e81fbdfb015` and OPS-P0-007 snapshot `dbaa36b082366737dca2461d15748103b9740ef6` remain unchanged. `productionDecision=NO_GO`; registered/eligible generations remain 0/0, with no human-approved objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review or human promotion.

## Next safe target

Extend critical shell body fingerprints to shared Go formatting, reconcile idempotence, rollback and metrics/observability steps, without changing workflow YAML or narrowing incomplete dependency-trigger coverage.
