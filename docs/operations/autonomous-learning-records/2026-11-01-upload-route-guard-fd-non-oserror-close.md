# Supplemental OPS learning — non-OSError staged guard FD close (2026-11-01)

This append-only execution learning follows `contracts/operations/autonomous-learning-system.json`. It is never production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** A `ValueError` from final staged guard-FD cleanup could mask an already active primary publication error. No live production incident was observed.
- **evidence:** Before [`600bcc1c`](https://github.com/m-shogo/memories-project/commit/600bcc1cf65c244529f6a634e562b4e39e559104), `atomic_write_bytes` caught only `OSError` from `os.close(staging_guard_fd)`. Its disposable proof covered only `before-guard-close` and `after-guard-close` OSError cases, and the source-negative guard was likewise bound to that limited handler.
- **rootCauseOrUnknown:** Verified ordinary-exception coverage gap: non-OSError cleanup faults bypassed the original-error preservation handler. A post-effect close error does not independently prove whether the FD was consumed.
- **failedApproach:** Treating OSError-only close-fault coverage as sufficient, or changing runtime without updating the existing exact-source negative and four-case loop bindings.
- **correction:** [`600bcc1c`](https://github.com/m-shogo/memories-project/commit/600bcc1cf65c244529f6a634e562b4e39e559104) catches ordinary `Exception` around guard close and retains the primary failure. [`f6451f4e`](https://github.com/m-shogo/memories-project/commit/f6451f4e4b366c078cfd09f0db5d44472dedd4f2) adds before/after-effect ValueError faults and checks. [`920e5785`](https://github.com/m-shogo/memories-project/commit/920e578594b398e0660a5272701e04e6bc6fd3f9) binds the four cases, ValueError injection, uncertainty diagnostic and handler to existing AST/source-negative CI.
- **recurrenceGuard:** CI-reached `prove_atomic_initial_fstat_failure_cleanup` now tests four actual staged guard close outcomes, original publication error, typed uncertainty note, independently observed FD state, unchanged original bytes/mode and external canary. Negative mutations reject a truncated scenario loop, removed ValueError injection or handler narrowed back to `OSError`. The CI entrypoint remains 4,096 lines.
- **retryCondition:** Revisit only if staged guard ownership, publication/close behavior, exception notes or proof/source-negative topology changes; never retry a close with unknown completion.

## Material success

- **outcome:** Exact-source independent CI succeeded on the hardened staged guard close code and tests.
- **evidence:** [Autonomous Learning Guard #41259522564](https://github.com/m-shogo/memories-project/actions/runs/41259522564) and [Operability Contracts #41259522548](https://github.com/m-shogo/memories-project/actions/runs/41259522548) completed SUCCESS on exact code HEAD `920e5785`.
- **whySafe:** This change preserves the active publication error and avoids a second close. Existing no-follow, pinned-parent, staging, rollback and publication controls are unchanged; isolated canary tests cannot become operational evidence.
- **reusableMechanism:** Pair a primary publication fault with pre/post-effect secondary cleanup faults of different ordinary exception types and enforce both runtime behavior and source-negative reachability.
- **protectedAuthorityCheck:** Nine protected production/recovery contract/registry blobs and the separate canonical learning blob remained unchanged on independent re-read. Production Status remains `productionDecision=NO_GO`; OPS-P0-007 remains `PREREQUISITES_BLOCKED`. Registered and semantically eligible generations remain distinct (0/0); preflight needs unsuperseded eligible generations from distinct environments plus an explicitly human-approved current recovery objective. Reviewed requests are planning-only, recovery evidence requires a current executable reviewed request, typed eight-domain non-resurrection and independent review are mandatory, and human promotion remains separate/non-automatic.

## Scoped blockers and next target

Quay MinIO HTTP 401, reviewed workflow-write permission, supplemental-learning-only CI reachability and independent Pre-MinIO Go execution remain unchanged blockers. Do not retry without changed preconditions. Next validate the analogous untransferred staged FD close across ordinary non-OSError faults; preserve original failure, FD ownership and external canary.
