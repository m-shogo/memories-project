# Supplemental OPS learning — Git environment index substitution (2026-10-30)

Append-only supplemental learning under `contracts/operations/autonomous-learning-system.json`. Canonical learning authority remains blob-SHA verified, not full-text retrieved. **Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, typed eight-domain non-resurrection, independent-review or human-promotion evidence.**

## Material failure / alternate index authority

- **symptom:** An externally selected `GIT_INDEX_FILE` can make a Git checkout report a clean workflow index even while the checkout's actual default index has staged workflow changes. The checkout root may remain unchanged.
- **evidence:** In a disposable local Git repo, after staging `on: workflow_dispatch` and restoring the worktree to committed `on: push`, default `git diff --cached --quiet HEAD` exited 1; with `GIT_INDEX_FILE` pointed at a saved clean index it exited 0, as did the worktree diff. `git rev-parse --show-toplevel` still reported the same root. This is a controlled source-identity bypass, not a production incident.
- **rootCauseOrUnknown:** Verified: the Git subprocess inherited ambient Git checkout/index selection variables, so index stage/mode/flag/diff checks could all consult a different index authority.
- **failedApproach:** Trusting Git root equality and clean diff status without binding Git subprocesses to the actual checkout/index environment.
- **correction:** [`675d618f`](https://github.com/m-shogo/memories-project/commit/675d618f4bbafab9cd9a06dbca59142368752cb8) rejects ambient `GIT_INDEX_FILE`, `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_COMMON_DIR` in opt-in Git index identity mode. [`cf1fd51f`](https://github.com/m-shogo/memories-project/commit/cf1fd51f59dace8fda49d4f9ab723e3d8ae8549f) adds an alternate-index staged-drift bypass fixture plus exact CLI negatives for all four variables, with index restoration.
- **recurrenceGuard:** Actual default-index staged-drift setup must exit 1 while the alternate index exits 0; each of four inherited override variables must cause CLI exit 1, empty stdout and exact `prewrite Git environment checkout override requires review` diagnostic. No environment override is promoted to a reviewed source identity by an otherwise clean Git diff.
- **retryCondition:** Any legitimate Git worktree or alternate-index setup requires separately reviewed checkout-root/index ownership and deterministic CLI controls; do not weaken the guard to accommodate ambient overrides without explicit authority. Do not retry unchanged external MinIO, workflow-write permission, canonical-learning transfer or human approval blockers.

## Material success / bounded verification

- **outcome:** Local Git reproduction established the index-selection bypass, and the fail-closed guard plus four executable negative fixtures were committed. Exact-source GitHub Actions completion was **not yet verified** at record creation.
- **evidence:** Disposable local Git: default staged diff exit 1, alternate staged diff exit 0, alternate worktree diff exit 0, unchanged reported checkout root. Committed code and fixtures are linked above; CI success is not inferred from the reproduction.
- **whySafe:** Only read-only prewrite validation and disposable Git negative fixtures changed; no workflow YAML, production runtime, credential, traffic, backup/restore or promotion authority modified.
- **reusableMechanism:** Fail closed on inherited Git checkout/index environment overrides before asserting tracked source identity, even when root and HEAD checks appear correct.
- **protectedAuthorityCheck:** Ten protected blob SHAs unchanged, including canonical learning `b809c69d`, contract `87712ea9`, production status `55b3e639`, OPS-P0-007 snapshot `dbaa36b0` and six generation/objective/drill/evidence/non-resurrection/promotion registries. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/eligible generations 0/0, no current human-approved recovery objective or human production-promotion authority.
- **limits / nextSafeTarget:** Verify exact-source CI; audit optional Git fsmonitor execution and full Go/Python CI dependency closure independently. Direct workflow matching does not establish transitive CI reachability or write permission.
