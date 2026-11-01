# Supplemental OPS learning — preflight primary atomic failure survives cleanup (2026-11-02)

Append-only operational learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. This is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, objective, reviewed request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure

- **symptom:** A secondary cleanup failure could mask the preflight reconciler's primary fixed-class atomic-write rejection.
- **evidence:** At `2f162ecc`, `scripts/reconcile-memory-os-backup-restore-drill-preflight.py` wrapped `os.replace` OSError into `Fail("preflight reconcile atomic write failed")`, but unconditionally raised `Fail("preflight reconcile atomic cleanup failed")` in `finally` when a descriptor close or temporary unlink raised OSError. No actual production corruption or real cleanup failure was observed.
- **rootCauseOrUnknown:** Verified Python finally exception precedence; real-world occurrence remains unknown.
- **failedApproach:** Always elevating secondary cleanup errors above an already-active primary atomic-write failure.
- **correction:** [e54d3e69](https://github.com/m-shogo/memories-project/commit/e54d3e6983e90d19aff59b4a382dad966fd8d2f1) preserves the original fixed-class write failure across secondary cleanup OSError. Standalone cleanup failure remains fail-closed, and orphan private temp files remain subject to existing clean-source/rollback checks.
- **recurrenceGuard:** Existing CI-reached preflight reconcile negative suite injects primary `os.replace` OSError and secondary `os.unlink` OSError in a scoped fixture; it asserts the original private-safe `Fail`, checks cleanup was attempted, compares fixture bytes/mode and canonical preflight/status bytes/modes, and removes only new synthetic temporary files.
- **retryCondition:** Revisit only after reviewed preflight atomic writer/rollback changes or exact-source CI regression. Do not retry unchanged MinIO HTTP 401, workflow write permissions, external production evidence or human promotion blockers.

## Material success

- **outcome:** The preflight atomic double-fault negative preserves primary diagnostic priority while leaving all protected authorities unchanged.
- **evidence:** [Backup Restore Drill Preflight Reconcile Negative #41332257672](https://github.com/m-shogo/memories-project/actions/runs/41332257672) completed **SUCCESS** at exact code HEAD `e54d3e69`; logs explicitly report `preflight primary atomic failure survives secondary cleanup OSError`, second-replace rollback without temp files, upstream validator order and full preflight reconcile negative suite PASS. [Backup Restore Drill Preflight #41332257663](https://github.com/m-shogo/memories-project/actions/runs/41332257663) also completed **SUCCESS** on the same code HEAD.
- **whySafe:** Only the existing preflight reconciler and its CI-invoked synthetic negative suite changed. No production status, OPS-P0-007 snapshot, generation/objective/request/recovery/typed/promotion registry, credential, traffic or reviewed workflow was modified.
- **reusableMechanism:** Preserve active primary exception across finally cleanup, test two injected faults with a bounded isolated fixture and verify canonical authority byte/mode identity.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`; OPS-P0-007 `PREREQUISITES_BLOCKED`; registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0 and final candidates 0. Preflight requires distinct unsuperseded semantically eligible environments and an explicitly human-approved current recovery objective; reviewed requests are planning-only, new generation recovery evidence remains bound to a current executable reviewed request, final candidates need complete typed eight-domain coverage and independent review, and human promotion remains separate/nonautomatic.

## Prior publisher CI closeout

[Backup Restore Drill Request Admission #41332053180](https://github.com/m-shogo/memories-project/actions/runs/41332053180) completed **SUCCESS** on code HEAD `2104d357`, closing the pending publisher classification in the append-only drill-request cleanup record without editing it. This is not evidence of an approved drill, restore, production traffic or readiness.

## Next safe target

Audit promotion-review and generation-status atomic cleanup precedence with existing CI-reached negatives; preserve all OPS-P0-007 and separate human-promotion gates.
