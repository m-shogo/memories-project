# Supplemental OPS learning — prestage pinned-parent close uncertainty (2026-11-01)

This append-only record follows `contracts/operations/autonomous-learning-system.json`. It is execution learning only, never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence. Canonical learning and production authorities are unchanged.

## Material failure: stage creation failure could be masked by a parent close failure

- **symptom:** The `atomic_write_bytes` stage-creation exception handler used an unguarded `os.close(parent_fd)` before re-raising. A separate close error could replace the original stage creation failure. No live production fault was observed.
- **evidence:** Code HEAD `b3d4b043` had `except BaseException: os.close(parent_fd); raise`. The new disposable proof forces a stage-creation error and independently injects both a pre-effect and post-effect parent descriptor close failure.
- **rootCauseOrUnknown:** Verified exception-masking risk from the unguarded cleanup close. A failed `os.close` does not establish whether the descriptor was consumed; that status is explicitly unknown without independent observation.
- **failedApproach:** Letting a secondary close replace the stage-creation error or retrying a descriptor close whose completion status is ambiguous.
- **correction:** [`a090eb8d`](https://github.com/m-shogo/memories-project/commit/a090eb8db516fa62b9875ad3ffc83852852decf8) captures the original `BaseException`, preserves it, and adds `prestage pinned parent descriptor close status unknown` when close fails, without retry. A stage-creation error is never converted into a successful write.
- **recurrenceGuard:** The existing CI-reached `prove_atomic_prestage_parent_swap` now exercises exact `before-prestage-close` and `after-prestage-close` cases against the actual pinned parent FD. It checks the primary error, bounded note, FD state, original authority bytes/mode, external canary and absence of staged residue. Canonical AST source binding and negative mutations reject missing injection, narrowed handler and removed second scenario. The entrypoint remains within its 4,096-line budget.
- **retryCondition:** Revisit only on changed stage-creation, parent-FD ownership, close behavior, Python exception notes, or reviewed proof topology. Never retry an ambiguous close without a new independently verified ownership precondition.

## Material success

- **outcome:** Both isolated pre- and post-close faults retain the original stage-creation error and do not mutate original or independent authority.
- **evidence:** [Autonomous Learning Guard #41236020284](https://github.com/m-shogo/memories-project/actions/runs/41236020284) and [Operability Contracts #41236020322](https://github.com/m-shogo/memories-project/actions/runs/41236020322) completed SUCCESS on exact code HEAD `a090eb8d`.
- **whySafe:** The fix changes only error preservation around a pre-publication cleanup close. Existing pinned-directory, no-follow, inode, rollback and publication checks remain intact; tests are disposable and never create production evidence.
- **reusableMechanism:** When a cleanup close can fail before or after its effect, retain the first error, attach a bounded uncertainty note and verify both fault orderings independently; do not infer leak freedom.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged after the code commit and prior append-only learning addition.

## Authority boundary, blockers, next safe target

`productionDecision=NO_GO` and OPS-P0-007=`PREREQUISITES_BLOCKED`; registered and semantically eligible environment generations remain 0/0. Preflight needs unsuperseded semantically eligible generations from distinct environments plus a current explicitly human-approved recovery objective. Reviewed drill requests are planning-only; new recovery evidence needs a current executable reviewed request; complete typed eight-domain non-resurrection coverage, independent review and separate non-automatic human promotion remain required.

The known Quay MinIO HTTP 401 blocks focused Upload Route Go/HTTP tests before they execute. Workflow-write permission, supplemental-learning-only Push/PR reachability and independent pre-MinIO Go execution remain scoped blockers; do not retry without changed conditions. This learning-only commit is not independent exact-source CI evidence.

**Next safe target:** Audit pinned `read_regular_bytes` final descriptor close against an independent primary read failure, using isolated before/after-close negative tests. Preserve the original read error and report uncertain close status without claiming leak-free completion.
