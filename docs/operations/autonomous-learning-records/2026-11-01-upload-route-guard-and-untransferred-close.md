# Supplemental OPS learning — staged guard and untransferred descriptor close uncertainty (2026-11-01)

Append-only execution learning under `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, generation-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate, or human promotion evidence. The canonical learning authority remains unchanged.

## Material failure class A — staged guard FD close could mask a primary publication error

- **symptom:** The final `os.close(staging_guard_fd)` was unguarded. A close failure could replace the original `os.replace` failure; no live production corruption or leak was observed.
- **evidence:** Prior source `1a17a4cf` closed the guard FD directly in a nested `finally`. A disposable test now injects an independent close failure both before and after the actual descriptor close, while a synthetic primary publication error is active.
- **rootCauseOrUnknown:** Verified exception masking from unguarded cleanup. Whether an errored close consumed the descriptor is explicitly unknown without separate observation.
- **failedApproach:** Assuming a failed `close` means the FD is still open, retrying an ambiguous close, or replacing the primary failure with a cleanup exception.
- **correction:** [`e385f4c2`](https://github.com/m-shogo/memories-project/commit/e385f4c2d198a2faee6010d8882e28675b14da46) preserves the original failure, adds a bounded `staged guard descriptor close status unknown` note, and never retries an ambiguous close. An isolated close error without an earlier primary failure still raises.
- **recurrenceGuard:** The existing CI-reached disposable `prove_atomic_initial_fstat_failure_cleanup` proof tests exact before/after-close cases, checks the primary error and note, independently observes FD state, and preserves authority bytes/mode and an external canary. The canonical AST binding and source-negative mutation reject removal of the loop, close injection or exception guard.
- **retryCondition:** Revisit only if stage guard ownership, close semantics, Python exception-note support or the reviewed CI proof topology changes.
- **outcome:** Primary publication errors are retained in both isolated staged-guard close fault modes.
- **success evidence:** [Autonomous Learning Guard #41235254115](https://github.com/m-shogo/memories-project/actions/runs/41235254115) and [Operability Contracts #41235254130](https://github.com/m-shogo/memories-project/actions/runs/41235254130) completed SUCCESS on exact code HEAD `e385f4c2`.
- **whySafe:** Descriptor-relative staging, no-follow and rollback checks remain in place; faults are confined to disposable files and no production evidence or approval is generated.
- **reusableMechanism:** Preserve the first failure and report bounded cleanup uncertainty rather than treating an ambiguous close as evidence of successful or failed closure.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged.

## Material failure class B — untransferred staged FD close could mask initial fstat failure

- **symptom:** If the first staged `fstat` fails before `fdopen` takes ownership, the final untransferred FD close could independently fail and mask that primary error. This was a verified source-path gap, not an observed live production fault.
- **evidence:** The previous `e385f4c2` source had a direct `os.close(untransferred_stage_fd)` in the outermost `finally`. Disposable tests now fail the initial staged `fstat` and then fail the final close both before and after its actual syscall effect.
- **rootCauseOrUnknown:** Verified unguarded close masking risk; after an error the close completion status remains unknown without independent observation.
- **failedApproach:** Relying on a nested `finally` to preserve the primary exception or blindly retrying the close.
- **correction:** [`b3d4b043`](https://github.com/m-shogo/memories-project/commit/b3d4b043ff1e91d5b8748cfeb1a87aafc0d0c32e) retains the initial `fstat` error and adds `untransferred stage descriptor close status unknown` without retrying. A standalone close error remains an error.
- **recurrenceGuard:** The existing pre-MinIO disposable negative tests `before-stage-close` and `after-stage-close`, exact original exception, uncertainty note, FD state and external canary preservation. AST source binding and source-negative mutations reject a missing scenario or narrowed exception handling; the entrypoint remains within the 4,096-line budget.
- **retryCondition:** Revisit if `fstat` recovery, `fdopen` transfer, descriptor ownership, close behavior or proof topology changes.
- **outcome:** Both synthetic untransferred close modes retain the original staged `fstat` failure without mutating the original authority or canary.
- **success evidence:** [Autonomous Learning Guard #41235637631](https://github.com/m-shogo/memories-project/actions/runs/41235637631) and [Operability Contracts #41235637676](https://github.com/m-shogo/memories-project/actions/runs/41235637676) completed SUCCESS on exact code HEAD `b3d4b043`. These checks are not production recovery evidence.
- **whySafe:** All tests use isolated temporary files; the original stage identity is never inferred from an unverified pathname, and ambiguous close is not retried.
- **reusableMechanism:** Track descriptor ownership across transfer boundaries; inject both pre-effect and post-effect close faults and verify the original failure independently.
- **protectedAuthorityCheck:** All ten protected authority blob SHAs remained unchanged after the code change.

## Authority boundary, scoped blockers and next safe target

`productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED` with registered/semantically eligible generations 0/0. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current recovery objective. Reviewed drill requests are planning-only; new recovery evidence requires a current executable reviewed request. Final candidates require complete typed eight-domain non-resurrection coverage and independent review. Human promotion remains separate and non-automatic.

Known Quay MinIO startup HTTP 401 prevents the Upload Route workflow from reaching focused Go/HTTP tests. Workflow-write permission, supplemental-learning-only Push/PR CI reachability, and independent pre-MinIO Go execution remain unchanged blockers; do not retry them without changed preconditions. This learning-only commit does not establish independent exact-source CI success.

**Next safe target:** Verify the pinned parent descriptor close when stage creation fails before a stage FD is returned. Test both pre- and post-close faults, preserving the primary stage error and explicitly distinguishing uncertain FD status.
