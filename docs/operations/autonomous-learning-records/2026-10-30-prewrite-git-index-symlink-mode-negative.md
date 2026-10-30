# Supplemental OPS learning — Git index symlink-mode source alias (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified, with full-text transport unavailable. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / Git index mode regression gap

- **symptom:** A workflow leaf can be a regular file in the working tree but have Git index mode `120000` (symlink), making its tracked source identity unsafe even though a filesystem-only symlink check passes.
- **evidence:** The optional Git index guard rejected non-regular modes in code, but earlier disposable fixtures exercised only dirty worktree, staged content drift, untracked source and missing Git metadata. No fixture changed the index mode while leaving the worktree leaf regular. This was a static test gap, not an observed production incident.
- **rootCauseOrUnknown:** Verified missing mode-120000 negative fixture; the actual reviewed workflow index remains regular.
- **failedApproach:** Inferring index-mode safety from regular worktree file type or generic content-drift controls.
- **correction:** [`e1ea6c5c`](https://github.com/m-shogo/memories-project/commit/e1ea6c5c8c2134e6e99e1007aaa0ee7af9b6f476) changes a disposable Git index entry to mode `120000` using `git update-index --cacheinfo` while keeping its worktree leaf regular, then requires exact `prewrite workflow Git index mode or stage drift` rejection. [`d877fb38`](https://github.com/m-shogo/memories-project/commit/d877fb3805b993112eefb1620a776a650cbb2c61) adds real CLI negative and resets the index before later tests.
- **recurrenceGuard:** One synthetic and one exact-diagnostic/exit-1/empty-stdout CLI negative; fail closed on mode mismatch independent of worktree symlink checks. Fail-closed negatives **500 → 501**, fanout synthetic **190 → 191**.
- **retryCondition:** A reviewed exception requires Git index stage/mode, checkout ownership and real CLI evidence. Do not retry unchanged MinIO 401, workflow-write permission, canonical-learning transfer or human promotion blockers.

## Material success / protected authority

- **outcome:** Exact-source [Autonomous Learning Guard #41015593932](https://github.com/m-shogo/memories-project/actions/runs/41015593932) completed **SUCCESS** for `d877fb3805b993112eefb1620a776a650cbb2c61`.
- **evidence:** CI logs show append-only PASS, contract PASS, **501** fail-closed negatives, **191** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **whySafe:** Only disposable Git fixture tests in the read-only auditor and CI-reachable negative suite changed; no workflow YAML, production runtime, credentials, traffic, recovery evidence, readiness, generation/objective or promotion authority changed.
- **reusableMechanism:** Independently validate index mode/stage even when the worktree file type and bytes appear safe, with deterministic Git index mutation and cleanup.
- **protectedAuthorityCheck:** All ten protected authority blobs matched run-start `7d2a0617`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human recovery or promotion authority.
- **limits / nextSafeTarget:** This is not a complete Git index conflict-stage or Go/Python transitive CI closure proof. Continue unmerged-stage negatives and Go-only CI path review without unauthorized workflow writes.
