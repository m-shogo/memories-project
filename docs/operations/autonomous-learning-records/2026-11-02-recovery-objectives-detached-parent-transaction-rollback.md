# Supplemental OPS learning — recovery objective detached-parent transaction rollback (2026-11-02)

Append-only operational learning subordinate to the canonical history and mandatory autonomous-learning contract. It does not satisfy any production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion gate.

## Material failure

- **symptom:** A directory swap inside an atomic replacement can leave the updated reviewed inode in a moved parent while the public pathname points elsewhere. A subsequent transaction rollback cannot be reported as completed when that pathname remains detached.
- **evidence:** Source-level inspection of `scripts/reconcile-memory-os-recovery-objectives.py::main` shows it catches the postcommit `Fail`, attempts `restore_original_text`, and reports `rollback incomplete` if restoration fails. The new synthetic negative injects a parent swap inside the first real FD-relative replacement; the original pathname is then a symlink to an isolated canary directory.
- **rootCauseOrUnknown:** Verified a rename race can detach the original parent after the precommit visibility check. No real adversarial swap or production corruption was observed. Complete prevention of adversarial rename races is unknown.
- **failedApproach:** Treating successful `os.replace` alone, or an attempted rollback, as proof of successful publication or complete rollback.
- **correction:** [`ad36ff49`](https://github.com/m-shogo/memories-project/commit/ad36ff493acd69ddecbdd618a0aed475b2c96820) adds a transaction-level negative asserting exact `recovery objective reconcile transaction failed (Fail); rollback incomplete`, no canary mutation, and synthetic fixture restoration. Existing FD-bound stage/replace/cleanup and postcommit visibility rejection remain intact.
- **recurrenceGuard:** Exact-source `recovery-objectives-reconcile-negative.yml` executes `prove_transaction_detached_parent_rollback_incomplete` on `so` code/test changes; it refuses any false rollback-completed result.
- **retryCondition:** Revisit when parent visibility, `main` rollback, transactional diagnostic or read-only CI behavior changes. Do not retry unchanged canonical 4MB blob transport, Quay MinIO 401, workflow permissions, or missing human approvals.

## Material success

- **outcome:** [Recovery Objectives Reconcile Negative #41382315657](https://github.com/m-shogo/memories-project/actions/runs/41382315657) completed **SUCCESS** on exact source `ad36ff493acd69ddecbdd618a0aed475b2c96820`. [Recovery Objectives Admission #41382315700](https://github.com/m-shogo/memories-project/actions/runs/41382315700) also completed **SUCCESS** on the same source.
- **evidence:** Targeted negative workflow completed/success after the new test was added; no production promotion was performed.
- **whySafe:** Test operates only on isolated synthetic copies and restores the original fixture bytes. It never supplies a recovery generation, objective, reviewed request, typed domain record or production decision.
- **reusableMechanism:** Pair postcommit parent-visibility rejection with a caller-level rollback-incomplete negative, verifying both the protected canary and the error classification.
- **protectedAuthorityCheck:** Compared `so` initial `c6bcdb85` to `ad36ff49`; production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion registry `99cb895f`, learning contract `87712ea9` are unchanged. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; all prerequisite generation, objective, request, recovery, typed coverage and candidate counts remain zero. Human promotion remains separate and nonautomatic.

## Next safe target

Audit generation-evidence reconciliation's existing authority target and temporary-file identity guards through its independent read-only negative workflow. Keep the Generation Evidence Writer Authority publisher-trigger blocker scoped until a safe independent CI path exists.
