# Supplemental OPS learning — recovery objective non-OSError atomic cleanup (2026-11-02)

Append-only record under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is learning only; it is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, registered/eligible environment generation, approved objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** Recovery-objective atomic writer cleanup caught `OSError` only. A secondary `ValueError` from closing a temporary descriptor or `TypeError` from unlinking a temporary file could replace the primary private atomic-write failure.
- **evidence:** On source HEAD `95259d084dbed9bae4afd3dfd9b0629c810c050a`, `scripts/reconcile-memory-os-recovery-objectives.py::write_text` had `except OSError` at both cleanup sites. The previous [atomic primary cleanup lesson](https://github.com/m-shogo/memories-project/blob/so/docs/operations/autonomous-learning-records/2026-11-02-recovery-objectives-atomic-primary-cleanup-precedence.md) covered only `OSError` double faults. No real production cleanup failure was observed.
- **rootCauseOrUnknown:** Verified source-level exception-class gap in the cleanup handlers. Whether a real runtime encountered malformed close/unlink exceptions is unknown.
- **failedApproach:** Relying on `except OSError` alone to preserve primary error precedence for all cleanup failures.
- **correction:** [`bc6a06bf`](https://github.com/m-shogo/memories-project/commit/bc6a06bfa2fd08507a8695ff014acc454db3ace9) handles `OSError`, `ValueError` and `TypeError` in both cleanup sites without changing the primary exception precedence. [`6445122f`](https://github.com/m-shogo/memories-project/commit/6445122f926b6e8ea210d776cceb4575951ae810) adds synthetic unlink-`TypeError` and close-`ValueError` double-fault negatives with temporary residue cleanup.
- **recurrenceGuard:** The existing read-only, exact-source `recovery-objectives-reconcile-negative.yml` runs `prove_atomic_non_oserror_cleanup_precedence`. It requires the primary private atomic-write failure class, suppression of canary diagnostics, fixture byte/mode identity and no final temporary residue.
- **retryCondition:** Revisit if atomic writer exception handling or the negative suite changes, or if a newly observed cleanup class appears. Do not retry unchanged MinIO HTTP 401, workflow-write permission, canonical 4.17 MiB learning transport or absent human evidence blockers.

## Material success

- **outcome:** Exact-source [Recovery Objectives Reconcile Negative #41376551600](https://github.com/m-shogo/memories-project/actions/runs/41376551600) completed **SUCCESS** on test HEAD `6445122f926b6e8ea210d776cceb4575951ae810`. [Recovery Objectives Admission #41376551616](https://github.com/m-shogo/memories-project/actions/runs/41376551616) also completed **SUCCESS** on that HEAD. Code-only [Reconcile Negative #41376523698](https://github.com/m-shogo/memories-project/actions/runs/41376523698) completed **SUCCESS** on `bc6a06bf`.
- **evidence:** GitHub Actions workflow-run conclusion/status, not a local execution claim; CI workflow statically invokes the negative script. No assertion is made here about a log line not independently read.
- **whySafe:** Only the cleanup exception-class boundary and a disposable synthetic negative fixture changed; no production, objective, generation, recovery or promotion authority was intentionally written.
- **reusableMechanism:** Pair primary-error precedence with two-fault tests for non-`OSError` cleanup exceptions and verify that fixture bytes, mode and cleanup residue remain stable.
- **protectedAuthorityCheck:** Immediately after the code/test commits, GitHub `contracts/operations` listing confirmed unchanged Git blob prefixes for production status `d677a1c9`, OPS-P0-007 admission snapshot `dbaa36b0`, environment generations `bfd1b045`, approved objectives `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, human promotion review `99cb895f`, objectives admission contract `be0b4604` and autonomous learning contract `87712ea9`. Production remains `NO_GO`; registered vs unsuperseded semantically eligible distinct environments, current explicitly human-approved recovery objective, executable reviewed request, request-bound evidence, complete typed eight-domain coverage, independent review and separate nonautomatic human promotion remain mandatory.

## Next safe target

Add a deterministic pre-write authority target mode/inode guard and negative controls in the same read-only CI path; then separately address the still-open parent-directory swap at the atomic replacement boundary without relying on path-only checks.
