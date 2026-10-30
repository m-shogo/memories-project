# Supplemental OPS learning — staged-only Git workflow index drift (2026-10-30)

Append-only supplemental learning governed by `contracts/operations/autonomous-learning-system.json`. Canonical `docs/operations/AUTONOMOUS-OPS-LEARNING.md` is blob-SHA verified; its large-blob text transport remains unavailable. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / index-versus-worktree ambiguity

- **symptom:** A Git workflow source can match committed HEAD in the working tree while its staged index blob differs. A worktree-only content check would miss that source-identity drift.
- **evidence:** The initial optional Git index guard included separate HEAD/worktree and HEAD/index checks, but the disposable fixtures only exercised a dirty working tree, untracked file and missing `.git`. The staged-only case was not yet executable as a regression control. This is a static testing gap, not an observed production incident.
- **rootCauseOrUnknown:** Verified missing negative fixture for an index change with the working tree restored to HEAD.
- **failedApproach:** Treating a clean working tree as sufficient proof of a clean staged Git workflow index.
- **correction:** [`f58fbeb5`](https://github.com/m-shogo/memories-project/commit/f58fbeb5db70d6a93c7847f12436947281e65a31) stages a modified workflow, restores its worktree bytes to HEAD and requires the optional Git index guard to reject it. [`80007c92`](https://github.com/m-shogo/memories-project/commit/80007c92a4f2c328d81774693dc982eb88777b0b) adds the exact-diagnostic real CLI negative.
- **recurrenceGuard:** One additional disposable Git synthetic and one exact CLI negative require `prewrite workflow Git index content drift` with exit 1 and empty stdout; the test resets the staged index before subsequent cases. Fail-closed negatives **498 → 499**, fanout synthetic **189 → 190**.
- **retryCondition:** Any staged workflow change requires reviewed HEAD/index/worktree reconciliation and new positive/negative tests. Do not weaken staged-index checks to accommodate an unreviewed dirty checkout or retry unchanged external MinIO, workflow permission, canonical-learning transfer or human promotion blockers.

## Material success / protected authority

- **outcome:** Exact-source [Autonomous Learning Guard #41015240504](https://github.com/m-shogo/memories-project/actions/runs/41015240504) completed **SUCCESS** for `80007c92a4f2c328d81774693dc982eb88777b0b`.
- **evidence:** CI logs show append-only PASS, learning contract PASS, **499** fail-closed negatives, **190** fanout synthetic cases, **1,186** helper-ancestor negative mutations, entry-document PASS and read-only completion.
- **whySafe:** Only disposable Git fixture tests in the read-only auditor and CI-reachable negative validator changed. No workflow YAML, production runtime, credentials, traffic, recovery evidence, readiness, generation/objective or promotion authority changed.
- **reusableMechanism:** Independently compare committed HEAD to both the working tree and staged index; prove staged-only drift rejection with a deterministic Git fixture rather than a generic dirty-worktree test.
- **protectedAuthorityCheck:** Ten protected authority blobs matched run-start `7d2a0617`, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0`, and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no human recovery/promotion authority.
- **limits / nextSafeTarget:** The optional index guard does not establish full transitive CI coverage or Go-only Upload Route validation. Verify real checkout strict+index parity and investigate Git index stage/mode negatives separately.
