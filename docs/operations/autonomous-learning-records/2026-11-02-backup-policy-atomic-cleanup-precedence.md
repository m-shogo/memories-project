# Supplemental OPS learning — backup policy atomic cleanup precedence (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or promotion evidence.

## Material failure — backup policy cleanup could mask primary write rejection

- **symptom:** The backup/restore policy reconciler's `atomic_write_bytes` could replace a primary atomic-write failure with a secondary `Path.unlink()` OSError during temporary cleanup.
- **evidence:** At `4cdd61e7`, `scripts/reconcile-memory-os-backup-restore.py` called `temp_path.unlink()` unguarded in a finally block after wrapping the primary write failure. This is the same verified exception-precedence risk already corrected in the two local backup/coherent reconcilers; no actual production status corruption or cleanup failure was observed.
- **rootCauseOrUnknown:** Verified Python finally exception precedence: a secondary cleanup OSError masks the original fixed-class write failure.
- **failedApproach:** Assuming unguarded cleanup cannot replace a primary atomic write/rollback diagnostic.
- **correction:** [`488366d3`](https://github.com/m-shogo/memories-project/commit/488366d3c54f86a8f3143ce83e01b0b2938af159) preserves the active primary ReconcileFailure across cleanup, while standalone cleanup errors remain fail-closed. The original production status remains unchanged on synthetic replacement failure.
- **recurrenceGuard:** The existing CI-reached `scripts/validate-memory-os-backup-restore-reconcile-negative.py` now injects both a primary `os.replace` OSError and a secondary temporary `Path.unlink` OSError, asserts the original fixed-class write failure, compares production-status bytes and cleans only newly created synthetic temp files.
- **retryCondition:** Revisit only on a reviewed atomic-writer cleanup/rollback change or exact-source negative-suite regression. Do not retry unchanged MinIO HTTP 401, workflow write permissions or missing human evidence.

## Material success — double-fault cleanup negative reached actual CI

- **outcome:** The backup policy reconciler preserves the primary atomic write failure under a synthetic secondary cleanup error, with protected status bytes unchanged.
- **evidence:** At exact code source `488366d3`, [Reconcile Backup Restore Policy #41326354900](https://github.com/m-shogo/memories-project/actions/runs/41326354900) completed its **Reconcile then validate status authority** step SUCCESS. Its logs explicitly report `atomic replacement cleanup failure precedence: enforced` and `Memory OS backup/restore policy reconcile negative suite PASS`. The subsequent bounded latest-source revalidation also logged both checks PASS. Independently, [Backup and Restore Contracts #41326354904](https://github.com/m-shogo/memories-project/actions/runs/41326354904) completed SUCCESS on the same code HEAD. The full reconcile workflow was CANCELLED, not SUCCESS.
- **whySafe:** Only the existing policy reconciler and existing synthetic negative suite changed; no protected production status, OPS-P0-007 snapshot, generation/objective/request/recovery/typed/promotion registry, reviewed workflow, credential or traffic authority was written.
- **reusableMechanism:** Preserve the primary exception across cleanup and prove it with a two-fault negative, byte-exact protected-authority check and scoped temporary-file cleanup.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remained unchanged after the code commit and the independent incident-control fixture update: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO` remains authoritative. OPS-P0-007 admission snapshot remains `PREREQUISITES_BLOCKED`, with registered/eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound evidence 0, complete typed eight-domain records 0 and final candidates 0. Preflight still requires unsuperseded semantically eligible generations from distinct environments and a current human-approved objective; reviewed requests are planning-only; complete typed eight-domain coverage and independent review remain mandatory; human promotion remains separate and nonautomatic.

## Material failure — full reconcile workflow cancelled after bounded latest-source recovery

- **symptom:** The exact-source Reconcile Backup Restore Policy workflow did not finish SUCCESS despite its initial and repeated negative-suite checks passing.
- **evidence:** [Run #41326354900](https://github.com/m-shogo/memories-project/actions/runs/41326354900) finished CANCELLED in the Commit reconciled status step. Its logs show that `origin/so` advanced from `488366d3` to `dec54980` because a separate Incident Control Exercise published two fixture updates, triggering the approved bounded latest-source revalidation. The revalidation logged the atomic cleanup negative PASS, then GitHub reported `The operation was canceled` at 2026-11-01 16:31:54 UTC. No status publication was observed.
- **rootCauseOrUnknown:** Verified concurrent source advancement; the direct reason GitHub cancelled the workflow is explicitly unknown. Do not conflate cancellation with an exit-75 source guard or a failed negative test.
- **failedApproach:** Treating a successful validation step as full workflow success, or retrying an unchanged cancellation/source-race path without new evidence.
- **correction:** Preserve the exact step-level PASS and full-run CANCELLED distinction; inspect the concurrent fixture-only commit and protected blob SHAs; leave production authorities unchanged.
- **recurrenceGuard:** Existing bounded latest-source reconcile and source identity checks remain intact; CI evidence is classified by exact source, step and full-run conclusion rather than promoted into readiness.
- **retryCondition:** Revisit only if a new independently approved execution path, a changed concurrency/source precondition, or actionable cancellation diagnostics become available. Do not rerun the unchanged workflow solely to turn a CANCELLED status green.

## Next safe target

Audit other local atomic-writer cleanup precedence and existing negative CI reachability without modifying reviewed workflows. Continue investigating approved source-bound pre-MinIO Focused Go Test options; never substitute learning or local synthetic tests for production evidence.
