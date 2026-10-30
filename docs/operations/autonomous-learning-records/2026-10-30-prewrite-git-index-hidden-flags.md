# Supplemental OPS learning — Git index hidden flags (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` remains blob-SHA verified; full-text retrieval remains unavailable. **Never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, recovery generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / source identity bypass

- **symptom:** A changed workflow worktree file could be reported clean by `git diff --quiet HEAD` when its index entry had an assume-unchanged or skip-worktree bit, despite the prewrite audit claiming tracked/HEAD workflow identity.
- **evidence:** A disposable local Git repository with a committed `on: push` workflow changed to `on: workflow_dispatch` returned `git diff --quiet HEAD` exit 0 under both flags. `git ls-files -v` showed `h` for assume-unchanged and `S` for skip-worktree, while a restored normal entry showed `H`. This is a reproduced test bypass, not a production incident.
- **rootCauseOrUnknown:** Verified: `git diff` honors index change-suppression flags; the existing stage/mode/inventory guard did not inspect them.
- **failedApproach:** Treating clean HEAD/index/worktree diff alone as proof of unchanged live workflow bytes.
- **correction:** [`ad69f34e`](https://github.com/m-shogo/memories-project/commit/ad69f34e7d4c56f71de2078da6763281a9e7e54d) requires `git ls-files -v -z` to show exactly ordinary `H` entries matching the tracked workflow inventory. [`ac6563fd`](https://github.com/m-shogo/memories-project/commit/ac6563fd7f448a1dc0ac3465a8bc0b832c90c835) adds two real CLI hidden-flag negatives and a clean restoration positive. [`55c790d0`](https://github.com/m-shogo/memories-project/commit/55c790d07cb1ef11c2fac0e60da31990e9d58d6f) includes the two new negatives in the exact CLI count.
- **recurrenceGuard:** Both hidden flags must fail with exit 1, empty stdout and the exact `prewrite workflow Git index sparse or assume-unchanged flag` diagnostic even when `git diff` exits 0; resetting both flags must restore the positive direct-match result. Inventory parity also rejects missing/duplicated flag entries.
- **retryCondition:** Reconsider non-`H` index states only after explicit review of Git sparse checkout, assume-unchanged semantics, checkout authority and deterministic positive/negative proof. Do not retry unchanged external MinIO, workflow permission, large canonical learning transport or human approval blockers.

## Material success / bounded verification

- **outcome:** Reproduced both bypasses and clean restoration locally; the guard and two CLI negative fixtures were committed. Exact-source GitHub Actions completion was **not yet verified** when this append-only record was written.
- **evidence:** Local disposable Git fixture: `h`/diff exit 0, `S`/diff exit 0, restored `H`. Commits above contain the executable guard and test; no CI SUCCESS is inferred from local reproduction.
- **whySafe:** Read-only auditor and disposable negative tests only; no workflow YAML, production runtime, evidence registries or promotion authority changed.
- **reusableMechanism:** Bind HEAD/index/worktree parity to explicit Git index flag identity, not only staged mode and diff status.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged after each code/test write, including canonical learning `b809c69d`, mandatory contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/request/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/eligible generations 0/0, no approved recovery objective or human promotion.
- **limits / nextSafeTarget:** Verify exact-source CI and inspect Git environment index overrides independently. Direct trigger matching is not complete transitive CI reachability or write permission.
