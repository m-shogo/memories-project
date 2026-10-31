# Supplemental OPS learning — final pinned-parent close uncertainty (2026-11-01)

This append-only record is execution learning under `contracts/operations/autonomous-learning-system.json`. It is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, generation-bound recovery evidence, typed eight-domain non-resurrection, independent review, final recovery candidate, or human promotion evidence.

## Material failure class — final parent FD close could mask primary publication failure

- **symptom:** The final pinned-parent `os.close(parent_fd)` in `atomic_write_bytes` was unguarded inside a `finally` block. An independently failing close could replace the original publication error. No live production FD leak or corruption was observed.
- **evidence:** The `6322ed59` source had a direct `os.close(parent_fd)` after cleanup. A deterministic disposable proof now faults this close both before and after actually consuming the descriptor while a synthetic primary `os.replace` error is active.
- **rootCauseOrUnknown:** Verified exception masking in the unguarded cleanup path. After an `os.close` error, whether the FD was consumed is explicitly unknown without independent observation; a retry may close a reused descriptor.
- **failedApproach:** Treating a close exception as proof that the FD remains open, or allowing it to replace the primary publication failure.
- **correction:** [`1a17a4cf`](https://github.com/m-shogo/memories-project/commit/1a17a4cfe342141299af2358f36e2d15d205a183) preserves the active primary exception and adds a bounded `pinned parent descriptor close status unknown` diagnostic. It does not retry an ambiguously completed close. A close error with no primary exception remains an error.
- **recurrenceGuard:** The existing CI-reached Upload Route disposable negative now tests `before-close` and `after-close` against the actual pinned parent FD. It verifies original authority bytes/mode, independent canary, exact primary exception, uncertainty note, and observed FD state, reclaiming a still-open test FD only after restoring injected faults. The canonical entrypoint binds the exact two-case AST loop and rejects mutations that disable the close fault or narrow the exception handler.
- **retryCondition:** Revisit when parent capability ownership, close behavior, stage guard FD cleanup, Python exception notes, or reviewed AST proof topology changes. Never retry an ambiguous close without a verified safe ownership precondition.

## Material success — bounded diagnostics without weakening authority

- **outcome:** The final parent close fault no longer masks the primary publication error in the two isolated failure modes, and the executable proof is reached through the existing pre-MinIO validation path.
- **evidence:** [Autonomous Learning Guard #41234874415](https://github.com/m-shogo/memories-project/actions/runs/41234874415) and [Operability Contracts #41234874451](https://github.com/m-shogo/memories-project/actions/runs/41234874451) both completed SUCCESS on exact code HEAD `1a17a4cf`. The guard includes 601 canonical fail-closed cases, 52 source-negative workflows, 63 direct Python commands, 204 source-negative fixtures, 195 fanout synthetics and 1,186 helper-ancestor mutations.
- **whySafe:** The original no-follow, pinned-parent, inode and rollback checks remain intact. Synthetic failures run only against disposable local files, and no external canary is mutated. No production-equivalent environment, recovery objective, drill request, recovery evidence, credential, traffic, readiness or promotion was fabricated.
- **reusableMechanism:** For an ambiguously completed descriptor close, preserve the original failure, report uncertainty rather than claiming closure, and test before/after syscall-effect cases independently. Do not infer leak freedom from a successful exception classification.
- **protectedAuthorityCheck:** All ten protected Git blob SHAs remained unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation recovery evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, human promotion `99cb895f`.

## Remaining limits and next safe target

`productionDecision=NO_GO`; OPS-P0-007 is `PREREQUISITES_BLOCKED`. Registered and semantically eligible generations remain 0/0. Preflight still requires unsuperseded semantically eligible generations from distinct environments and an explicitly human-approved current objective. Reviewed drill requests are planning authority only, new generation recovery evidence requires a current executable reviewed request, final candidates require complete typed eight-domain non-resurrection coverage and independent review, and human production promotion remains separate and non-automatic.

The known [Upload Route #41234874456](https://github.com/m-shogo/memories-project/actions/runs/41234874456) failed at the MinIO startup step before focused Go/HTTP tests. No Go success is claimed. Workflow-write permission, supplemental-learning-only Push/PR CI reachability and independent pre-MinIO focused Go execution remain scoped blockers; do not retry without changed preconditions. The learning-only HEAD has no independently observed exact-source CI SUCCESS.

**Next safe target:** Audit staged guard FD and untransferred stage FD final close failure ordering. Any correction must preserve the original error, avoid unsafe close retries, and independently test both pre- and post-close faults without claiming leak-free cleanup where ownership cannot be established.
