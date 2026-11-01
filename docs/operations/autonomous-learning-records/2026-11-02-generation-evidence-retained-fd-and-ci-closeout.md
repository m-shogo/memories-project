# Supplemental OPS learning — generation-evidence retained FD and exact-source CI closeout (2026-11-02)

Append-only learning subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and `contracts/operations/autonomous-learning-system.json`. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed request, request-bound recovery evidence, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure — generation-evidence writer's untransferred FD

- **symptom:** The generation-evidence atomic writer could leak the temporary descriptor on `os.fchmod` or `os.fdopen` failure before stream ownership was established.
- **evidence:** At `547ad688`, `scripts/reconcile-memory-os-backup-restore-generation-evidence.py` called `os.fchmod(fd, ...)` and `os.fdopen(fd, ...)` without an outer raw-FD owner/close. No real production leak was observed.
- **rootCauseOrUnknown:** Verified missing explicit FD ownership for both pre-fdopen and fdopen-constructor failures. Actual production reachability is unknown.
- **failedApproach:** Assuming every exceptional stream-construction path closes an originally allocated `mkstemp` FD. The previously recorded unsafe post-handoff numeric reclose was explicitly not reused.
- **correction:** [735cadb1](https://github.com/m-shogo/memories-project/commit/735cadb13959ad3485a7ff2373e60afdbc96ab62) uses `os.fdopen(..., closefd=False)`, retains raw ownership, closes exactly once before replacement, and releases any retained descriptor in a bounded failure-path `finally`.
- **recurrenceGuard:** The existing CI-invoked generation-evidence reconcile negative suite now injects both `fchmod` and `fdopen` OSError, requires `closefd=False`, checks the captured descriptor is closed, verifies no temporary residue, and compares all canonical authority bytes/modes. Existing success-path atomic mode preservation remains.
- **retryCondition:** Revisit only if stream/FD ownership, Python closefd semantics, source-bound negative suite or reviewed atomic publication changes. Do not retry unchanged external MinIO 401, workflow permissions or missing human production evidence.

## Material success — exact-source negative CI

- **outcome:** The generation-evidence writer's pre-fdopen and fdopen-failure descriptor cleanup is exercised by existing read-only CI, with protected authority unchanged.
- **evidence:** [Backup Restore Generation Evidence Reconcile Negative #41331574284](https://github.com/m-shogo/memories-project/actions/runs/41331574284) completed **SUCCESS** on `735cadb1`. Logs explicitly report `generation-evidence fchmod/fdopen faults close retained raw descriptors`, `generation-evidence primary atomic failure survives secondary cleanup exception`, `atomic generation-evidence write preserves existing file mode` and `Generation evidence reconcile negative suite PASS`.
- **whySafe:** Only the existing generation-evidence reconciler and CI-reached isolated negative suite changed. No production status, reviewed request, generation/objective/evidence/typed/promotion registry, credential, traffic or reviewed workflow changed.
- **reusableMechanism:** Explicit `closefd=False` plus single raw-FD close before publication, with two constructor-boundary negative injections and byte-exact authority comparisons.
- **protectedAuthorityCheck:** Ten protected Git blob SHAs unchanged: canonical learning `b809c69d`, learning contract `87712ea9`, production status `b55ee4ad`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, objective registry `f4d74f33`, reviewed drill requests `acebcd02`, generation evidence `ae7e57ef`, typed eight-domain registry `26bb1cc7`, promotion review `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007 `PREREQUISITES_BLOCKED`, registered/semantically eligible generations 0/0, approved objectives 0, executable reviewed requests 0, request-bound recovery evidence 0, complete typed eight-domain coverage 0, final candidates 0. Preflight requires distinct unsuperseded semantically eligible environments and current explicit human objective approval; reviewed drill requests are planning only, generation recovery evidence remains current executable-request-bound, final candidates need typed eight-domain coverage and independent review, and human promotion is separate/nonautomatic.

## Earlier pending CI outcomes now observed

- **Generation-evidence atomic cleanup:** [Reconcile Negative #41330684695](https://github.com/m-shogo/memories-project/actions/runs/41330684695) completed **SUCCESS** on `935ee432`. Logs show `generation-evidence primary atomic failure survives secondary cleanup exception` and full reconcile negative suite PASS. This closes the explicitly pending exact-source result in `2026-11-02-generation-evidence-atomic-cleanup-precedence.md` without editing that historical record.
- **Generation-status FD ownership:** [Generation Binding Readonly #41331301602](https://github.com/m-shogo/memories-project/actions/runs/41331301602) and [Generation Binding #41331300960](https://github.com/m-shogo/memories-project/actions/runs/41331300960) both completed **SUCCESS** on `681a8006`. The read-only log explicitly reports `generation-status fdopen failure closes untransferred descriptor`, byte/mode-preserving reconciliation and no production decision change. This closes the pending CI state in the earlier generation-status FD learning without editing it.

## Next safe target

Audit promotion-review atomic writer's pre-fdopen ownership with its already CI-reached isolated negative suite; preserve separate human promotion and all OPS-P0-007 gates. Learning remains non-production evidence.
