# Supplemental OPS learning — generation-evidence atomic cleanup precedence (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** A secondary non-OSError during generation-evidence atomic temporary-file cleanup could replace the primary write-failure diagnostic.
- **evidence:** At `42154700`, `scripts/reconcile-memory-os-backup-restore-generation-evidence.py` wrapped `os.replace` OSError into domain `Fail`, but its `finally` cleanup suppressed only `OSError` and `FileNotFoundError`. A synthetic cleanup `ValueError` could mask the original failure. No actual production corruption or real cleanup fault was observed.
- **rootCauseOrUnknown:** Verified Python finally exception precedence and incomplete cleanup exception boundary. Ordinary OS unlink ValueError reachability outside synthetic fault injection is unknown.
- **failedApproach:** Treating OSError-only cleanup handling as preserving every active primary write exception.
- **correction:** [935ee432](https://github.com/m-shogo/memories-project/commit/935ee432071bac9aeeb8f3821c5b8a96bb22308d) preserves an active primary exception across ordinary cleanup faults, while standalone cleanup faults remain fail-closed.
- **recurrenceGuard:** Existing CI-reachable generation-evidence reconcile negative suite now uses a scoped isolated fixture, injects `os.replace` OSError and `os.unlink` ValueError, asserts the original fixed-class failure and private diagnostic precedence, checks fixture bytes/mode and all canonical authority bytes/modes, and cleans only newly created temporary files.
- **retryCondition:** Revisit only on reviewed generation-evidence atomic writer/rollback changes or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow write permission or missing human evidence.

## Material success and validation state

- **outcome:** Atomic code and negative fixture are committed together at `935ee432`; the guard is reachable through the existing generation-evidence reconcile-negative workflow.
- **evidence:** [Backup Restore Generation Evidence Rollback Diagnostics Negative #41330684763](https://github.com/m-shogo/memories-project/actions/runs/41330684763), [Backup Restore Unreadable Authority Negatives #41330684682](https://github.com/m-shogo/memories-project/actions/runs/41330684682), and [Backup Restore Generation Evidence #41330684743](https://github.com/m-shogo/memories-project/actions/runs/41330684743) completed SUCCESS on the code HEAD. The directly targeted [Generation Evidence Reconcile Negative #41330684695](https://github.com/m-shogo/memories-project/actions/runs/41330684695) was still running at record preparation; **no targeted negative-suite PASS is claimed yet**.
- **whySafe:** Only the existing reconciler and its existing synthetic negative suite changed. No protected production, generation, recovery objective, reviewed request, request-bound evidence, typed coverage or promotion authority was written.
- **reusableMechanism:** Capture the active primary exception before temporary cleanup and prove double-fault precedence with scoped synthetic cleanup and byte-exact canonical checks.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs remain unchanged: learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, recovery objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed registry `26bb1cc7`, promotion registry `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, approved recovery objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0 and final candidates 0. Preflight requires distinct unsuperseded semantically eligible environments plus a current explicitly human-approved recovery objective; reviewed drill requests are planning-only; new generation evidence must be current executable-request-bound; final candidates require typed eight-domain coverage and independent review; human production promotion is separate and nonautomatic.

## Next safe target

Finish exact-source targeted negative-suite classification, then audit other independent atomic-writer FD ownership and cleanup paths using their existing read-only negative suites. Never promote CI or learning to production readiness.
