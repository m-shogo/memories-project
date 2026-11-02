# Supplemental OPS learning — generation evidence publisher trigger topology guard (2026-11-02)

Append-only supplemental operational history under the canonical learning document and mandatory learning contract. Not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, objective, reviewed request, request-bound evidence, typed eight-domain non-resurrection, independent review, final candidate or human promotion evidence.

## Material failure — publisher-coupled code change

- **symptom:** A prior generation-evidence reconciler code/test change triggered a write-capable publisher as well as a read-only negative workflow. Reviewing only the read-only trigger was insufficient to classify the write surface.
- **evidence:** Publisher [#41382441848](https://github.com/m-shogo/memories-project/actions/runs/41382441848) ran and completed SUCCESS on `b31c59ac`; `.github/workflows/backup-restore-generation-evidence.yml` has `push.paths` containing `scripts/reconcile-memory-os-backup-restore-generation-evidence.py`, a `validate` job with `contents: write`, and a bounded source-reconciliation/push sequence.
- **rootCauseOrUnknown:** Verified pre-write trigger-topology review omission. No protected authority mutation was observed. Future publisher behavior under genuine external evidence is not inferred from this synthetic run.
- **failedApproach:** Assuming that the existence of an independent read-only CI trigger means a script change will not also activate a write-capable workflow.
- **correction:** [`1f5207cf`](https://github.com/m-shogo/memories-project/commit/1f5207cf3ca66e3bb1cec76b9e0a00e6ee89dfcd) adds an executable publisher-coupling check to the existing read-only generation-evidence reconcile workflow-negative suite; [`aa320d1e`](https://github.com/m-shogo/memories-project/commit/aa320d1ee4df08788cc5254f18e4a512a3844794) fixes its Python newline-escape fixture.
- **recurrenceGuard:** The read-only `scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py` now classifies the known publisher-coupled `push.paths`, requires bounded reconcile, latest-source check and guarded publication when write capability is present, injects two negative mutations, and accepts removal of the publisher trigger as a safe improvement. This is a scoped executable guard, not an exhaustive audit of every workflow in the repository.
- **retryCondition:** Revisit if publisher path triggers, write permission, bounded reconcile, source guard or read-only negative workflow changes. Do not repeat unchanged workflow permission failures or attempt an unreviewed publisher dispatch.

## Material failure — escaped newline fixture

- **symptom:** The first topology guard used doubly escaped `\\n` in its Python marker strings and failed to match the real YAML header.
- **evidence:** Exact-source [Reconcile Negative #41382850540](https://github.com/m-shogo/memories-project/actions/runs/41382850540) FAILED on `1f5207cf`; job `125077196193` printed `generation evidence publisher trigger topology unknown` and exited 1. The reviewed publisher header itself had not changed.
- **rootCauseOrUnknown:** Verified double escaping introduced during source construction; not a publisher YAML drift.
- **failedApproach:** Embedding JavaScript-escaped newline sequences into generated Python string literals without inspecting the resulting source before the first CI run.
- **correction:** `aa320d1e` replaced the double escapes with proper Python newline escapes; the resulting file was read back and the publisher header/token inventory checked.
- **recurrenceGuard:** Exact-source negative CI now exercises the actual YAML marker and two guard-removal mutations. Future generated Python source must be read back to confirm escape levels before interpreting CI failures as workflow drift.
- **retryCondition:** Retry only if string construction, YAML markers or source-generation transport changes; this particular corrected fixture has a terminal SUCCESS result.

## Material success

- **outcome:** [Generation Evidence Reconcile Negative #41382876223](https://github.com/m-shogo/memories-project/actions/runs/41382876223) completed **SUCCESS** on exact source `aa320d1ee4df08788cc5254f18e4a512a3844794`.
- **evidence:** Job `125077274188` logged `PASS: generation evidence publisher trigger coupling and bounded source guard (2 negatives)`, `Generation evidence reconcile negative suite PASS`, and `production decision: NO_GO`.
- **whySafe:** Only a read-only negative validator changed; its path is in the read-only reconcile-negative workflow trigger but not the write-capable generation-evidence publisher trigger. No workflow file or production authority was modified.
- **reusableMechanism:** Audit both publisher and read-only trigger lists, test source-guard removal, permit publisher decoupling, and prove the guard through exact-source CI.
- **protectedAuthorityCheck:** Starting `so` `c6bcdb85` and final code `aa320d1e` preserve canonical learning blob `b809c69d`, learning contract `87712ea9`, production status `d677a1c9`, OPS-P0-007 snapshot `dbaa36b0`, generation registry `bfd1b045`, approved objective registry `f4d74f33`, drill request registry `acebcd02`, generation evidence registry `ae7e57ef`, typed eight-domain registry `26bb1cc7`, and promotion registry `99cb895f`. `productionDecision=NO_GO`, OPS-P0-007=`PREREQUISITES_BLOCKED`; registered and semantically eligible distinct environments, current human-approved objective, executable reviewed request, request-bound evidence, typed coverage and final candidates remain zero. Human promotion remains separate/nonautomatic.

## Next safe target

Audit another CI-reachable, publisher-free negative suite's source/permission boundary. Do not expand generation-evidence publisher or writer-authority code while the scoped permission/trigger blocker remains unchanged.
